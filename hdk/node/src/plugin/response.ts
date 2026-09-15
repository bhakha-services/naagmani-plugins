import { HookResponse, HookUsage } from "../protocol/messages";

export interface Usage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

export class Response {
  model: string;
  content: string;
  usage?: Usage;

  constructor(protoResp?: HookResponse) {
    this.model = protoResp?.model || "";
    this.content = protoResp?.content || "";
    if (protoResp?.usage) {
      this.usage = {
        promptTokens: protoResp.usage.prompt_tokens,
        completionTokens: protoResp.usage.completion_tokens,
        totalTokens: protoResp.usage.total_tokens,
      };
    }
  }

  toProtocol(): HookResponse {
    const proto: HookResponse = {
      model: this.model,
      content: this.content,
    };
    if (this.usage) {
      proto.usage = {
        prompt_tokens: this.usage.promptTokens,
        completion_tokens: this.usage.completionTokens,
        total_tokens: this.usage.totalTokens,
      };
    }
    return proto;
  }
}
