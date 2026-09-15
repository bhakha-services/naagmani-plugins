import sys
import os

# Add hdk/python to sys.path so local example can import naagmani
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from naagmani import Plugin, Result

plugin = Plugin(
    name="hello-plugin-python",
    version="0.1.0",
    description="Hello World plugin in Python",
    author="developer",
)

@plugin.on("request.before")
def before_request(ctx, req):
    sys.stderr.write(f"[hello-plugin-python] intercepted request ID={ctx.request_id}\n")
    sys.stderr.flush()
    req.add_message("user", "Hello from Python HDK!")
    return Result.modify_request(req)

if __name__ == "__main__":
    plugin.run()
