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
  $secure = Read-Host "Paste GitHub token with repo scope (input is hidden)" -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Run-Git([string[]]$Arguments) {
  & git @Arguments
  if ($LASTEXITCODE -ne 0) { throw "git command failed: git $($Arguments -join ' ')" }
}

function Run-GitAuth([string[]]$Arguments, [string]$Token) {
  & git -c http.extraHeader="Authorization: Bearer $Token" @Arguments
  if ($LASTEXITCODE -ne 0) { throw "git command failed: git $($Arguments -join ' ')" }
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
  Write-Warn "Push failed. Most common reason: the repository does not exist yet or token has no repo access."
  Write-Warn "Create this public repo in browser, then run this script again:"
  Write-Host "https://github.com/new?name=$RepoName&visibility=public" -ForegroundColor Cyan
  throw
}

Write-Step "Pushing release tag $Tag"
git tag -d $Tag 2>$null | Out-Null
Run-Git @("tag", "-a", $Tag, "-m", "Dicode Config Checker $Tag")
Run-GitAuth @("push", "origin", $Tag, "--force") $token

Write-Step "Done"
Write-Ok "GitHub Actions will now build the Windows EXE and create the release on GitHub."
Write-Host "Repository: https://github.com/$Owner/$RepoName" -ForegroundColor Green
Write-Host "Actions:    https://github.com/$Owner/$RepoName/actions" -ForegroundColor Green
Write-Host "Release:    https://github.com/$Owner/$RepoName/releases/tag/$Tag" -ForegroundColor Green
