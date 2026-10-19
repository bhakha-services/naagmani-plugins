"""
Naagmani Sample Guard — Reference Python Plugin
Demonstrates building an offline, hermetically packaged Python security plugin
using the Naagmani Python HDK.
"""
import os
import sys

# Ensure self-contained vendor and site-packages directories are available in sys.path
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _d in [os.path.join(_BASE_DIR, "vendor"), os.path.join(_BASE_DIR, "site-packages")]:
    if os.path.isdir(_d) and _d not in sys.path:
        sys.path.insert(0, _d)

from naagmani.plugin import Context, Plugin, Request, Response, Result

plugin = Plugin(
    name="sample-guard",
    version="1.0.0",
    description="Minimal Reference Naagmani Python Safety Plugin",
    author="Bhakha Services / Developer Ecosystem",
    capabilities=["safety.content_guard"],
)

PROHIBITED_TERMS = ["SYSTEM_OVERRIDE_ESCAPE", "DROP_ALL_TABLES"]


@plugin.on_provider_before
def handle_provider_before(ctx: Context, req: Request) -> Result:
    messages = req.messages
    if not messages:
        return Result.continue_()

    modified = False
    new_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        for term in PROHIBITED_TERMS:
            if term in content:
                content = content.replace(term, "[BLOCKED_PROHIBITED_TERM]")
                modified = True
        new_messages.append({"role": role, "content": content})

    if modified:
        return Result.modify(messages=new_messages)
    return Result.continue_()


if __name__ == "__main__":
    plugin.run()
