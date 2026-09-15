package protocol

import "encoding/json"

// ProtocolVersion is the frozen canonical protocol identifier for Naagmani Plugin Protocol v1.
const ProtocolVersion = "naagmani.plugin/v1"

// Standard JSON-RPC 2.0 and Naagmani Protocol v1 error codes.
const (
	CodeParseError              = -32700
	CodeInvalidRequest          = -32600
	CodeMethodNotFound          = -32601
	CodeInvalidParams           = -32602
	CodeInternalError           = -32603
	CodeRegistrationFailed      = -32000
	CodeProtocolVersionMismatch = -32001
	CodePermissionDenied        = -32002
	CodeExecutionTimeout        = -32003
	CodeExecutionFailed         = -32004
	CodeModificationRejected    = -32005
	CodePluginUnhealthy         = -32006
)

// Frozen Protocol v1 Method Names.
const (
	MethodRegister   = "plugin.register"
	MethodHealth     = "plugin.health"
	MethodShutdown   = "plugin.shutdown"
	MethodHookInvoke = "plugin.hook.invoke"
)

// Pipeline Hook Names.
const (
	HookRequestBefore  = "request.before"
	HookRequestAfter   = "request.after"
	HookResponseBefore = "response.before"
	HookResponseAfter  = "response.after"
)

// Hook Decision values.
const (
	DecisionContinue = "continue"
	DecisionModify   = "modify"
	DecisionBlock    = "block"
)

// RPCRequest is a JSON-RPC 2.0 request payload.
type RPCRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
	ID      int64           `json:"id"`
}

// RPCResponse is a JSON-RPC 2.0 response payload.
type RPCResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
	ID      int64           `json:"id"`
}

// RPCError represents a JSON-RPC 2.0 error object.
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

// RegisterParams is passed by Naagmani OS during the "plugin.register" handshake.
type RegisterParams struct {
	PluginName      string            `json:"plugin_name"`
	PluginVersion   string            `json:"plugin_version"`
	APIVersion      string            `json:"api_version"`
	ProtocolVersion string            `json:"protocol_version,omitempty"`
	Config          json.RawMessage   `json:"config,omitempty"`
	Permissions     []string          `json:"permissions"`
	Metadata        map[string]string `json:"metadata,omitempty"`
}

// RegisterResult is returned by the plugin to complete the handshake.
type RegisterResult struct {
	Status          string   `json:"status"` // "ok" or "error"
	ProtocolVersion string   `json:"protocol_version,omitempty"`
	Capabilities    []string `json:"capabilities,omitempty"`
	Message         string   `json:"message,omitempty"`
}

// HealthParams is passed during "plugin.health".
type HealthParams struct{}

// HealthResult is returned by the plugin for liveness/readiness probes.
type HealthResult struct {
	Status  string `json:"status"` // "healthy", "degraded", "unhealthy"
	Uptime  string `json:"uptime,omitempty"`
	Message string `json:"message,omitempty"`
}

// ShutdownParams is passed during "plugin.shutdown".
type ShutdownParams struct{}

// ShutdownResult is returned by the plugin before exiting.
type ShutdownResult struct {
	Status string `json:"status"` // "shutting_down"
}

// HookInvokeParams is sent by the OS to invoke an ingress/egress hook.
type HookInvokeParams struct {
	Hook    string      `json:"hook"`
	Context HookContext `json:"context"`
}

// TenantContext carries tenant scoping information.
type TenantContext struct {
	OrganizationID string `json:"organization_id,omitempty"`
	ProjectID      string `json:"project_id,omitempty"`
	EnvironmentID  string `json:"environment_id,omitempty"`
}

// HookMessage is a single chat completion message.
type HookMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// HookRequest carries the current chat request payload.
type HookRequest struct {
	Model    string        `json:"model"`
	Messages []HookMessage `json:"messages"`
	Stream   bool          `json:"stream,omitempty"`
}

// HookUsage carries token usage metrics.
type HookUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// HookResponse carries the model response payload.
type HookResponse struct {
	Model   string     `json:"model"`
	Content string     `json:"content,omitempty"`
	Usage   *HookUsage `json:"usage,omitempty"`
}

// HookContext carries all context for a hook execution.
type HookContext struct {
	Hook      string            `json:"hook"`
	RequestID string            `json:"request_id"`
	Tenant    TenantContext     `json:"tenant,omitempty"`
	Request   *HookRequest      `json:"request,omitempty"`
	Response  *HookResponse     `json:"response,omitempty"`
	Metadata  map[string]string `json:"metadata,omitempty"`
}

// HookDecision is returned by the plugin to instruct the OS pipeline.
type HookDecision struct {
	Decision         string        `json:"decision"`
	ModifiedRequest  *HookRequest  `json:"modified_request,omitempty"`
	ModifiedResponse *HookResponse `json:"modified_response,omitempty"`
	BlockReason      string        `json:"block_reason,omitempty"`
	Error            string        `json:"error,omitempty"`
}
