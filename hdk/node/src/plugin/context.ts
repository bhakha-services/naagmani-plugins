import { HookContext, TenantContext } from "../protocol/messages";
import { HookName } from "../protocol/constants";

export class Context {
  readonly hook: HookName;
  readonly requestId: string;
  readonly orgId?: string;
  readonly projectId?: string;
  readonly environmentId?: string;
  readonly metadata: Readonly<Record<string, string>>;

  constructor(protoCtx: HookContext) {
    this.hook = protoCtx.hook;
    this.requestId = protoCtx.request_id;
    this.orgId = protoCtx.tenant?.organization_id;
    this.projectId = protoCtx.tenant?.project_id;
    this.environmentId = protoCtx.tenant?.environment_id;
    this.metadata = Object.freeze({ ...(protoCtx.metadata || {}) });
    Object.freeze(this);
  }

  // Backward compatibility getters
  get organization_id(): string | undefined {
    return this.orgId;
  }
  get project_id(): string | undefined {
    return this.projectId;
  }
  get environment_id(): string | undefined {
    return this.environmentId;
  }
  get request_id(): string {
    return this.requestId;
  }
}
