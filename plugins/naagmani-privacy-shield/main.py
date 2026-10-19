"""
Naagmani Privacy Shield — Official Production Python Security Plugin
Provides pre-provider PII tokenization, Indian national identifier detection,
and response privacy inspection for Naagmani AI Operating System.
"""
import os
import sys

# Ensure self-contained vendor and site-packages directories are available in sys.path
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_VENDOR_DIR = os.path.join(_BASE_DIR, "vendor")
_SP_DIR = os.path.join(_BASE_DIR, "site-packages")
for _d in [_VENDOR_DIR, _SP_DIR]:
    if os.path.isdir(_d) and _d not in sys.path:
        sys.path.insert(0, _d)

# Enforce 100% offline execution for tldextract (used by presidio email recognizer)
os.environ["TLDEXTRACT_PUBLIC_SUFFIX_LIST_URLS"] = ""

from naagmani.plugin import Context, Plugin, Request, Response, Result

from shield import (
    PrivacyEngine,
    ResponseInspector,
    Tokenizer,
    resolve_policy,
)

plugin = Plugin(
    name="naagmani-privacy-shield",
    version="1.0.0",
    description="Official Naagmani AI Privacy Shield and PII Tokenizer",
    author="Bhakha Services / Naagmani Security Team",
    capabilities=["privacy.pii"],
)

engine = PrivacyEngine()
tokenizer = Tokenizer(engine)
inspector = ResponseInspector(engine)


@plugin.on_provider_before
def handle_provider_before(ctx: Context, req: Request) -> Result:
    """
    Executes at canonical provider dispatch boundary before inference payload serialization.
    Detects sensitive entities, applies tenant policy, generates 128-bit placeholders,
    and returns token mappings for privileged OS Vault envelope encryption.
    """
    org_id = ctx.org_id
    project_id = ctx.project_id
    env_id = ctx.environment_id

    try:
        policy = resolve_policy(ctx.config, org_id, project_id, env_id)
        sanitized_req, mappings, block_reason = tokenizer.process_request(req, policy)
        if block_reason:
            return Result.block(block_reason)

        if mappings or sanitized_req.messages != req.messages:
            return Result.modify_request(sanitized_req, token_mappings=mappings)

        return Result.continue_()

    except Exception as e:
        # In fail-close posture, any policy or internal processing failure aborts request
        return Result.block(f"Privacy Shield security policy violation: {e}")


@plugin.on_provider_after
def handle_provider_after(ctx: Context, resp: Response) -> Result:
    """
    Executes after provider inference and OS Vault token restoration.
    Performs full response PII audit if policy requires and enforces safety constraints.
    """
    org_id = ctx.org_id
    project_id = ctx.project_id
    env_id = ctx.environment_id

    try:
        policy = resolve_policy(ctx.config, org_id, project_id, env_id)
        modified_resp, block_reason = inspector.inspect_response(resp, policy)
        if block_reason:
            return Result.block(block_reason)

        if modified_resp:
            return Result.modify_response(modified_resp)

        return Result.continue_()

    except Exception as e:
        return Result.block(f"Privacy Shield response security violation: {e}")


if __name__ == "__main__":
    plugin.run()
