from typing import Any, Dict, List, Optional

class Message:
    def __init__(self, role: str, content: str, name: Optional[str] = None):
        self.role = role
        self.content = content
        self.name = name

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            d["name"] = self.name
        return d

class Request:
    def __init__(self, raw_req: Optional[Dict[str, Any]] = None):
        raw = raw_req or {}
        self.model: str = raw.get("model", "")
        self.stream: bool = bool(raw.get("stream", False))
        self.messages: List[Message] = [
            Message(m.get("role", ""), m.get("content", ""), m.get("name"))
            for m in raw.get("messages", [])
        ]
        self.tools: List[Any] = list(raw.get("tools") or [])
        self.metadata: Dict[str, Any] = dict(raw.get("metadata") or {})

    def prompt_text(self) -> str:
        return "\n".join(m.content for m in self.messages if m.role == "user")

    def add_message(self, role: str, content: str, name: Optional[str] = None) -> None:
        self.messages.append(Message(role=role, content=content, name=name))

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
            "stream": self.stream,
        }
        if self.tools:
            d["tools"] = self.tools
        if self.metadata:
            d["metadata"] = self.metadata
        return d
