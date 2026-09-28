#!/usr/bin/env python3
"""Conservative local secret scanner for KnotBridge automation.

This is a safety check, not a replacement for a dedicated secret-scanning service.
It intentionally reports filenames and line numbers, never matching secret values.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
SECRET_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "authorized_keys"}
SECRET_SUFFIXES = {".pem", ".p12", ".pfx", ".key", ".der"}
PATTERNS = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9_\-]{20,}")),
    ("GitHub fine-grained token", re.compile(r"(?i)\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("OpenAI-style key", re.compile(r"(?i)\b(?:sk|rk)-[A-Za-z0-9]{20,}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}")),
    ("credential URL", re.compile(r"https?://[^\s/@]+:[^\s/@]+@")),
]


def files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def scan(root: Path) -> list[tuple[Path, str, int | None]]:
    findings: list[tuple[Path, str, int | None]] = []
    for path in files(root):
        if path.name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES:
            findings.append((path, "secret-like filename", None))
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append((path, label, number))
                    break
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a repository for likely secrets")
    parser.add_argument("path", nargs="?", default=".")
    args = parser.parse_args(argv)
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    findings = scan(root)
    if findings:
        print("SECRET_SCAN_FAILED")
        for path, label, line in findings:
            suffix = f":{line}" if line else ""
            print(f"- {path.relative_to(root)}{suffix}: {label}")
        print("Do not stage or push these files until the finding is removed or intentionally excluded.")
        return 1
    print("SECRET_SCAN_CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
