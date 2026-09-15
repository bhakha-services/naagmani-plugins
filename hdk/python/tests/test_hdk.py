import io
import json
import unittest
from naagmani import (
    Plugin,
    Result,
    PROTOCOL_VERSION,
    CODE_PARSE_ERROR,
    CODE_METHOD_NOT_FOUND,
    CODE_PROTOCOL_VERSION_MISMATCH,
    METHOD_REGISTER,
    METHOD_HEALTH,
    METHOD_SHUTDOWN,
    METHOD_HOOK_INVOKE,
    HOOK_REQUEST_BEFORE,
    HOOK_REQUEST_AFTER,
    HOOK_RESPONSE_BEFORE,
    DECISION_CONTINUE,
    DECISION_MODIFY,
    DECISION_BLOCK,
)

class TestPythonHDK(unittest.TestCase):
    def _run_single(self, plugin: Plugin, method: str, params: dict, req_id: int = 1) -> dict:
        in_buf = io.StringIO(json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id,
        }) + "\n")
        out_buf = io.StringIO()
        plugin.serve(in_buf, out_buf)
        out_buf.seek(0)
        line = out_buf.readline()
        self.assertTrue(bool(line), f"Expected response for {method}")
        return json.loads(line.strip())

    def test_registration_handshake(self):
        p = Plugin("test-python-plugin", version="2.0.0", capabilities=["nlp"])
        resp = self._run_single(p, METHOD_REGISTER, {
            "plugin_name": "test-python-plugin",
            "plugin_version": "2.0.0",
            "api_version": "v1",
            "protocol_version": PROTOCOL_VERSION,
            "permissions": ["request.read"],
        })
        self.assertNotIn("error", resp)
        res = resp["result"]
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["protocol_version"], PROTOCOL_VERSION)
        self.assertEqual(res["capabilities"], ["nlp"])

    def test_protocol_version_mismatch(self):
        p = Plugin("mismatch-plugin")
        resp = self._run_single(p, METHOD_REGISTER, {
            "plugin_name": "mismatch-plugin",
            "plugin_version": "0.1.0",
            "api_version": "v1",
            "protocol_version": "naagmani.plugin/v99",
            "permissions": ["request.read"],
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], CODE_PROTOCOL_VERSION_MISMATCH)

    def test_health_probe(self):
        p = Plugin("health-plugin")
        resp = self._run_single(p, METHOD_HEALTH, {})
        self.assertNotIn("error", resp)
        res = resp["result"]
        self.assertEqual(res["status"], "healthy")
        self.assertIn("uptime", res)

    def test_hook_request_before_continue(self):
        captured_org = None
        p = Plugin("continue-plugin")

        @p.on(HOOK_REQUEST_BEFORE)
        def before(ctx, req):
            nonlocal captured_org
            captured_org = ctx.org_id
            self.assertEqual(req.prompt_text(), "User prompt")
            return Result.continue_()

        resp = self._run_single(p, METHOD_HOOK_INVOKE, {
            "hook": HOOK_REQUEST_BEFORE,
            "context": {
                "hook": HOOK_REQUEST_BEFORE,
                "request_id": "req_1",
                "tenant": {"organization_id": "org_py"},
                "request": {
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": "User prompt"}],
                },
            },
        })
        self.assertEqual(captured_org, "org_py")
        self.assertEqual(resp["result"]["decision"], DECISION_CONTINUE)

    def test_hook_request_before_modify(self):
        p = Plugin("modify-plugin")

        @p.on(HOOK_REQUEST_BEFORE)
        def before(ctx, req):
            req.add_message("system", "Injected Python prompt")
            return Result.modify_request(req)

        resp = self._run_single(p, METHOD_HOOK_INVOKE, {
            "hook": HOOK_REQUEST_BEFORE,
            "context": {
                "hook": HOOK_REQUEST_BEFORE,
                "request_id": "req_mod",
                "request": {
                    "model": "mock-model",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            },
        })
        self.assertEqual(resp["result"]["decision"], DECISION_MODIFY)
        mod_msgs = resp["result"]["modified_request"]["messages"]
        self.assertEqual(len(mod_msgs), 2)
        self.assertEqual(mod_msgs[1]["content"], "Injected Python prompt")

    def test_hook_request_before_block(self):
        p = Plugin("block-plugin")

        @p.on(HOOK_REQUEST_BEFORE)
        def before(ctx, req):
            if "forbidden" in req.prompt_text():
                return Result.block("Security policy violation: forbidden keyword")
            return Result.continue_()

        resp = self._run_single(p, METHOD_HOOK_INVOKE, {
            "hook": HOOK_REQUEST_BEFORE,
            "context": {
                "hook": HOOK_REQUEST_BEFORE,
                "request_id": "req_block",
                "request": {
                    "model": "mock-model",
                    "messages": [{"role": "user", "content": "This is forbidden content"}],
                },
            },
        })
        self.assertEqual(resp["result"]["decision"], DECISION_BLOCK)
        self.assertEqual(resp["result"]["block_reason"], "Security policy violation: forbidden keyword")

    def test_hook_response_before_modify(self):
        p = Plugin("dlp-resp-plugin")

        @p.on(HOOK_RESPONSE_BEFORE)
        def before_resp(ctx, resp):
            resp.content = resp.content.replace("123-456-7890", "[REDACTED_PHONE]")
            return Result.modify_response(resp)

        resp = self._run_single(p, METHOD_HOOK_INVOKE, {
            "hook": HOOK_RESPONSE_BEFORE,
            "context": {
                "hook": HOOK_RESPONSE_BEFORE,
                "request_id": "req_dlp",
                "response": {
                    "model": "mock-model",
                    "content": "Call support at 123-456-7890.",
                },
            },
        })
        self.assertEqual(resp["result"]["decision"], DECISION_MODIFY)
        self.assertEqual(resp["result"]["modified_response"]["content"], "Call support at [REDACTED_PHONE].")

    def test_method_not_found(self):
        p = Plugin("unknown-plugin")
        resp = self._run_single(p, "unknown.method", {})
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], CODE_METHOD_NOT_FOUND)

    def test_handler_exception_converted_to_continue_with_error(self):
        p = Plugin("err-plugin")

        @p.on(HOOK_REQUEST_BEFORE)
        def failing(ctx, req):
            raise ValueError("Intentional exception in Python handler")

        resp = self._run_single(p, METHOD_HOOK_INVOKE, {
            "hook": HOOK_REQUEST_BEFORE,
            "context": {
                "hook": HOOK_REQUEST_BEFORE,
                "request_id": "req_fail",
                "request": {
                    "model": "mock-model",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            },
        })
        self.assertNotIn("error", resp)
        self.assertEqual(resp["result"]["decision"], DECISION_CONTINUE)
        self.assertIn("Intentional exception in Python handler", resp["result"]["error"])

if __name__ == "__main__":
    unittest.main()
