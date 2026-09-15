# Naagmani Plugin Protocol v1 Specification

**Protocol Identifier**: `naagmani.plugin/v1`  
**Status**: **FROZEN** (Architectural Standard)  
**Transport**: Standard Input/Output (`stdio`), Newline-Delimited JSON-RPC 2.0  

---

## 1. Overview & Principles

Naagmani OS operates as an AI Operating System kernel with an open, language-independent plugin extension model.

- **Language Agnostic**: Plugins can be written in Go, TypeScript / Node.js, Python, Rust, C++, or any language capable of reading and writing JSON over `stdin`/`stdout`.
- **Strict Transport Isolation**:
  - **`stdout`**: Strictly reserved for single-line JSON-RPC 2.0 frames terminated by `\n`. Writing raw strings, debug statements, or non-protocol output to `stdout` corrupts the communication stream.
  - **`stderr`**: Reserved exclusively for developer diagnostic logging. Naagmani OS intercepts `stderr` lines and integrates them safely into the host audit and debug log streams.
- **Process Model**: The host process spawns each plugin as a dedicated subprocess, conducts a registration handshake, executes hook pipelines, and manages process shutdown.

---

## 2. Wire Framing & Transport

All messages exchanged between the host and the plugin are JSON-RPC 2.0 objects formatted as a single line terminated by `\n`:

```
{"jsonrpc":"2.0","id":1,"method":"...","params":{...}}\n
```

### 2.1 Request Structure
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "<method_name>",
  "params": { ... }
}
```

### 2.2 Success Response Structure
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { ... }
}
```

### 2.3 Error Response Structure
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32000,
    "message": "Human readable explanation",
    "data": { ... }
  }
}
```

---

## 3. Standard Protocol Methods

### 3.1 `plugin.register` (Handshake)
Sent by the host immediately after launching the plugin subprocess. The plugin must reply with its capabilities and confirm protocol compatibility before any hooks can be invoked.

**Request Params:**
```json
{
  "plugin_name": "ai-firewall",
  "plugin_version": "1.0.0",
  "api_version": "v1",
  "protocol_version": "naagmani.plugin/v1",
  "config": {},
  "permissions": ["request.read", "request.modify"]
}
```

**Success Response Result:**
```json
{
  "status": "ready",
  "protocol_version": "naagmani.plugin/v1",
  "capabilities": ["request.read", "request.modify"],
  "message": "plugin initialized successfully"
}
```

---

### 3.2 `plugin.health` (Liveness & Readiness Probe)
Sent periodically by the host to verify that the plugin process is alive and healthy.

**Request Params:**
```json
{}
```

**Success Response Result:**
```json
{
  "status": "healthy",
  "uptime_ms": 12450,
  "message": "plugin operating normally"
}
```

---

### 3.3 `plugin.shutdown` (Graceful Termination)
Sent by the host during system shutdown or plugin reconfiguration.

**Request Params:**
```json
{
  "reason": "host_shutdown",
  "grace_period_ms": 3000
}
```

**Success Response Result:**
```json
{
  "status": "terminating"
}
```

---

### 3.4 `plugin.hook.invoke` (Hook Execution)
Dispatched by the host when a gateway request or response reaches a registered pipeline hook.

**Supported Lifecycle Hooks:**
- `request.before`: Intercepts inbound client requests before routing to AI providers (allows `continue`, `modify`, `block`).
- `request.after`: Read-only hook dispatched immediately before provider dispatch.
- `response.before`: Intercepts outbound AI provider responses before returning to the client (allows `continue`, `modify`, `block`).
- `response.after`: Read-only hook dispatched after response delivery for telemetry and auditing.

**Request Params Structure:**
```json
{
  "hook": "request.before",
  "context": {
    "hook": "request.before",
    "request_id": "req_01j7abc123",
    "tenant": {
      "organization_id": "org_123",
      "project_id": "proj_456",
      "environment_id": "env_prod"
    },
    "metadata": {}
  },
  "request": {
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": "Hello AI assistant"
      }
    ],
    "stream": false
  }
}
```

**Hook Decisions:**

1. **Continue** (Pass-through without modification):
```json
{
  "decision": "continue"
}
```

2. **Modify Request** (Requires `request.modify` permission):
```json
{
  "decision": "modify",
  "modified_request": {
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": "Hello AI assistant [PII Redacted]"
      }
    ]
  }
}
```

3. **Modify Response** (Requires `response.modify` permission):
```json
{
  "decision": "modify",
  "modified_response": {
    "model": "gpt-4o",
    "content": "Redacted model completion output"
  }
}
```

4. **Block** (Halts pipeline execution with HTTP 403 Forbidden):
```json
{
  "decision": "block",
  "block_reason": "Prompt contains prohibited patterns or security violation"
}
```

---

## 4. Standard Protocol Error Codes

| Code | Constant | Meaning |
| :--- | :--- | :--- |
| `-32700` | `ParseError` | Invalid JSON received by plugin/host |
| `-32600` | `InvalidRequest` | JSON payload is not a valid JSON-RPC 2.0 object |
| `-32601` | `MethodNotFound` | Method not supported or registered |
| `-32602` | `InvalidParams` | Parameter validation failed |
| `-32603` | `InternalError` | Unhandled internal exception |
| `-32000` | `RegistrationFailed` | Plugin handshake registration failed |
| `-32001` | `ProtocolVersionMismatch` | Incompatible protocol version declared |
| `-32002` | `PermissionDenied` | Plugin attempted action without declared permission |
| `-32003` | `ExecutionTimeout` | Hook execution exceeded configured deadline |
| `-32004` | `ExecutionFailed` | Hook handler threw an error |
| `-32005` | `ModificationRejected` | Host rejected payload modification |
| `-32006` | `PluginUnhealthy` | Health probe reported unhealthy state |

---

## 5. Security Invariants & Isolation

1. **Tenant Scope Immutability**: Plugins cannot alter tenant identifiers (`organization_id`, `project_id`, `environment_id`). Any attempt is stripped by the host kernel.
2. **Permission Boundary**: Declaring permissions in `plugin.json` is a prerequisite. Actions attempted without valid permissions will be rejected with error `-32002`.
3. **Fail-Safe Execution Policies**:
   - `fail_open`: Exceptions or timeouts log audit alerts while permitting traffic to proceed.
   - `fail_close`: Critical DLP/firewall failures immediately abort requests, preventing leakage.
