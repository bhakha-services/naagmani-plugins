# Naagmani HDK for Python

The official Python HDK (Host Development Kit) for building plugins on the **Naagmani AI OS**.

## Protocol

This package implements the canonical **Naagmani Plugin Protocol v1** (`naagmani.plugin/v1`) using JSON-RPC 2.0 over standard input and output (`stdio`).

## Installation

```bash
pip install naagmani-hdk
```

## Quick Start

```python
from naagmani import Plugin, Result

plugin = Plugin(
    name="my-python-plugin",
    version="0.1.0",
)

@plugin.on("request.before")
def on_request(ctx, req):
    if "secret" in req.prompt_text():
        return Result.block("Secret keyword detected")
    return Result.continue_()

if __name__ == "__main__":
    plugin.run()
```
