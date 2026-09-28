@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem KnotBridge generic safe sync workflow.
rem Usage:
rem   KnotBridge-sync.bat "C:\path\to\repo" "github-url" "tangled-url" "commit message"
rem Example:
rem   KnotBridge-sync.bat "." "git@github.com:USER/REPO.git" "git@tangled.org:did:plc:REPO_DID" "sync repository"

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage
if "%~3"=="" goto :usage

set "REPO=%~1"
set "GITHUB_URL=%~2"
set "TANGLED_URL=%~3"
set "COMMIT_MESSAGE=%~4"
if "%COMMIT_MESSAGE%"=="" set "COMMIT_MESSAGE=sync repository"

if not exist "%REPO%\.git" (
  echo Initializing Git repository in %REPO%...
  git -C "%REPO%" init
  if errorlevel 1 goto :fail
)

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher 'py' was not found. Install Python 3.10+ or use forge_sync.py manually.
  goto :fail
)

set "SCRIPT_DIR=%~dp0"
set "SCANNER=%SCRIPT_DIR%secret_scan.py"
set "FORGE_SYNC=%SCRIPT_DIR%forge_sync.py"

if not exist "%SCANNER%" (
  echo Missing secret scanner: %SCANNER%
  goto :fail
)
if not exist "%FORGE_SYNC%" (
  echo Missing sync engine: %FORGE_SYNC%
  goto :fail
)

echo.
echo [1/6] Scanning repository for private keys and credentials...
py "%SCANNER%" "%REPO%"
if errorlevel 1 (
  echo Secret scan failed. Nothing will be staged or pushed.
  goto :fail
)

echo.
echo [2/6] Configuring GitHub and Tangled remotes...
py "%FORGE_SYNC%" --json init --github "%GITHUB_URL%" --tangled "%TANGLED_URL%"
if errorlevel 1 goto :fail

echo.
echo [3/6] Checking current repository state...
git -C "%REPO%" status --short
if errorlevel 1 goto :fail

for /f "delims=" %%B in ('git -C "%REPO%" branch --show-current') do set "BRANCH=%%B"
if "%BRANCH%"=="" (
  git -C "%REPO%" switch -c main 2>nul
  if errorlevel 1 git -C "%REPO%" checkout -b main
  set "BRANCH=main"
)

for /f "delims=" %%H in ('git -C "%REPO%" rev-parse --verify HEAD 2^>nul') do set "HEAD=%%H"
if "%HEAD%"=="" (
  echo.
  echo [4/6] Creating the first commit from all repository files...
  git -C "%REPO%" add -A
  if errorlevel 1 goto :fail
  git -C "%REPO%" diff --cached --quiet
  if errorlevel 1 (
    git -C "%REPO%" commit -m "%COMMIT_MESSAGE%"
    if errorlevel 1 goto :fail
  ) else (
    echo No files are available for the first commit.
    goto :fail
  )
) else (
  echo.
  echo [4/6] Staging repository changes after the clean secret scan...
  git -C "%REPO%" add -A
  if errorlevel 1 goto :fail
  git -C "%REPO%" diff --cached --quiet
  if errorlevel 1 (
    git -C "%REPO%" commit -m "%COMMIT_MESSAGE%"
    if errorlevel 1 goto :fail
  ) else (
    echo No new file changes to commit; existing HEAD will be synchronized.
  )
)

echo.
echo [5/6] Previewing GitHub and Tangled push...
py "%FORGE_SYNC%" --json push --branch "%BRANCH%" --dry-run
if errorlevel 1 goto :fail

echo.
echo [6/6] Pushing the same commit to both remotes...
py "%FORGE_SYNC%" --json push --branch "%BRANCH%"
if errorlevel 1 (
  echo One or more destinations failed. Use the targeted retry command from the README.
  goto :fail
)

echo.
echo SUCCESS: %REPO% synchronized to GitHub and Tangled.
py "%FORGE_SYNC%" status --branch "%BRANCH%"
exit /b 0

:usage
echo Usage:
echo   KnotBridge-sync.bat "REPO_PATH" "GITHUB_URL" "TANGLED_URL" "COMMIT_MESSAGE"
echo.
echo Example:
echo   KnotBridge-sync.bat "." "git@github.com:USER/REPO.git" "git@tangled.org:did:plc:REPO_DID" "sync repository"
exit /b 2

:fail
echo.
echo FAILED: no push was performed after the failing step, or a destination reported failure.
exit /b 1
