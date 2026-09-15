import os
import re
import sys
from typing import Any, Dict, List, Optional

# Locate and import naagmani Python HDK
current_dir = os.path.dirname(os.path.abspath(__file__))
search_dirs = [
    os.path.join(current_dir, "..", "..", "hdk", "python"),
    os.path.join(current_dir, "..", "hdk", "python"),
    os.path.join(current_dir, "hdk", "python"),
]
for d in search_dirs:
    if os.path.isdir(d):
        sys.path.insert(0, os.path.abspath(d))
        break

from naagmani import Plugin, Result

plugin = Plugin(
    name="rag",
    version="1.0.0",
    description="Naagmani Retrieval-Augmented Generation (RAG) & Knowledge Plugin",
    author="Naagmani Knowledge Team",
    capabilities=["knowledge.rag", "knowledge.retrieval"],
)

# ----------------------------------------------------------------------
# In-memory Tenant-Scoped Knowledge Store
# ----------------------------------------------------------------------

class Chunk:
    def __init__(self, chunk_id: str, document_id: str, title: str, content: str, metadata: Dict[str, Any]):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.title = title
        self.content = content
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
        }

# Maps tenant_id -> List[Chunk]
_tenant_chunks: Dict[str, List[Chunk]] = {}

# Default seed knowledge pre-populated for test/default tenants
DEFAULT_REFUND_DOC = (
    "Naagmani Enterprise Refund Policy: Customers are eligible for a 100% full refund "
    "within 30 days of purchase by submitting a support ticket to the billing desk. "
    "All subscriptions include a 14-day grace period."
)

def _get_tenant_id(ctx: Any) -> str:
    if hasattr(ctx, "org_id") and ctx.org_id:
        return ctx.org_id
    if hasattr(ctx, "tenant") and isinstance(ctx.tenant, dict):
        return ctx.tenant.get("organization_id", "default")
    return "default"

def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text)]

def chunk_text(content: str, max_chunk_size: int = 300) -> List[str]:
    # Split by paragraphs or sentences
    paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) + 1 <= max_chunk_size:
            current = (current + " " + p).strip()
        else:
            if current:
                chunks.append(current)
            current = p
    if current:
        chunks.append(current)
    if not chunks and content:
        chunks.append(content)
    return chunks

def ingest_document(tenant_id: str, doc_id: str, title: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
    if tenant_id not in _tenant_chunks:
        _tenant_chunks[tenant_id] = []
    
    meta = metadata or {}
    text_chunks = chunk_text(content)
    created_chunks = []
    for idx, text in enumerate(text_chunks):
        cid = f"{doc_id}-chunk-{idx + 1}"
        c = Chunk(cid, doc_id, title, text, meta)
        _tenant_chunks[tenant_id].append(c)
        created_chunks.append(c)
    
    sys.stderr.write(f"[rag] ingested document {doc_id} ({len(created_chunks)} chunks) for tenant {tenant_id}\n")
    sys.stderr.flush()
    return created_chunks

def retrieve_chunks(tenant_id: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    chunks = _tenant_chunks.get(tenant_id, [])
    if not chunks and tenant_id in ("default", ""):
        # Pre-seed default tenant
        ingest_document("default", "doc-refund-01", "Refund Policy", DEFAULT_REFUND_DOC)
        chunks = _tenant_chunks.get("default", [])

    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return []

    scored: List[tuple] = []
    for c in chunks:
        c_tokens = _tokenize(c.content + " " + c.title)
        if not c_tokens:
            continue
        overlap = query_tokens.intersection(c_tokens)
        if overlap:
            # Lexical overlap score normalized by query length
            score = len(overlap) / float(len(query_tokens))
            scored.append((score, c))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, chunk in scored[:top_k]:
        item = chunk.to_dict()
        item["score"] = round(score, 3)
        results.append(item)
    return results

# ----------------------------------------------------------------------
# JSON-RPC Capability Methods
# ----------------------------------------------------------------------

def handle_ingest(params: Dict[str, Any]) -> Dict[str, Any]:
    tenant_id = params.get("tenant_id", "default")
    doc = params.get("document", {})
    doc_id = doc.get("id") or f"doc-{os.urandom(4).hex()}"
    title = doc.get("title", "Untitled Document")
    content = doc.get("content", "")
    metadata = doc.get("metadata", {})

    chunks = ingest_document(tenant_id, doc_id, title, content, metadata)
    return {
        "status": "ingested",
        "document_id": doc_id,
        "chunks_count": len(chunks),
        "chunks": [c.to_dict() for c in chunks],
    }

def handle_query(params: Dict[str, Any]) -> Dict[str, Any]:
    tenant_id = params.get("tenant_id", "default")
    query = params.get("query", "")
    top_k = params.get("top_k", 3)
    results = retrieve_chunks(tenant_id, query, top_k=top_k)
    return {
        "query": query,
        "results_count": len(results),
        "results": results,
    }

plugin.register_method("rag.ingest", handle_ingest)
plugin.register_method("rag.query", handle_query)
plugin.register_method("knowledge.ingest", handle_ingest)
plugin.register_method("knowledge.query", handle_query)

# ----------------------------------------------------------------------
# Pipeline Hook: request.before
# ----------------------------------------------------------------------

@plugin.on("request.before")
def on_request_before(ctx: Any, req: Any):
    tenant_id = _get_tenant_id(ctx)
    prompt = req.prompt_text()
    sys.stderr.write(f"[rag] request.before tenant={tenant_id} query='{prompt[:50]}...'\n")
    sys.stderr.flush()

    # Pre-seed default refund policy if query asks about refund and tenant has no custom docs
    if "refund" in prompt.lower() and tenant_id not in _tenant_chunks:
        ingest_document(tenant_id, "doc-refund-01", "Refund Policy", DEFAULT_REFUND_DOC)

    matches = retrieve_chunks(tenant_id, prompt, top_k=2)
    if not matches:
        return Result.continue_()

    # Format context injection block
    context_lines = []
    for idx, match in enumerate(matches):
        context_lines.append(f"[{idx + 1}] {match['content']}")

    context_str = "\n".join(context_lines)
    augmented_prompt = f"Context:\n{context_str}\n\nQuestion:\n{prompt}"

    # Update the last user message
    modified = False
    for msg in reversed(req.messages):
        if msg.role == "user":
            msg.content = augmented_prompt
            modified = True
            break

    if modified:
        sys.stderr.write(f"[rag] augmented user request with {len(matches)} retrieved chunks\n")
        sys.stderr.flush()
        return Result.modify_request(req)

    return Result.continue_()

if __name__ == "__main__":
    plugin.run()
