# Naagmani Sample Guard — Reference Python Plugin

This directory provides a minimal reference implementation demonstrating how any third-party or enterprise developer can build, test, and package an offline, production-grade Python plugin for the Naagmani AI Operating System.

## Packaging

Use the generic Naagmani packaging toolchain:

```bash
python3 tools/packager/pack_plugin.py \
    --plugin-dir examples/sample-guard \
    --output-dir examples/sample-guard/dist \
    --target-os linux \
    --target-arch amd64
```

This command will:
1. Validate `plugin.json` and `manifest.yaml`.
2. Vendor the Naagmani Python HDK into `vendor/naagmani`.
3. Hermetically build and package Linux x86_64 wheels for all dependencies listed in `requirements.txt` using a containerized toolchain.
4. Prune docs, test suites, and bytecode caches, and strip native `.so` C-extensions.
5. Generate hermetic launchers (`bin/launcher` and `bin/launcher.bat`).
6. Pack into a deterministic `.tar.gz` with normalized timestamps (`mtime=1700000000`).
7. Sign the canonical release envelope using Ed25519 and produce `artifact_manifest.json`.

## Testing Locally

Run offline smoke tests inside an unprivileged container:

```bash
docker run --rm --network none \
    -v "$(pwd)/scripts/clean_linux_cert.py:/cert/clean_linux_cert.py:ro" \
    -v "$(pwd)/examples/sample-guard/dist:/dist:ro" \
    python:3.11-slim \
    python3 /cert/clean_linux_cert.py /dist/sample-guard-1.0.0.tar.gz /tmp/cert_work
```
