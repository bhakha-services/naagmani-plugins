#!/usr/bin/env python3
"""
Naagmani OS — Secure Release Signing Utility
Applies authorized Ed25519 digital signatures to packaged plugin distribution artifacts.
Loads private keys strictly from protected credential files or environment variables.
Binds canonical metadata, artifact SHA-256 digest, package identity, version, and publisher identity.
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    from . import ed25519
except ImportError:
    import ed25519


def load_private_key(key_file: Optional[Path] = None, key_env: Optional[str] = None) -> Tuple[bytes, bytes]:
    """
    Loads Ed25519 private key from protected file or environment variable.
    Enforces strict validation: private key must be 32 raw bytes or 64 hex characters.
    Validates file permissions on POSIX to prevent reading world-readable keys.
    Returns (private_key_bytes, public_key_bytes).
    """
    raw_key = None

    if key_file:
        key_path = Path(key_file).resolve()
        if not key_path.exists():
            raise FileNotFoundError(f"Signing key file not found: {key_path}")

        # Check POSIX permissions (must not be readable by others)
        if os.name == "posix":
            st_mode = key_path.stat().st_mode
            if st_mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH):
                print(f"[WARN] Insecure key file permissions ({oct(st_mode)[-4:]}). Tightening to 0600...", file=sys.stderr)
                try:
                    os.chmod(key_path, 0o600)
                except Exception as e:
                    print(f"[WARN] Could not update key file permissions: {e}", file=sys.stderr)

        with open(key_path, "rb") as f:
            raw_key = f.read().strip()

    elif key_env:
        val = os.getenv(key_env)
        if not val:
            raise ValueError(f"Environment variable {key_env} is unset or empty")
        raw_key = val.strip().encode("utf-8")
    else:
        # Default environment fallback
        env_val = os.getenv("NAAGMANI_SIGNING_KEY_FILE")
        if env_val:
            return load_private_key(key_file=Path(env_val))
        env_val = os.getenv("NAAGMANI_SIGNING_KEY")
        if env_val:
            raw_key = env_val.strip().encode("utf-8")

    if not raw_key:
        raise ValueError("No signing key specified. Provide --key-file or set NAAGMANI_SIGNING_KEY_FILE / NAAGMANI_SIGNING_KEY.")

    # Parse 64-char hex or 32 raw bytes
    try:
        text = raw_key.decode("ascii")
        if len(text) == 64:
            sk = bytes.fromhex(text)
        elif len(raw_key) == 32:
            sk = raw_key
        else:
            raise ValueError(f"Invalid key length ({len(raw_key)} bytes). Expected 32 raw bytes or 64 hex chars.")
    except UnicodeDecodeError:
        if len(raw_key) == 32:
            sk = raw_key
        else:
            raise ValueError(f"Invalid binary key length ({len(raw_key)} bytes). Expected 32 raw bytes.")

    pk = ed25519.publickey(sk)
    return sk, pk


def sign_artifact(
    manifest_path: Path,
    artifact_path: Optional[Path] = None,
    key_file: Optional[Path] = None,
    key_env: Optional[str] = None,
    publisher_id: Optional[str] = None,
    timestamp: Optional[str] = None
) -> dict:
    """Signs an artifact manifest and writes back the signed release envelope."""
    manifest_path = manifest_path.resolve()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    name = manifest.get("name")
    version = manifest.get("version")
    if not name or not version:
        raise ValueError(f"Manifest at {manifest_path} is missing required 'name' or 'version'")

    # Locate and verify artifact file
    if artifact_path:
        art_path = Path(artifact_path).resolve()
    else:
        art_name = manifest.get("filename", f"{name}-{version}.tar.gz")
        art_path = manifest_path.parent / art_name

    if not art_path.exists():
        raise FileNotFoundError(f"Artifact archive not found: {art_path}")

    # Verify SHA-256 digest of artifact
    hasher = hashlib.sha256()
    with open(art_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    computed_digest = "sha256:" + hasher.hexdigest()

    declared_digest = manifest.get("digest")
    if declared_digest and declared_digest != computed_digest:
        raise ValueError(f"Artifact integrity mismatch: manifest declares {declared_digest}, file has {computed_digest}")

    sk, pk = load_private_key(key_file, key_env)
    pub_hex = pk.hex()
    key_id = pub_hex[:16]

    pub_id = publisher_id or manifest.get("publisher", "pub_naagmani_official")
    signed_time = timestamp or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Construct canonical payload
    canonical_payload = {
        "schema_version": "naagmani.package.signature/v1",
        "package_id": f"pkg_plugin_{name.replace('-', '_')}_01",
        "package_slug": name,
        "version": version,
        "artifact_digest": computed_digest,
        "publisher_id": pub_id,
        "signed_at": signed_time,
        "key_id": key_id
    }

    # Deterministic JSON canonical string
    canonical_str = json.dumps(canonical_payload, separators=(',', ':'))
    payload_bytes = canonical_str.encode("utf-8")

    sig_bytes = ed25519.signature(payload_bytes, sk, pk)
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    # Update manifest
    manifest["status"] = "signed-release"
    manifest["publisher"] = pub_id
    manifest["public_key"] = pub_hex
    manifest["key_id"] = key_id
    manifest["signature"] = sig_b64
    manifest["canonical_payload"] = canonical_str
    manifest["digest"] = computed_digest
    manifest["size"] = art_path.stat().st_size

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("=================================================================")
    print("NAAGMANI RELEASE ARTIFACT SIGNED")
    print("=================================================================")
    print(f"Plugin:           {name} v{version}")
    print(f"Artifact:         {art_path.name}")
    print(f"Digest:           {computed_digest}")
    print(f"Publisher:        {pub_id}")
    print(f"Publisher Key ID: {key_id}")
    print(f"Public Key (hex): {pub_hex}")
    print(f"Signature:        {sig_b64[:32]}...")
    print(f"Manifest Updated: {manifest_path}")
    print("=================================================================")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Naagmani Secure Release Signer")
    parser.add_argument("--manifest", required=True, help="Path to artifact_manifest.json")
    parser.add_argument("--artifact", default=None, help="Path to artifact .tar.gz (optional)")
    parser.add_argument("--key-file", default=None, help="Path to protected private key file")
    parser.add_argument("--key-env", default=None, help="Environment variable containing private key hex")
    parser.add_argument("--publisher-id", default=None, help="Publisher ID (default: from manifest)")
    parser.add_argument("--timestamp", default=None, help="Deterministic signing timestamp (RFC 3339)")

    args = parser.parse_args()
    try:
        sign_artifact(
            manifest_path=Path(args.manifest),
            artifact_path=Path(args.artifact) if args.artifact else None,
            key_file=Path(args.key_file) if args.key_file else None,
            key_env=args.key_env,
            publisher_id=args.publisher_id,
            timestamp=args.timestamp
        )
    except Exception as e:
        print(f"Fatal signing error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
