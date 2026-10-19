#!/usr/bin/env python3
"""
Naagmani OS — Secure Publisher Key Generation Utility
Generates cryptographically random Ed25519 keypairs for official and third-party plugin publishers.
Enforces strict file permissions (0600) and never prints or logs private keys.
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from . import ed25519
except ImportError:
    import ed25519


def generate_publisher_key(output_key_path: Path, force: bool = False) -> str:
    """Generates an Ed25519 keypair and securely saves the private key."""
    if output_key_path.exists() and not force:
        raise FileExistsError(f"Target key file already exists: {output_key_path}. Use --force to overwrite.")

    output_key_path.parent.mkdir(parents=True, exist_ok=True)

    sk, pk = ed25519.generate_keypair()
    pub_hex = pk.hex()
    key_id = pub_hex[:16]

    # Write private key with strict 0600 permissions
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    mode = 0o600
    fd = os.open(str(output_key_path), flags, mode)
    with os.fdopen(fd, "wb") as f:
        # Save as 32-byte raw binary or clean hex
        f.write(sk.hex().encode("ascii"))

    # Extra chmod for POSIX safety
    try:
        os.chmod(output_key_path, 0o600)
    except Exception:
        pass

    print("=================================================================")
    print("NAAGMANI SECURE PUBLISHER KEY GENERATION")
    print("=================================================================")
    print(f"Public Key (hex):  {pub_hex}")
    print(f"Key ID:            {key_id}")
    print(f"Private Key File:  {output_key_path} (mode: 0600)")
    print("=================================================================")
    print("CRITICAL: Keep the private key file confidential.")
    print("NEVER commit it to source control or embed it in artifacts.")
    print("=================================================================")

    return pub_hex


def main():
    parser = argparse.ArgumentParser(description="Naagmani Secure Ed25519 Keypair Generator")
    parser.add_argument("--output-key", required=True, help="Destination path for private key file")
    parser.add_argument("--force", action="store_true", help="Overwrite existing key file")

    args = parser.parse_args()
    try:
        generate_publisher_key(Path(args.output_key), force=args.force)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
