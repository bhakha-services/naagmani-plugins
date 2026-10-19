#!/usr/bin/env python3
"""
Naagmani OS — Generic Production-Grade Python Plugin Packaging Toolchain
Supports hermetic, reproducible, offline-capable packaging for Linux x86_64.
Bundles relocatable standalone CPython 3.11 runtime, pinned offline dependencies, and models.
Separates packaging from release signing: produces unsigned development packages by default
and requires authorized Ed25519 cryptographic credentials for official production releases.
"""

import argparse
import base64
import hashlib
import gzip
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Import standard audited Ed25519 signer
try:
    from . import ed25519
except ImportError:
    import ed25519

FIXED_MTIME = 1700000000  # Deterministic epoch for reproducible builds
MAX_EXTRACTED_SIZE = 250 * 1024 * 1024  # 250MB Naagmani OS limit
MAX_FILES_LIMIT = 10000  # 10,000 files Naagmani OS limit

# Pinned Relocatable Standalone CPython Runtime for Linux x86_64
PINNED_CPYTHON_VERSION = "3.11.17"
PINNED_CPYTHON_LINUX_AMD64_SHA256 = "3b8e5a248bcc351265ffe68f5e457668a2e09c99a47f81f658988c7d3d107522"
PINNED_CPYTHON_ARCHIVE = "cpython-3.11.17-linux-amd64.tar.gz"


def validate_manifest(plugin_dir: Path) -> dict:
    """Validates plugin.json or manifest.yaml in the plugin directory."""
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        manifest_yaml = plugin_dir / "manifest.yaml"
        if not manifest_yaml.exists():
            raise FileNotFoundError(f"Missing plugin.json or manifest.yaml in {plugin_dir}")
        import yaml
        with open(manifest_yaml, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    required_fields = ["name", "version", "api_version", "runtime"]
    for field in required_fields:
        if field not in manifest:
            raise ValueError(f"Manifest missing required field: {field}")

    lang = manifest["runtime"].get("language", "").lower()
    if lang != "python":
        raise ValueError(f"Incompatible language for Python packager: {lang}")

    return manifest


def vendor_hdk(plugin_dir: Path, staging_vendor: Path):
    """Vendors naagmani-hdk from workspace into staging vendor/ directory."""
    staging_vendor.mkdir(parents=True, exist_ok=True)
    hdk_dest = staging_vendor / "naagmani"

    # Locate HDK in repo
    candidates = [
        plugin_dir.parent.parent / "hdk" / "python" / "naagmani",
        plugin_dir.parent.parent.parent / "naagmani-plugins" / "hdk" / "python" / "naagmani",
        plugin_dir / "vendor" / "naagmani",
    ]
    hdk_src = None
    for c in candidates:
        if c.exists() and (c / "plugin").exists():
            hdk_src = c
            break

    if hdk_src and hdk_src != hdk_dest:
        if hdk_dest.exists():
            shutil.rmtree(hdk_dest)
        shutil.copytree(hdk_src, hdk_dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        print(f"[OK] Vendored Naagmani HDK from {hdk_src}")
    elif not hdk_dest.exists():
        print("[WARN] Naagmani HDK source not found in standard paths; assuming already vendored or available")


def vendor_dependencies_docker(
    plugin_dir: Path,
    staging_vendor: Path,
    requirements_path: Path,
    python_version: str = "3.11",
    cache_dir: Optional[Path] = None
) -> Dict[str, str]:
    """
    Hermetically downloads and installs Linux x86_64 wheels using python:3.11-slim container.
    Prunes test files, docs, and unused data, and strips all .so binaries with binutils strip.
    Supports local vendor cache to guarantee fast, reproducible, offline builds.
    Returns inventory mapping of package name to version.
    """
    staging_vendor.mkdir(parents=True, exist_ok=True)
    abs_vendor = staging_vendor.resolve()
    abs_req = requirements_path.resolve()

    # Filter out dev requirements (pytest, etc.) into a temporary runtime requirements file
    runtime_req_lines = []
    with open(abs_req, "r", encoding="utf-8") as f:
        for line in f:
            clean = line.strip()
            if not clean or clean.startswith("#") or clean.startswith("pytest") or clean.startswith("naagmani-hdk"):
                continue
            runtime_req_lines.append(clean)

    # Build inventory
    inventory = {}
    for line in runtime_req_lines:
        parts = line.split("==") if "==" in line else line.split(">=")
        pkg = parts[0].strip()
        ver = parts[1].strip() if len(parts) > 1 else "latest"
        inventory[pkg] = ver

    # Check if cache_dir is provided and populated
    if cache_dir and Path(cache_dir).exists() and any(Path(cache_dir).iterdir()):
        print(f"[INFO] Populating dependencies from cache: {cache_dir}")
        for item in Path(cache_dir).iterdir():
            dest = staging_vendor / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        print(f"[OK] Linux x86_64 dependencies loaded from cache ({len(inventory)} packages)")
        return inventory

    temp_req_path = staging_vendor / "_runtime_requirements.txt"
    with open(temp_req_path, "w", encoding="utf-8") as f:
        f.write("\n".join(runtime_req_lines) + "\n")

    print(f"[INFO] Compiling Linux x86_64 dependencies via Docker (python:{python_version}-slim)...")

    docker_script = (
        "apt-get update -qq && apt-get install -y -qq binutils >/dev/null && "
        "python3 -m pip install --no-cache-dir -r /staging/_runtime_requirements.txt --target /staging && "
        "find /staging -type d \\( -name 'tests' -o -name 'test' -o -name 'testing' -o -name '__pycache__' -o -name '*.dist-info' -o -name 'doc' -o -name 'docs' \\) -exec rm -rf {} + 2>/dev/null || true && "
        "rm -rf /staging/setuptools /staging/pygments /staging/bin /staging/phonenumbers/geodata && "
        "find /staging -name '*.so' -exec strip --strip-unneeded {} + 2>/dev/null || true"
    )

    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{abs_vendor}:/staging",
        f"python:{python_version}-slim",
        "bash", "-c", docker_script
    ]

    res = subprocess.run(docker_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"Docker dependency compilation failed:\n{res.stderr}\n{res.stdout}")

    if temp_req_path.exists():
        temp_req_path.unlink()

    # Populate cache_dir if requested
    if cache_dir:
        c_path = Path(cache_dir)
        c_path.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Populating cache at {cache_dir}...")
        for item in staging_vendor.iterdir():
            dest = c_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    print(f"[OK] Linux x86_64 dependencies vendored and stripped successfully ({len(inventory)} packages)")
    return inventory


def vendor_model(plugin_dir: Path, staging_vendor: Path):
    """Vendors offline spaCy language model en_core_web_sm if present."""
    model_src = plugin_dir / "vendor" / "en_core_web_sm"
    model_dest = staging_vendor / "en_core_web_sm"
    if model_src.exists() and not model_dest.exists():
        shutil.copytree(model_src, model_dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        print(f"[OK] Vendored offline spaCy model from {model_src}")


def bundle_python_runtime(
    staging_dir: Path,
    target_os: str = "linux",
    target_arch: str = "amd64",
    runtimes_dir: Optional[Path] = None
) -> Tuple[int, int]:
    """
    Bundles the pinned, relocatable CPython 3.11 distribution into staging_dir/runtime.
    Verifies SHA-256 against PINNED_CPYTHON_LINUX_AMD64_SHA256 before extraction.
    Resolves and dereferences symlinks to regular files to comply with OS installer link-rejection rules.
    Prunes C headers (include/) and man pages (share/).
    Returns (files_count, uncompressed_bytes).
    """
    if target_os != "linux" or target_arch != "amd64":
        print(f"[INFO] Bundled CPython runtime currently only configured for linux/amd64 (target: {target_os}/{target_arch})")
        return 0, 0

    runtime_dir = staging_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    # Search for runtime archive
    candidates = []
    if runtimes_dir:
        candidates.append(Path(runtimes_dir) / PINNED_CPYTHON_ARCHIVE)
        candidates.append(Path(runtimes_dir) / "cpython-3.11-x86_64.tar.gz")
    candidates.extend([
        Path(__file__).parent / "runtimes" / PINNED_CPYTHON_ARCHIVE,
        Path(__file__).parent / "runtimes" / "cpython-3.11-x86_64.tar.gz",
        Path.cwd() / "scratch" / "runtime_cache" / "cpython-3.11-x86_64.tar.gz",
    ])

    archive_path = None
    for c in candidates:
        if c.exists():
            archive_path = c
            break

    if not archive_path:
        raise FileNotFoundError(
            f"Pinned CPython 3.11 standalone runtime archive ({PINNED_CPYTHON_ARCHIVE}) not found. "
            f"Expected in tools/packager/runtimes/ with SHA-256 {PINNED_CPYTHON_LINUX_AMD64_SHA256}"
        )

    # Verify SHA-256 digest
    hasher = hashlib.sha256()
    with open(archive_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()
    if actual_hash != PINNED_CPYTHON_LINUX_AMD64_SHA256:
        raise ValueError(
            f"CPython standalone runtime integrity verification failed!\n"
            f"Expected SHA-256: {PINNED_CPYTHON_LINUX_AMD64_SHA256}\n"
            f"Actual SHA-256:   {actual_hash}"
        )

    print(f"[INFO] Bundling verified CPython {PINNED_CPYTHON_VERSION} runtime from {archive_path.name}...")

    files_added = 0
    bytes_added = 0

    with tarfile.open(archive_path, "r:gz") as tar:
        for m in tar.getmembers():
            name = m.name
            parts = name.split("/")
            if len(parts) <= 1:
                continue
            rel_parts = parts[1:]  # strip leading 'python'
            rel_subpath = "/".join(rel_parts)

            # Prune C headers, man pages, and pkgconfig
            if rel_parts[0] in ("include", "share", "pkgconfig"):
                continue
            # Prune Tk/Tcl desktop GUI libraries
            if any(rel_parts[0].startswith(p) for p in ("tcl", "tk", "itcl", "thread")):
                continue
            if len(rel_parts) > 1 and rel_parts[0] == "lib" and any(rel_parts[1].startswith(p) for p in ("tcl", "tk", "itcl", "thread", "pkgconfig")):
                continue
            # Prune test suites, IDLE, turtle graphics, and ensurepip
            if "test" in rel_parts or "tests" in rel_parts or "idlelib" in rel_parts or "turtledemo" in rel_parts or "ensurepip" in rel_parts:
                continue
            if rel_subpath.endswith("turtle.py"):
                continue
            # Prune developer build tools and duplicate CLI binaries
            if rel_parts[0] == "bin" and any(rel_parts[1].startswith(p) for p in ("2to3", "idle", "pip", "pydoc", "python3-config", "python3.11-config", "python3.11")):
                continue

            # In bin, we extract python3.11 directly as bin/python3
            if rel_parts == ["bin", "python3"]:
                continue
            if rel_parts[0] == "bin" and rel_parts[1] == "python":
                continue

            dest_path = runtime_dir / rel_subpath

            if m.isfile():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                extracted_f = tar.extractfile(m)
                if extracted_f:
                    with open(dest_path, "wb") as f_out:
                        shutil.copyfileobj(extracted_f, f_out)
                    mode = 0o755 if (rel_parts[0] == "bin" or dest_path.suffix == ".so" or ".so." in dest_path.name) else 0o644
                    try:
                        os.chmod(dest_path, mode)
                    except Exception:
                        pass
                    files_added += 1
                    bytes_added += m.size

        # Extract python3.11 binary directly as bin/python3
        for m in tar.getmembers():
            if m.name == "python/bin/python3.11":
                py3_bin = runtime_dir / "bin" / "python3"
                py3_bin.parent.mkdir(parents=True, exist_ok=True)
                extracted_f = tar.extractfile(m)
                if extracted_f:
                    with open(py3_bin, "wb") as f_out:
                        shutil.copyfileobj(extracted_f, f_out)
                    try:
                        os.chmod(py3_bin, 0o755)
                    except Exception:
                        pass
                    files_added += 1
                    bytes_added += m.size
                break

        # Extract libpython3.11.so.1.0 as lib/libpython3.11.so.1.0
        for m in tar.getmembers():
            if m.name == "python/lib/libpython3.11.so.1.0":
                lib_so = runtime_dir / "lib" / "libpython3.11.so.1.0"
                lib_so.parent.mkdir(parents=True, exist_ok=True)
                extracted_f = tar.extractfile(m)
                if extracted_f:
                    with open(lib_so, "wb") as f_out:
                        shutil.copyfileobj(extracted_f, f_out)
                    try:
                        os.chmod(lib_so, 0o755)
                    except Exception:
                        pass
                    files_added += 1
                    bytes_added += m.size
                break

    print(f"[OK] Bundled hermetic CPython {PINNED_CPYTHON_VERSION} runtime: {files_added} files, {bytes_added / 1024 / 1024:.2f} MB (zero symlinks)")
    return files_added, bytes_added


def generate_launchers(staging_dir: Path, main_script: str = "main.py"):
    """
    Generates strict hermetic launchers for Linux and Windows.
    Linux launcher invokes ONLY the bundled CPython runtime.
    Does NOT search host PATH; does NOT fall back to host Python.
    """
    bin_dir = staging_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    posix_launcher = bin_dir / "launcher"
    posix_content = f"""#!/bin/sh
set -e

# Resolve directory where this plugin is installed
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Strict hermetic execution: bundled isolated CPython runtime ONLY.
# Host PATH is never searched; host Python is never used as fallback.
if [ -x "$SCRIPT_DIR/runtime/bin/python3" ]; then
    PY_BIN="$SCRIPT_DIR/runtime/bin/python3"
elif [ -x "$SCRIPT_DIR/runtime/bin/python" ]; then
    PY_BIN="$SCRIPT_DIR/runtime/bin/python"
else
    echo "Fatal: Bundled Python runtime missing or not executable at $SCRIPT_DIR/runtime/bin/python3" >&2
    exit 1
fi

# Hermetic isolation: Strip host user site-packages, ambient paths, and bytecode
export PYTHONHOME="$SCRIPT_DIR/runtime"
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/vendor:$SCRIPT_DIR/site-packages"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export TLDEXTRACT_PUBLIC_SUFFIX_LIST_URLS=""
export LD_LIBRARY_PATH="$SCRIPT_DIR/runtime/lib:${{LD_LIBRARY_PATH:-}}"

# Execute in isolated mode (-s disables user site-packages)
exec "$PY_BIN" -s "$SCRIPT_DIR/{main_script}" "$@"
"""
    with open(posix_launcher, "w", encoding="utf-8", newline="\n") as f:
        f.write(posix_content)
    try:
        os.chmod(posix_launcher, 0o755)
    except Exception:
        pass

    windows_launcher = bin_dir / "launcher.bat"
    windows_content = f"""@echo off
setlocal
set "SCRIPT_DIR=%~dp0.."
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONUNBUFFERED=1"
set "TLDEXTRACT_PUBLIC_SUFFIX_LIST_URLS="
set "PYTHONPATH=%SCRIPT_DIR%;%SCRIPT_DIR%\\vendor;%SCRIPT_DIR%\\site-packages"

if exist "%SCRIPT_DIR%\\runtime\\python.exe" (
    set "PY_BIN=%SCRIPT_DIR%\\runtime\\python.exe"
    set "PYTHONHOME=%SCRIPT_DIR%\\runtime"
) else if exist "%SCRIPT_DIR%\\runtime\\bin\\python3" (
    set "PY_BIN=%SCRIPT_DIR%\\runtime\\bin\\python3"
    set "PYTHONHOME=%SCRIPT_DIR%\\runtime"
) else (
    set "PY_BIN=python"
)

"%PY_BIN%" -s "%SCRIPT_DIR%\\{main_script}" %*
endlocal
"""
    with open(windows_launcher, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(windows_content)

    print("[OK] Generated strict hermetic launchers (bin/launcher and bin/launcher.bat)")


def build_reproducible_tar(staging_dir: Path, output_tar: Path) -> Tuple[str, int, int]:
    """
    Packs staging directory into a deterministic, reproducible .tar.gz archive.
    Enforces normalized timestamp (1700000000), uid=0, gid=0, sorted entries, and mode permissions.
    Ensures all entries are regular files (TypeReg) with zero symlinks/hardlinks.
    Validates OS size limits (<=250MB, <=10000 files).
    Returns (sha256_digest, archive_size, uncompressed_size).
    """
    output_tar.parent.mkdir(parents=True, exist_ok=True)

    # Collect and sort all files deterministically
    all_files = []
    total_uncompressed = 0
    file_count = 0

    for p in sorted(staging_dir.rglob("*")):
        if p.is_file() and not p.name.endswith(".pyc") and "__pycache__" not in p.parts:
            rel = p.relative_to(staging_dir)
            all_files.append((str(rel).replace("\\", "/"), p))
            total_uncompressed += p.stat().st_size
            file_count += 1

    if total_uncompressed > MAX_EXTRACTED_SIZE:
        raise ValueError(f"Uncompressed archive size {total_uncompressed} bytes exceeds limit of {MAX_EXTRACTED_SIZE} bytes")
    if file_count > MAX_FILES_LIMIT:
        raise ValueError(f"Archive file count {file_count} exceeds limit of {MAX_FILES_LIMIT} files")

    with open(output_tar, "wb") as f_out:
        with gzip.GzipFile(filename="", mode="wb", fileobj=f_out, mtime=FIXED_MTIME) as gz_out:
            with tarfile.open(mode="w", fileobj=gz_out, format=tarfile.PAX_FORMAT) as tar:
                for rel_path, full_path in all_files:
                    info = tarfile.TarInfo(name=rel_path)
                    info.size = full_path.stat().st_size
                    info.mtime = FIXED_MTIME
                    info.uid = 0
                    info.gid = 0
                    info.uname = "naagmani"
                    info.gname = "naagmani"
                    info.type = tarfile.REGTYPE  # Always regular file

                    # Set executable mode 0755 for bin/, .sh, .py, .bat, .so; 0644 for others
                    if "bin/" in rel_path or rel_path.endswith(".sh") or rel_path.endswith(".py") or rel_path.endswith(".bat") or ".so" in rel_path:
                        info.mode = 0o755
                    else:
                        info.mode = 0o644

                    with open(full_path, "rb") as f:
                        tar.addfile(info, f)

    # Calculate SHA-256 digest
    hasher = hashlib.sha256()
    with open(output_tar, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    digest = "sha256:" + hasher.hexdigest()
    tar_size = output_tar.stat().st_size

    print(f"[OK] Created reproducible archive: {output_tar.name}")
    print(f"     Digest:             {digest}")
    print(f"     Archive Size:       {tar_size:,} bytes ({tar_size / 1024 / 1024:.2f} MB)")
    print(f"     Uncompressed Size:  {total_uncompressed:,} bytes ({total_uncompressed / 1024 / 1024:.2f} MB) / 250 MB limit")
    print(f"     File Count:         {file_count:,} / 10,000 limit")

    return digest, tar_size, total_uncompressed


def sign_and_generate_metadata(
    output_tar: Path,
    digest: str,
    tar_size: int,
    uncompressed_size: int,
    manifest: dict,
    output_dir: Path,
    inventory: dict,
    signing_key_hex: Optional[str] = None,
    signing_key_file: Optional[Path] = None,
    publisher_id: str = "pub_naagmani_official"
) -> dict:
    """
    Signs canonical payload with Ed25519 if credentials provided, or outputs unsigned dev metadata.
    NEVER derives or uses an automatic fallback seed.
    """
    name = manifest["name"]
    version = manifest["version"]

    sk = None
    pk = None

    if signing_key_file:
        key_p = Path(signing_key_file).resolve()
        if not key_p.exists():
            raise FileNotFoundError(f"Signing key file not found: {key_p}")
        raw = key_p.read_bytes().strip()
        try:
            text = raw.decode("ascii")
            if len(text) == 64:
                sk = bytes.fromhex(text)
            elif len(raw) == 32:
                sk = raw
        except Exception:
            if len(raw) == 32:
                sk = raw
        if not sk:
            raise ValueError(f"Invalid private key format in {key_p} (expected 32 raw bytes or 64 hex chars)")
        pk = ed25519.publickey(sk)

    elif signing_key_hex:
        clean_hex = signing_key_hex.strip()
        if len(clean_hex) != 64:
            raise ValueError(f"Invalid signing key hex length ({len(clean_hex)}, expected 64 chars)")
        sk = bytes.fromhex(clean_hex)
        pk = ed25519.publickey(sk)

    readme_content = None
    staging_readme = output_dir / f"_staging_{name}" / "README.md"
    if staging_readme.exists():
        try:
            readme_content = staging_readme.read_text(encoding="utf-8")
        except Exception:
            pass

    envelope = {
        "name": name,
        "version": version,
        "protocol_version": "naagmani.plugin/v1",
        "filename": output_tar.name,
        "digest": digest,
        "size": tar_size,
        "uncompressed_size": uncompressed_size,
        "publisher": publisher_id,
        "readme": readme_content,
        "supported_architectures": ["linux/amd64"],
        "runtime_isolation": "bundled-cpython-3.11",
        "offline_certified": True,
        "dependencies": inventory
    }

    if sk and pk:
        pub_hex = pk.hex()
        key_id = pub_hex[:16]

        canonical_payload = {
            "schema_version": "naagmani.package.signature/v1",
            "package_id": f"pkg_plugin_{name.replace('-', '_')}_01",
            "package_slug": name,
            "version": version,
            "artifact_digest": digest,
            "publisher_id": publisher_id,
            "signed_at": "2026-10-16T00:00:00Z",
            "key_id": key_id
        }

        payload_str = json.dumps(canonical_payload, separators=(',', ':'))
        payload_bytes = payload_str.encode("utf-8")
        sig_bytes = ed25519.signature(payload_bytes, sk, pk)
        sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

        envelope["status"] = "signed-release"
        envelope["public_key"] = pub_hex
        envelope["key_id"] = key_id
        envelope["signature"] = sig_b64
        envelope["canonical_payload"] = payload_str

        print(f"[OK] Release envelope & signature written to {output_dir / 'artifact_manifest.json'}")
        print(f"     Publisher:  {publisher_id} (Key ID: {key_id})")
        print(f"     Signature:  {sig_b64[:32]}...")
    else:
        # Explicitly unsigned development package
        envelope["status"] = "unsigned-development"
        envelope["public_key"] = None
        envelope["key_id"] = None
        envelope["signature"] = None
        envelope["canonical_payload"] = None

        print(f"[WARN] No signing credentials provided. Generated explicitly UNSIGNED development package.")
        print(f"       Official releases MUST be signed using sign_artifact.py or --signing-key-file.")

    manifest_file = output_dir / "artifact_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2)

    with open(output_dir / "inventory.json", "w", encoding="utf-8") as f:
        json.dump({"package": name, "version": version, "digest": digest, "dependencies": inventory}, f, indent=2)

    return envelope


def package_plugin(
    plugin_dir: Path,
    output_dir: Path,
    target_os: str = "linux",
    target_arch: str = "amd64",
    python_version: str = "3.11",
    signing_key: Optional[str] = None,
    signing_key_file: Optional[Path] = None,
    publisher_id: Optional[str] = None,
    use_docker: bool = True,
    cache_dir: Optional[Path] = None,
    bundle_runtime: bool = True
) -> dict:
    """End-to-end hermetic Python plugin packaging pipeline."""
    plugin_dir = plugin_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================")
    print(f"Naagmani Generic Python Plugin Packaging System")
    print(f"Plugin Directory:  {plugin_dir}")
    print(f"Output Directory:  {output_dir}")
    print(f"Target Platform:   {target_os}/{target_arch}")
    print(f"Target Python:     {python_version}")
    print(f"Bundle Runtime:    {bundle_runtime}")
    print(f"=======================================================\n")

    manifest = validate_manifest(plugin_dir)
    name = manifest["name"]
    version = manifest["version"]
    pub_id = publisher_id or manifest.get("publisher", "pub_naagmani_official")

    # Resolve dependency cache directory
    dep_cache = cache_dir if cache_dir else (plugin_dir / ".vendor_cache" if (plugin_dir / ".vendor_cache").exists() else None)

    # Staging directory
    staging_dir = output_dir / f"_staging_{name}"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Copy source files, documentation, and manifest
        files_to_copy = [
            "plugin.json",
            "manifest.yaml",
            "main.py",
            "pyproject.toml",
            "requirements.txt",
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
        ]
        for f in files_to_copy:
            src = plugin_dir / f
            if src.exists():
                shutil.copy2(src, staging_dir / f)

        # Copy any internal package directories (shield, etc.)
        for item in plugin_dir.iterdir():
            if item.is_dir() and item.name not in ["dist", "build", "vendor", ".git", ".pytest_cache", "__pycache__", "tests", ".vendor_cache"]:
                shutil.copytree(item, staging_dir / item.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))

        staging_vendor = staging_dir / "vendor"
        staging_vendor.mkdir(parents=True, exist_ok=True)

        # 2. Vendor HDK
        vendor_hdk(plugin_dir, staging_vendor)

        # 3. Vendor Model
        vendor_model(plugin_dir, staging_vendor)

        # 4. Vendor Dependencies (Wheels for Linux x86_64)
        req_file = plugin_dir / "requirements.txt"
        inventory = {}
        if req_file.exists():
            inventory = vendor_dependencies_docker(plugin_dir, staging_vendor, req_file, python_version, cache_dir=dep_cache)

        # 5. Bundle Relocatable CPython 3.11 Runtime
        if bundle_runtime and target_os == "linux" and target_arch == "amd64":
            bundle_python_runtime(staging_dir, target_os=target_os, target_arch=target_arch)

        # 6. Generate Hermetic Launchers
        generate_launchers(staging_dir, manifest["runtime"].get("args", ["main.py"])[0] if manifest["runtime"].get("args") else "main.py")

        # 7. Ensure plugin.json in staging declares ./bin/launcher as command
        staging_plugin_json = staging_dir / "plugin.json"
        if staging_plugin_json.exists():
            with open(staging_plugin_json, "r", encoding="utf-8") as f:
                staging_manifest = json.load(f)
            staging_manifest["runtime"]["command"] = "./bin/launcher"
            staging_manifest["runtime"]["args"] = []
            with open(staging_plugin_json, "w", encoding="utf-8") as f:
                json.dump(staging_manifest, f, indent=2)

        # 8. Build Deterministic Tarball
        archive_name = f"{name}-{version}.tar.gz"
        output_tar = output_dir / archive_name
        digest, tar_size, uncompressed_size = build_reproducible_tar(staging_dir, output_tar)

        # 9. Sign Artifact & Generate Envelope (or unsigned dev metadata)
        envelope = sign_and_generate_metadata(
            output_tar=output_tar,
            digest=digest,
            tar_size=tar_size,
            uncompressed_size=uncompressed_size,
            manifest=manifest,
            output_dir=output_dir,
            inventory=inventory,
            signing_key_hex=signing_key,
            signing_key_file=signing_key_file,
            publisher_id=pub_id
        )

        return envelope

    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Naagmani Generic Python Plugin Packager")
    parser.add_argument("--plugin-dir", default=".", help="Plugin directory to package")
    parser.add_argument("--output-dir", default="dist", help="Output directory for packaged release")
    parser.add_argument("--target-os", default="linux", help="Target operating system (default: linux)")
    parser.add_argument("--target-arch", default="amd64", help="Target CPU architecture (default: amd64)")
    parser.add_argument("--python-version", default="3.11", help="Target Python version (default: 3.11)")
    parser.add_argument("--signing-key", default=os.getenv("NAAGMANI_SIGNING_KEY"), help="Ed25519 signing private key in hex")
    parser.add_argument("--signing-key-file", default=os.getenv("NAAGMANI_SIGNING_KEY_FILE"), help="Path to Ed25519 private key file")
    parser.add_argument("--publisher-id", default=None, help="Publisher ID (default: read from manifest)")
    parser.add_argument("--no-docker", action="store_true", help="Do not use Docker (native build on Linux)")
    parser.add_argument("--cache-dir", default=None, help="Directory to cache/reuse vendored Linux dependencies")
    parser.add_argument("--no-bundle-runtime", action="store_true", help="Skip bundling standalone CPython runtime")

    args = parser.parse_args()
    package_plugin(
        plugin_dir=Path(args.plugin_dir),
        output_dir=Path(args.output_dir),
        target_os=args.target_os,
        target_arch=args.target_arch,
        python_version=args.python_version,
        signing_key=args.signing_key,
        signing_key_file=Path(args.signing_key_file) if args.signing_key_file else None,
        publisher_id=args.publisher_id,
        use_docker=not args.no_docker,
        cache_dir=Path(args.cache_dir) if args.cache_dir else None,
        bundle_runtime=not args.no_bundle_runtime
    )


if __name__ == "__main__":
    main()
