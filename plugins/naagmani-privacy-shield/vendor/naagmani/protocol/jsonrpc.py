import json
from typing import Any, Dict, Optional
from .messages import RPCError, RPCResponse

def create_success_response(req_id: int, result: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": req_id,
    }

def create_error_response(req_id: int, code: int, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if data is not None:
        err["data"] = data
    return {
        "jsonrpc": "2.0",
        "error": err,
        "id": req_id,
    }

def serialize_response(resp: Dict[str, Any]) -> str:
    return json.dumps(resp) + "\n"
