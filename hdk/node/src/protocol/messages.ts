import { DecisionAction, HookName } from "./constants";

/**
 * JSON-RPC 2.0 Request payload.
 */
export interface RPCRequest {
  jsonrpc: "2.0";
  method: string;
  params?: any;
  id: number;
}

/**
 * JSON-RPC 2.0 Error object.
 */
export interface RPCError {
  code: number;
  message: string;
  data?: any;
}

/**
 * JSON-RPC 2.0 Response payload.
 */
export interface RPCResponse {
  jsonrpc: "2.0";
  result?: any;
  error?: RPCError;
  id: number;
}

/**
 * Registration parameters sent by OS during "plugin.register".
 */
export interface RegisterParams {
  plugin_name: string;
  plugin_version: string;
  api_version: string;
  protocol_version?: string;
  config?: any;
  permissions: string[];
  metadata?: Record<string, string>;
}

/**
 * Registration result returned by plugin to OS.
 */
export interface RegisterResult {
  status: "ok" | "error";
  protocol_version?: string;
  capabilities?: string[];
  message?: string;
}

/**
 * Health probe result returned by plugin during "plugin.health".
 */
export interface HealthResult {
  status: "healthy" | "degraded" | "unhealthy";
  uptime?: string;
  message?: string;
}

/**
 * Shutdown result returned by plugin during "plugin.shutdown".
 */
export interface ShutdownResult {
  status: "shutting_down";
}

/**
 * Tenant scoping context.
 */
export interface TenantContext {
  organization_id?: string;
  project_id?: string;
  environment_id?: string;
}

/**
 * Chat message model.
 */
export interface HookMessage {
  role: string;
  content: string;
}

/**
 * Inbound request model.
 */
export interface HookRequest {
  model: string;
  messages: HookMessage[];
  stream?: boolean;
}

/**
 * Token usage statistics.
 */
export interface HookUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/**
 * Model completion response model.
 */
export interface HookResponse {
  model: string;
  content?: string;
  usage?: HookUsage;
}

/**
 * Pipeline hook execution context sent by OS.
 */
export interface HookContext {
  hook: HookName;
  request_id: string;
  tenant?: TenantContext;
  request?: HookRequest;
  response?: HookResponse;
  metadata?: Record<string, string>;
}

/**
 * Parameters sent during "plugin.hook.invoke".
 */
export interface HookInvokeParams {
  hook: HookName;
  context: HookContext;
}

/**
 * Decision returned by plugin for hook execution.
 */
export interface HookDecision {
  decision: DecisionAction;
  modified_request?: HookRequest;
  modified_response?: HookResponse;
  block_reason?: string;
  error?: string;
}
