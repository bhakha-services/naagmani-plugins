# Naagmani Go HDK (`naagmani-hdk-go`)

The official Go Hardware & Software Development Kit (HDK) for authoring [Naagmani](https://github.com/bhakha-services/naagmani) plugins.

## Overview

Naagmani plugins run as isolated child processes communicating with the Naagmani OS kernel via line-delimited **JSON-RPC 2.0** over standard input (`stdin`) and standard output (`stdout`).

The Go HDK encapsulates:
* Protocol handshake (`plugin.register`)
* Health check probes (`plugin.health`)
* Graceful termination (`plugin.shutdown`)
* Inbound & outbound hook interception (`plugin.hook.invoke`)
* Thread-safe stream serialization and correlation
* Automatic redirection of developer diagnostic logs to `stderr` (preventing protocol stream corruption)

---

## Quickstart

### 1. Install HDK

```bash
go get github.com/bhakha-services/naagmani-plugins/hdk/go
```

### 2. Implement Your Plugin

```go
package main

import (
	"log"
	"strings"

	"github.com/bhakha-services/naagmani-plugins/hdk/go/plugin"
)

func main() {
	p := plugin.New("sentiment-guard").
		Version("0.1.0").
		Description("Checks inbound prompts for restricted keywords").
		Author("Developer").
		OnRequestBefore(func(ctx *plugin.Context, req *plugin.Request) (*plugin.Result, error) {
			// Developer diagnostic logging to stderr
			log.Printf("Received prompt for model %s", req.Model)

			if strings.Contains(req.PromptText(), "prohibited_action") {
				return plugin.Block("Prompt contains prohibited keyword"), nil
			}

			return plugin.Continue(), nil
		})

	if err := p.Run(); err != nil {
		log.Fatalf("Plugin exited with error: %v", err)
	}
}
```

### 3. Hook Decisions

| Method | Behavior |
| :--- | :--- |
| `plugin.Continue()` | Lets the request proceed unchanged through the pipeline. |
| `plugin.Block(reason)` | Immediately halts the pipeline and returns `HTTP 403 Forbidden` with the reason. |
| `plugin.ModifyRequest(req)` | Overrides the prompt messages before routing to the AI provider. |
| `plugin.ModifyResponse(resp)` | Overrides the model output before returning to the client. |

---

## Testing

```bash
go test -v ./...
```
