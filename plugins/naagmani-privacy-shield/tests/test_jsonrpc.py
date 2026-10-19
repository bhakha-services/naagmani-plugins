"""
JSON-RPC Integration test for naagmani-privacy-shield stdio protocol.
Simulates Naagmani OS subprocess execution and verifies IPC responses.
"""
import io
import json
from main import plugin


def run_rpc(requests):
    in_buf = io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n")
    out_buf = io.StringIO()
    plugin.serve(in_buf, out_buf)
    out_lines = [line.strip() for line in out_buf.getvalue().splitlines() if line.strip()]
    return [json.loads(line) for line in out_lines]


def test_jsonrpc_handshake_and_provider_before():
    reqs = [
        # 1. Registration handshake
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "plugin.register",
            "params": {
                "plugin_name": "naagmani-privacy-shield",
                "protocol_version": "naagmani.plugin/v1",
            },
        },
        # 2. Health check
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "plugin.health",
            "params": {},
        },
        # 3. Invoke provider.before hook
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "plugin.hook.invoke",
            "params": {
                "hook": "provider.before",
                "context": {
                    "hook": "provider.before",
                    "request_id": "req_rpc_test",
                    "tenant": {
                        "organization_id": "org_test",
                        "project_id": "proj_test",
                        "environment_id": "production",
                    },
                    "config": {
                        "confidence_threshold": 0.6,
                    },
                    "request": {
                        "model": "gpt-4o",
                        "stream": False,
                        "messages": [
                            {"role": "user", "content": "Please contact test_user@company.com immediately"},
                        ],
                    },
                },
            },
        },
    ]

    responses = run_rpc(reqs)
    assert len(responses) == 3

    # Check Registration response
    reg_resp = responses[0]
    assert reg_resp.get("id") == 1
    assert reg_resp.get("result", {}).get("status") == "ok"
    assert "privacy.pii" in reg_resp.get("result", {}).get("capabilities", [])

    # Check Health response
    health_resp = responses[1]
    assert health_resp.get("id") == 2
    assert health_resp.get("result", {}).get("status") == "healthy"

    # Check provider.before response
    hook_resp = responses[2]
    assert hook_resp.get("id") == 3
    result = hook_resp.get("result", {})
    assert result.get("decision") == "modify"

    # Verify TokenMappings were emitted across JSON-RPC stdout
    token_mappings = result.get("token_mappings", [])
    assert len(token_mappings) >= 1
    mapping = token_mappings[0]
    assert mapping["entity"] == "EMAIL_ADDRESS"
    assert mapping["original"] == "test_user@company.com"
    assert mapping["placeholder"].startswith("[EMAIL_ADDRESS_")

    # Verify modified request
    mod_req = result.get("modified_request", {})
    mod_content = mod_req.get("messages", [])[0].get("content")
    assert "test_user@company.com" not in mod_content
    assert mapping["placeholder"] in mod_content
