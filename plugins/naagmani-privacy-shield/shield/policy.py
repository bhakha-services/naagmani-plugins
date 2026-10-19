"""
Multi-Tenant Privacy Policy Evaluator for Naagmani Privacy Shield.
Scopers policies by Organization, Project, and Environment ('test' vs 'production').
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class PolicyAction(str, Enum):
    TOKENIZE = "TOKENIZE"  # Reversible tokenization via OS Vault
    MASK = "MASK"          # Static character masking (irreversible)
    REDACT = "REDACT"      # Remove and replace with [REDACTED]
    ALLOW = "ALLOW"        # Permit raw plaintext
    BLOCK = "BLOCK"        # Fail-closed rejection of provider dispatch


@dataclass
class PrivacyPolicy:
    """
    Resolved privacy policy for an authenticated execution scope.
    """
    organization_id: str
    project_id: str
    environment_id: str  # "test" or "production"
    confidence_threshold: float = 0.60
    action_map: Dict[str, PolicyAction] = field(default_factory=dict)
    default_action: PolicyAction = PolicyAction.TOKENIZE
    allow_list: Set[str] = field(default_factory=set)
    block_list: Set[str] = field(default_factory=set)
    inspect_response_pii: bool = False
    strict_streaming_no_downgrade: bool = False

    def get_action_for_entity(self, entity_type: str) -> PolicyAction:
        """
        Resolve the configured policy action for a given entity type.
        """
        # Critical credentials default to BLOCK if not explicitly overridden
        if entity_type == "API_KEY" and entity_type not in self.action_map:
            return PolicyAction.BLOCK

        return self.action_map.get(entity_type, self.default_action)

    def is_allowed(self, text: str) -> bool:
        """
        Check if text or substring is explicitly allow-listed.
        """
        clean = text.strip().lower()
        return clean in self.allow_list


class InvalidEnvironmentError(Exception):
    """Raised when environment identifier is invalid or missing."""
    pass


def resolve_policy(config: Dict[str, Any], org_id: str, project_id: str, env_id: str) -> PrivacyPolicy:
    """
    Construct a PrivacyPolicy from tenant scoped configuration and verified context.
    Strictly validates environments (only 'test' and 'production' permitted).
    Rejects missing, empty, or invalid environments fail-closed.
    """
    if not org_id or not project_id:
        raise ValueError("Tenant context violation: organization_id and project_id are required")

    normalized_env = (env_id or "").strip().lower()
    if normalized_env not in ("test", "production"):
        raise InvalidEnvironmentError(
            f"Access denied: invalid environment '{env_id}'. Only 'test' and 'production' are permitted."
        )

    threshold = float(config.get("confidence_threshold", 0.60))

    action_map: Dict[str, PolicyAction] = {}
    raw_actions = config.get("action_map") or {}
    for entity, action_str in raw_actions.items():
        try:
            action_map[entity.upper()] = PolicyAction(action_str.upper())
        except ValueError:
            action_map[entity.upper()] = PolicyAction.TOKENIZE

    # Allow and block lists
    raw_allow = config.get("allow_list") or []
    allow_list = {str(item).strip().lower() for item in raw_allow}
    # Common transliterated Hindi particles that small English NER models misclassify
    default_hindi_particles = {"hai", "hain", "aur", "mera", "meri", "mere", "kripya", "karo", "ka", "ki", "ke", "ko", "se", "me", "mein"}
    allow_list.update(default_hindi_particles)

    raw_block = config.get("block_list") or []
    block_list = {str(item).strip().lower() for item in raw_block}

    inspect_response = bool(config.get("inspect_response_pii", False))
    strict_streaming = bool(config.get("strict_streaming_no_downgrade", False))

    default_action_str = str(config.get("default_action", "TOKENIZE")).upper()
    try:
        default_action = PolicyAction(default_action_str)
    except ValueError:
        default_action = PolicyAction.TOKENIZE

    return PrivacyPolicy(
        organization_id=org_id,
        project_id=project_id,
        environment_id=normalized_env,
        confidence_threshold=threshold,
        action_map=action_map,
        default_action=default_action,
        allow_list=allow_list,
        block_list=block_list,
        inspect_response_pii=inspect_response,
        strict_streaming_no_downgrade=strict_streaming,
    )
