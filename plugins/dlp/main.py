import os
import re
import sys

# Locate and import naagmani Python HDK
current_dir = os.path.dirname(os.path.abspath(__file__))
search_dirs = [
    os.path.join(current_dir, "..", "..", "hdk", "python"),
    os.path.join(current_dir, "..", "hdk", "python"),
    os.path.join(current_dir, "hdk", "python"),
]
for d in search_dirs:
    if os.path.isdir(d):
        sys.path.insert(0, os.path.abspath(d))
        break

from naagmani import Plugin, Result

plugin = Plugin(
    name="dlp",
    version="1.0.0",
    description="Naagmani Data Loss Prevention (DLP) & PII Redaction Plugin",
    author="Naagmani Security Team",
)

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
API_KEY_REGEX = re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|key-[a-zA-Z0-9]{16,})\b")

def redact_text(text: str) -> str:
    redacted = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
    redacted = PHONE_REGEX.sub("[REDACTED_PHONE]", redacted)
    redacted = API_KEY_REGEX.sub("[REDACTED_SECRET]", redacted)
    return redacted

@plugin.on("request.before")
def on_request_before(ctx, req):
    sys.stderr.write(f"[dlp] scanning request ID={ctx.request_id} for PII/secrets\n")
    sys.stderr.flush()

    modified = False
    for msg in req.messages:
        original = msg.content
        redacted = redact_text(original)
        if redacted != original:
            msg.content = redacted
            modified = True
            sys.stderr.write(f"[dlp] redacted sensitive patterns in message role={msg.role}\n")
            sys.stderr.flush()

    if modified:
        return Result.modify_request(req)

    return Result.continue_()

if __name__ == "__main__":
    plugin.run()
