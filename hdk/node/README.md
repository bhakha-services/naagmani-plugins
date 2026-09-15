# Naagmani HDK for Node.js / TypeScript

The official Node.js / TypeScript HDK (Host Development Kit) for building plugins on the **Naagmani AI OS**.

## Protocol

This package implements the canonical **Naagmani Plugin Protocol v1** (`naagmani.plugin/v1`) using JSON-RPC 2.0 over standard input and output (`stdio`).

## Installation

```bash
npm install @naagmani/hdk
```

## Quick Start

```typescript
import { Plugin, Result } from "@naagmani/hdk";

const plugin = new Plugin({
  name: "my-plugin",
  version: "0.1.0",
});

plugin.on("request.before", async (ctx, req) => {
  console.error(`Received request ID=${ctx.requestId}`);
  if (req.promptText().includes("evil")) {
    return Result.block("Prompt injection blocked");
  }
  return Result.continue();
});

plugin.run();
```
