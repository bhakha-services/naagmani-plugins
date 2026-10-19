# Naagmani Agent Runtime v1.0.0

> **Autonomous Agent Reasoning Loop & Governed Multi-Tool Orchestration Engine**

The **Naagmani Agent Runtime** is an enterprise-grade agent orchestration plugin that executes multi-step reasoning loops, autonomous goal decomposition, and governed tool calling across MCP and RAG knowledge bases under strict Naagmani OS policies.

- **Category**: Plugin (`Agent Orchestration`)
- **Entitlement Tier**: Enterprise
- **Certification**: Certified by Naagmani Core Team
- **License**: Apache-2.0
- **Runtime**: Node.js 20+ (`naagmani.plugin/v1`)
- **Failure Policy**: `fail_close` (30,000ms timeout)
- **Permissions**: `request.read`, `request.modify`, `agent.execute`, `tools.mcp`, `knowledge.rag`

---

## 1. Motto & Core Value Proposition

Standard AI agent loops are prone to infinite recursion, runaway token consumption, unauthorized data access, and unsafe tool execution. Naagmani Agent Runtime provides **Governed Autonomy**:
- **Controlled ReAct Loops**: Bounded step-by-step reasoning (Thought $\rightarrow$ Action $\rightarrow$ Observation) with hard quotas.
- **Strict Execution Boundaries**: Maximum step count, tool call ceilings, and timeout enforcement stop infinite loops.
- **Enterprise Safety Policies**: Tool calls must be validated against tenant permissions before execution.
- **Native MCP & RAG Bridge**: Seamlessly invokes Model Context Protocol (MCP) tools and semantic retrieval systems within the same runtime session.

---

## 2. Architecture & Reasoning Loop

The plugin intercepts inference requests at `request.before` and orchestrates the autonomous agent workflow:

```
[ User Request / Prompt ]
       │
       ▼
[ Naagmani OS Gateway ]
       │
       │ (1) Hook: 'request.before'
       ▼
[ Agent Runtime Engine ]
       │
       ├──► (2) Goal Decomposition & Plan Initialization
       │
       ├──► (3) Reasoning Loop (Max Steps: 8)
       │         │
       │         ├─► LLM Reasoning Call (Generate Thought & Tool Invocation)
       │         │
       │         ├─► Policy & Permission Validation (OS Sandboxed)
       │         │
       │         ├─► Tool Execution (MCP Tools / RAG Vector Store)
       │         │
       │         └─► Feed Observation back into Context
       │
       ▼ (4) Final Synthesized Answer Produced
[ Client Application ] (Receives complete response with audit trail)
```

---

## 3. Key Capabilities & Technical Features

| Feature | Category | Description | Technical Details |
| :--- | :--- | :--- | :--- |
| **Bounded ReAct Loop** | Lifecycle | Enforces finite reasoning iterations with strict termination criteria. | Configurable `max_steps` (default 8). Halts gracefully if limit is reached without erroring out unhandled. |
| **Multi-Tool Dispatch** | Orchestration | Concurrently or sequentially dispatches validated tool calls. | Integrates with `tools.mcp` protocol servers and internal native OS tools. Limits concurrent invocations (`max_tool_calls: 5`). |
| **Context Window Guard** | Memory | Prevents token overflow by pruning intermediate observation noise. | Monitored by `max_context_size` (16,000 tokens). Compresses older scratchpad turns while preserving active task objectives. |
| **Tenant Tool Sandbox** | Security | Validates user and project authorization before calling sensitive tools. | Evaluates `agent.execute` and tool permissions in Naagmani OS PDP before executing downstream commands. |

---

## 4. Configuration Schema

Configured per project workspace and environment via Developer Portal or Naagmani CLI:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_steps` | `integer` | `8` | Maximum reasoning iterations allowed per agent execution turn |
| `max_tool_calls` | `integer` | `5` | Maximum total tool calls permitted across the full execution turn |
| `max_execution_time_ms`| `integer` | `30000` | Hard deadline (in ms) before the agent execution aborts |
| `max_context_size` | `integer` | `16000` | Context token ceiling before automated scratchpad pruning triggers |

---

## 5. Installation & Usage

### Via Naagmani CLI

```bash
# 1. Install agent runtime into test environment
naagmani plugins install agent-runtime --project <project_id> --env test

# 2. Test an agent execution turn via OS Gateway
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer <test_api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Look up order #9821 and verify its shipment status"}],
    "agent_mode": true
  }'

# 3. Promote to production
naagmani plugins install agent-runtime --project <project_id> --env production
```

---

## 6. Security Boundary & Failure Policy

- **Policy**: `fail_close`
- **Timeout**: 30,000 milliseconds
- **Behavior**: If the reasoning loop exceeds its step quota or execution deadline, the engine terminates the loop and returns a structured failure explanation, preventing orphaned background worker processes or runaway API billing.
