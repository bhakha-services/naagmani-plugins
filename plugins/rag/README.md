# Naagmani RAG & Knowledge Retrieval Plugin v1.0.0

> **Enterprise Semantic Retrieval-Augmented Generation & Context Injection Engine**

The **Naagmani RAG Plugin** is an enterprise knowledge retrieval interceptor written in Python using the Naagmani HDK. It intercepts prompt requests at `request.before`, converts the user query into dense vector embeddings, performs semantic vector search across tenant-isolated knowledge collections, and injects verified context and citations into the prompt before model inference.

- **Category**: Plugin (`Knowledge & RAG`)
- **Entitlement Tier**: Enterprise
- **Certification**: Certified by Naagmani Knowledge Team
- **License**: Apache-2.0
- **Runtime**: Python 3.11 (`naagmani.plugin/v1`)
- **Failure Policy**: `fail_open` (1500ms timeout)
- **Permissions**: `request.read`, `request.modify`
- **Capabilities**: `knowledge.rag`, `knowledge.retrieval`
- **Hook**: `request.before`

---

## 1. Motto & Core Value Proposition

Generative AI models suffer from knowledge hallucination and lack real-time access to private enterprise documents. Naagmani RAG ensures **Grounded & Verifiable Knowledge**:
- **Zero Hallucination Grounding**: Dynamically surfaces relevant facts from private document stores, PDFs, knowledge bases, and wikis.
- **Strict Tenant & Project Isolation**: Embeddings and documents are segmented strictly by organization and project workspace boundaries.
- **Automated Citations**: Injects markdown citations (`[Doc: Q3_Financials.pdf, p. 4]`) so users can verify statements against source material.
- **Fail-Open Resilience**: If the vector index or embedding service experiences transient latency, the prompt falls back to unaugmented execution without failing user requests.

---

## 2. Architecture & Knowledge Retrieval Pipeline

RAG hooks into the pre-inference path at `request.before`:

```
[ User Query / Prompt ]
       │
       ▼
[ Naagmani OS Gateway ]
       │
       │ (1) Hook: 'request.before'
       ▼
[ Naagmani RAG Plugin ]
       │
       ├──► (2) Generates Semantic Query Embedding
       │
       ├──► (3) Vector Similarity Search across Knowledge Collections
       │         - Cosine similarity matching (top_k chunks)
       │         - Re-ranks and filters by similarity_threshold
       │
       ├──► (4) Synthesizes Context Block with Source Citations
       │
       ▼ (5) Augmented Prompt with Grounded Context Egress
[ External LLM Provider ] (OpenAI / Anthropic / Bedrock)
       │
       ▼ (6) Factually Grounded Response with Citations
[ Client Application ]
```

---

## 3. Key Capabilities & Technical Features

| Feature | Category | Description | Technical Details |
| :--- | :--- | :--- | :--- |
| **Dense Vector Retrieval** | Retrieval | Performs semantic similarity search across chunked vector embeddings. | Uses dense vector indexing with cosine/dot-product similarity scoring against tenant collections. |
| **Context Window Optimization** | Memory | Dynamically chunks and fits top-$K$ passages into the prompt context limit. | Configurable `top_k` (default 5) and `max_chunk_tokens` to prevent context buffer starvation. |
| **Relevance Thresholding** | Accuracy | Discards noisy passages that fall below a minimum similarity cutoff. | Controlled by `similarity_threshold` (default 0.75). Only high-confidence chunks are injected. |
| **Multi-Collection Scoping** | Isolation | Restricts search space to designated enterprise collections. | Enforces project workspace isolation so Project A cannot query Project B's proprietary documentation. |

---

## 4. Configuration Schema

Configured per project workspace and environment via Developer Portal or Naagmani CLI:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `top_k` | `integer` | `5` | Maximum number of relevant document chunks to inject into prompt |
| `similarity_threshold` | `number` | `0.75` | Minimum cosine similarity score ($0.0 - 1.0$) required for chunk inclusion |
| `collection_id` | `string` | `"default"` | Target knowledge collection identifier within active project workspace |
| `citation_format` | `string` | `"markdown"` | Citation styling in prompt context: `"markdown"` or `"footnote"` |

---

## 5. Installation & Verification

### Via Naagmani CLI

```bash
# 1. Install RAG plugin into test environment
naagmani plugins install rag --project <project_id> --env test

# 2. Query with grounded semantic knowledge
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer <test_api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "What is our company policy on international travel expenses?"}]
  }'
# The prompt is augmented with travel policy chunks and returned with citations

# 3. Promote to production
naagmani plugins install rag --project <project_id> --env production
```

---

## 6. Security Boundary & Failure Policy

- **Policy**: `fail_open`
- **Timeout**: 1500 milliseconds
- **Behavior**: If the knowledge store is experiencing a cold start or network delay exceeding 1500ms, the request proceeds directly to the LLM without augmentation to maintain end-user continuity.
