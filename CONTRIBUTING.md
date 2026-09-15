# Contributing to Naagmani Plugins & HDKs

Thank you for your interest in contributing to the Naagmani Plugin Ecosystem!

This repository contains the official Host Development Kits (HDKs), reference plugins, protocol specifications, and templates for the Naagmani AI Operating System.

---

## 🛠️ Prerequisites

To develop and test all components in this repository, you will need:
- **Go**: 1.22+
- **Node.js**: 18.0.0+ (and npm 9+)
- **Python**: 3.10+
- **Git**

---

## 🧪 Local Development & Testing

### 1. Go HDK (`hdk/go`)
```bash
cd hdk/go
go test -v ./...

# Build the example plugin
cd examples/hello-plugin
go build -v .
```

### 2. Node.js / TypeScript HDK (`hdk/node`)
```bash
cd hdk/node
npm install
npm run build
npm test

# Build the example plugin
cd examples/hello-plugin
npm install
npm run build
```

### 3. Python HDK (`hdk/python`)
```bash
cd hdk/python
python -m unittest discover tests
```

### 4. Reference Plugins (`plugins/`)
Each plugin can be tested and built independently:
```bash
# TypeScript Plugins (agent-runtime, ai-firewall-node, mcp)
cd plugins/ai-firewall-node
npm install
npm run build

# Python Plugins (dlp, rag)
cd plugins/dlp
python -c "import main; print('DLP loaded')"
```

---

## 📐 Protocol Invariants & Guidelines

1. **Protocol Immutability**: All HDKs must strictly conform to `naagmani.plugin/v1`. Do not introduce non-standard methods or fields without updating the specification.
2. **Standard Output Cleanliness**: Never print non-JSON-RPC lines to `stdout`. All diagnostic logs, stack traces, and debug prints must be routed to `stderr`.
3. **Decisions Model**: Every hook invocation must return a valid decision (`continue`, `modify`, `block`).
4. **Security & Zero Secrets**: Never commit real API keys, credentials, or private tokens. Always use mock strings for tests.

---

## 📬 Pull Requests

1. Fork the repository and create a feature branch (`git checkout -b feature/my-new-plugin`).
2. Verify all test suites pass in Go, Node, and Python.
3. Commit your changes with clear, descriptive commit messages.
4. Push to your fork and submit a Pull Request.

---

## 🔒 Security Reporting

If you discover a potential security vulnerability within Naagmani HDKs or reference plugins, please do not file a public issue. Instead, report it responsibly to `security@bhakha.com`.
