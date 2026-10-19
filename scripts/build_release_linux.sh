#!/usr/bin/env bash
# ==============================================================================
# Naagmani OS — Official Python Plugin Release Build Script
# Hermetically packages, bundles CPython runtime, signs, and certifies for Linux x86_64.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR="${1:-${SCRIPT_DIR}/plugins/naagmani-privacy-shield}"
OUTPUT_DIR="${2:-${PLUGIN_DIR}/dist}"

echo "================================================================="
echo "NAAGMANI PYTHON PLUGIN RELEASE BUILD PIPELINE"
echo "Plugin Directory: ${PLUGIN_DIR}"
echo "Output Directory: ${OUTPUT_DIR}"
echo "================================================================="

# 1. Package plugin using generic hermetic toolchain (bundles CPython runtime)
echo "[1/5] Packaging hermetic plugin artifact with bundled CPython runtime..."
python3 "${SCRIPT_DIR}/tools/packager/pack_plugin.py" \
    --plugin-dir "${PLUGIN_DIR}" \
    --output-dir "${OUTPUT_DIR}" \
    --target-os linux \
    --target-arch amd64 \
    --python-version 3.11

# 2. Cryptographic Release Signing (if key is provisioned)
if [ -n "${NAAGMANI_SIGNING_KEY_FILE:-}" ]; then
    echo "[2/5] Signing release artifact using key file: ${NAAGMANI_SIGNING_KEY_FILE}..."
    python3 "${SCRIPT_DIR}/tools/packager/sign_artifact.py" \
        --manifest "${OUTPUT_DIR}/artifact_manifest.json" \
        --key-file "${NAAGMANI_SIGNING_KEY_FILE}"
elif [ -n "${NAAGMANI_SIGNING_KEY:-}" ]; then
    echo "[2/5] Signing release artifact using NAAGMANI_SIGNING_KEY..."
    python3 "${SCRIPT_DIR}/tools/packager/sign_artifact.py" \
        --manifest "${OUTPUT_DIR}/artifact_manifest.json" \
        --key-env "NAAGMANI_SIGNING_KEY"
else
    echo "[2/5] [WARN] No signing credentials provided; artifact is unsigned-development."
fi

# 3. Verify build reproducibility
echo "[3/5] Verifying bit-for-bit reproducibility..."
ARTIFACT_NAME="$(basename "$(ls "${OUTPUT_DIR}"/*.tar.gz | head -n 1)")"
DIGEST_1="$(sha256sum "${OUTPUT_DIR}/${ARTIFACT_NAME}" | awk '{print $1}')"

TEMP_DIST="$(mktemp -d)"
python3 "${SCRIPT_DIR}/tools/packager/pack_plugin.py" \
    --plugin-dir "${PLUGIN_DIR}" \
    --output-dir "${TEMP_DIST}" \
    --target-os linux \
    --target-arch amd64 \
    --python-version 3.11 >/dev/null

DIGEST_2="$(sha256sum "${TEMP_DIST}/${ARTIFACT_NAME}" | awk '{print $1}')"
rm -rf "${TEMP_DIST}"

if [ "${DIGEST_1}" != "${DIGEST_2}" ]; then
    echo "FATAL: Build reproducibility verification failed!" >&2
    echo "Run 1: sha256:${DIGEST_1}" >&2
    echo "Run 2: sha256:${DIGEST_2}" >&2
    exit 1
fi
echo "[OK] Build is 100% bit-for-bit deterministic: sha256:${DIGEST_1}"

# 4. Clean Linux Offline Certification
echo "[4/5] Running Clean Linux Offline Certification..."
CERT_WORK="$(mktemp -d)"
python3 "${SCRIPT_DIR}/scripts/clean_linux_cert.py" \
    "${OUTPUT_DIR}/${ARTIFACT_NAME}" \
    "${CERT_WORK}"
rm -rf "${CERT_WORK}"

# 5. Summary & Verification
echo "[5/5] Release build successfully completed."
cat "${OUTPUT_DIR}/artifact_manifest.json"
echo ""
echo "================================================================="
echo "RELEASE BUILD SUCCESSFUL"
echo "================================================================="
