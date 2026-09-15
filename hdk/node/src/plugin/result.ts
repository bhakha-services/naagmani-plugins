import { Decisions, DecisionAction } from "../protocol/constants";
import { HookDecision } from "../protocol/messages";
import { Request } from "./request";
import { Response } from "./response";

export class Result {
  readonly action: DecisionAction;
  readonly blockReason?: string;
  readonly modifiedRequest?: Request;
  readonly modifiedResponse?: Response;

  private constructor(
    action: DecisionAction,
    options?: {
      blockReason?: string;
      modifiedRequest?: Request;
      modifiedResponse?: Response;
    }
  ) {
    this.action = action;
    this.blockReason = options?.blockReason;
    this.modifiedRequest = options?.modifiedRequest;
    this.modifiedResponse = options?.modifiedResponse;
    Object.freeze(this);
  }

  /**
   * Continue normal pipeline execution without modifying the payload.
   */
  static continue(): Result {
    return new Result(Decisions.Continue);
  }

  /**
   * Immediately abort the request with HTTP 403 Forbidden.
   */
  static block(reason: string): Result {
    return new Result(Decisions.Block, { blockReason: reason });
  }

  /**
   * Replace the chat completion request with the modified request.
   */
  static modifyRequest(req: Request): Result {
    return new Result(Decisions.Modify, { modifiedRequest: req });
  }

  /**
   * Replace the chat completion response with the modified response.
   */
  static modifyResponse(resp: Response): Result {
    return new Result(Decisions.Modify, { modifiedResponse: resp });
  }

  toProtocolDecision(): HookDecision {
    return {
      decision: this.action,
      block_reason: this.blockReason,
      modified_request: this.modifiedRequest?.toProtocol(),
      modified_response: this.modifiedResponse?.toProtocol(),
    };
  }
}
