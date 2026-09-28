# AGENTS.md — GitHub–Tangled Mirror MVP

## Mission

Build a small, safe command-line tool that helps a developer push the same local Git commits and tags to GitHub and Tangled. The tool is a **Git mirror assistant**, not a full repository synchronization service.

The core workflow is:

```text
Local commit → push to GitHub → push to Tangled → report each result
```

The tool must never imply that a push to two independent remotes is atomic. If one remote succeeds and another fails, the local commit remains safe and the user receives a precise retry command.

## Product boundary

### In scope

- Inspect the current Git repository.
- Configure named GitHub and Tangled destinations.
- Push a selected branch to each destination.
- Push tags when explicitly requested.
- Report per-remote success, failure, and unknown/ambiguous outcomes.
- Retry one destination without repeating successful destinations.
- Show branch and commit comparison information.
- Run safe connectivity and configuration diagnostics.
- Support SSH and HTTPS URLs through the user’s existing Git credential and SSH configuration.
- Provide dry-run mode.
- Provide machine-readable JSON output.

### Out of scope

- Synchronizing issues, pull requests, reviews, comments, labels, releases, or CI results.
- Storing private keys or passwords.
- Automatically creating repositories on GitHub or Tangled.
- Automatic force pushes, branch deletions, or history rewrites.
- Background daemons or silent scheduled pushes.
- Claiming atomic consistency across providers.
- Scraping GitHub or Tangled web pages.

## Safety invariants

1. The tool never creates a commit by itself. The developer creates commits locally.
2. A normal push never uses `--force`, `--force-with-lease`, or `--delete`.
3. A normal push never changes the working tree.
4. A failed destination never causes a successful destination to be rolled back.
5. An ambiguous network result is reported as `unknown`, not `failed`, until the remote state is checked.
6. The tool never retries a push automatically after an ambiguous result.
7. Private keys, tokens, credentials, and full environment variables never appear in output or logs.
8. Remote URLs are redacted in normal output if they contain embedded credentials.
9. Configuration changes are explicit and previewable.
10. The tool must work without Tangled API access because Git push uses the configured remote URL.

## Required commands

```text
forge-sync init       Configure GitHub and Tangled destinations
forge-sync status     Compare local branch state and configured destinations
forge-sync push       Push branch to configured destinations
forge-sync retry      Retry one named destination
forge-sync doctor     Check Git, remotes, URL format, SSH/HTTPS reachability
```

Recommended options:

```text
--branch <name>
--tags
--remote <name>
--target <github|tangled>
--dry-run
--json
--verbose
```

## Remote model

Keep fetch and push URLs separate. A safe default is:

```text
origin fetch URL: GitHub or Tangled primary
github push URL: git@github.com:owner/repo.git
tangled push URL: git@tangled.org:handle/repo
```

Do not assume that every Tangled handle is a valid repository path. Preserve the exact clone URL supplied by the user.

Use Git’s process interface with argument arrays. Never build a shell command string from user input.

## Result model

Every destination must return:

```json
{
  "target": "github",
  "operation": "push",
  "status": "success|failed|unknown|skipped",
  "branch": "main",
  "commit": "<sha>",
  "message": "safe human-readable summary",
  "retryable": true,
  "exit_code": 0
}
```

`unknown` means Git could not confirm whether the remote accepted the update. This commonly occurs when the connection breaks after the remote receives data. The next action is status verification, not blind retry.

## Error handling

Classify errors into stable codes:

```text
CONFIG_MISSING
NOT_A_REPOSITORY
NO_HEAD
DIRTY_WORKTREE          # only when an operation requires clean state
REMOTE_NOT_FOUND
AUTHENTICATION_FAILED
HOST_KEY_ERROR
NETWORK_TIMEOUT
NON_FAST_FORWARD
REMOTE_REJECTED
AMBIGUOUS_RESULT
GIT_NOT_FOUND
UNSUPPORTED_OPERATION
```

Messages must explain:

1. What happened.
2. Which destination was affected.
3. Whether the local commit is safe.
4. What command or action should happen next.

## Agent workflow

Before editing:

1. Read this file and the project README.
2. Inspect the current Git adapter and tests.
3. Confirm whether the requested change affects push safety or remote configuration.
4. State the smallest testable change.

While editing:

- Keep the implementation deterministic.
- Use standard library functionality where practical.
- Add tests before changing error behavior.
- Use fake Git runners in unit tests.
- Use temporary real Git repositories in integration tests.
- Never use a developer’s real GitHub or Tangled credentials in tests.
- Preserve successful remote results when another destination fails.

After editing:

```text
format → typecheck → unit tests → integration tests → manual dry-run
```

Review the diff for shell injection, secret leakage, accidental force-push flags, and destructive defaults.

## Testing requirements

At minimum test:

- Both destinations succeed.
- GitHub succeeds and Tangled fails.
- Tangled succeeds and GitHub fails.
- Both destinations fail.
- No configured destination.
- Missing branch.
- Non-fast-forward rejection.
- Authentication failure.
- Timeout after remote may have accepted the push.
- Tag push is opt-in.
- Dry-run performs no mutation.
- JSON output is valid and secret-free.
- Retry targets only the selected destination.
- Remote URLs with embedded credentials are redacted.

## Definition of done

A change is complete only when:

- It cannot silently overwrite remote history.
- It distinguishes failed from unknown push outcomes.
- It provides a precise retry path.
- It preserves local work.
- It has deterministic tests for success and failure paths.
- It documents any provider-specific behavior.
- It does not claim to synchronize issues, PRs, or metadata unless that feature is separately implemented and tested.
