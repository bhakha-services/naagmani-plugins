#!/usr/bin/env python3
"""
Hermetic & Reproducible Release Packaging Script for Naagmani Privacy Shield.
Delegates to the generic Naagmani Python packaging toolchain to compile,
vendor, and sign an offline-capable, Linux x86_64 distribution archive (.tar.gz).
"""

import os
import sys
from pathlib import Path

# Add workspace tools to path
here = Path(__file__).resolve().parent
plugin_dir = here.parent
tools_dir = plugin_dir.parent.parent / "tools" / "packager"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from pack_plugin import package_plugin


def main():
    dist_dir = plugin_dir / "dist"
    signing_key = os.getenv("NAAGMANI_SIGNING_KEY")
    publisher_id = os.getenv("NAAGMANI_PUBLISHER_ID", "pub_naagmani_official")
    
    envelope = package_plugin(
        plugin_dir=plugin_dir,
        output_dir=dist_dir,
        target_os="linux",
        target_arch="amd64",
        python_version="3.11",
        signing_key=signing_key,
        publisher_id=publisher_id,
        use_docker=True
    )
    
    print("\n[SUCCESS] Naagmani Privacy Shield packaged successfully:")
    print(f"Artifact:   {dist_dir / envelope['filename']}")
    print(f"Digest:     {envelope['digest']}")
    print(f"Signature:  {envelope['signature'][:32]}...")
    print(f"Key ID:     {envelope['key_id']}")


if __name__ == "__main__":
    main()
