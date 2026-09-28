[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('init', 'push', 'status', 'doctor', 'retry')]
    [string]$Command = 'push',

    [string]$GitHubUrl,
    [string]$TangledUrl = 'git@tangled.org:did:plc:52gfehzyxijezbd7y726ces7',
    [string]$Branch,
    [ValidateSet('github', 'tangled')]
    [string]$Target,
    [switch]$Tags,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & git @Arguments
    return $LASTEXITCODE
}

function Get-CurrentBranch {
    $value = (& git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($value)) {
        throw 'Could not determine the current branch. Make sure this is a non-detached Git repository.'
    }
    return $value
}

function Get-HeadSha {
    $value = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($value)) {
        throw 'This repository has no commit yet. Create a commit before pushing.'
    }
    return $value
}

function Test-Remote {
    param([string]$Name)
    & git remote get-url $Name *> $null
    return ($LASTEXITCODE -eq 0)
}

function Set-Remote {
    param([string]$Name, [string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url)) {
        throw "A URL is required for the $Name remote."
    }
    if (Test-Remote $Name) {
        $code = Invoke-Git @('remote', 'set-url', $Name, $Url)
    } else {
        $code = Invoke-Git @('remote', 'add', $Name, $Url)
    }
    if ($code -ne 0) { throw "Could not configure the $Name remote." }
    Write-Host "Configured $Name remote."
}

function Push-One {
    param([string]$Name, [string]$BranchName, [bool]$PushTags)
    if (-not (Test-Remote $Name)) {
        Write-Host "[SKIP] $Name remote is not configured."
        return $false
    }
    if ($DryRun) {
        Write-Host "[DRY-RUN] Would push $BranchName to $Name$(if ($PushTags) { ' and tags' } else { '' })."
        return $true
    }

    Write-Host "Pushing $BranchName to $Name..."
    $code = Invoke-Git @('push', $Name, "HEAD:refs/heads/$BranchName")
    if ($code -ne 0) {
        Write-Host "[FAIL] $Name push failed. The local commit is still safe." -ForegroundColor Red
        return $false
    }
    if ($PushTags) {
        $code = Invoke-Git @('push', $Name, '--tags')
        if ($code -ne 0) {
            Write-Host "[FAIL] $Name branch succeeded, but tag push failed." -ForegroundColor Red
            return $false
        }
    }
    Write-Host "[OK] $Name push succeeded." -ForegroundColor Green
    return $true
}

switch ($Command) {
    'init' {
        if ([string]::IsNullOrWhiteSpace($GitHubUrl)) {
            throw 'Use -GitHubUrl with init, for example git@github.com:USER/KnotBridge.git'
        }
        Set-Remote 'github' $GitHubUrl
        Set-Remote 'tangled' $TangledUrl
        Write-Host ''
        Write-Host 'Configured remotes:'
        & git remote -v
    }
    'push' {
        $branchName = if ($Branch) { $Branch } else { Get-CurrentBranch }
        $null = Get-HeadSha
        $names = if ($Target) { @($Target) } else { @('github', 'tangled') }
        $results = @()
        foreach ($name in $names) {
            $results += Push-One $name $branchName $Tags.IsPresent
        }
        if ($results -contains $false) { exit 1 }
    }
    'retry' {
        if (-not $Target) { throw 'Use -Target github or -Target tangled with retry.' }
        $branchName = if ($Branch) { $Branch } else { Get-CurrentBranch }
        $null = Get-HeadSha
        if (-not (Push-One $Target $branchName $Tags.IsPresent)) { exit 1 }
    }
    'status' {
        $branchName = if ($Branch) { $Branch } else { Get-CurrentBranch }
        $sha = Get-HeadSha
        Write-Host "Local: $branchName ($($sha.Substring(0, 12)))"
        foreach ($name in @('github', 'tangled')) {
            if (-not (Test-Remote $name)) {
                Write-Host "[SKIP] $name remote is not configured."
                continue
            }
            $remoteSha = (& git ls-remote $name "refs/heads/$branchName").Split("`t")[0]
            if ($LASTEXITCODE -ne 0) { Write-Host "[OFF] $name could not be queried."; continue }
            if ([string]::IsNullOrWhiteSpace($remoteSha)) { Write-Host "[INFO] $name has no $branchName branch." }
            elseif ($remoteSha -eq $sha) { Write-Host "[OK] $name matches local HEAD." }
            else { Write-Host "[DIFF] $name is at $($remoteSha.Substring(0, 12))." }
        }
    }
    'doctor' {
        git --version
        Write-Host ''
        Write-Host 'Remotes:'
        & git remote -v
        Write-Host ''
        Write-Host 'SSH test for Tangled:'
        & ssh -T git@tangled.org
    }
}
