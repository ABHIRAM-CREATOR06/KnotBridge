#!/usr/bin/env python3
"""Safe, small GitHub–Tangled push assistant.

This prototype intentionally uses the user's existing Git and SSH/HTTPS setup.
It does not store credentials, create commits, or force-push.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Iterable

TARGETS = ("github", "tangled")
_SHA_RE = re.compile(r"^[0-9a-f]{7,64}$", re.I)


@dataclass
class Result:
    target: str
    operation: str
    status: str
    branch: str | None = None
    commit: str | None = None
    message: str = ""
    retryable: bool = False
    exit_code: int | None = None


class GitError(RuntimeError):
    def __init__(self, code: str, message: str, exit_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


def run_git(args: list[str], *, cwd: str | None = None, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    """Run Git without a shell and with credentials excluded from output."""
    if dry_run:
        return subprocess.CompletedProcess(["git", *args], 0, "", "")
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
        )
    except FileNotFoundError as exc:
        raise GitError("GIT_NOT_FOUND", "Git is not installed or is not on PATH") from exc


def git_output(args: list[str], *, cwd: str | None = None) -> str:
    result = run_git(args, cwd=cwd)
    if result.returncode:
        message = redact(result.stderr or result.stdout).strip()
        raise GitError("GIT_ERROR", message or "Git command failed", result.returncode)
    return result.stdout.strip()


def redact(value: str) -> str:
    """Remove common credential-bearing URL forms from displayed text."""
    value = re.sub(r"(https?://)([^/@\s]+):([^/@\s]+)@", r"\1***:***@", value)
    value = re.sub(r"(https?://)([^/@\s]+)@", r"\1***@", value)
    value = re.sub(r"(?i)(authorization\s*[:=]\s*)([^\s]+)", r"\1***", value)
    return value


def repo_root() -> str:
    return git_output(["rev-parse", "--show-toplevel"])


def current_branch() -> str:
    branch = git_output(["symbolic-ref", "--quiet", "--short", "HEAD"])
    if not branch:
        raise GitError("NO_HEAD", "The repository is in detached HEAD state; specify a branch explicitly")
    return branch


def head_sha() -> str:
    sha = git_output(["rev-parse", "HEAD"])
    if not _SHA_RE.fullmatch(sha):
        raise GitError("NO_HEAD", "The repository has no valid HEAD commit")
    return sha


def remote_url(name: str) -> str:
    result = run_git(["remote", "get-url", name])
    if result.returncode:
        raise GitError("REMOTE_NOT_FOUND", f"Git remote '{name}' is not configured", result.returncode)
    return result.stdout.strip()


def configured_targets() -> dict[str, str]:
    targets: dict[str, str] = {}
    for target in TARGETS:
        result = run_git(["remote", "get-url", target])
        if result.returncode == 0 and result.stdout.strip():
            targets[target] = result.stdout.strip()
    return targets


def classify_push(result: subprocess.CompletedProcess[str]) -> tuple[str, str, bool]:
    text = redact((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    lowered = text.lower()
    if result.returncode == 0:
        return "success", "Push completed", False
    if any(word in lowered for word in ("timed out", "timeout", "connection reset", "connection closed", "early eof")):
        return "unknown", "The connection ended before Git could confirm the remote result; verify remote state before retrying", False
    if "non-fast-forward" in lowered or "rejected" in lowered:
        return "failed", "The remote rejected the update; fetch and reconcile the branch before retrying", False
    if "permission denied" in lowered or "authentication" in lowered or "could not read password" in lowered:
        return "failed", "Authentication or permission failed; check the credential or SSH configuration", True
    return "failed", text[-500:] or "Git rejected the push", True


def push_target(target: str, branch: str, *, tags: bool = False, dry_run: bool = False) -> Result:
    commit = head_sha()
    if target not in configured_targets():
        return Result(target, "push", "skipped", branch, commit, f"No '{target}' remote is configured", False)

    if dry_run:
        message = f"Would push {branch} ({commit[:12]}) to {target}"
        if tags:
            message += " and tags"
        return Result(target, "push", "success", branch, commit, message, False, 0)

    args = ["push", target, f"HEAD:refs/heads/{branch}"]
    result = run_git(args)
    status, message, retryable = classify_push(result)
    if status == "success" and tags:
        tag_result = run_git(["push", target, "--tags"])
        tag_status, tag_message, tag_retryable = classify_push(tag_result)
        if tag_status != "success":
            status = tag_status
            message = f"Branch push succeeded, but tag push: {tag_message}"
            retryable = tag_retryable
            return Result(target, "push", status, branch, commit, message, retryable, tag_result.returncode)
        message = "Branch and tag push completed"
    return Result(target, "push", status, branch, commit, message, retryable, result.returncode)


def configure(args: argparse.Namespace) -> list[Result]:
    results: list[Result] = []
    for target, url in (("github", args.github), ("tangled", args.tangled)):
        if not url:
            continue
        existing = run_git(["remote", "get-url", target])
        if existing.returncode == 0:
            result = run_git(["remote", "set-url", target, url])
        else:
            result = run_git(["remote", "add", target, url])
        if result.returncode:
            results.append(Result(target, "configure", "failed", message=redact(result.stderr.strip()), retryable=True, exit_code=result.returncode))
        else:
            results.append(Result(target, "configure", "success", message=f"Configured {target} remote", exit_code=0))
    return results


def status(args: argparse.Namespace) -> list[Result]:
    branch = args.branch or current_branch()
    commit = head_sha()
    results: list[Result] = []
    for target in TARGETS:
        if target not in configured_targets():
            results.append(Result(target, "status", "skipped", branch, commit, f"No '{target}' remote is configured"))
            continue
        result = run_git(["ls-remote", target, f"refs/heads/{branch}"])
        if result.returncode:
            results.append(Result(target, "status", "unavailable", branch, commit, redact(result.stderr.strip()), True, result.returncode))
            continue
        remote_sha = result.stdout.split()[0] if result.stdout.strip() else None
        message = "Remote branch not found" if not remote_sha else ("Remote matches local HEAD" if remote_sha == commit else f"Remote is at {remote_sha[:12]}")
        results.append(Result(target, "status", "success", branch, commit, message, False, 0))
    return results


def doctor() -> list[Result]:
    results: list[Result] = []
    results.append(Result("local", "doctor", "success" if shutil.which("git") else "failed", message="Git is available" if shutil.which("git") else "Git is not installed", retryable=False))
    try:
        root = repo_root()
        results.append(Result("local", "doctor", "success", message=f"Repository: {root}"))
    except GitError as exc:
        results.append(Result("local", "doctor", "failed", message=str(exc), retryable=False, exit_code=exc.exit_code))
        return results
    for target, url in configured_targets().items():
        scheme = "SSH/other" if "://" not in url else url.split(":", 1)[0].upper()
        results.append(Result(target, "doctor", "success", message=f"Configured ({scheme})"))
    for target in TARGETS:
        if target not in configured_targets():
            results.append(Result(target, "doctor", "skipped", message=f"No '{target}' remote is configured"))
    return results


def emit(results: Iterable[Result], as_json: bool) -> int:
    items = [asdict(item) for item in results]
    if as_json:
        print(json.dumps(items, indent=2))
    else:
        for item in items:
            symbol = {"success": "OK", "failed": "FAIL", "unknown": "?", "unavailable": "OFF", "skipped": "SKIP"}.get(item["status"], item["status"].upper())
            target = item["target"]
            print(f"[{symbol}] {target}: {item['message']}")
    return 1 if any(item["status"] in {"failed", "unknown"} for item in items) else 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="forge-sync", description="Safely push the same Git commits to GitHub and Tangled")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Configure GitHub and Tangled remotes")
    init.add_argument("--github", help="GitHub clone/push URL")
    init.add_argument("--tangled", help="Tangled clone/push URL")

    push = sub.add_parser("push", help="Push the current branch to both targets")
    push.add_argument("--branch", help="Branch to push (default: current branch)")
    push.add_argument("--tags", action="store_true", help="Also push tags")
    push.add_argument("--target", choices=TARGETS, help="Push only one destination")
    push.add_argument("--dry-run", action="store_true")

    retry = sub.add_parser("retry", help="Retry one destination")
    retry.add_argument("target", choices=TARGETS)
    retry.add_argument("--branch", help="Branch to push (default: current branch)")
    retry.add_argument("--tags", action="store_true")
    retry.add_argument("--dry-run", action="store_true")

    stat = sub.add_parser("status", help="Compare local HEAD with remote branches")
    stat.add_argument("--branch", help="Branch to inspect")
    sub.add_parser("doctor", help="Check local Git and remote configuration")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            results = configure(args)
        elif args.command == "push":
            branch = args.branch or current_branch()
            targets = [args.target] if args.target else list(TARGETS)
            results = [push_target(t, branch, tags=args.tags, dry_run=args.dry_run) for t in targets]
        elif args.command == "retry":
            results = [push_target(args.target, args.branch or current_branch(), tags=args.tags, dry_run=args.dry_run)]
        elif args.command == "status":
            results = status(args)
        else:
            results = doctor()
        return emit(results, args.json)
    except GitError as exc:
        return emit([Result("local", args.command, "failed", message=f"{exc.code}: {exc}", retryable=False, exit_code=exc.exit_code)], args.json)


if __name__ == "__main__":
    raise SystemExit(main())
