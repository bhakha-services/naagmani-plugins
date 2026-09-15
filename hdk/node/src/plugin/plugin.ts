import { Readable, Writable } from "stream";
import { HookName, Hooks } from "../protocol/constants";
import { Context } from "./context";
import { Request } from "./request";
import { Response } from "./response";
import { Result } from "./result";
import { Server } from "./server";

export type RequestHandler = (
  ctx: Context,
  req: Request
) => Promise<Result> | Result;

export type ResponseHandler = (
  ctx: Context,
  resp: Response
) => Promise<Result> | Result;

export type HookHandler = RequestHandler | ResponseHandler;

export interface PluginOptions {
  name: string;
  version?: string;
  description?: string;
  author?: string;
  capabilities?: string[];
}

export class Plugin {
  readonly name: string;
  version: string;
  description: string;
  author: string;
  capabilities: string[];
  readonly requestHandlers: Map<string, RequestHandler>;
  readonly responseHandlers: Map<string, ResponseHandler>;
  readonly customMethods: Map<string, (params: any) => Promise<any> | any>;

  constructor(options: string | PluginOptions) {
    if (typeof options === "string") {
      this.name = options;
      this.version = "0.1.0";
      this.description = "";
      this.author = "";
      this.capabilities = [];
    } else {
      this.name = options.name;
      this.version = options.version || "0.1.0";
      this.description = options.description || "";
      this.author = options.author || "";
      this.capabilities = options.capabilities || [];
    }
    this.requestHandlers = new Map();
    this.responseHandlers = new Map();
    this.customMethods = new Map();
  }

  registerMethod(name: string, handler: (params: any) => Promise<any> | any): this {
    this.customMethods.set(name, handler);
    return this;
  }

  getMethod(name: string): ((params: any) => Promise<any> | any) | undefined {
    return this.customMethods.get(name);
  }

  setVersion(v: string): this {
    this.version = v;
    return this;
  }

  setDescription(desc: string): this {
    this.description = desc;
    return this;
  }

  setAuthor(author: string): this {
    this.author = author;
    return this;
  }

  addCapabilities(...caps: string[]): this {
    this.capabilities.push(...caps);
    return this;
  }

  /**
   * Universal hook registration supporting string literal hook names.
   */
  on(hook: "request.before" | "request.after", handler: RequestHandler): this;
  on(hook: "response.before" | "response.after", handler: ResponseHandler): this;
  on(hook: HookName, handler: any): this {
    if (hook === Hooks.RequestBefore || hook === Hooks.RequestAfter) {
      this.requestHandlers.set(hook, handler);
    } else {
      this.responseHandlers.set(hook, handler);
    }
    return this;
  }

  getRequestHandler(hook: string): RequestHandler | undefined {
    return this.requestHandlers.get(hook);
  }

  getResponseHandler(hook: string): ResponseHandler | undefined {
    return this.responseHandlers.get(hook);
  }

  onRequestBefore(handler: RequestHandler): this {
    return this.on(Hooks.RequestBefore, handler);
  }

  onRequestAfter(handler: RequestHandler): this {
    return this.on(Hooks.RequestAfter, handler);
  }

  onResponseBefore(handler: ResponseHandler): this {
    return this.on(Hooks.ResponseBefore, handler);
  }

  onResponseAfter(handler: ResponseHandler): this {
    return this.on(Hooks.ResponseAfter, handler);
  }

  /**
   * Start plugin event loop using process.stdin and process.stdout.
   */
  async run(): Promise<void> {
    return this.serve(process.stdin, process.stdout);
  }

  /**
   * Serve plugin protocol on custom streams (ideal for testing).
   */
  async serve(input: Readable, output: Writable): Promise<void> {
    const server = new Server(this, input, output);
    return server.serve();
  }
}
