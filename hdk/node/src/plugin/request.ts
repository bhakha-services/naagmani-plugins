import { HookMessage, HookRequest } from "../protocol/messages";

export interface Message {
  role: string;
  content: string;
}

export class Request {
  model: string;
  messages: Message[];
  stream: boolean;

  constructor(protoReq?: HookRequest) {
    this.model = protoReq?.model || "";
    this.messages = (protoReq?.messages || []).map((m) => ({
      role: m.role,
      content: m.content,
    }));
    this.stream = Boolean(protoReq?.stream);
  }

  /**
   * Combined text of all user messages in the request.
   */
  promptText(): string {
    return this.messages
      .filter((m) => m.role === "user")
      .map((m) => m.content)
      .join("\n");
  }

  /**
   * Append a new message to the chat history.
   */
  addMessage(role: string, content: string): void {
    this.messages.push({ role, content });
  }

  toProtocol(): HookRequest {
    return {
      model: this.model,
      messages: this.messages.map((m) => ({ role: m.role, content: m.content })),
      stream: this.stream,
    };
  }
}
