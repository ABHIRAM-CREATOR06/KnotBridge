from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "forge_sync.py"


def run(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        if args and args[0] == "show-ref" and not result.stdout.strip():
            return ""
        raise AssertionError(f"git failed: {args}\n{result.stderr}")
    return result.stdout.strip()


class KnotBridgeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git("init", "-q", cwd=self.repo)
        git("config", "user.name", "KnotBridge Test", cwd=self.repo)
        git("config", "user.email", "test@example.invalid", cwd=self.repo)
        (self.repo / "README.md").write_text("# test\n", encoding="utf-8")
        git("add", "README.md", cwd=self.repo)
        git("commit", "-q", "-m", "initial commit", cwd=self.repo)
        git("branch", "-M", "main", cwd=self.repo)
        self.github = self.root / "github.git"
        self.tangled = self.root / "tangled.git"
        git("init", "--bare", "-q", str(self.github), cwd=self.root)
        git("init", "--bare", "-q", str(self.tangled), cwd=self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dry_run_does_not_mutate_remotes(self) -> None:
        run("init", "--github", str(self.github), "--tangled", str(self.tangled), cwd=self.repo)
        result = run("push", "--branch", "main", "--dry-run", cwd=self.repo)
        self.assertIn("Would push main", result.stdout)
        self.assertEqual(git("show-ref", cwd=self.github), "")
        self.assertEqual(git("show-ref", cwd=self.tangled), "")

    def test_push_updates_both_remotes(self) -> None:
        run("init", "--github", str(self.github), "--tangled", str(self.tangled), cwd=self.repo)
        result = run("push", "--branch", "main", cwd=self.repo)
        self.assertIn("github", result.stdout)
        self.assertIn("tangled", result.stdout)
        local = git("rev-parse", "HEAD", cwd=self.repo)
        github = git("rev-parse", "refs/heads/main", cwd=self.github)
        tangled = git("rev-parse", "refs/heads/main", cwd=self.tangled)
        self.assertEqual(local, github)
        self.assertEqual(local, tangled)

    def test_json_status_is_valid(self) -> None:
        run("init", "--github", str(self.github), "--tangled", str(self.tangled), cwd=self.repo)
        run("push", "--branch", "main", cwd=self.repo)
        result = run("--json", "status", "--branch", "main", cwd=self.repo)
        self.assertIn('"target": "github"', result.stdout)
        self.assertIn('"target": "tangled"', result.stdout)


if __name__ == "__main__":
    unittest.main()
