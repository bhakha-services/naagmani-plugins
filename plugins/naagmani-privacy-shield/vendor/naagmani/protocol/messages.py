from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class RPCRequest:
    jsonrpc: str
    method: str
    id: int
    params: Optional[Dict[str, Any]] = None

@dataclass
class RPCError:
    code: int
    message: str
    data: Optional[Any] = None

@dataclass
class RPCResponse:
    jsonrpc: str
    id: int
    result: Optional[Any] = None
    error: Optional[RPCError] = None

@dataclass
class RegisterParams:
    plugin_name: str
    plugin_version: str
    api_version: str
    permissions: List[str]
    protocol_version: Optional[str] = None
    config: Optional[Any] = None
    metadata: Optional[Dict[str, str]] = None

@dataclass
class RegisterResult:
    status: str
    protocol_version: Optional[str] = None
    capabilities: Optional[List[str]] = None
    message: Optional[str] = None

@dataclass
class HealthResult:
    status: str
    uptime: Optional[str] = None
    message: Optional[str] = None

@dataclass
class ShutdownResult:
    status: str = "shutting_down"

@dataclass
class TenantContext:
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    environment_id: Optional[str] = None

@dataclass
class HookMessage:
    role: str
    content: str

@dataclass
class HookRequest:
    model: str
    messages: List[HookMessage]
    stream: bool = False

@dataclass
class HookUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

@dataclass
class HookResponse:
    model: str
    content: Optional[str] = None
    usage: Optional[HookUsage] = None

@dataclass
class HookContext:
    hook: str
    request_id: str
    tenant: Optional[TenantContext] = None
    request: Optional[HookRequest] = None
    response: Optional[HookResponse] = None
    metadata: Optional[Dict[str, str]] = None

@dataclass
class HookInvokeParams:
    hook: str
    context: HookContext

@dataclass
class HookDecision:
    decision: str
    modified_request: Optional[HookRequest] = None
    modified_response: Optional[HookResponse] = None
    block_reason: Optional[str] = None
    error: Optional[str] = None
