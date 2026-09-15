from typing import Any, Dict, Optional
from ..protocol.constants import DECISION_CONTINUE, DECISION_MODIFY, DECISION_BLOCK
from .request import Request
from .response import Response

class Result:
    """
    Hook execution decision returned by plugin to OS.
    """
    def __init__(
        self,
        action: str,
        block_reason: Optional[str] = None,
        modified_request: Optional[Request] = None,
        modified_response: Optional[Response] = None,
    ):
        self.action = action
        self.block_reason = block_reason
        self.modified_request = modified_request
        self.modified_response = modified_response

    @classmethod
    def continue_(cls) -> "Result":
        return cls(action=DECISION_CONTINUE)

    @classmethod
    def block(cls, reason: str) -> "Result":
        return cls(action=DECISION_BLOCK, block_reason=reason)

    @classmethod
    def modify_request(cls, req: Request) -> "Result":
        return cls(action=DECISION_MODIFY, modified_request=req)

    @classmethod
    def modify_response(cls, resp: Response) -> "Result":
        return cls(action=DECISION_MODIFY, modified_response=resp)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"decision": self.action}
        if self.block_reason is not None:
            d["block_reason"] = self.block_reason
        if self.modified_request is not None:
            d["modified_request"] = self.modified_request.to_dict()
        if self.modified_response is not None:
            d["modified_response"] = self.modified_response.to_dict()
        return d
