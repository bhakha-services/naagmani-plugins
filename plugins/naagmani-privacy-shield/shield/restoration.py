"""
Response Inspector & Sanitizer for Naagmani Privacy Shield (provider.after hook).
Audits final responses, detects model-generated sensitive data, and enforces policy redactions.
"""
from typing import Optional, Tuple

from naagmani.plugin import Response

from .engine import PrivacyEngine
from .policy import PolicyAction, PrivacyPolicy


class ResponseInspector:
    def __init__(self, engine: PrivacyEngine):
        self.engine = engine

    def inspect_response(
        self,
        resp: Response,
        policy: PrivacyPolicy,
    ) -> Tuple[Optional[Response], Optional[str]]:
        """
        Inspects provider response before delivery to the client.
        If inspect_response_pii is enabled, detects if model generated new sensitive PII
        and applies policy actions (redact or block).
        Returns:
            - modified Response (or None if unchanged)
            - block_reason (if response violates policy and should be blocked)
        """
        if not resp.content:
            return None, None

        if not policy.inspect_response_pii:
            return None, None

        results = self.engine.analyze(resp.content, policy)
        if not results:
            return None, None

        sorted_results = sorted(results, key=lambda r: r.start, reverse=True)
        chars = list(resp.content)
        modified = False
        processed_intervals = []

        for r in sorted_results:
            start, end = r.start, r.end
            overlap = any(not (end <= p_start or start >= p_end) for p_start, p_end in processed_intervals)
            if overlap:
                continue

            entity_type = r.entity_type
            action = policy.get_action_for_entity(entity_type)

            if action == PolicyAction.BLOCK:
                return None, f"Response blocked: provider generated prohibited sensitive entity: {entity_type}"

            elif action in (PolicyAction.MASK, PolicyAction.REDACT, PolicyAction.TOKENIZE):
                # On response side, new sensitive PII cannot be tokenized into vault; redact it
                replacement = f"[REDACTED_{entity_type}]"
                chars[start:end] = list(replacement)
                processed_intervals.append((start, end))
                modified = True

        if modified:
            new_resp = Response()
            new_resp.model = resp.model
            new_resp.content = "".join(chars)
            new_resp.usage = resp.usage
            return new_resp, None

        return None, None
