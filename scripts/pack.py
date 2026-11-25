#!/usr/bin/env python3
"""Refresh SHA256SUMS and create a new resumable ZIP of this project.

Run only after intentional source changes, state updates, and PDF checks.
Runtime build caches, Python caches, VCS metadata and old ZIPs at the project
root are excluded. archive/ contains one intentional recovered-source ZIP.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {"build", ".git", "__pycache__", ".venv", "node_modules"}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def included_files():
    files = []
    for f in ROOT.rglob("*"):
        relative = f.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if f.is_symlink():
            raise ValueError("Symlinks must be resolved before packaging: " + str(relative))
        if not f.is_file():
            continue
        if f.name == "SHA256SUMS" or (relative.parent == Path(".") and f.suffix == ".zip"):
            continue
        if f.suffix in (".pyc", ".aux", ".fls", ".fdb_latexmk", ".synctex.gz"):
            continue
        files.append(f)
    return sorted(files, key=lambda f: f.relative_to(ROOT).as_posix())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path, help="destination ZIP outside this project")
    args = p.parse_args()
    destination = args.output.resolve()
    if destination == ROOT or ROOT in destination.parents:
        p.error("Choose a ZIP destination outside the project directory")
    files = included_files()
    checksums = ROOT / "SHA256SUMS"
    checksums.write_text("".join(digest(f) + "  " + f.relative_to(ROOT).as_posix() + "\n" for f in files), encoding="utf-8")
    files.append(checksums)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
        for f in files:
            archive.write(f, ROOT.name + "/" + f.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(destination) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError("ZIP CRC failed: " + bad)
        # Verify the archived bytes, not just the source directory. This also
        # catches a file that was changed after its checksum was computed.
        checksum_member = ROOT.name + "/SHA256SUMS"
        expected = {}
        for line in archive.read(checksum_member).decode("utf-8").splitlines():
            hash_value, name = line.split("  ", 1)
            expected[ROOT.name + "/" + name] = hash_value
        if set(archive.namelist()) != set(expected) | {checksum_member}:
            raise RuntimeError("ZIP member list does not match SHA256SUMS")
        for name, hash_value in expected.items():
            h = hashlib.sha256()
            with archive.open(name) as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(block)
            if h.hexdigest() != hash_value:
                raise RuntimeError("Archived SHA-256 mismatch: " + name)
    print("Archive:", destination)
    print("Files:", len(files))
    print("Bytes:", destination.stat().st_size)
    print("SHA256:", digest(destination))
    return 0


if __name__ == "__main__":
    sys.exit(main())
