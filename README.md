# Naagmani Plugin Ecosystem (`naagmani-plugins`)

Welcome to the official repository for the **Naagmani AI Operating System Plugin Ecosystem**, containing official Host Development Kits (HDKs), reference plugins, protocol specifications, and templates.

---

## 🚀 Overview

The Naagmani AI Operating System enables developers to build powerful extensions, security controls, and enterprise guardrails for AI applications. All plugins run as isolated child processes communicating over the canonical, language-independent **`naagmani.plugin/v1`** wire protocol.

```
┌─────────────────────────────────────────────────────────────┐
│                      Naagmani OS Core                       │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON-RPC 2.0 over stdio
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Naagmani Plugin Host Development              │
├───────────────────┬─────────────────────┬───────────────────┤
│      Go HDK       │      Node HDK       │    Python HDK     │
│  hdk/go (Go 1.22) │ hdk/node (TS/Node)  │ hdk/python (Py3)  │
└───────────────────┴─────────────────────┴───────────────────┘
```

---

## 📦 Repository Structure

```
naagmani-plugins/
├── spec/
│   └── plugin-v1/          # Frozen naagmani.plugin/v1 protocol wire specification
├── hdk/
│   ├── go/                 # Official Go HDK (github.com/bhakha-services/naagmani-plugins/hdk/go)
│   ├── node/               # Official Node.js / TypeScript HDK (@naagmani/hdk)
│   └── python/             # Official Python HDK (naagmani-hdk)
├── plugins/                # Open-source reference and community plugins
│   ├── agent-runtime/      # Autonomous agent reasoning and tool coordination plugin (Node.js)
│   ├── ai-firewall-node/   # Real-time prompt guard and safety filtering plugin (Node.js)
│   ├── dlp/                # Data loss prevention & PII masking plugin (Python)
│   ├── mcp/                # Model Context Protocol (MCP) tool execution plugin (Node.js)
│   └── rag/                # Retrieval-Augmented Generation & knowledge retrieval (Python)
├── examples/               # End-to-end integration and custom plugin examples
├── templates/              # Starter templates for rapid plugin authoring
├── CONTRIBUTING.md         # Guidelines for contributing and extending HDKs
└── LICENSE                 # Apache License 2.0
```

---

## 🛠️ Supported Host Development Kits (HDKs)

### 1. Go HDK (`hdk/go`)
Author ultra-fast, native plugins compiled to single static binaries.

```bash
go get github.com/bhakha-services/naagmani-plugins/hdk/go
```

```go
package main

import (
	"log"
	"github.com/bhakha-services/naagmani-plugins/hdk/go/plugin"
)

func main() {
	p := plugin.New("guard-plugin").
		Version("0.1.0").
		OnRequestBefore(func(ctx *plugin.Context, req *plugin.Request) (*plugin.Result, error) {
			log.Printf("Intercepted request: ID=%s model=%s", ctx.RequestID, req.Model)
			return plugin.Continue(), nil
		})

	if err := p.Run(); err != nil {
		log.Fatalf("Runtime error: %v", err)
	}
}
```

### 2. Node.js / TypeScript HDK (`hdk/node`)
Author type-safe, asynchronous plugins using Node.js 18+ and TypeScript.

```bash
npm install @naagmani/hdk
```

```typescript
import { Plugin, Result, Context, Request } from "@naagmani/hdk";

const plugin = new Plugin({
  name: "sentiment-guard",
  version: "0.1.0",
});

plugin.onRequestBefore(async (ctx: Context, req: Request) => {
  console.error(`Processing request ID=${ctx.requestId}`);
  return Result.continue();
});

plugin.start();
```

### 3. Python HDK (`hdk/python`)
Author AI data science, RAG, and DLP plugins with zero runtime dependencies.

```bash
pip install naagmani-hdk
```

```python
from naagmani import Plugin, Result

plugin = Plugin(
    name="pii-sanitizer",
    version="0.1.0",
)

@plugin.on("request.before")
def on_request_before(ctx, req):
    # Diagnostic logs to stderr
    sys.stderr.write(f"Auditing prompt for request {ctx.request_id}\n")
    return Result.continue_()

if __name__ == "__main__":
    plugin.run()
```

---

## 🔌 Reference Plugins

| Plugin | Language | Description | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **`plugins/agent-runtime`** | TypeScript | Autonomous multi-step agent reasoning and tool orchestration | `agent.reasoning`, `tool.dispatch` |
| **`plugins/ai-firewall-node`** | TypeScript | Prompt injection detection, keyword blocking, safety enforcement | `firewall.prompt_guard` |
| **`plugins/dlp`** | Python | High-performance PII redaction (email, phone, API keys) | `dlp.masking`, `security.pii` |
| **`plugins/mcp`** | TypeScript | Model Context Protocol tool execution runner | `mcp.tools`, `mcp.execution` |
| **`plugins/rag`** | Python | Multi-tenant in-memory RAG with vector chunk injection | `knowledge.rag`, `retrieval` |

---

## 📖 Plugin Protocol (`naagmani.plugin/v1`)

All communication between Naagmani OS and plugins follows the **`naagmani.plugin/v1`** standard.
See full specification in [`spec/plugin-v1/README.md`](spec/plugin-v1/README.md).

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for testing guidelines and pull request instructions.

## 📄 License

This repository is licensed under the [Apache License 2.0](LICENSE).
Copyright 2026 Bhakha Services / Naagmani Team.
