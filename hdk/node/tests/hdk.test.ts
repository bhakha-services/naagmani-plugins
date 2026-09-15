import { test, describe } from "node:test";
import * as assert from "node:assert";
import { PassThrough } from "stream";
import {
  Plugin,
  Result,
  PROTOCOL_VERSION,
  ErrorCodes,
  Methods,
  Hooks,
  Decisions,
} from "../src";

function createHarness(plugin: Plugin) {
  const stdin = new PassThrough();
  const stdout = new PassThrough();

  const servePromise = plugin.serve(stdin, stdout);

  let buffer = "";
  const responses: any[] = [];
  stdout.on("data", (chunk: Buffer) => {
    buffer += chunk.toString("utf8");
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (line.trim()) {
        responses.push(JSON.parse(line.trim()));
      }
    }
  });

  async function call(method: string, params?: any, id: number = 1): Promise<any> {
    const payload = JSON.stringify({
      jsonrpc: "2.0",
      method,
      params,
      id,
    }) + "\n";
    stdin.write(payload);

    // Wait for response with matching id
    const start = Date.now();
    while (Date.now() - start < 2000) {
      const idx = responses.findIndex((r) => r.id === id);
      if (idx !== -1) {
        return responses.splice(idx, 1)[0];
      }
      await new Promise((r) => setTimeout(r, 10));
    }
    throw new Error(`Timeout waiting for response to ${method}`);
  }

  return { stdin, stdout, call, servePromise };
}

describe("Node.js HDK Tests", () => {
  test("Registration Handshake", async () => {
    const plugin = new Plugin({
      name: "test-plugin",
      version: "1.2.3",
      capabilities: ["filter"],
    });

    const harness = createHarness(plugin);

    const resp = await harness.call(Methods.Register, {
      plugin_name: "test-plugin",
      plugin_version: "1.2.3",
      api_version: "v1",
      protocol_version: PROTOCOL_VERSION,
      permissions: ["request.read"],
    });

    assert.strictEqual(resp.error, undefined);
    assert.strictEqual(resp.result.status, "ok");
    assert.strictEqual(resp.result.protocol_version, PROTOCOL_VERSION);
    assert.deepStrictEqual(resp.result.capabilities, ["filter"]);

    await harness.call(Methods.Shutdown, {}, 99);
    harness.stdin.end();
    await harness.servePromise;
  });

  test("Protocol Version Mismatch", async () => {
    const plugin = new Plugin("mismatch-plugin");
    const harness = createHarness(plugin);

    const resp = await harness.call(Methods.Register, {
      plugin_name: "mismatch-plugin",
      plugin_version: "0.1.0",
      api_version: "v1",
      protocol_version: "naagmani.plugin/v99",
      permissions: ["request.read"],
    });

    assert.ok(resp.error);
    assert.strictEqual(resp.error.code, ErrorCodes.ProtocolVersionMismatch);

    await harness.call(Methods.Shutdown, {}, 99);
    harness.stdin.end();
    await harness.servePromise;
  });

  test("Health Probe", async () => {
    const plugin = new Plugin("health-plugin");
    const harness = createHarness(plugin);

    const resp = await harness.call(Methods.Health);
    assert.strictEqual(resp.error, undefined);
    assert.strictEqual(resp.result.status, "healthy");
    assert.ok(resp.result.uptime);

    await harness.call(Methods.Shutdown, {}, 99);
    harness.stdin.end();
    await harness.servePromise;
  });

  test("Hook request.before Continue", async () => {
    let capturedOrg: string | undefined;
    const plugin = new Plugin("hook-plugin").onRequestBefore((ctx, req) => {
      capturedOrg = ctx.orgId;
      assert.strictEqual(req.promptText(), "Hello World");
      return Result.continue();
    });

    const harness = createHarness(plugin);

    const resp = await harness.call(Methods.HookInvoke, {
      hook: Hooks.RequestBefore,
      context: {
        hook: Hooks.RequestBefore,
        request_id: "req_123",
        tenant: {
          organization_id: "org_acme",
        },
        request: {
          model: "gpt-4",
          messages: [{ role: "user", content: "Hello World" }],
        },
      },
    });

    assert.strictEqual(capturedOrg, "org_acme");
    assert.strictEqual(resp.error, undefined);
    assert.strictEqual(resp.result.decision, Decisions.Continue);

    await harness.call(Methods.Shutdown, {}, 99);
    harness.stdin.end();
    await harness.servePromise;
  });

  test("Hook request.before Modify", async () => {
    const plugin = new Plugin("modify-plugin").on(Hooks.RequestBefore, (ctx, req) => {
      req.addMessage("system", "Injected system instruction");
      return Result.modifyRequest(req);
    });

    const harness = createHarness(plugin);

    const resp = await harness.call(Methods.HookInvoke, {
      hook: Hooks.RequestBefore,
      context: {
        hook: Hooks.RequestBefore,
        request_id: "req_mod",
        request: {
          model: "mock-model",
          messages: [{ role: "user", content: "Original" }],
        },
      },
    });

    assert.strictEqual(resp.result.decision, Decisions.Modify);
    assert.strictEqual(resp.result.modified_request.messages.length, 2);
    assert.strictEqual(resp.result.modified_request.messages[1].content, "Injected system instruction");

    await harness.call(Methods.Shutdown, {}, 99);
    harness.stdin.end();
    await harness.servePromise;
  });

  test("Hook request.before Block", async () => {
    const plugin = new Plugin("firewall-plugin").onRequestBefore((ctx, req) => {
      if (req.promptText().includes("evil")) {
        return Result.block("Prompt injection attack detected");
      }
      return Result.continue();
    });

    const harness = createHarness(plugin);

    const resp = await harness.call(Methods.HookInvoke, {
      hook: Hooks.RequestBefore,
      context: {
        hook: Hooks.RequestBefore,
        request_id: "req_block",
        request: {
          model: "mock-model",
          messages: [{ role: "user", content: "Run this evil exploit" }],
        },
      },
    });

    assert.strictEqual(resp.result.decision, Decisions.Block);
    assert.strictEqual(resp.result.block_reason, "Prompt injection attack detected");

    await harness.call(Methods.Shutdown, {}, 99);
    harness.stdin.end();
    await harness.servePromise;
  });

  test("Hook response.before Modify", async () => {
    const plugin = new Plugin("resp-plugin").onResponseBefore((ctx, resp) => {
      resp.content = resp.content.replace("secret-key-123", "[REDACTED]");
      return Result.modifyResponse(resp);
    });

    const harness = createHarness(plugin);

    const resp = await harness.call(Methods.HookInvoke, {
      hook: Hooks.ResponseBefore,
      context: {
        hook: Hooks.ResponseBefore,
        request_id: "req_resp",
        response: {
          model: "mock-model",
          content: "Here is your key: secret-key-123",
        },
      },
    });

    assert.strictEqual(resp.result.decision, Decisions.Modify);
    assert.strictEqual(resp.result.modified_response.content, "Here is your key: [REDACTED]");

    await harness.call(Methods.Shutdown, {}, 99);
    harness.stdin.end();
    await harness.servePromise;
  });

  test("Method Not Found", async () => {
    const plugin = new Plugin("unknown-plugin");
    const harness = createHarness(plugin);

    const resp = await harness.call("plugin.unknown_method");
    assert.ok(resp.error);
    assert.strictEqual(resp.error.code, ErrorCodes.MethodNotFound);

    await harness.call(Methods.Shutdown, {}, 99);
    harness.stdin.end();
    await harness.servePromise;
  });

  test("Graceful Shutdown", async () => {
    const plugin = new Plugin("shutdown-plugin");
    const harness = createHarness(plugin);

    const resp = await harness.call(Methods.Shutdown);
    assert.strictEqual(resp.error, undefined);
    assert.strictEqual(resp.result.status, "shutting_down");

    harness.stdin.end();
    await harness.servePromise;
  });

  test("Handler Exception Converted to Continue with Error Message", async () => {
    const plugin = new Plugin("throwing-plugin").onRequestBefore(() => {
      throw new Error("Simulated failure in handler");
    });

    const harness = createHarness(plugin);

    const resp = await harness.call(Methods.HookInvoke, {
      hook: Hooks.RequestBefore,
      context: {
        hook: Hooks.RequestBefore,
        request_id: "req_err",
        request: {
          model: "mock-model",
          messages: [{ role: "user", content: "Test" }],
        },
      },
    });

    assert.strictEqual(resp.error, undefined);
    assert.strictEqual(resp.result.decision, Decisions.Continue);
    assert.strictEqual(resp.result.error, "Simulated failure in handler");

    await harness.call(Methods.Shutdown, {}, 99);
    harness.stdin.end();
    await harness.servePromise;
  });
});
