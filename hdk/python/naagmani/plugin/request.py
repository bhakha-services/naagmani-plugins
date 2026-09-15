from typing import Any, Dict, List, Optional

class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}

class Request:
    def __init__(self, raw_req: Optional[Dict[str, Any]] = None):
        raw = raw_req or {}
        self.model: str = raw.get("model", "")
        self.stream: bool = bool(raw.get("stream", False))
        self.messages: List[Message] = [
            Message(m.get("role", ""), m.get("content", ""))
            for m in raw.get("messages", [])
        ]

    def prompt_text(self) -> str:
        return "\n".join(m.content for m in self.messages if m.role == "user")

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
            "stream": self.stream,
        }
