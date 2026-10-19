# Naagmani DLP & Confidential Data Redaction Plugin v1.0.0

> **High-Throughput In-Flight Data Loss Prevention & Secret Redaction Interceptor**

The **Naagmani DLP Plugin** is an enterprise data loss prevention interceptor written in Python using the Naagmani HDK. It executes on the pre-inference path (`request.before`) to scan prompt payloads and redact sensitive corporate secrets, cloud API keys, passwords, database URLs, emails, and phone numbers before egress.

- **Category**: Plugin (`Security & DLP`)
- **Entitlement Tier**: Enterprise
- **Certification**: Certified by Naagmani Security Team
- **License**: Apache-2.0
- **Runtime**: Python 3.11 (`naagmani.plugin/v1`)
- **Failure Policy**: `fail_close` (1000ms execution timeout)
- **Permissions**: `request.read`, `request.modify`
- **Hook**: `request.before`

---

## 1. Motto & Core Value Proposition

Developers and end-users frequently paste source code, configuration files, and stack traces containing raw credentials into generative AI prompts. Naagmani DLP provides an **Automated In-Flight Redaction Guardrail**:
- **Automatic Secret Sanitization**: Detects and redacts high-entropy API tokens (AWS, OpenAI, GitHub, Slack) and private keys.
- **In-Place Mutation**: Replaces detected values with safe redaction masks (`[REDACTED_SECRET]`, `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`) without breaking prompt readability or model completions.
- **Fail-Close Latency Budget**: Strictly bounded within a 1000ms timeout.
- **Lightweight HDK Core**: High throughput with minimal memory footprint, ideal for low-latency API proxy gateways.

---

## 2. Architecture & Redaction Pipeline

The DLP interceptor hooks directly into the gateway request lifecycle:

```
[ User Prompt / Code Snippet ]
       │
       ▼
[ Naagmani OS Gateway ]
       │
       │ (1) Hook: 'request.before'
       ▼
[ Naagmani DLP Plugin ]
       │
       ├──► (2) Regular Expression & Entropy Analyzers
       │         - Cloud API Keys (AWS AKIA..., OpenAI sk-..., GitHub ghp_...)
       │         - Private Key Headers (-----BEGIN RSA PRIVATE KEY-----)
       │         - High-Entropy Passwords & Connection Strings
       │         - Email Addresses & Phone Numbers
       │
       ├──► (3) In-Place Prompt Transformation
       │         Replaces matched substrings with typed redaction tokens
       │
       ▼ (4) Clean Sanitized Prompt Egress
[ External LLM Provider ] (OpenAI / Anthropic / Bedrock)
```

---

## 3. Supported Detection Categories

| Secret Type | Matcher Pattern / Heuristic | Redaction Token |
| :--- | :--- | :--- |
| **AWS Access Key** | Regex pattern matching `AKIA[0-9A-Z]{16}` | `[REDACTED_SECRET]` |
| **OpenAI API Key** | `sk-[a-zA-Z0-9_-]{32,}` prefix and length validation | `[REDACTED_SECRET]` |
| **GitHub Personal Token** | Pattern `ghp_[0-9a-zA-Z]{36}` | `[REDACTED_SECRET]` |
| **Private Keys & Certificates** | PEM boundaries (`BEGIN PRIVATE KEY`, `BEGIN RSA`) | `[REDACTED_SECRET]` |
| **Email Addresses** | Standard RFC 5322 email syntax | `[REDACTED_EMAIL]` |
| **Phone Numbers** | International and 10-digit formats with prefixes | `[REDACTED_PHONE]` |

---

## 4. Configuration Schema

Configured per project workspace and environment via Developer Portal or Naagmani CLI:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `redaction_mode` | `string` | `MASK` | Output masking format: `MASK` (`[REDACTED_...]`) or `HASH` |
| `detect_secrets` | `boolean` | `true` | Enable deep inspection for API keys and database credentials |
| `detect_contact_info` | `boolean` | `true` | Enable inspection and masking of emails and telephone numbers |
| `exempt_domains` | `array` | `[]` | Company domain suffixes excluded from email redaction |

---

## 5. Installation & Verification

### Via Naagmani CLI

```bash
# 1. Install DLP plugin into test environment
naagmani plugins install dlp --project <project_id> --env test

# 2. Test DLP secret redaction with an API key
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer <test_api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Help me debug this AWS key: AKIAIOSFODNN7EXAMPLE and email test@example.com"}]
  }'
# The prompt received by upstream model will contain:
# "Help me debug this AWS key: [REDACTED_SECRET] and email [REDACTED_EMAIL]"

# 3. Promote to production
naagmani plugins install dlp --project <project_id> --env production
```

---

## 6. Security Boundary & Failure Policy

- **Policy**: `fail_close`
- **Timeout**: 1000 milliseconds
- **Behavior**: If the regex engine times out or encounters unexpected input encoding, Naagmani OS rejects the prompt to prevent accidental leak of confidential keys.
