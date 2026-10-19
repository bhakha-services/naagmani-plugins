from typing import Any, Dict, Optional

class Usage:
    def __init__(self, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }

class Response:
    def __init__(self, raw_resp: Optional[Dict[str, Any]] = None):
        raw = raw_resp or {}
        self.model: str = raw.get("model", "")
        self.content: str = raw.get("content", "")
        raw_usage = raw.get("usage")
        if raw_usage:
            self.usage: Optional[Usage] = Usage(
                prompt_tokens=raw_usage.get("prompt_tokens", 0),
                completion_tokens=raw_usage.get("completion_tokens", 0),
                total_tokens=raw_usage.get("total_tokens", 0),
            )
        else:
            self.usage = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "model": self.model,
            "content": self.content,
        }
        if self.usage is not None:
            d["usage"] = self.usage.to_dict()
        return d
