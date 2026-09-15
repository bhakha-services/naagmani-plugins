import * as readline from "readline";
import { Readable, Writable } from "stream";
import {
  ErrorCodes,
  Hooks,
  Methods,
  PROTOCOL_VERSION,
} from "../protocol/constants";
import {
  createErrorResponse,
  createSuccessResponse,
  serializeResponse,
} from "../protocol/jsonrpc";
import {
  HealthResult,
  HookDecision,
  HookInvokeParams,
  RegisterParams,
  RegisterResult,
  RPCRequest,
  RPCResponse,
  ShutdownResult,
} from "../protocol/messages";
import { Context } from "./context";
import { Plugin } from "./plugin";
import { Request } from "./request";
import { Response } from "./response";
import { Result } from "./result";

export class Server {
  private readonly plugin: Plugin;
  private readonly input: Readable;
  private readonly output: Writable;
  private readonly startedAt: Date;

  constructor(plugin: Plugin, input: Readable, output: Writable) {
    this.plugin = plugin;
    this.input = input;
    this.output = output;
    this.startedAt = new Date();
  }

  log(message: string, ...args: any[]): void {
    process.stderr.write(
      `[${this.plugin.name}] ${message} ${args.length ? JSON.stringify(args) : ""}\n`
    );
  }

  async serve(): Promise<void> {
    const rl = readline.createInterface({
      input: this.input,
      crlfDelay: Infinity,
    });

    for await (const line of rl) {
      const trimmed = line.trim();
      if (!trimmed) {
        continue;
      }

      let req: RPCRequest;
      try {
        req = JSON.parse(trimmed);
      } catch (err: any) {
        this.log("failed parsing JSON-RPC line:", err?.message);
        this.sendError(0, ErrorCodes.ParseError, "Parse error");
        continue;
      }

      const shouldExit = await this.handleRequest(req);
      if (shouldExit) {
        rl.close();
        break;
      }
    }
  }

  private async handleRequest(req: RPCRequest): Promise<boolean> {
    if (req.jsonrpc !== "2.0") {
      this.sendError(
        req.id,
        ErrorCodes.InvalidRequest,
        "Invalid JSON-RPC version, expected '2.0'"
      );
      return false;
    }

    try {
      switch (req.method) {
        case Methods.Register: {
          const params: RegisterParams = req.params || {};

          // Validate protocol version
          if (
            params.protocol_version &&
            params.protocol_version !== PROTOCOL_VERSION
          ) {
            const errMsg = `incompatible protocol version: expected ${PROTOCOL_VERSION}, got ${params.protocol_version}`;
            this.log(errMsg);
            this.sendError(req.id, ErrorCodes.ProtocolVersionMismatch, errMsg);
            return false;
          }

          const caps =
            this.plugin.capabilities.length > 0
              ? this.plugin.capabilities
              : ["core"];

          const res: RegisterResult = {
            status: "ok",
            protocol_version: PROTOCOL_VERSION,
            capabilities: caps,
            message: `${this.plugin.name} v${this.plugin.version} initialized successfully`,
          };
          this.sendSuccess(req.id, res);
          return false;
        }

        case Methods.Health: {
          const uptimeSec = Math.round(
            (Date.now() - this.startedAt.getTime()) / 1000
          );
          const res: HealthResult = {
            status: "healthy",
            uptime: `${uptimeSec}s`,
            message: "Plugin operational",
          };
          this.sendSuccess(req.id, res);
          return false;
        }

        case Methods.Shutdown: {
          const res: ShutdownResult = {
            status: "shutting_down",
          };
          this.sendSuccess(req.id, res);
          return true; // Exit event loop
        }

        case Methods.HookInvoke: {
          const params: HookInvokeParams = req.params;
          if (!params || !params.hook || !params.context) {
            this.sendError(
              req.id,
              ErrorCodes.InvalidParams,
              "Invalid hook invoke params"
            );
            return false;
          }

          const decision = await this.dispatchHook(params);
          this.sendSuccess(req.id, decision);
          return false;
        }

        default: {
          const customMethod = this.plugin.getMethod(req.method);
          if (customMethod) {
            const customResult = await customMethod(req.params);
            this.sendSuccess(req.id, customResult);
            return false;
          }
          this.sendError(
            req.id,
            ErrorCodes.MethodNotFound,
            `Method '${req.method}' not found`
          );
          return false;
        }
      }
    } catch (err: any) {
      this.log(`internal error handling ${req.method}:`, err?.message || err);
      this.sendError(
        req.id,
        ErrorCodes.InternalError,
        err?.message || "Internal error"
      );
      return false;
    }
  }

  private async dispatchHook(params: HookInvokeParams): Promise<HookDecision> {
    const ctx = new Context(params.context);

    try {
      switch (params.hook) {
        case Hooks.RequestBefore: {
          const handler = this.plugin.getRequestHandler(Hooks.RequestBefore);
          if (handler) {
            const req = new Request(params.context.request);
            const res: Result = await handler(ctx, req);
            return res ? res.toProtocolDecision() : Result.continue().toProtocolDecision();
          }
          break;
        }

        case Hooks.RequestAfter: {
          const handler = this.plugin.getRequestHandler(Hooks.RequestAfter);
          if (handler) {
            const req = new Request(params.context.request);
            const res: Result = await handler(ctx, req);
            const dec = res ? res.toProtocolDecision() : Result.continue().toProtocolDecision();
            dec.modified_request = undefined; // read-only
            return dec;
          }
          break;
        }

        case Hooks.ResponseBefore: {
          const handler = this.plugin.getResponseHandler(Hooks.ResponseBefore);
          if (handler) {
            const resp = new Response(params.context.response);
            const res: Result = await handler(ctx, resp);
            return res ? res.toProtocolDecision() : Result.continue().toProtocolDecision();
          }
          break;
        }

        case Hooks.ResponseAfter: {
          const handler = this.plugin.getResponseHandler(Hooks.ResponseAfter);
          if (handler) {
            const resp = new Response(params.context.response);
            const res: Result = await handler(ctx, resp);
            const dec = res ? res.toProtocolDecision() : Result.continue().toProtocolDecision();
            dec.modified_response = undefined; // audit only
            return dec;
          }
          break;
        }
      }
    } catch (err: any) {
      this.log(`error executing hook ${params.hook}:`, err?.message || err);
      return {
        decision: "continue",
        error: err?.message || String(err),
      };
    }

    return Result.continue().toProtocolDecision();
  }

  private sendSuccess(id: number, result: any): void {
    const resp = createSuccessResponse(id, result);
    this.writeResponse(resp);
  }

  private sendError(id: number, code: number, message: string, data?: any): void {
    const resp = createErrorResponse(id, code, message, data);
    this.writeResponse(resp);
  }

  private writeResponse(resp: RPCResponse): void {
    this.output.write(serializeResponse(resp));
  }
}
