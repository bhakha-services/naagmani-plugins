"""
Outbound Payload Tokenization & Sanitization for Naagmani Privacy Shield.
Reversibly tokenizes protected PII into 128-bit placeholders, applies masks/redactions,
enforces BLOCK decisions, and guarantees no plaintext leakage.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from naagmani.plugin import Message, Request

from .engine import PrivacyEngine
from .policy import PolicyAction, PrivacyPolicy


class TokenizationError(Exception):
    """Raised when tokenization fails or blocked entity is detected."""
    pass


class Tokenizer:
    def __init__(self, engine: PrivacyEngine):
        self.engine = engine

    def process_request(
        self,
        req: Request,
        policy: PrivacyPolicy,
    ) -> Tuple[Request, List[Dict[str, str]], Optional[str]]:
        """
        Sanitizes request messages and tool arguments.
        Returns:
            - sanitized Request
            - list of TokenMapping dicts ({"placeholder": ..., "entity": ..., "original": ...})
            - block_reason (if any entity was BLOCKED, None otherwise)
        """
        token_mappings: List[Dict[str, str]] = []
        sanitized_messages: List[Message] = []

        for msg in req.messages:
            sanitized_content, mappings, block_reason = self.sanitize_content(msg.content, policy)
            if block_reason:
                return req, [], block_reason

            token_mappings.extend(mappings)
            sanitized_messages.append(Message(role=msg.role, content=sanitized_content, name=msg.name))

        # Schema-preserving inspection of tool definitions and arguments
        sanitized_tools = []
        for tool in req.tools:
            if isinstance(tool, dict):
                sanitized_tool, tool_mappings, block_reason = self.sanitize_tool_definition(tool, policy)
                if block_reason:
                    return req, [], block_reason
                token_mappings.extend(tool_mappings)
                sanitized_tools.append(sanitized_tool)
            else:
                sanitized_tools.append(tool)

        # Verification pass: ensure NO original values exist in sanitized messages (outside placeholders)
        placeholder_regex = re.compile(r"\[[A-Z0-9_]+_[a-f0-9]{32}\]|\[REDACTED_[A-Z0-9_]+\]")
        for mapping in token_mappings:
            orig = mapping.get("original_value") or mapping.get("original")
            if not orig:
                continue
            for s_msg in sanitized_messages:
                content_clean = placeholder_regex.sub(" ", s_msg.content)
                if orig in content_clean:
                    ent = mapping.get("entity_type") or mapping.get("entity")
                    raise TokenizationError(
                        f"outbound leakage check failed: original plaintext for entity {ent} "
                        f"still present in message payload"
                    )

        sanitized_req = Request()
        sanitized_req.model = req.model
        sanitized_req.stream = req.stream
        sanitized_req.messages = sanitized_messages
        sanitized_req.tools = sanitized_tools
        sanitized_req.metadata = dict(req.metadata)

        return sanitized_req, token_mappings, None

    def sanitize_content(
        self,
        content: str,
        policy: PrivacyPolicy,
    ) -> Tuple[str, List[Dict[str, str]], Optional[str]]:
        """
        Sanitizes message content. If content is valid JSON, applies schema-preserving
        recursive traversal so control structures remain valid.
        """
        if not content or not content.strip():
            return content, [], None

        trimmed = content.strip()
        if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
            try:
                parsed = json.loads(trimmed)
                sanitized_data, mappings, block_reason = self.sanitize_structured_data(parsed, policy)
                if block_reason:
                    return content, [], block_reason
                if mappings:
                    return json.dumps(sanitized_data, ensure_ascii=False), mappings, None
                return content, [], None
            except (json.JSONDecodeError, ValueError):
                pass

        return self.sanitize_text(content, policy)

    def sanitize_structured_data(
        self,
        data: Any,
        policy: PrivacyPolicy,
    ) -> Tuple[Any, List[Dict[str, str]], Optional[str]]:
        """
        Recursively sanitizes values in structured dicts/lists while preserving
        control keys, data types, and JSON schema integrity.
        """
        if isinstance(data, dict):
            sanitized_dict = {}
            all_mappings = []
            for k, v in data.items():
                sanitized_val, mappings, block_reason = self.sanitize_structured_data(v, policy)
                if block_reason:
                    return data, [], block_reason
                all_mappings.extend(mappings)
                sanitized_dict[k] = sanitized_val
            return sanitized_dict, all_mappings, None

        elif isinstance(data, list):
            sanitized_list = []
            all_mappings = []
            for item in data:
                sanitized_item, mappings, block_reason = self.sanitize_structured_data(item, policy)
                if block_reason:
                    return data, [], block_reason
                all_mappings.extend(mappings)
                sanitized_list.append(sanitized_item)
            return sanitized_list, all_mappings, None

        elif isinstance(data, str):
            return self.sanitize_text(data, policy)

        else:
            return data, [], None

    def sanitize_tool_definition(
        self,
        tool: Dict[str, Any],
        policy: PrivacyPolicy,
    ) -> Tuple[Dict[str, Any], List[Dict[str, str]], Optional[str]]:
        """
        Schema-preserving inspection of tool definitions.
        Preserves function name and schema structure; sanitizes descriptions and default values.
        """
        sanitized = dict(tool)
        mappings = []
        if "function" in sanitized and isinstance(sanitized["function"], dict):
            fn = dict(sanitized["function"])
            if "description" in fn and isinstance(fn["description"], str):
                s_desc, desc_maps, block_reason = self.sanitize_text(fn["description"], policy)
                if block_reason:
                    return tool, [], block_reason
                fn["description"] = s_desc
                mappings.extend(desc_maps)
            if "parameters" in fn and isinstance(fn["parameters"], dict):
                s_params, param_maps, block_reason = self.sanitize_structured_data(fn["parameters"], policy)
                if block_reason:
                    return tool, [], block_reason
                fn["parameters"] = s_params
                mappings.extend(param_maps)
            sanitized["function"] = fn
        return sanitized, mappings, None

    def sanitize_text(
        self,
        text: str,
        policy: PrivacyPolicy,
    ) -> Tuple[str, List[Dict[str, str]], Optional[str]]:
        """
        Applies policy actions to detected entities in text.
        Replaces spans in reverse offset order to maintain index integrity.
        """
        if not text or not text.strip():
            return text, [], None

        results = self.engine.analyze(text, policy)
        if not results:
            return text, [], None

        # Sort reverse by start position
        sorted_results = sorted(results, key=lambda r: r.start, reverse=True)

        mappings: List[Dict[str, str]] = []
        chars = list(text)

        # Track processed intervals to avoid nested corruption
        processed_intervals: List[Tuple[int, int]] = []

        for r in sorted_results:
            start, end = r.start, r.end

            # Check overlap with already-replaced spans
            overlap = any(not (end <= p_start or start >= p_end) for p_start, p_end in processed_intervals)
            if overlap:
                continue

            entity_type = r.entity_type
            original_val = text[start:end]
            action = policy.get_action_for_entity(entity_type)

            if action == PolicyAction.BLOCK:
                return text, [], f"Blocked high-risk protected entity: {entity_type}"

            elif action == PolicyAction.ALLOW:
                continue

            elif action == PolicyAction.REDACT:
                replacement = f"[REDACTED_{entity_type}]"
                chars[start:end] = list(replacement)
                processed_intervals.append((start, end))

            elif action == PolicyAction.MASK:
                # Mask with asterisks preserving length or fixed 4-asterisk mask
                mask_len = max(4, len(original_val))
                replacement = "*" * mask_len
                chars[start:end] = list(replacement)
                processed_intervals.append((start, end))

            elif action == PolicyAction.TOKENIZE:
                placeholder = self.engine.generate_placeholder(entity_type)
                mappings.append({
                    "placeholder": placeholder,
                    "original_value": original_val,
                    "entity_type": entity_type,
                    "original": original_val,
                    "entity": entity_type,
                })
                chars[start:end] = list(placeholder)
                processed_intervals.append((start, end))

        sanitized_text = "".join(chars)
        return sanitized_text, mappings, None
