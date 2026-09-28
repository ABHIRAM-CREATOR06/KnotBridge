# KnotBridge

> Push once locally, keep GitHub and Tangled connected.

KnotBridge is an early-stage, local-first Git mirroring assistant for developers who want to publish the same Git commits to **GitHub** and **Tangled** without manually repeating the push workflow.

It is intentionally smaller than a complete desktop Git client. The first goal is to make the GitHub–Tangled workflow reliable, visible, and easy to retry.

```
Local commit
    ├── push to GitHub
    └── push to Tangled

KnotBridge reports the result of each destination separately.
```

## Project status

This is an exploratory prototype, not a production release. It was created to validate whether a small mirroring workflow is useful before attempting a larger Tangled desktop application.

The current prototype provides:

- A Python CLI for Windows, macOS, and Linux.

- A Windows PowerShell wrapper for common commands.

- Explicit GitHub and Tangled remotes.

- Per-remote push results.

- Dry-run support.

- Retry of one destination.

- Branch status comparison.

- Basic SSH and Git diagnostics.

- Safe defaults that do not force-push or store credentials.

## Why KnotBridge exists

Developers may want to try Tangled while continuing to use GitHub. A local mirror can make that transition gradual:

- Continue using an existing GitHub workflow.

- Publish source commits to Tangled as well.

- Experiment with Tangled without immediately migrating every collaboration workflow.

- Keep a second copy of Git history on another forge.

- Get clearer feedback when one remote succeeds and another fails.

KnotBridge does **not** claim that GitHub and Tangled become identical. It mirrors Git data only.

## What KnotBridge mirrors

### Supported

- Local commits.

- Branch references.

- Tags, when explicitly requested.

- Pushes over the Git URLs configured by the user.

### Not currently supported

- Issues.

- Pull requests.

- Reviews.

- Comments.

- Labels.

- Releases.

- Wikis.

- Project boards.

- CI results.

- Repository creation through APIs.

- Automatic conflict resolution.

- Atomic transactions across two forges.

GitHub and Tangled are independent services. A successful GitHub push cannot be rolled back automatically if Tangled fails.

## Safety model

KnotBridge follows these rules:

1. It never creates a commit automatically.

1. It never changes files in the working tree.

1. It never force-pushes by default.

1. It never deletes branches or tags automatically.

1. It never stores private SSH keys, passwords, or access tokens.

1. It uses the Git and SSH credentials already configured on the computer.

1. It reports GitHub and Tangled independently.

1. It distinguishes a confirmed failure from an ambiguous network result.

1. It makes retry explicit.

1. It does not pretend that a two-remote push is atomic.

If GitHub succeeds and Tangled fails, the local commit remains safe and the GitHub result is preserved. Retry only the failed destination after checking its state.

## Repository files

```
README.md                 Detailed project documentation
AGENTS-mirror.md          Instructions for coding agents and contributors
forge_sync.py             Cross-platform Python prototype
KnotBridge.ps1            Windows PowerShell wrapper
forge-sync-README.md      Short command reference
```

## Requirements

### Windows

- Windows 10 or Windows 11.

- Git for Windows.

- OpenSSH Client, normally included with Git for Windows or Windows optional features.

- Python 3.10 or newer for the Python CLI.

- PowerShell 5.1 or PowerShell 7 for the wrapper.

### macOS/Linux

- Git.

- Python 3.10 or newer for the Python CLI.

- OpenSSH for SSH-based remotes.

KnotBridge does not require a Python package installation for the current prototype.

## SSH setup on Windows

KnotBridge uses the existing Git/SSH setup. It does not manage private keys itself.

### Check Git and SSH

Open PowerShell:

```
git --version
ssh -V
```

If Git is missing, install [Git for Windows](https://git-scm.com/download/win).

### Start the Windows SSH agent

Open PowerShell as Administrator and run:

```
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
```

Then open a normal PowerShell window and add your private key:

```
ssh-add "$HOME\.ssh\id_ed25519_github_tangled"
```

Check loaded keys:

```
ssh-add -l
```

### Use a dedicated Ed25519 key

If you need a new key:

```
ssh-keygen -t ed25519 -C "your-email@example.com" -f "$HOME\.ssh\id_ed25519_github_tangled"
```

The files are:

```
%USERPROFILE%\.ssh\id_ed25519_github_tangled       private key
%USERPROFILE%\.ssh\id_ed25519_github_tangled.pub   public key
```

Never share the file without `.pub`.

Add the `.pub` file to:

- GitHub → Settings → SSH and GPG keys.

- Tangled → Settings → Keys.

Copy the public key on Windows:

```
Get-Content "$HOME\.ssh\id_ed25519_github_tangled.pub" | Set-Clipboard
```

### Optional SSH configuration

Create or edit:

```
notepad "$HOME\.ssh\config"
```

Example:

```
Host github.com
    HostName github.com
    User git
    IdentityFile C:/Users/YOUR_WINDOWS_USER/.ssh/id_ed25519_github_tangled
    IdentitiesOnly yes

Host tangled.org
    HostName tangled.org
    User git
    IdentityFile C:/Users/YOUR_WINDOWS_USER/.ssh/id_ed25519_github_tangled
    IdentitiesOnly yes
```

Use your actual Windows username in the path.

Test authentication:

```
ssh -T git@github.com
ssh -T git@tangled.org
```

A Tangled response such as the following means SSH authentication worked:

```
You're authenticated to ... knot.
This knot serves git over ssh, so there's no shell here.
```

## First-time setup with the Python CLI

### 1. Open your local project

```
cd "C:\Users\YOUR_WINDOWS_USER\OneDrive\Documents\GitHub\KnotBridge"
```

Use the actual path of your project.

### 2. Confirm it is a Git repository

```
git status
```

If needed:

```
git init
git branch -M main
```

### 3. Create a first commit if needed

```
git add .
git commit -m "initial commit"
```

If Git asks for your identity:

```
git config user.name "Your Name"
git config user.email "your-email@example.com"
```

Use an email address accepted or verified by the relevant service. Tangled may also support a DID-based commit email according to its documentation.

### 4. Configure the remotes

Use your GitHub repository SSH URL and the exact Tangled Git URL shown by Tangled.

For the current KnotBridge Tangled repository, the Git URL is:

```
git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7
```

Configure:

```
python forge_sync.py init `
  --github "git@github.com:YOUR_GITHUB_USERNAME/KnotBridge.git" `
  --tangled "git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7"
```

On one line:

```
python forge_sync.py init --github "git@github.com:YOUR_GITHUB_USERNAME/KnotBridge.git" --tangled "git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7"
```

### 5. Preview the push

```
python forge_sync.py push --branch main --dry-run
```

### 6. Push to both destinations

```
python forge_sync.py push --branch main
```

To include tags:

```
python forge_sync.py push --branch main --tags
```

### 7. Check the result

```
python forge_sync.py status --branch main
```

Run diagnostics:

```
python forge_sync.py doctor
```

## Windows PowerShell wrapper

The PowerShell wrapper is designed for users who want shorter Windows commands.

Copy `KnotBridge.ps1` into the local repository folder, then run:

```
cd "C:\Users\YOUR_WINDOWS_USER\OneDrive\Documents\GitHub\KnotBridge"
```

If PowerShell blocks local scripts, use this user-scoped setting:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Configure both remotes:

```
.\KnotBridge.ps1 init `
  -GitHubUrl "git@github.com:YOUR_GITHUB_USERNAME/KnotBridge.git" `
  -TangledUrl "git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7"
```

Preview:

```
.\KnotBridge.ps1 push -Branch main -DryRun
```

Push to both:

```
.\KnotBridge.ps1 push -Branch main
```

Push only to Tangled:

```
.\KnotBridge.ps1 push -Branch main -Target tangled
```

Push only to GitHub:

```
.\KnotBridge.ps1 push -Branch main -Target github
```

Retry Tangled:

```
.\KnotBridge.ps1 retry -Target tangled -Branch main
```

Compare remote state:

```
.\KnotBridge.ps1 status -Branch main
```

Run diagnostics:

```
.\KnotBridge.ps1 doctor
```

## One-command Windows sync for any repository

`KnotBridge-sync.bat` can be called from any local Git repository. It:

1. Initializes Git if needed.
2. Scans files for private keys and common credentials.
3. Configures the GitHub and Tangled remotes.
4. Stages all files only after the scan passes.
5. Creates a commit if there are changes.
6. Runs a dry-run preview.
7. Pushes the branch to both destinations.
8. Prints the final remote status.

Copy these files together or keep the batch file beside the project tools:

```text
KnotBridge-sync.bat
forge_sync.py
secret_scan.py
```

Run from PowerShell or Command Prompt:

```powershell
.\KnotBridge-sync.bat `
  "C:\path\to\any-repository" `
  "git@github.com:USERNAME/REPOSITORY.git" `
  "git@tangled.org:did:plc:REPOSITORY_DID" `
  "sync repository"
```

The batch file refuses to stage or push when it detects likely private keys, `.env` files, credential-bearing URLs, or common GitHub/AWS/OpenAI/Slack token patterns. This is a safety guard, not a replacement for reviewing the staged diff.

The batch file uses the user’s existing Git credential helper or SSH agent. It never reads, copies, uploads, or stores private keys.

For the current KnotBridge repository:

```powershell
.\KnotBridge-sync.bat `
  "C:\Users\abhir\OneDrive\Documents\GitHub\KnotBridge" `
  "git@github.com:ABHIRAM-CREATOR06/KnotBridge.git" `
  "git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7" `
  "sync repository"
```

If the scanner reports a file, inspect it before continuing. Do not bypass the scanner by adding private keys or credentials to the repository.

## Typical output

Successful push:

```
Pushing main to github...
[OK] github push succeeded.
Pushing main to tangled...
[OK] tangled push succeeded.
```

Partial success:

```
Pushing main to github...
[OK] github push succeeded.
Pushing main to tangled...
[FAIL] tangled push failed. The local commit is still safe.
```

In the partial-success case:

```
.\KnotBridge.ps1 status -Branch main
.\KnotBridge.ps1 retry -Target tangled -Branch main
```

## Troubleshooting

### `Permission denied (publickey)`

Check the SSH agent:

```
ssh-add -l
```

If the key is missing:

```
ssh-add "$HOME\.ssh\id_ed25519_github_tangled"
```

Confirm the matching `.pub` key is added to both GitHub and Tangled. Test directly:

```
ssh -i "$HOME\.ssh\id_ed25519_github_tangled" -o IdentitiesOnly=yes -T git@tangled.org
```

### You entered the Git URL by itself

This is incorrect in PowerShell:

```
git@tangled.org:did:plc:...
```

Use it with Git:

```
git ls-remote git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7
```

or:

```
git clone git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7
```

### The Tangled web URL does not work as a Git remote

A Tangled browser URL and Git SSH URL are different. Use the exact Git URL provided by the repository’s **Clone** action. A repository may use a DID-based Git URL such as:

```
git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7
```

Do not guess a path from the browser URL.

### `src refspec main does not match any`

There is no local `main` branch or no commit yet:

```
git status
git branch --show-current
git log --oneline -1
```

Create a commit and set the branch:

```
git add .
git commit -m "initial commit"
git branch -M main
```

### `non-fast-forward` or rejected push

The remote contains commits that are not in your local branch. Do not force-push automatically. Inspect first:

```
git fetch tangled main
git log --oneline --graph --decorate --all
```

Then decide whether to merge or rebase. Make a backup branch before rewriting local history.

### GitHub succeeds but Tangled fails

This is expected to be recoverable. Confirm Tangled state:

```
git ls-remote tangled refs/heads/main
```

Then retry only Tangled:

```
.\KnotBridge.ps1 retry -Target tangled -Branch main
```

### A network error occurs after pushing

The result may be ambiguous: the remote might have accepted the commit even though the client did not receive confirmation. Check status before retrying:

```
.\KnotBridge.ps1 status -Branch main
```

Do not blindly repeat a push after an ambiguous result.

## Design principles

### Local-first

A local commit is the source of truth for the initial workflow. Tangled availability should not prevent developers from committing locally.

### Explicit remotes

KnotBridge uses named remotes:

```
github   GitHub destination
tangled  Tangled destination
```

This makes each result visible and makes targeted retries possible.

### Provider-neutral Git layer

The first version uses ordinary Git commands and Git URLs. It does not require a GitHub-specific API or Tangled API for basic pushes.

### No hidden credentials

Authentication belongs to Git, SSH, the OS credential manager, or the user’s configured credential helper. KnotBridge does not ask for or store private keys.

### Clear failure recovery

A failed remote should result in a safe retry path, not a misleading “everything failed” message and not an automatic destructive recovery.

## Development

The Python prototype is dependency-free:

```
python -m py_compile forge_sync.py
python forge_sync.py --help
```

Run a dry-run inside a disposable Git repository:

```
python forge_sync.py doctor
python forge_sync.py push --branch main --dry-run
python forge_sync.py --json status --branch main
```

The PowerShell wrapper should be tested on Windows because PowerShell is platform-specific.

## Agent and contribution guidance

Read [AGENTS-mirror.md](AGENTS-mirror.md) before modifying the implementation. It defines:

- Scope boundaries.

- Safety invariants.

- Error states.

- Testing requirements.

- Credential-handling rules.

- Definition of done.

Contributions should remain small and focused. A good first contribution might be:

- Improve URL validation.

- Add a provider-neutral remote configuration file.

- Add better status comparison.

- Add deterministic tests with fake Git commands.

- Improve Windows error messages.

- Add optional JSON output fields.

Do not add issue or pull-request synchronization until the Git mirroring behavior is stable.

## Roadmap

### Phase 1: reliable Git mirroring

- Validate GitHub and Tangled URLs.

- Improve branch and tag status reporting.

- Add deterministic tests for partial failure.

- Add clearer SSH diagnostics.

- Add JSON output suitable for scripts.

### Phase 2: better developer experience

- Interactive setup wizard.

- Automatic detection of the current branch.

- Safe repository discovery.

- More useful non-fast-forward guidance.

- Optional desktop notification after completion.

### Phase 3: Tangled-aware collaboration

Only after API contracts are confirmed:

- Open a repository or commit in Tangled.

- Display pipeline status.

- Link a local branch to a Tangled pull request.

- Provide guided repository setup.

### Phase 4: possible desktop client

A full desktop client should be considered only after validating that the smaller workflow is useful. It should not be assumed to be necessary from the beginning.

## Limitations and disclaimer

KnotBridge is an experimental project. Use it first with disposable or non-critical repositories. Always keep an independent backup of important code.

The project does not guarantee atomic synchronization between GitHub and Tangled. A push can succeed on one service and fail on the other. The tool exists to make that state visible and recoverable.

## License

Choose and add a license before public distribution. Until then, treat this repository as an experimental prototype and do not assume that reuse rights are granted.
