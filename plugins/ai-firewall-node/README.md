# Naagmani AI Firewall (Node.js)

Reference AI Firewall plugin written in TypeScript for Node.js using the **Naagmani HDK for Node.js**.

## Capabilities

- Subscribes to `request.before`.
- Detects prompt injection, jailbreak attempts, and system prompt exfiltration.
- Returns `block` decision with 403 Forbidden to protect downstream models.
