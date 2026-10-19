# Naagmani Privacy Shield v1.0.0

> **Enterprise AI Privacy Boundary & PII Tokenization Guardrail for LLM Gateways**

The **Naagmani Privacy Shield** is a production-grade security plugin engineered to detect, tokenize, and redact Personally Identifiable Information (PII), Indian national identifiers, and cloud credentials before prompts are transmitted to external LLM providers (e.g. OpenAI, Anthropic, Bedrock).

- **Category**: Plugin (`Security & Privacy`)
- **Entitlement Tier**: Enterprise
- **Certification**: Certified by Naagmani Security Team
- **Digest**: `sha256:d8b2e5a407e3240e59c63673dc2d26f63c873ad92a6c2f354780512809489f68`
- **Signing Algorithm**: Ed25519 (Key ID: `naagmani-official-root-key-2026`)
- **License**: Apache-2.0
- **Runtime**: Python 3.11 (`naagmani.plugin/v1`)
- **Failure Policy**: `fail_close` (1500ms timeout)

---

## 1. Motto & Core Value Proposition

External LLM APIs introduce significant data leakage and regulatory risks. Naagmani Privacy Shield guarantees **Zero LLM Data Leakage** while maintaining model reasoning quality:
- **Zero Third-Party Plaintext Egress**: External model providers never see your users' Aadhaar, PAN, credit cards, or API credentials.
- **Bi-directional Transparency**: Prompts are masked using 128-bit CSPRNG surrogate placeholders before egress; model responses are automatically restored with original plaintext before reaching the client application.
- **Fail-Close Architecture**: If tokenization encounters an error or latency exceeds 1500ms, the request is halted safely rather than exposing sensitive customer data.
- **Regulatory Compliance**: Built-in adherence to India's DPDP Act, GDPR, HIPAA, and PCI-DSS standards.

---

## 2. Architecture & Lifecycle Flow

Privacy Shield attaches to two strategic intercept hooks in the Naagmani OS gateway:

```
[ Client Application ]
       │
       │ (1) POST /v1/chat/completions (Prompt with PII)
       ▼
[ Naagmani OS Gateway ]
       │
       │ (2) Hook: 'provider.before' (Pre-Inference Intercept)
       ▼
[ Naagmani Privacy Shield ] ──(Presidio NLP & Indian Recognizers)
       │
       ├─► [ Naagmani Vault ] (AES-256-GCM Encrypted Token Store)
       │
       ▼ (3) Redacted Prompt with 128-bit Surrogates
[ External LLM Provider ] (OpenAI / Anthropic / Bedrock)
       │
       ▼ (4) Model Completion referencing Surrogates
[ Naagmani OS Gateway ]
       │
       │ (5) Hook: 'provider.after' (Post-Inference Intercept)
       ▼
[ Naagmani Privacy Shield ] ──► (Resolves Surrogates from Vault)
       │
       ▼ (6) Natural Response with Plaintext Restored
[ Client Application ]
```

---

## 3. Supported Detection Categories

| Entity Category | Recognizer Implementation | Validation Logic |
| :--- | :--- | :--- |
| **Aadhaar Number** | Custom `IndianAadhaarRecognizer` | 12-digit format with Verhoeff mathematical checksum |
| **PAN Card** | Custom `IndianPanRecognizer` | 10-character Indian Income Tax alphanumeric syntax |
| **GSTIN** | Custom `IndianGstinRecognizer` | 15-character State-coded GST format |
| **UPI ID / VPA** | Custom `IndianUpiRecognizer` | Handle + virtual payment bank suffix pattern |
| **IFSC Code** | Custom `IndianIfscRecognizer` | RBI 11-character bank branch alphanumeric pattern |
| **API Keys & Secrets** | Custom `ApiKeyRecognizer` | High-entropy cloud credentials (AWS, OpenAI, GitHub) |
| **Email Address** | Presidio Analyzer | RFC 5322 regex + NLP context score |
| **Phone Number** | Presidio Analyzer | E.164 international & 10-digit Indian formats |
| **Credit Card** | Presidio Analyzer | Luhn algorithm validation (Visa, MC, Amex, RuPay) |
| **US SSN** | Presidio Analyzer | 9-digit US Social Security number validation |

---

## 4. Runtime Requirements & Offline Isolation

- **Runtime**: Pinned standalone CPython 3.11 (`cpython-3.11.17-linux-amd64`).
- **Dependencies**: Bundled hermetically inside the `.tar.gz` distribution archive.
  - `presidio-analyzer>=2.2.364`, `presidio-anonymizer>=2.2.364`
  - `spacy>=3.7.0` with offline pre-vendored `en_core_web_sm` model
  - `phonenumbers>=8.13.0`
- **Zero Network Egress**: 100% offline-certified at runtime. Disables telemetry, ambient packages, and external TLD lookups.
- **Limits**: Extracted size $\le$ 250MB, file count $\le$ 10,000 files.

---

## 5. Configuration Schema

Configured per project workspace and environment via Developer Portal or Naagmani CLI:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `confidence_threshold` | `number` | `0.60` | Minimum confidence score ($0.0 - 1.0$) for PII recognition |
| `default_action` | `string` | `TOKENIZE` | Default action: `TOKENIZE`, `MASK`, `REDACT`, `ALLOW`, `BLOCK` |
| `inspect_response_pii` | `boolean` | `false` | Scan model response for unprompted PII generation |
| `strict_streaming_no_downgrade` | `boolean` | `false` | Prevent fallback to raw streaming if unmasking cannot be guaranteed |
| `mapping_ttl_seconds` | `integer` | `3600` | Vault tokenization session TTL ($60 - 86400$ seconds) |
| `allow_list` | `array` | `[]` | Whitelisted entity values or internal company domains |
| `block_list` | `array` | `[]` | Explicit terms that trigger automatic request rejection |

---

## 6. Installation & Environment Scoping

### Via Naagmani CLI

```bash
# 1. Install into a project workspace for testing
naagmani plugins install naagmani-privacy-shield --project <project_id> --env test

# 2. Verify behavior in test environment
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer <test_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "My Aadhaar is 3675 9834 6012"}]}'

# 3. Promote to production environment
naagmani plugins install naagmani-privacy-shield --project <project_id> --env production
```

### Via Developer Portal
1. Navigate to **Marketplace** (`/marketplace`).
2. Select **Naagmani Privacy Shield**.
3. Click **Add to Project / Manage Scope**.
4. Choose target project(s) and select `test` or `production`.

---

## 7. Security Boundary & Failure Policy

- **Policy**: `fail_close`
- **Timeout**: 1500 milliseconds
- **Behavior**: If the plugin process aborts, times out, or encounters an internal NLP error, Naagmani OS aborts the request with `502 Bad Gateway / Plugin Execution Failure`, ensuring sensitive data is never transmitted unredacted.
