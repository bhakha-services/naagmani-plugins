# Naagmani DLP & PII Redaction Plugin

Data Loss Prevention (DLP) plugin written in Python using the **Naagmani HDK for Python**.

## Features

- Scans chat completion requests on hook `request.before`.
- Automatically redacts email addresses (`[REDACTED_EMAIL]`).
- Automatically redacts phone numbers (`[REDACTED_PHONE]`).
- Automatically redacts API keys and secret tokens (`[REDACTED_SECRET]`).
- Uses `request.modify` permission safely within OS sandbox boundaries.
