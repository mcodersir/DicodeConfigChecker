param(
  [string]$RepoName = "DicodeConfigChecker",
  [string]$Owner = "mcodersir",
  [string]$Tag = "v1.0.1",
  [string]$RemoteUrl = "",
  [string]$GitProxy = ""
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
  $pair = "x-access-token:$Token"
  $bytes = [Text.Encoding]::ASCII.GetBytes($pair)
  $encoded = [Convert]::ToBase64String($bytes)
  return "Authorization: Basic $encoded"
}

function Get-GitPrefix([string]$Token, [string]$ProxyUrl) {
  $authHeader = Convert-ToBasicAuthHeader $Token
  $prefix = @("-c", "credential.helper=", "-c", "http.extraHeader=$authHeader")
  if ($ProxyUrl -and $ProxyUrl.Trim().Length -gt 0) {
    $p = $ProxyUrl.Trim()
    # http.proxy is used by Git/libcurl for HTTPS remotes too. socks5h:// makes DNS resolve through the proxy.
    $prefix += @("-c", "http.proxy=$p", "-c", "https.proxy=$p")
    $env:HTTP_PROXY = $p
    $env:HTTPS_PROXY = $p
    $env:ALL_PROXY = $p
    $env:http_proxy = $p
    $env:https_proxy = $p
    $env:all_proxy = $p
  }
  return $prefix
}

function Run-GitAuth([string[]]$Arguments, [string]$Token, [string]$ProxyUrl) {
  $prefix = Get-GitPrefix $Token $ProxyUrl
  $oldErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & git @prefix @Arguments
    $code = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $oldErrorActionPreference
  }
  if ($code -ne 0) { throw "git command failed: git $($Arguments -join ' ')" }
}

function Test-GitHubNameResolution {
  $oldErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    Resolve-DnsName github.com -ErrorAction Stop | Out-Null
    return $true
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $oldErrorActionPreference
  }
}

function Show-PushHelp([string]$RepoName, [string]$ProxyUrl) {
  Write-Host ""
  Write-Warn "Push failed. Read the exact error above."
  Write-Warn "If it says 'Could not resolve host: github.com', Git cannot resolve DNS on this PC."
  Write-Warn "Run this BAT again and enter a proxy for Git push. Common values:"
  Write-Host "  http://127.0.0.1:10809" -ForegroundColor Cyan
  Write-Host "  http://127.0.0.1:7890" -ForegroundColor Cyan
  Write-Host "  socks5h://127.0.0.1:10808" -ForegroundColor Cyan
  Write-Host "  socks5h://127.0.0.1:7891" -ForegroundColor Cyan
  Write-Warn "Use socks5h://, not socks5://, when you want DNS to resolve through the proxy."
  Write-Warn "Other common reasons: repository does not exist, token is wrong/expired, or token lacks repo + workflow scopes."
  Write-Warn "Create this public repo in browser if it does not exist:"
  Write-Host "https://github.com/new?name=$RepoName&visibility=public" -ForegroundColor Cyan
  if ($ProxyUrl) { Write-Warn "Proxy used for this attempt: $ProxyUrl" }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "Git was not found in PATH. Install Git for Windows first."
}

if (-not (Test-Path ".github\workflows\release-windows.yml")) {
  throw "GitHub Actions workflow is missing: .github\workflows\release-windows.yml"
}

$GitProxy = $GitProxy.Trim()
if ($GitProxy -and $GitProxy -notmatch '^(http|https|socks5|socks5h)://') {
  Write-Warn "Proxy value has no scheme. Assuming http://"
  $GitProxy = "http://$GitProxy"
}
if ($GitProxy) { Write-Ok "Git push proxy enabled: $GitProxy" }
else {
  if (-not (Test-GitHubNameResolution)) {
    Write-Warn "Windows cannot resolve github.com directly right now."
    Write-Warn "This push will probably fail unless Git has a working global proxy."
    Write-Warn "Rerun and enter a proxy like socks5h://127.0.0.1:10808 or http://127.0.0.1:10809."
  }
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

Write-Step "Testing GitHub remote with Git"
try {
  Run-GitAuth @("ls-remote", "--heads", "origin") $token $GitProxy
} catch {
  Show-PushHelp $RepoName $GitProxy
  throw
}

Write-Step "Pushing source to GitHub"
try {
  Run-GitAuth @("push", "-u", "origin", "main", "--force") $token $GitProxy
} catch {
  Show-PushHelp $RepoName $GitProxy
  throw
}

Write-Step "Pushing release tag $Tag"
Run-Git @("tag", "-f", "-a", $Tag, "-m", "Dicode Config Checker $Tag")
try {
  Run-GitAuth @("push", "origin", "refs/tags/$Tag", "--force") $token $GitProxy
} catch {
  Show-PushHelp $RepoName $GitProxy
  throw
}

Write-Step "Done"
Write-Ok "GitHub Actions will now build the Windows EXE and create the release on GitHub."
Write-Host "Repository: https://github.com/$Owner/$RepoName" -ForegroundColor Green
Write-Host "Actions:    https://github.com/$Owner/$RepoName/actions" -ForegroundColor Green
Write-Host "Release:    https://github.com/$Owner/$RepoName/releases/tag/$Tag" -ForegroundColor Green
