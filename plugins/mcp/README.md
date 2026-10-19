# Naagmani MCP Tool Execution Bridge v1.0.0

> **Model Context Protocol (MCP) Standard Client & Dynamic Tool Invocation Gateway**

The **Naagmani MCP Plugin** is an enterprise tool execution gateway that bridges Anthropic's Model Context Protocol (MCP) servers with the Naagmani OS runtime. It allows AI models and autonomous agents to dynamically discover, validate, and execute external tools, APIs, database connectors, and filesystem operations through a governed, audited boundary.

- **Category**: Plugin (`Tool Execution & MCP`)
- **Entitlement Tier**: Enterprise
- **Certification**: Certified by Naagmani Tool Team
- **License**: Apache-2.0
- **Runtime**: Node.js 20+ (`naagmani.plugin/v1`)
- **Failure Policy**: `fail_open` (1500ms timeout)
- **Permissions**: `request.read`, `request.modify`
- **Capabilities**: `tools.mcp`, `tools.function`
- **Hook**: `request.before`

---

## 1. Motto & Core Value Proposition

Connecting generative AI models to internal enterprise APIs, databases, and third-party tools creates critical governance and data security challenges. Naagmani MCP provides a **Standardized, Governed Tool Interface**:
- **Protocol Standardization**: Implements the official Model Context Protocol (MCP) JSON-RPC specification.
- **Dynamic Tool Schema Injection**: Injects tool definitions and parameter constraints directly into model system messages on `request.before`.
- **Parameter Validation & Type Safety**: Rejects malformed function arguments before tool execution occurs.
- **Audited Sandbox Execution**: Every tool invocation produces structured trace events with tenant isolation, caller identity, and return artifacts.

---

## 2. Architecture & Tool Execution Lifecycle

MCP attaches to `request.before` to inject available MCP server tools into the model context, and coordinates execution callbacks:

```
[ Agent / User Prompt ]
       │
       ▼
[ Naagmani OS Gateway ]
       │
       │ (1) Hook: 'request.before'
       ▼
[ Naagmani MCP Plugin ]
       │
       ├──► (2) Queries Connected MCP Servers (Filesystem, DB, GitHub, Slack)
       │         - Enumerates registered tool definitions & JSON schemas
       │
       ├──► (3) Injects Tool Definitions into Prompt Context
       │
       ▼ (4) LLM Request Egress with Registered Tools
[ Upstream LLM Provider ]
       │
       ▼ (5) LLM Returns Tool Call Decision: 'execute_query(sql=...)'
[ Naagmani OS Gateway ]
       │
       ▼ (6) MCP Tool Executor runs in Sandboxed Environment
[ Downstream MCP Server ]
       │
       ▼ (7) Observation / Result returned back to Agent
[ Client Application ]
```

---

## 3. Key Capabilities & Technical Features

| Feature | Category | Description | Technical Details |
| :--- | :--- | :--- | :--- |
| **MCP Standard Compliant** | Integration | Full compatibility with MCP client/server specifications over stdio & SSE. | Connects to standard MCP servers (e.g. `@modelcontextprotocol/server-filesystem`, PostgreSQL, Git). |
| **Schema Validation** | Security | Enforces JSON Schema validation on all inbound and outbound tool arguments. | Catches type mismatches, missing required keys, or parameter tampering before invocation. |
| **Per-Tool RBAC Policies** | Governance | Restricts tool execution to authorized roles and environments. | Evaluates `tools.mcp` permission against active project permissions before delegating calls. |
| **Execution Timeouts** | Reliability | Prevents long-running tool scripts from hanging inference workers. | Enforces per-tool execution budgets (default 1500ms for gateway negotiation). |

---

## 4. Configuration Schema

Configured per project workspace and environment via Developer Portal or Naagmani CLI:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `mcp_servers` | `array` | `[]` | List of target MCP server configurations (command, args, env, or SSE URLs) |
| `execution_timeout_ms` | `integer` | `5000` | Hard execution timeout for individual tool function calls |
| `auto_approve_read_only` | `boolean` | `true` | Automatically approve non-mutating idempotent tool executions |
| `max_concurrent_invocations` | `integer` | `3` | Maximum concurrent tool invocations permitted per prompt turn |

---

## 5. Installation & Verification

### Via Naagmani CLI

```bash
# 1. Install MCP plugin into test environment
naagmani plugins install mcp --project <project_id> --env test

# 2. Test tool execution with MCP-enabled prompt
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer <test_api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "List the files in the project workspace directory"}],
    "tools_enabled": true
  }'

# 3. Promote to production
naagmani plugins install mcp --project <project_id> --env production
```

---

## 6. Security Boundary & Failure Policy

- **Policy**: `fail_open`
- **Timeout**: 1500 milliseconds
- **Behavior**: If an MCP server is unreachable or fails to list tools within the timeout, the prompt proceeds to the LLM without tool injection rather than failing user requests entirely.
