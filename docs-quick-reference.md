
## Windows PowerShell shortcut

For Windows, `KnotBridge.ps1` provides a simpler workflow without remembering the Python arguments.

From your local repository folder, copy the script there or call it by its full path.

Configure both remotes:

```powershell
.\KnotBridge.ps1 init `
  -GitHubUrl "git@github.com:YOUR_GITHUB_USERNAME/KnotBridge.git" `
  -TangledUrl "git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7"
```

Preview the push:

```powershell
.\KnotBridge.ps1 push -Branch main -DryRun
```

Push to both destinations:

```powershell
.\KnotBridge.ps1 push -Branch main
```

Push only to Tangled:

```powershell
.\KnotBridge.ps1 push -Branch main -Target tangled
```

Retry Tangled after a GitHub-success/Tangled-failure result:

```powershell
.\KnotBridge.ps1 retry -Target tangled -Branch main
```

Compare remote branches:

```powershell
.\KnotBridge.ps1 status -Branch main
```

Run diagnostics:

```powershell
.\KnotBridge.ps1 doctor
```

If PowerShell blocks local scripts, use this one-time, user-scoped setting:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

The script never force-pushes and never stores credentials. It uses the Git and SSH configuration already installed on your laptop.
