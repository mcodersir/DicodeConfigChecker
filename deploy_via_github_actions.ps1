param(
  [string]$RepoName = "DicodeConfigChecker",
  [string]$Owner = "mcodersir",
  [string]$Tag = "v1.0.1",
  [string]$RemoteUrl = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Write-Step($Text) { Write-Host "`n==> $Text" -ForegroundColor Cyan }
function Write-Warn($Text) { Write-Host $Text -ForegroundColor Yellow }
function Write-Ok($Text) { Write-Host $Text -ForegroundColor Green }

function Get-Token {
  if ($env:GITHUB_TOKEN -and $env:GITHUB_TOKEN.Trim().Length -gt 0) { return $env:GITHUB_TOKEN.Trim() }
  if ($env:GH_TOKEN -and $env:GH_TOKEN.Trim().Length -gt 0) { return $env:GH_TOKEN.Trim() }
  $secure = Read-Host "Paste GitHub token with repo + workflow scope (input is hidden)" -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Run-Git([string[]]$Arguments) {
  # Native tools like git can write harmless messages to stderr.
  # Do not let PowerShell stop on stderr; fail only on the process exit code.
  $oldErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & git @Arguments
    $code = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $oldErrorActionPreference
  }
  if ($code -ne 0) { throw "git command failed: git $($Arguments -join ' ')" }
}

function Try-Git([string[]]$Arguments) {
  $oldErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & git @Arguments
    return $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $oldErrorActionPreference
  }
}

function Convert-ToBasicAuthHeader([string]$Token) {
  # GitHub HTTPS git pushes expect the PAT as the password in Basic auth.
  # We send it as an in-memory extraHeader, so it is not written to .git/config.
  $pair = "x-access-token:$Token"
  $bytes = [Text.Encoding]::ASCII.GetBytes($pair)
  $encoded = [Convert]::ToBase64String($bytes)
  return "Authorization: Basic $encoded"
}

function Run-GitAuth([string[]]$Arguments, [string]$Token) {
  $authHeader = Convert-ToBasicAuthHeader $Token
  # Disable cached credential helpers for this command so old/wrong Windows credentials cannot override the token.
  $oldErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & git -c credential.helper= -c "http.extraHeader=$authHeader" @Arguments
    $code = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $oldErrorActionPreference
  }
  if ($code -ne 0) { throw "git command failed: git $($Arguments -join ' ')" }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "Git was not found in PATH. Install Git for Windows first."
}

if (-not (Test-Path ".github\workflows\release-windows.yml")) {
  throw "GitHub Actions workflow is missing: .github\workflows\release-windows.yml"
}

$token = Get-Token
if (-not $token) { throw "GitHub token is empty." }

if (-not $RemoteUrl -or $RemoteUrl.Trim().Length -eq 0) {
  $RemoteUrl = "https://github.com/$Owner/$RepoName.git"
}
$RemoteUrl = $RemoteUrl.Trim()

Write-Step "Preparing local repository"
if (-not (Test-Path ".git")) { Run-Git @("init") }
Run-Git @("config", "user.name", "Dicode Release")
Run-Git @("config", "user.email", "release@dicode.local")
Run-Git @("config", "core.autocrlf", "false")
Run-Git @("config", "core.safecrlf", "false")
# Never commit local secrets. The package may contain .env for local testing; keep it out of git.
Try-Git @("rm", "--cached", "--ignore-unmatch", ".env", ".env.local") | Out-Null
Run-Git @("add", ".")
$hasChanges = git status --porcelain
if ($hasChanges) {
  Run-Git @("commit", "-m", "Release $Tag with GitHub Actions builder")
} else {
  Write-Warn "No source changes to commit."
}
Run-Git @("branch", "-M", "main")

$remotes = git remote
if ($remotes -contains "origin") { Run-Git @("remote", "set-url", "origin", $RemoteUrl) }
else { Run-Git @("remote", "add", "origin", $RemoteUrl) }

Write-Step "Pushing source to GitHub"
try {
  Run-GitAuth @("push", "-u", "origin", "main", "--force") $token
} catch {
  Write-Host ""
  Write-Warn "Push failed. Most common reasons:"
  Write-Warn "1) The repository does not exist yet."
  Write-Warn "2) The token is wrong/expired, or it was generated for another account."
  Write-Warn "3) The token lacks repo + workflow scopes. Workflow scope is required because this package pushes .github/workflows/release-windows.yml."
  Write-Warn "Create this public repo in browser, then run this script again:"
  Write-Host "https://github.com/new?name=$RepoName&visibility=public" -ForegroundColor Cyan
  throw
}

Write-Step "Pushing release tag $Tag"
# Create or replace the local tag. Do not delete first; deleting a missing tag exits non-zero and can stop PowerShell.
Run-Git @("tag", "-f", "-a", $Tag, "-m", "Dicode Config Checker $Tag")
# Push the exact tag ref with --force so rerunning the deploy is safe.
Run-GitAuth @("push", "origin", "refs/tags/$Tag", "--force") $token

Write-Step "Done"
Write-Ok "GitHub Actions will now build the Windows EXE and create the release on GitHub."
Write-Host "Repository: https://github.com/$Owner/$RepoName" -ForegroundColor Green
Write-Host "Actions:    https://github.com/$Owner/$RepoName/actions" -ForegroundColor Green
Write-Host "Release:    https://github.com/$Owner/$RepoName/releases/tag/$Tag" -ForegroundColor Green
