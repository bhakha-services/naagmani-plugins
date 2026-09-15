import sys
from typing import Any, Callable, Dict, List, Optional, TextIO, Union
from ..protocol.constants import (
    HOOK_REQUEST_AFTER,
    HOOK_REQUEST_BEFORE,
    HOOK_RESPONSE_AFTER,
    HOOK_RESPONSE_BEFORE,
)
from .context import Context
from .request import Request
from .response import Response
from .result import Result
from .server import Server

HandlerFunc = Callable[..., Any]

class Plugin:
    def __init__(
        self,
        name: str,
        version: str = "0.1.0",
        description: str = "",
        author: str = "",
        capabilities: Optional[List[str]] = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.capabilities: List[str] = list(capabilities) if capabilities else []
        self._handlers: Dict[str, HandlerFunc] = {}
        self._methods: Dict[str, Callable[..., Any]] = {}

    def register_method(self, name: str, handler: Callable[..., Any]) -> "Plugin":
        self._methods[name] = handler
        return self

    def get_method(self, name: str) -> Optional[Callable[..., Any]]:
        return self._methods.get(name)

    def set_version(self, version: str) -> "Plugin":
        self.version = version
        return self

    def set_description(self, description: str) -> "Plugin":
        self.description = description
        return self

    def set_author(self, author: str) -> "Plugin":
        self.author = author
        return self

    def add_capabilities(self, *caps: str) -> "Plugin":
        self.capabilities.extend(caps)
        return self

    def on(self, hook: str, handler: Optional[HandlerFunc] = None) -> Any:
        """
        Register a handler for a hook. Can be used as a function or a decorator:

            @plugin.on("request.before")
            def handle(ctx, req):
                return Result.continue_()
        """
        if handler is not None:
            self._handlers[hook] = handler
            return self

        def decorator(fn: HandlerFunc) -> HandlerFunc:
            self._handlers[hook] = fn
            return fn

        return decorator

    def on_request_before(self, handler: HandlerFunc) -> "Plugin":
        return self.on(HOOK_REQUEST_BEFORE, handler)

    def on_request_after(self, handler: HandlerFunc) -> "Plugin":
        return self.on(HOOK_REQUEST_AFTER, handler)

    def on_response_before(self, handler: HandlerFunc) -> "Plugin":
        return self.on(HOOK_RESPONSE_BEFORE, handler)

    def on_response_after(self, handler: HandlerFunc) -> "Plugin":
        return self.on(HOOK_RESPONSE_AFTER, handler)

    def get_handler(self, hook: str) -> Optional[HandlerFunc]:
        return self._handlers.get(hook)

    def run(self) -> None:
        """
        Execute plugin stdio server loop using sys.stdin and sys.stdout.
        """
        self.serve(sys.stdin, sys.stdout)

    def serve(self, in_stream: TextIO, out_stream: TextIO) -> None:
        """
        Execute plugin on given input and output streams.
        """
        server = Server(self, in_stream, out_stream)
        server.serve()
