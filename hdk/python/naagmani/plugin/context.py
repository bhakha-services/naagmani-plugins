from typing import Any, Dict, Optional

class Context:
    """
    Immutable execution and multi-tenant scoping context passed to hook handlers.
    """
    def __init__(self, raw_context: Dict[str, Any]):
        self._hook: str = raw_context.get("hook", "")
        self._request_id: str = raw_context.get("request_id", "")
        tenant = raw_context.get("tenant") or {}
        self._org_id: Optional[str] = tenant.get("organization_id")
        self._project_id: Optional[str] = tenant.get("project_id")
        self._environment_id: Optional[str] = tenant.get("environment_id")
        self._metadata: Dict[str, str] = dict(raw_context.get("metadata") or {})

    @property
    def hook(self) -> str:
        return self._hook

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def org_id(self) -> Optional[str]:
        return self._org_id

    @property
    def project_id(self) -> Optional[str]:
        return self._project_id

    @property
    def environment_id(self) -> Optional[str]:
        return self._environment_id

    @property
    def organization_id(self) -> Optional[str]:
        return self._org_id

    @property
    def metadata(self) -> Dict[str, str]:
        return dict(self._metadata)

    def __setattr__(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            raise AttributeError("Context fields are immutable")
        super().__setattr__(key, value)
