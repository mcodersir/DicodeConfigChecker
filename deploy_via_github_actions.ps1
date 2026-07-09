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

function Normalize-ProxyUrl([string]$ProxyUrl) {
  if (-not $ProxyUrl) { return "" }
  $p = $ProxyUrl.Trim()
  if (-not $p) { return "" }
  if ($p -notmatch '^(http|https|socks5|socks5h)://') { $p = "http://$p" }
  return $p
}

function Get-GitPrefix([string]$Token, [string]$ProxyUrl) {
  $authHeader = Convert-ToBasicAuthHeader $Token
  $prefix = @("-c", "credential.helper=", "-c", "http.extraHeader=$authHeader")
  $p = Normalize-ProxyUrl $ProxyUrl
  if ($p) {
    # http.proxy is used by Git/libcurl for HTTPS remotes too. socks5h:// makes DNS resolve through the proxy.
    $prefix += @("-c", "http.proxy=$p", "-c", "https.proxy=$p")
  }
  return $prefix
}

function Invoke-GitAuthRaw([string[]]$Arguments, [string]$Token, [string]$ProxyUrl) {
  $proxy = Normalize-ProxyUrl $ProxyUrl
  $envNames = @('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy','GIT_TERMINAL_PROMPT')
  $oldEnv = @{}
  foreach ($name in $envNames) {
    $oldEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
  }
  try {
    $env:GIT_TERMINAL_PROMPT = "0"
    if ($proxy) {
      $env:HTTP_PROXY = $proxy
      $env:HTTPS_PROXY = $proxy
      $env:ALL_PROXY = $proxy
      $env:http_proxy = $proxy
      $env:https_proxy = $proxy
      $env:all_proxy = $proxy
    }
    $prefix = Get-GitPrefix $Token $proxy
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
      & git @prefix @Arguments
      $code = $LASTEXITCODE
    } finally {
      $ErrorActionPreference = $oldErrorActionPreference
    }
    return $code
  } finally {
    foreach ($name in $envNames) {
      [Environment]::SetEnvironmentVariable($name, $oldEnv[$name], 'Process')
    }
  }
}

function Get-ProxyCandidates([string]$PreferredProxy) {
  # Direct-only by default. No automatic proxy retries.
  # If the user explicitly enters a proxy, only that proxy is used.
  $p = Normalize-ProxyUrl $PreferredProxy
  if ($p) { return @($p) }
  return @("")
}

function Run-GitAuthWithFallback([string[]]$Arguments, [string]$Token, [string]$PreferredProxy, [string]$Label) {
  $candidates = Get-ProxyCandidates $PreferredProxy
  foreach ($candidate in $candidates) {
    if ($candidate) { Write-Host "Running $Label via explicit proxy: $candidate" -ForegroundColor DarkCyan }
    else { Write-Host "Running $Label direct, without proxy" -ForegroundColor DarkCyan }

    $code = Invoke-GitAuthRaw $Arguments $Token $candidate
    if ($code -eq 0) {
      if ($candidate) { Write-Ok "Git push succeeded via explicit proxy: $candidate" }
      else { Write-Ok "Git push succeeded direct. No proxy was used." }
      return "ok"
    }
  }
  if ($PreferredProxy) { throw "git command failed with explicit proxy: git $($Arguments -join ' ')" }
  throw "git command failed without proxy: git $($Arguments -join ' ')"
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
  Write-Warn "This script did not auto-use proxy. If direct DNS fails, either fix VPN/TUN/DNS or rerun and explicitly enter a proxy:"
  Write-Host "  http://127.0.0.1:10809" -ForegroundColor Cyan
  Write-Host "  http://127.0.0.1:7890" -ForegroundColor Cyan
  Write-Host "  socks5h://127.0.0.1:10808" -ForegroundColor Cyan
  Write-Host "  socks5h://127.0.0.1:7891" -ForegroundColor Cyan
  Write-Warn "Use socks5h://, not socks5://, only if you explicitly decide to use a SOCKS proxy."
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

$GitProxy = Normalize-ProxyUrl $GitProxy
if ($GitProxy) {
  Write-Ok "Explicit Git push proxy: $GitProxy"
} else {
  if (-not (Test-GitHubNameResolution)) {
    Write-Warn "Windows cannot resolve github.com directly right now."
    Write-Warn "You chose no proxy, so this script will still try direct Git only."
    Write-Warn "If direct push fails, fix DNS/VPN/TUN mode and run it again."
  } else {
    Write-Ok "No proxy entered. Git push will run direct only."
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

Write-Step "Creating local release tag $Tag"
Run-Git @("tag", "-f", "-a", $Tag, "-m", "Dicode Config Checker $Tag")

Write-Step "Pushing source and release tag to GitHub in one Git connection"
try {
  $usedProxy = Run-GitAuthWithFallback -Arguments @("push", "-u", "origin", "main", "refs/tags/$Tag", "--force") -Token $token -PreferredProxy $GitProxy -Label "combined branch+tag push"
} catch {
  Show-PushHelp $RepoName $GitProxy
  throw
}

Write-Step "Done"
Write-Ok "GitHub Actions will now build the Windows EXE and create the release on GitHub."
Write-Host "Repository: https://github.com/$Owner/$RepoName" -ForegroundColor Green
Write-Host "Actions:    https://github.com/$Owner/$RepoName/actions" -ForegroundColor Green
Write-Host "Release:    https://github.com/$Owner/$RepoName/releases/tag/$Tag" -ForegroundColor Green
