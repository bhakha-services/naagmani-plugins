import { Plugin, Result } from "@naagmani/hdk";

const plugin = new Plugin({
  name: "ai-firewall-node",
  version: "1.0.0",
  description: "Naagmani AI Firewall reference plugin in Node.js",
  author: "Naagmani Security Team",
});

const INJECTION_PATTERNS = [
  /ignore\s+(all\s+)?(previous|prior)\s+instructions/i,
  /bypass\s+(the\s+)?(ai\s+)?firewall/i,
  /system\s+prompt\s+leak/i,
  /dan\s+mode\s+enabled/i,
  /jailbreak/i,
];

plugin.on("request.before", async (ctx, req) => {
  const prompt = req.promptText();
  console.error(`[ai-firewall-node] inspecting request ID=${ctx.requestId}`);

  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(prompt)) {
      console.error(`[ai-firewall-node] blocked prompt injection pattern: ${pattern}`);
      return Result.block("Prompt injection attack detected by AI Firewall Node");
    }
  }

  return Result.continue();
});

plugin.run().catch((err) => {
  console.error("AI Firewall Node runtime error:", err);
  process.exit(1);
});
