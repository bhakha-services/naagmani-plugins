import sys
from naagmani import Plugin, Result

plugin = Plugin(
    name="my-py-plugin",
    version="0.1.0",
    description="A starter Naagmani plugin built with Python",
    author="developer",
)

@plugin.on("request.before")
def on_request_before(ctx, req):
    sys.stderr.write(f"[my-py-plugin] processing request ID={ctx.request_id} model={req.model}\n")
    sys.stderr.flush()
    return Result.continue_()

if __name__ == "__main__":
    plugin.run()
