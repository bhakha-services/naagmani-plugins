import { RPCError, RPCRequest, RPCResponse } from "./messages";

export function createSuccessResponse(id: number, result: any): RPCResponse {
  return {
    jsonrpc: "2.0",
    result,
    id,
  };
}

export function createErrorResponse(
  id: number,
  code: number,
  message: string,
  data?: any
): RPCResponse {
  const error: RPCError = {
    code,
    message,
  };
  if (data !== undefined) {
    error.data = data;
  }
  return {
    jsonrpc: "2.0",
    error,
    id,
  };
}

export function serializeResponse(resp: RPCResponse): string {
  return JSON.stringify(resp) + "\n";
}
