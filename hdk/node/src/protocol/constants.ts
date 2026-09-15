/**
 * Canonical protocol identifier for Naagmani Plugin Protocol v1.
 * FROZEN PROTOCOL: DO NOT ALTER.
 */
export const PROTOCOL_VERSION = "naagmani.plugin/v1";

/**
 * Standard JSON-RPC 2.0 and Naagmani Protocol v1 error codes.
 */
export const ErrorCodes = {
  ParseError: -32700,
  InvalidRequest: -32600,
  MethodNotFound: -32601,
  InvalidParams: -32602,
  InternalError: -32603,
  RegistrationFailed: -32000,
  ProtocolVersionMismatch: -32001,
  PermissionDenied: -32002,
  ExecutionTimeout: -32003,
  ExecutionFailed: -32004,
  ModificationRejected: -32005,
  PluginUnhealthy: -32006,
} as const;

/**
 * Protocol v1 Method Names.
 */
export const Methods = {
  Register: "plugin.register",
  Health: "plugin.health",
  Shutdown: "plugin.shutdown",
  HookInvoke: "plugin.hook.invoke",
} as const;

/**
 * Pipeline Hook Names.
 */
export const Hooks = {
  RequestBefore: "request.before",
  RequestAfter: "request.after",
  ResponseBefore: "response.before",
  ResponseAfter: "response.after",
} as const;

/**
 * Hook Decision actions.
 */
export const Decisions = {
  Continue: "continue",
  Modify: "modify",
  Block: "block",
} as const;

export type HookName = typeof Hooks[keyof typeof Hooks];
export type DecisionAction = typeof Decisions[keyof typeof Decisions];
