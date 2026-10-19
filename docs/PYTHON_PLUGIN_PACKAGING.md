# Naagmani OS — Production-Grade Python Plugin Packaging Architecture

## 1. Executive Summary

Naagmani OS provides a secure, multi-tenant AI operating system with a marketplace-driven plugin architecture. Plugins execute as isolated child processes communicating with the Go core runtime via JSON-RPC 2.0 over standard I/O (`stdio`).

This specification documents the **Generic Python Plugin Packaging and Execution System** established in Stage 2. It defines the supply-chain security model, hermetic dependency bundling, POSIX launcher standards, Ed25519 publisher signature verification, deterministic tarball generation, and clean offline Linux certification.

Naagmani Privacy Shield (`naagmani-privacy-shield`) serves as the reference production implementation.

---

## 2. Packaging Architecture

### High-Level Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                               DEVELOPER WORKSTATION                             |
|                                                                                 |
|   +--------------------------+       +-------------------+                      |
|   | plugin.json / main.py    | ----> | requirements.txt  |                      |
|   +--------------------------+       +-------------------+                      |
|                 |                              |                                |
|                 v                              v                                |
|   +-------------------------------------------------------------------------+   |
|   |         Generic Packaging Toolchain (tools/packager/pack_plugin.py)     |   |
|   |  - Manifest Validation (OS limits: <=250MB extracted, <=10,000 files)   |   |
|   |  - HDK Auto-Vendoring (hdk/python/naagmani -> vendor/naagmani)          |   |
|   |  - Containerized Native Wheel Compilation (python:3.11-slim)            |   |
|   |  - Prune tests, caches, docs, dist-info; Strip .so with binutils strip  |   |
|   |  - Generate Hermetic Launchers (bin/launcher and bin/launcher.bat)      |   |
|   |  - Build Deterministic Tarball (mtime=1700000000, uid=0, gzip fixed)   |   |
|   |  - RFC 8032 Ed25519 Canonical Envelope Signing                          |   |
|   +-------------------------------------------------------------------------+   |
|                 |                                                               |
|                 v                                                               |
|   +-----------------------------------------+   +---------------------------+   |
|   | <plugin>-<version>.tar.gz (Artifact)    |   | artifact_manifest.json    |   |
|   +-----------------------------------------+   +---------------------------+   |
+---------------------------------------------------------------------------------+
                                      |
                                      | Publish to Marketplace
                                      v
+---------------------------------------------------------------------------------+
|                             NAAGMANI CLOUD MARKETPLACE                          |
|   - Reconciler Registry & Metadata Catalog                                      |
|   - Ed25519 Signature & Digest Storage                                          |
+---------------------------------------------------------------------------------+
                                      |
                                      | Reconcile / Download
                                      v
+---------------------------------------------------------------------------------+
|                                NAAGMANI OS RUNTIME                              |
|                                                                                 |
|   1. Verify Ed25519 publisher signature against local TrustStore (Fail-Closed)   |
|   2. Verify SHA-256 digest of downloaded tarball                                 |
|   3. Unpack into sandboxed tenant dir (/plugins/<org>/<proj>/<env>/<plugin>)    |
|   4. Supervise process via ./bin/launcher with JSON-RPC 2.0 over stdio           |
|   5. Zero network access at runtime (100% offline-certified)                    |
+---------------------------------------------------------------------------------+
```

---

## 3. Runtime Isolation Model

The packaged plugin must never depend on host ambient conditions or ambient Python packages.

1. **Host Python Isolation**:
   - The launcher explicitly sets `PYTHONNOUSERSITE=1` to prevent loading user-level `~/.local/lib/python3.x/site-packages`.
   - The launcher sets `PYTHONDONTWRITEBYTECODE=1` to prevent altering the installation filesystem with `__pycache__` `.pyc` files.
   - The launcher sets `PYTHONUNBUFFERED=1` to ensure synchronous JSON-RPC stdio flushing.
   - The launcher sets `TLDEXTRACT_PUBLIC_SUFFIX_LIST_URLS=""` ensuring zero HTTP requests for domain/email recognizers.
   - The launcher sets `PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/vendor:$SCRIPT_DIR/site-packages"` ensuring bundled packages take absolute precedence.
   - The Python invocation uses `-s` (`exec "$PY_BIN" -s "$SCRIPT_DIR/main.py"`).

2. **Zero Network Egress**:
   - No pip downloads during installation.
   - No model downloads during cold startup.
   - No domain/TLD fetches during inference.
   - All spaCy models (`en_core_web_sm`) and native binary wheels are pre-vendored inside the release tarball.

3. **Multi-Tenant Directory Isolation**:
   - Plugins are installed in tenant-isolated paths:
     `{DataDir}/plugins/{OrgID}/{ProjectID}/{EnvironmentID}/{PluginName}/`
   - Only two environments are permitted: `test` and `production`.

---

## 4. Generic Packaging Toolchain

The packaging toolchain is located at:
`tools/packager/pack_plugin.py`

### Key Capabilities:
- **Manifest Validation**: Ensures required fields (`name`, `version`, `protocol_version`, `capabilities`, `runtime`, `hooks`) exist and adhere to Naagmani specifications.
- **HDK Vendoring**: Automatically copies the Naagmani Python HDK into `vendor/naagmani`.
- **Offline Model Vendoring**: Copies offline spaCy language models (`vendor/en_core_web_sm`).
- **Containerized Native Wheel Compilation**: Uses `python:3.11-slim` with `binutils` to download and compile native wheels (`.so` extensions for `linux/amd64`).
- **Binary Stripping & Pruning**:
  - Prunes `tests/`, `test/`, `testing/`, `__pycache__/`, `*.dist-info/`, `doc/`, `docs/`.
  - Removes redundant build tools (`setuptools`, `pygments`, `phonenumbers/geodata`).
  - Runs `strip --strip-unneeded` across all compiled `.so` binaries.
  - Slashes uncompressed footprint from 387MB down to **141.63MB**, safely below the OS 250MB limit.
- **Deterministic Tarball**:
  - Normalized `mtime=1700000000` on both tar archive and gzip header stream.
  - Deterministic entry sorting.
  - Fixed ownership (`uid=0`, `gid=0`, `uname="naagmani"`).
  - Mode bits: `0755` for executables (`bin/`, `.sh`, `.py`, `.bat`), `0644` for data files.
- **RFC 8032 Ed25519 Signing**:
  - Implemented via zero-dependency pure-Python engine (`tools/packager/ed25519.py`).
  - Produces canonical signed envelope with `publisher_id`, `key_id`, `artifact_digest`, and Base64 signature.

---

## 5. Developer Guide: Creating a Python Plugin

### Step 1: Directory Structure
```
my-plugin/
├── plugin.json
├── manifest.yaml
├── requirements.txt
├── main.py
└── (optional) vendor/
```

### Step 2: Declare `plugin.json`
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "protocol_version": "naagmani.plugin/v1",
  "description": "My custom security plugin",
  "author": "My Organization",
  "publisher": "pub_my_org",
  "entrypoint": "main.py",
  "capabilities": ["custom.filter"],
  "runtime": {
    "language": "python",
    "command": "./bin/launcher",
    "args": []
  },
  "hooks": ["provider.before"]
}
```

### Step 3: Implement `main.py`
```python
import os
import sys

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _d in [os.path.join(_BASE_DIR, "vendor"), os.path.join(_BASE_DIR, "site-packages")]:
    if os.path.isdir(_d) and _d not in sys.path:
        sys.path.insert(0, _d)

from naagmani.plugin import Context, Plugin, Request, Result

plugin = Plugin(
    name="my-plugin",
    version="1.0.0",
    description="Custom Filter",
    capabilities=["custom.filter"]
)

@plugin.on_provider_before
def on_provider_before(ctx: Context, req: Request) -> Result:
    # Custom inspection logic
    return Result.continue_()

if __name__ == "__main__":
    plugin.run()
```

### Step 4: Package the Plugin
```bash
python3 tools/packager/pack_plugin.py \
    --plugin-dir path/to/my-plugin \
    --output-dir path/to/my-plugin/dist \
    --target-os linux \
    --target-arch amd64
```

---

## 6. Offline Verification & Certification

All release candidates must pass clean Linux offline certification before publication.

Run the certification suite inside a container with `--network none`:

```bash
docker run --rm --network none \
    -v "$(pwd)/scripts/clean_linux_cert.py:/cert/clean_linux_cert.py:ro" \
    -v "$(pwd)/plugins/naagmani-privacy-shield/dist:/dist:ro" \
    python:3.11-slim \
    python3 /cert/clean_linux_cert.py /dist/naagmani-privacy-shield-1.0.0.tar.gz /tmp/cert_work
```

### 15 Verified Scenarios:
1. Clean installation from `.tar.gz` archive.
2. Runtime startup using hermetic launcher.
3. JSON-RPC 2.0 handshake (`plugin.register`).
4. `provider.before` hook execution.
5. Indian PII detection (Aadhaar, PAN, GSTIN, UPI, IFSC, email, phone).
6. PII tokenization into Vault-compatible placeholders.
7. Mock provider receives sanitized inputs without plaintext PII.
8. `provider.after` response privacy inspection.
9. Authorized re-identification via Vault KMS.
10. Unauthorized re-identification rejection (fail-closed).
11. Streaming compatibility with multi-chunk SSE buffers.
12. Graceful process termination and restart.
13. Plugin crash recovery and process supervision.
14. Corrupted and tampered artifact rejection.
15. 100% offline execution after supervisor restart.

---

## 7. OS Verification, Upgrades & Rollbacks

1. **Signature & Digest Verification**:
   - The OS Reconciler fetches the signed metadata from Cloud Marketplace.
   - The OS TrustStore verifies the Ed25519 signature of the canonical envelope against trusted public keys.
   - The OS calculates the SHA-256 digest of the downloaded `.tar.gz` and verifies it matches `artifact_digest`.
   - Never allows unsigned or checksum-only verification for official or production plugins.
2. **Atomic Upgrades**:
   - The new version is extracted to a temporary sibling directory:
     `{PluginDir}.new`
   - Once verified, the supervisor signals graceful shutdown (`SIGTERM`) to the running version.
   - The directory is atomically swapped (`os.Rename`), and the new version is launched.
3. **Rollback**:
   - If the new version crashes during initialization or health checks, the supervisor immediately reverts to the previous signed release.
   - Re-identification token mappings in Vault remain backward-compatible across versions.

---

## 8. Supported Platforms & Limitations

- **Linux x86_64 (`linux/amd64`)**: Fully supported, offline-certified reference target.
- **Windows x86_64 (`windows/amd64`)**: Supported for local development via `bin/launcher.bat`.
- **macOS (Darwin ARM64/x86_64)**: Developer workstations supported; production runtime targets Linux x86_64.
- **Limitations**:
  - C-extension native binaries are architecture-dependent; Linux x86_64 artifacts cannot run on ARM64 hosts without cross-packaging.
  - OS limits enforce extracted archive size `<= 250 MB` and total file count `<= 10,000 files`.
