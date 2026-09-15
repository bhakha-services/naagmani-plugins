import { Plugin, Result } from "@naagmani/hdk";

const plugin = new Plugin({
  name: "mcp",
  version: "1.0.0",
  description: "Naagmani Model Context Protocol (MCP) Tool Execution Plugin",
  author: "Naagmani Tool Team",
  capabilities: ["tools.mcp", "tools.function"],
});

// ----------------------------------------------------------------------
// Tool Definitions and Registry
// ----------------------------------------------------------------------

interface ToolDefinition {
  name: string;
  description: string;
  input_schema: {
    type: string;
    properties: Record<string, { type: string; description?: string }>;
    required?: string[];
  };
}

const TOOLS: Record<string, ToolDefinition> = {
  get_weather: {
    name: "get_weather",
    description: "Get current weather condition and temperature for a city",
    input_schema: {
      type: "object",
      properties: {
        city: { type: "string", description: "City name, e.g. San Francisco or Tokyo" },
      },
      required: ["city"],
    },
  },
  get_ticket_status: {
    name: "get_ticket_status",
    description: "Get the support ticket status and assigned department",
    input_schema: {
      type: "object",
      properties: {
        ticket_id: { type: "string", description: "Unique ticket identifier, e.g. 1234" },
      },
      required: ["ticket_id"],
    },
  },
};

// ----------------------------------------------------------------------
// Schema Validation & Tool Execution
// ----------------------------------------------------------------------

function validateToolArgs(toolDef: ToolDefinition, args: any): { valid: boolean; error?: string } {
  if (!args || typeof args !== "object") {
    return { valid: false, error: "Tool arguments must be a JSON object" };
  }

  if (toolDef.input_schema.required) {
    for (const reqField of toolDef.input_schema.required) {
      if (args[reqField] === undefined || args[reqField] === null || args[reqField] === "") {
        return { valid: false, error: `Missing required property: ${reqField}` };
      }
    }
  }

  for (const [propName, propDef] of Object.entries(toolDef.input_schema.properties)) {
    if (args[propName] !== undefined) {
      const actualType = typeof args[propName];
      if (propDef.type === "string" && actualType !== "string") {
        return { valid: false, error: `Property ${propName} must be string, got ${actualType}` };
      }
    }
  }

  return { valid: true };
}

function executeTool(
  toolName: string,
  args: any,
  tenantId: string
): { success: boolean; result?: any; error?: string } {
  const toolDef = TOOLS[toolName];
  if (!toolDef) {
    return { success: false, error: `Unknown tool: ${toolName}` };
  }

  const validation = validateToolArgs(toolDef, args);
  if (!validation.valid) {
    return { success: false, error: validation.error };
  }

  // Deterministic Mock Tool Implementations
  switch (toolName) {
    case "get_weather": {
      const city = String(args.city || "Unknown");
      return {
        success: true,
        result: {
          city,
          temperature: "72°F",
          condition: "Sunny",
          humidity: "45%",
          source: "mock-weather-service",
        },
      };
    }

    case "get_ticket_status": {
      const ticketId = String(args.ticket_id);
      return {
        success: true,
        result: {
          ticket_id: ticketId,
          status: "in_progress",
          priority: "high",
          department: "Billing Support",
          tenant_id: tenantId,
          updated_at: "2026-09-12T12:00:00Z",
        },
      };
    }

    default:
      return { success: false, error: `Unsupported tool: ${toolName}` };
  }
}

// ----------------------------------------------------------------------
// JSON-RPC Capability Methods
// ----------------------------------------------------------------------

plugin.registerMethod("tools.list", () => {
  return {
    tools: Object.values(TOOLS),
  };
});

plugin.registerMethod("tools.execute", (params: any) => {
  const tool = params?.tool;
  const args = params?.arguments || {};
  const tenantId = params?.tenant_id || "default";

  console.error(`[mcp] tool.invoked tool=${tool} tenant=${tenantId}`);

  const execRes = executeTool(tool, args, tenantId);
  if (!execRes.success) {
    throw new Error(execRes.error || "Tool execution failed");
  }

  return {
    status: "success",
    tool,
    result: execRes.result,
  };
});

// ----------------------------------------------------------------------
// Pipeline Hook: request.before
// ----------------------------------------------------------------------

plugin.on("request.before", async (ctx, req) => {
  const prompt = req.promptText();
  const tenantId = ctx.orgId || "default";

  console.error(`[mcp] request.before tenant=${tenantId} request_id=${ctx.requestId}`);

  let executedTool: string | null = null;
  let toolOutput: any = null;

  // Check for ticket status queries: e.g. "status of ticket 1234" or "ticket 1234"
  const ticketMatch = prompt.match(/ticket\s*(?:#|id\s*)?(\w+)/i);
  if (ticketMatch && ticketMatch[1]) {
    const ticketId = ticketMatch[1];
    const res = executeTool("get_ticket_status", { ticket_id: ticketId }, tenantId);
    if (res.success) {
      executedTool = "get_ticket_status";
      toolOutput = res.result;
      console.error(
        `[mcp] tool.invoked tool=get_ticket_status tenant=${tenantId} request_id=${ctx.requestId}`
      );
    }
  }

  // Check for weather queries: e.g. "weather in San Francisco"
  const weatherMatch = prompt.match(/weather\s+in\s+([A-Za-z\s]+)/i);
  if (!executedTool && weatherMatch && weatherMatch[1]) {
    const city = weatherMatch[1].trim();
    const res = executeTool("get_weather", { city }, tenantId);
    if (res.success) {
      executedTool = "get_weather";
      toolOutput = res.result;
      console.error(
        `[mcp] tool.invoked tool=get_weather tenant=${tenantId} request_id=${ctx.requestId}`
      );
    }
  }

  if (executedTool && toolOutput) {
    const toolResultBlock = `\n\n[Tool Result (${executedTool})]:\n${JSON.stringify(toolOutput)}`;
    const lastUserMsg = [...req.messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      lastUserMsg.content += toolResultBlock;
      console.error(`[mcp] augmented request with tool result for ${executedTool}`);
      return Result.modifyRequest(req);
    }
  }

  return Result.continue();
});

plugin.run().catch((err) => {
  console.error("MCP Plugin runtime error:", err);
  process.exit(1);
});
