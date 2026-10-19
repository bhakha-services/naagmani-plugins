"""
Unit tests for Reversible Tokenization, Leakage Verification, and Response Inspection.
"""
import pytest
from naagmani.plugin import Message, Request, Response
from shield.engine import PrivacyEngine
from shield.policy import PolicyAction, PrivacyPolicy
from shield.restoration import ResponseInspector
from shield.tokenization import TokenizationError, Tokenizer


def test_tokenization_reversible_mappings():
    engine = PrivacyEngine()
    tokenizer = Tokenizer(engine)

    policy = PrivacyPolicy(
        organization_id="org_enterprise",
        project_id="proj_ai",
        environment_id="production",
        default_action=PolicyAction.TOKENIZE,
    )

    req = Request({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a customer assistant."},
            {"role": "user", "content": "Contact Alice Walker at alice@example.com or phone 212-555-0199"},
        ],
    })

    sanitized_req, mappings, block_reason = tokenizer.process_request(req, policy)
    assert block_reason is None
    assert len(mappings) >= 2

    user_msg = sanitized_req.messages[1].content
    assert "alice@example.com" not in user_msg
    assert "212-555-0199" not in user_msg

    # Verify 128-bit CSPRNG placeholder structure
    for m in mappings:
        placeholder = m["placeholder"]
        assert placeholder.startswith("[")
        assert placeholder.endswith("]")
        assert len(placeholder) >= 36  # [TAG_<32hex>]
        assert placeholder in user_msg


def test_tokenization_block_decision():
    engine = PrivacyEngine()
    tokenizer = Tokenizer(engine)

    policy = PrivacyPolicy(
        organization_id="org_sec",
        project_id="proj_safe",
        environment_id="production",
        action_map={"API_KEY": PolicyAction.BLOCK},
    )

    req = Request({
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": "My secret is sk-proj-1234567890abcdef1234567890abcdef1234567890"},
        ],
    })

    _, mappings, block_reason = tokenizer.process_request(req, policy)
    assert block_reason is not None
    assert "Blocked high-risk protected entity: API_KEY" in block_reason
    assert len(mappings) == 0


def test_tokenization_mask_and_redact():
    engine = PrivacyEngine()
    tokenizer = Tokenizer(engine)

    policy = PrivacyPolicy(
        organization_id="org_sec",
        project_id="proj_mask",
        environment_id="test",
        action_map={
            "EMAIL_ADDRESS": PolicyAction.REDACT,
            "PHONE_NUMBER": PolicyAction.MASK,
        },
    )

    req = Request({
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": "Email: user@test.com Phone: 212-555-1234"},
        ],
    })

    sanitized_req, mappings, block_reason = tokenizer.process_request(req, policy)
    assert block_reason is None
    content = sanitized_req.messages[0].content
    assert "[REDACTED_EMAIL_ADDRESS]" in content
    assert "****" in content
    assert len(mappings) == 0  # Irreversible actions generate no mappings for Vault


def test_response_inspection_new_pii_detected():
    engine = PrivacyEngine()
    inspector = ResponseInspector(engine)

    policy = PrivacyPolicy(
        organization_id="org_inspect",
        project_id="proj_stream",
        environment_id="production",
        inspect_response_pii=True,
    )

    # Provider response contains newly generated email
    resp = Response({
        "model": "gpt-4o",
        "content": "Sure, send an email to leaked_person@domain.com for billing.",
    })

    mod_resp, block_reason = inspector.inspect_response(resp, policy)
    assert block_reason is None
    assert mod_resp is not None
    assert "leaked_person@domain.com" not in mod_resp.content
    assert "[REDACTED_EMAIL_ADDRESS]" in mod_resp.content


def test_hinglish_pan_and_aadhaar_tokenization():
    engine = PrivacyEngine()
    tokenizer = Tokenizer(engine)

    policy = PrivacyPolicy(
        organization_id="org_india",
        project_id="proj_hinglish",
        environment_id="production",
        default_action=PolicyAction.TOKENIZE,
    )

    from shield.recognizers.verhoeff import calculate_verhoeff

    base_uid = "23456789012"
    check_digit = calculate_verhoeff(base_uid)
    valid_aadhaar = f"{base_uid[:4]} {base_uid[4:8]} {base_uid[8:]}{check_digit}"

    # Conversational Hinglish prompts
    prompt = (
        f"Bhai mera PAN card number ABCPE1234F hai aur Aadhaar sankhya {valid_aadhaar} hai. "
        "Paisa is UPI ID par bhejo: suresh@okhdfcbank"
    )

    req = Request({
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
    })

    sanitized_req, mappings, block_reason = tokenizer.process_request(req, policy)
    assert block_reason is None
    assert len(mappings) >= 3

    content = sanitized_req.messages[0].content
    assert "ABCPE1234F" not in content
    assert valid_aadhaar not in content
    assert "suresh@okhdfcbank" not in content
    assert "[IN_PAN_" in content
    assert "[IN_AADHAAR_" in content
    assert "[IN_UPI_" in content


def test_nested_json_content_sanitization():
    import json
    engine = PrivacyEngine()
    tokenizer = Tokenizer(engine)

    policy = PrivacyPolicy(
        organization_id="org_fin",
        project_id="proj_json",
        environment_id="production",
        default_action=PolicyAction.TOKENIZE,
    )

    payload = {
        "status": "success",
        "data": {
            "customer_id": "cust_9981",
            "pan": "ABCPE1234F",
            "contact": {
                "email": "customer@fintech.in",
                "phone": "+91 98765 43210"
            }
        },
        "flags": [True, False, 100]
    }

    req = Request({
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": json.dumps(payload)},
        ],
    })

    sanitized_req, mappings, block_reason = tokenizer.process_request(req, policy)
    assert block_reason is None
    assert len(mappings) >= 2

    # Verify JSON syntax and schema are preserved
    sanitized_str = sanitized_req.messages[0].content
    parsed = json.loads(sanitized_str)
    assert parsed["status"] == "success"
    assert parsed["data"]["customer_id"] == "cust_9981"
    assert "ABCPE1234F" not in parsed["data"]["pan"]
    assert "[IN_PAN_" in parsed["data"]["pan"]
    assert "customer@fintech.in" not in parsed["data"]["contact"]["email"]
    assert "[EMAIL_ADDRESS_" in parsed["data"]["contact"]["email"]
    assert parsed["flags"] == [True, False, 100]


def test_tool_definitions_schema_preserving_sanitization():
    engine = PrivacyEngine()
    tokenizer = Tokenizer(engine)

    policy = PrivacyPolicy(
        organization_id="org_sec",
        project_id="proj_tool",
        environment_id="production",
        default_action=PolicyAction.TOKENIZE,
    )

    req = Request({
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Fetch invoice"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup_taxpayer",
                    "description": "Lookup taxpayer details by PAN ABCPE1234F or email test@corp.com",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pan": {"type": "string", "description": "PAN string"}
                        }
                    }
                }
            }
        ]
    })

    sanitized_req, mappings, block_reason = tokenizer.process_request(req, policy)
    assert block_reason is None
    assert len(mappings) >= 2

    # Verify tool name and structure preserved, description sanitized
    tool = sanitized_req.tools[0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "lookup_taxpayer"
    assert "ABCPE1234F" not in tool["function"]["description"]
    assert "[IN_PAN_" in tool["function"]["description"]

