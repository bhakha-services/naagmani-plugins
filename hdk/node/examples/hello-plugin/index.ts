import { Plugin, Result } from "@naagmani/hdk";

const plugin = new Plugin({
  name: "hello-plugin-node",
  version: "0.1.0",
  description: "Hello World plugin written in Node.js TypeScript",
  author: "developer",
});

plugin.on("request.before", async (ctx, req) => {
  console.error(`[hello-plugin-node] intercepted request ID=${ctx.requestId}`);
  req.addMessage("user", "Hello from Node.js HDK!");
  return Result.modifyRequest(req);
});

plugin.run().catch((err) => {
  console.error("Plugin failed to run:", err);
  process.exit(1);
});
