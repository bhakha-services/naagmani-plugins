"""
Unit tests for Policy Evaluation, Tenant Scoping, and Environment Isolation.
"""
import pytest
from shield.policy import InvalidEnvironmentError, PolicyAction, PrivacyPolicy, resolve_policy


def test_resolve_policy_tenant_scoping():
    config_a = {
        "confidence_threshold": 0.85,
        "default_action": "REDACT",
        "action_map": {"PHONE_NUMBER": "TOKENIZE"},
        "allow_list": ["corporate@company.com"],
    }

    policy_a = resolve_policy(config_a, "org_1", "proj_a", "test")
    assert policy_a.organization_id == "org_1"
    assert policy_a.project_id == "proj_a"
    assert policy_a.environment_id == "test"
    assert policy_a.confidence_threshold == 0.85
    assert policy_a.default_action == PolicyAction.REDACT
    assert policy_a.get_action_for_entity("PHONE_NUMBER") == PolicyAction.TOKENIZE
    assert policy_a.get_action_for_entity("EMAIL_ADDRESS") == PolicyAction.REDACT
    assert policy_a.is_allowed("corporate@company.com") is True

    # Separate project with distinct config
    config_b = {
        "confidence_threshold": 0.50,
        "default_action": "TOKENIZE",
        "allow_list": [],
    }

    policy_b = resolve_policy(config_b, "org_1", "proj_b", "production")
    assert policy_b.project_id == "proj_b"
    assert policy_b.environment_id == "production"
    assert policy_b.confidence_threshold == 0.50
    assert policy_b.default_action == PolicyAction.TOKENIZE
    assert policy_b.is_allowed("corporate@company.com") is False


def test_environment_scoping_strictness():
    # Valid environment 'test'
    p_test = resolve_policy({}, "org_x", "proj_x", "test")
    assert p_test.environment_id == "test"

    # Valid environment 'production'
    p_prod = resolve_policy({}, "org_x", "proj_x", "production")
    assert p_prod.environment_id == "production"

    # Invalid environments must strictly raise InvalidEnvironmentError fail-closed
    for invalid_env in ["staging", "dev", "local", "sandbox", "", None]:
        with pytest.raises(InvalidEnvironmentError):
            resolve_policy({}, "org_x", "proj_x", invalid_env)

    # Missing org or project must raise ValueError
    with pytest.raises(ValueError):
        resolve_policy({}, "", "proj_x", "production")
    with pytest.raises(ValueError):
        resolve_policy({}, "org_x", "", "production")
