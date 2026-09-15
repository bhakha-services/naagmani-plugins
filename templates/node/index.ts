import { Plugin, Result, Context, Request } from "@naagmani/hdk";

const plugin = new Plugin({
  name: "my-node-plugin",
  version: "0.1.0",
  description: "A starter Naagmani plugin built with Node.js & TypeScript",
  author: "developer",
});

plugin.onRequestBefore(async (ctx: Context, req: Request) => {
  console.error(`[my-node-plugin] processing request ID=${ctx.requestId} model=${req.model}`);
  return Result.continue();
});

plugin.start().catch((err: Error) => {
  console.error(`[my-node-plugin] fatal error:`, err);
  process.exit(1);
});
