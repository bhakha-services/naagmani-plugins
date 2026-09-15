import io
import json
import sys
import time
from typing import Any, Dict, Optional, TextIO
from ..protocol.constants import (
    CODE_INTERNAL_ERROR,
    CODE_INVALID_PARAMS,
    CODE_INVALID_REQUEST,
    CODE_METHOD_NOT_FOUND,
    CODE_PARSE_ERROR,
    CODE_PROTOCOL_VERSION_MISMATCH,
    DECISION_CONTINUE,
    HOOK_REQUEST_AFTER,
    HOOK_REQUEST_BEFORE,
    HOOK_RESPONSE_AFTER,
    HOOK_RESPONSE_BEFORE,
    METHOD_HEALTH,
    METHOD_HOOK_INVOKE,
    METHOD_REGISTER,
    METHOD_SHUTDOWN,
    PROTOCOL_VERSION,
)
from ..protocol.jsonrpc import create_error_response, create_success_response, serialize_response
from .context import Context
from .request import Request
from .response import Response
from .result import Result

class Server:
    def __init__(self, plugin: Any, in_stream: Optional[TextIO] = None, out_stream: Optional[TextIO] = None):
        self.plugin = plugin
        self.in_stream: TextIO = in_stream if in_stream is not None else sys.stdin
        self.out_stream: TextIO = out_stream if out_stream is not None else sys.stdout
        self.started_at = time.time()

    def log(self, message: str, *args: Any) -> None:
        extra = f" {args}" if args else ""
        sys.stderr.write(f"[{self.plugin.name}] {message}{extra}\n")
        sys.stderr.flush()

    def serve(self) -> None:
        for line in self.in_stream:
            trimmed = line.strip()
            if not trimmed:
                continue

            try:
                req = json.loads(trimmed)
            except Exception as e:
                self.log(f"failed parsing JSON-RPC line: {e}")
                self.send_error(0, CODE_PARSE_ERROR, "Parse error")
                continue

            should_exit = self.handle_request(req)
            if should_exit:
                break

    def handle_request(self, req: Dict[str, Any]) -> bool:
        if req.get("jsonrpc") != "2.0":
            self.send_error(
                req.get("id", 0),
                CODE_INVALID_REQUEST,
                "Invalid JSON-RPC version, expected '2.0'",
            )
            return False

        req_id = req.get("id", 0)
        method = req.get("method", "")
        params = req.get("params") or {}

        try:
            if method == METHOD_REGISTER:
                proto_ver = params.get("protocol_version")
                if proto_ver and proto_ver != PROTOCOL_VERSION:
                    err_msg = f"incompatible protocol version: expected {PROTOCOL_VERSION}, got {proto_ver}"
                    self.log(err_msg)
                    self.send_error(req_id, CODE_PROTOCOL_VERSION_MISMATCH, err_msg)
                    return False

                caps = self.plugin.capabilities if self.plugin.capabilities else ["core"]
                res = {
                    "status": "ok",
                    "protocol_version": PROTOCOL_VERSION,
                    "capabilities": caps,
                    "message": f"{self.plugin.name} v{self.plugin.version} initialized successfully",
                }
                self.send_success(req_id, res)
                return False

            elif method == METHOD_HEALTH:
                uptime_sec = int(time.time() - self.started_at)
                res = {
                    "status": "healthy",
                    "uptime": f"{uptime_sec}s",
                    "message": "Plugin operational",
                }
                self.send_success(req_id, res)
                return False

            elif method == METHOD_SHUTDOWN:
                res = {"status": "shutting_down"}
                self.send_success(req_id, res)
                return True

            elif method == METHOD_HOOK_INVOKE:
                hook_name = params.get("hook")
                raw_ctx = params.get("context")
                if not hook_name or not raw_ctx:
                    self.send_error(req_id, CODE_INVALID_PARAMS, "Invalid hook invoke params")
                    return False

                decision = self.dispatch_hook(hook_name, raw_ctx)
                self.send_success(req_id, decision)
                return False

            elif self.plugin.get_method(method):
                custom_fn = self.plugin.get_method(method)
                res = custom_fn(params)
                self.send_success(req_id, res)
                return False

            else:
                self.send_error(req_id, CODE_METHOD_NOT_FOUND, f"Method '{method}' not found")
                return False

        except Exception as e:
            self.log(f"internal error handling {method}: {e}")
            self.send_error(req_id, CODE_INTERNAL_ERROR, str(e))
            return False

    def dispatch_hook(self, hook_name: str, raw_ctx: Dict[str, Any]) -> Dict[str, Any]:
        ctx = Context(raw_ctx)

        try:
            if hook_name == HOOK_REQUEST_BEFORE:
                handler = self.plugin.get_handler(HOOK_REQUEST_BEFORE)
                if handler:
                    req = Request(raw_ctx.get("request"))
                    res = handler(ctx, req)
                    return self._to_decision(res)

            elif hook_name == HOOK_REQUEST_AFTER:
                handler = self.plugin.get_handler(HOOK_REQUEST_AFTER)
                if handler:
                    req = Request(raw_ctx.get("request"))
                    res = handler(ctx, req)
                    dec = self._to_decision(res)
                    dec.pop("modified_request", None)  # read-only
                    return dec

            elif hook_name == HOOK_RESPONSE_BEFORE:
                handler = self.plugin.get_handler(HOOK_RESPONSE_BEFORE)
                if handler:
                    resp = Response(raw_ctx.get("response"))
                    res = handler(ctx, resp)
                    return self._to_decision(res)

            elif hook_name == HOOK_RESPONSE_AFTER:
                handler = self.plugin.get_handler(HOOK_RESPONSE_AFTER)
                if handler:
                    resp = Response(raw_ctx.get("response"))
                    res = handler(ctx, resp)
                    dec = self._to_decision(res)
                    dec.pop("modified_response", None)  # audit only
                    return dec

        except Exception as e:
            self.log(f"error executing hook {hook_name}: {e}")
            return {
                "decision": DECISION_CONTINUE,
                "error": str(e),
            }

        return {"decision": DECISION_CONTINUE}

    def _to_decision(self, res: Any) -> Dict[str, Any]:
        if isinstance(res, Result):
            return res.to_dict()
        elif isinstance(res, dict):
            return res
        return {"decision": DECISION_CONTINUE}

    def send_success(self, req_id: int, result: Any) -> None:
        resp = create_success_response(req_id, result)
        self.out_stream.write(serialize_response(resp))
        self.out_stream.flush()

    def send_error(self, req_id: int, code: int, message: str, data: Optional[Any] = None) -> None:
        resp = create_error_response(req_id, code, message, data)
        self.out_stream.write(serialize_response(resp))
        self.out_stream.flush()
