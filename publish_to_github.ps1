param(
  [string]$RepoName = "DicodeConfigChecker",
  [string]$Owner = "mcodersir",
  [string]$Tag = "v1.0.0",
  [string]$Description = "Dicode Config Checker - Telegram config checker with Xray based quality testing",
  [string]$Proxy = "",
  [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$script:ActiveProxy = $null

function Write-Step($Text) { Write-Host "`n==> $Text" -ForegroundColor Cyan }
function Write-Ok($Text) { Write-Host $Text -ForegroundColor Green }
function Write-Warn($Text) { Write-Host $Text -ForegroundColor Yellow }
function Fail($Text) { throw "`n$Text`n" }

function Normalize-Proxy($Value) {
  if (-not $Value) { return $null }
  $v = $Value.Trim()
  if ($v.Length -eq 0) { return $null }
  if ($v -notmatch "^https?://") { $v = "http://$v" }
  return $v
}

function Get-Token {
  if ($env:GITHUB_TOKEN -and $env:GITHUB_TOKEN.Trim().Length -gt 0) { return $env:GITHUB_TOKEN.Trim() }
  Write-Host "GitHub token is required." -ForegroundColor Yellow
  Write-Host "Use a new token with repo/public_repo permission. Do not put tokens inside source files." -ForegroundColor Yellow
  $secure = Read-Host "Paste GitHub token (hidden)" -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function New-GitBasicHeader($Token) {
  $pair = "x-access-token:$Token"
  $bytes = [Text.Encoding]::ASCII.GetBytes($pair)
  return [Convert]::ToBase64String($bytes)
}

function Invoke-GitHubJson($Method, $Uri, $Token, $Body = $null) {
  $headers = @{
    "Authorization" = "Bearer $Token"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "DicodeConfigCheckerReleaseScript"
  }

  $args = @{
    Method = $Method
    Uri = $Uri
    Headers = $headers
    TimeoutSec = 30
  }
  if ($script:ActiveProxy) { $args.Proxy = $script:ActiveProxy }
  if ($Body -ne $null) {
    $args.Body = ($Body | ConvertTo-Json -Depth 30)
    $args.ContentType = "application/json; charset=utf-8"
  }

  try { return Invoke-RestMethod @args }
  catch {
    $status = $null
    if ($_.Exception.Response) { try { $status = [int]$_.Exception.Response.StatusCode } catch {} }
    $msg = $_.Exception.Message
    if ($status) { $msg = "HTTP $status - $msg" }
    throw $msg
  }
}

function Invoke-GitHubRaw($Method, $Uri, $Token, $ContentType, $InFile) {
  $headers = @{
    "Authorization" = "Bearer $Token"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "DicodeConfigCheckerReleaseScript"
  }
  $args = @{
    Method = $Method
    Uri = $Uri
    Headers = $headers
    ContentType = $ContentType
    InFile = $InFile
    TimeoutSec = 120
  }
  if ($script:ActiveProxy) { $args.Proxy = $script:ActiveProxy }
  return Invoke-RestMethod @args
}

function Test-Command($Name) { return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Test-Url($Url, $ProxyValue = $null) {
  try {
    $args = @{
      Uri = $Url
      Method = "GET"
      TimeoutSec = 12
      UseBasicParsing = $true
      Headers = @{ "User-Agent" = "DicodeConfigCheckerReleaseScript" }
    }
    if ($ProxyValue) { $args.Proxy = $ProxyValue }
    Invoke-WebRequest @args | Out-Null
    return $true
  }
  catch { return $false }
}

function Resolve-GithubProxy {
  $manualProxy = Normalize-Proxy $Proxy
  if (-not $manualProxy) { $manualProxy = Normalize-Proxy $env:GITHUB_PROXY }
  if (-not $manualProxy) { $manualProxy = Normalize-Proxy $env:HTTPS_PROXY }
  if (-not $manualProxy) { $manualProxy = Normalize-Proxy $env:HTTP_PROXY }

  if (Test-Url "https://api.github.com") {
    $script:ActiveProxy = $null
    Write-Ok "GitHub is reachable directly."
    return
  }

  $candidates = New-Object System.Collections.Generic.List[string]
  if ($manualProxy) { $candidates.Add($manualProxy) }
  @(
    "http://127.0.0.1:10809",
    "http://127.0.0.1:7890",
    "http://127.0.0.1:2080",
    "http://127.0.0.1:2081",
    "http://127.0.0.1:8080",
    "http://localhost:10809",
    "http://localhost:7890"
  ) | ForEach-Object { if (-not $candidates.Contains($_)) { $candidates.Add($_) } }

  foreach ($p in $candidates) {
    Write-Warn "Testing proxy: $p"
    if ((Test-Url "https://api.github.com" $p) -and (Test-Url "https://github.com" $p)) {
      $script:ActiveProxy = $p
      $env:HTTP_PROXY = $p
      $env:HTTPS_PROXY = $p
      Write-Ok "Using proxy for this run: $p"
      return
    }
  }

  Write-Warn "GitHub is not reachable directly and no common local HTTP proxy worked."
  Write-Warn "If you use v2rayN, turn on System Proxy or enter its HTTP proxy, usually http://127.0.0.1:10809"
  Write-Warn "If you use Clash, it is often http://127.0.0.1:7890"
  $typed = Read-Host "Proxy URL or host:port, or press Enter to stop"
  $typed = Normalize-Proxy $typed
  if (-not $typed) { Fail "GitHub is not reachable. Turn on a working proxy/VPN for PowerShell/Git and run again." }
  if (-not ((Test-Url "https://api.github.com" $typed) -and (Test-Url "https://github.com" $typed))) {
    Fail "Proxy did not reach GitHub: $typed"
  }
  $script:ActiveProxy = $typed
  $env:HTTP_PROXY = $typed
  $env:HTTPS_PROXY = $typed
  Write-Ok "Using proxy for this run: $typed"
}

function Run-GitAuth($Token, [string[]]$GitArgs) {
  $basic = New-GitBasicHeader $Token
  $prefix = @("-c", "credential.helper=", "-c", "http.https://github.com/.extraheader=AUTHORIZATION: basic $basic")
  if ($script:ActiveProxy) {
    $prefix += @("-c", "http.proxy=$script:ActiveProxy", "-c", "https.proxy=$script:ActiveProxy")
  }
  & git @prefix @GitArgs
  if ($LASTEXITCODE -ne 0) { Fail "Git command failed: git $($GitArgs -join ' ')" }
}

function Run-Git([string[]]$GitArgs) {
  $prefix = @()
  if ($script:ActiveProxy) {
    $prefix += @("-c", "http.proxy=$script:ActiveProxy", "-c", "https.proxy=$script:ActiveProxy")
  }
  & git @prefix @GitArgs
  if ($LASTEXITCODE -ne 0) { Fail "Git command failed: git $($GitArgs -join ' ')" }
}

$token = Get-Token
if (-not $token) { Fail "GitHub token is empty." }

Write-Step "Preflight checks"
if (-not (Test-Command git)) { Fail "Git was not found in PATH. Install Git for Windows and run this script again." }
Resolve-GithubProxy

try {
  $user = Invoke-GitHubJson "GET" "https://api.github.com/user" $token
  Write-Ok "Authenticated as: $($user.login)"
}
catch {
  Fail "GitHub authentication failed. Create a new token with repo/public_repo permission and set it with: `$env:GITHUB_TOKEN='TOKEN'`nDetails: $($_.Exception.Message)"
}

if (-not $NoBuild) {
  Write-Step "Building Windows executable"
  & .\build_exe.bat
  if ($LASTEXITCODE -ne 0) { Fail "build_exe.bat failed." }
} else {
  Write-Warn "Skipping build because -NoBuild was used."
}

if (-not (Test-Path "dist\DicodeConfigChecker.exe")) { Fail "dist\DicodeConfigChecker.exe was not found." }

Write-Step "Creating repository if needed"
$repo = $null
try {
  $repo = Invoke-GitHubJson "POST" "https://api.github.com/user/repos" $token @{
    name = $RepoName
    description = $Description
    private = $false
    has_issues = $true
    has_projects = $false
    has_wiki = $false
    auto_init = $false
  }
  $Owner = $repo.owner.login
  Write-Ok "Created repository: $($repo.html_url)"
}
catch {
  Write-Warn "Repository may already exist. Trying $Owner/$RepoName ..."
  try {
    $repo = Invoke-GitHubJson "GET" "https://api.github.com/repos/$Owner/$RepoName" $token
    Write-Ok "Using repository: $($repo.html_url)"
  }
  catch { Fail "Could not create or load repository $Owner/$RepoName. Details: $($_.Exception.Message)" }
}

Write-Step "Preparing local git repository"
if (-not (Test-Path ".git")) { Run-Git @("init") }
Run-Git @("config", "user.name", "Dicode Release")
Run-Git @("config", "user.email", "release@dicode.local")

if (Test-Path ".gitignore") {
  $gitignore = Get-Content ".gitignore" -Raw
  foreach ($item in @(".env", "core/xray.exe", "dist/", "build/", "release/")) {
    $escaped = [regex]::Escape($item)
    if ($gitignore -notmatch "(?m)^$escaped$") { Add-Content ".gitignore" $item }
  }
}

Run-Git @("add", ".")
$hasChanges = (& git status --porcelain)
if ($hasChanges) { Run-Git @("commit", "-m", "Release 1.0.0") }
else { Write-Warn "No source changes to commit." }

Run-Git @("branch", "-M", "main")
$remoteUrl = "https://github.com/$Owner/$RepoName.git"
$remoteList = (& git remote)
if ($remoteList -contains "origin") { Run-Git @("remote", "set-url", "origin", $remoteUrl) }
else { Run-Git @("remote", "add", "origin", $remoteUrl) }

Write-Step "Pushing source code"
Run-GitAuth $token @("push", "-u", "origin", "main")

Write-Step "Creating and pushing tag"
Run-Git @("tag", "-f", "-a", $Tag, "-m", "Dicode Config Checker 1.0.0")
Run-GitAuth $token @("push", "origin", $Tag, "--force")

Write-Step "Creating source archive"
New-Item -ItemType Directory -Force -Path release | Out-Null
$sourceZip = "release\DicodeConfigChecker-source-v1.0.0.zip"
if (Test-Path $sourceZip) { Remove-Item $sourceZip -Force }
$exclude = @(".git", "build", "dist", "release", "__pycache__", ".env")
$files = Get-ChildItem -Force | Where-Object { $exclude -notcontains $_.Name }
Compress-Archive -Path $files.FullName -DestinationPath $sourceZip -Force

$releaseBody = @"
# Dicode Config Checker v1.0.0

## فارسی
یک ابزار دسکتاپ ویندوزی برای جمع‌آوری کانفیگ از کانال‌های عمومی تلگرام، تست واقعی‌تر با Xray-core و ساخت خروجی‌های sub.txt و proxy.txt.

## English
A Windows desktop tool for collecting public Telegram config candidates, checking them with Xray-core based quality testing, and generating sub.txt / proxy.txt outputs.

### Included
- DicodeConfigChecker.exe
- Source code archive
"@

Write-Step "Creating or updating GitHub release"
$release = $null
try {
  $release = Invoke-GitHubJson "GET" "https://api.github.com/repos/$Owner/$RepoName/releases/tags/$Tag" $token
  Write-Warn "Release already exists. It will be updated."
  $release = Invoke-GitHubJson "PATCH" "https://api.github.com/repos/$Owner/$RepoName/releases/$($release.id)" $token @{
    name = "Dicode Config Checker v1.0.0"
    body = $releaseBody
    draft = $false
    prerelease = $false
  }
}
catch {
  $release = Invoke-GitHubJson "POST" "https://api.github.com/repos/$Owner/$RepoName/releases" $token @{
    tag_name = $Tag
    target_commitish = "main"
    name = "Dicode Config Checker v1.0.0"
    body = $releaseBody
    draft = $false
    prerelease = $false
  }
}

function Remove-ExistingAsset($AssetName) {
  $assets = Invoke-GitHubJson "GET" "https://api.github.com/repos/$Owner/$RepoName/releases/$($release.id)/assets" $token
  foreach ($asset in $assets) {
    if ($asset.name -eq $AssetName) {
      Invoke-GitHubJson "DELETE" "https://api.github.com/repos/$Owner/$RepoName/releases/assets/$($asset.id)" $token | Out-Null
      Write-Warn "Removed old asset: $AssetName"
    }
  }
}

function Upload-Asset($Path, $Name, $ContentType) {
  if (-not (Test-Path $Path)) { Fail "Asset not found: $Path" }
  Remove-ExistingAsset $Name
  $uploadBase = $release.upload_url -replace "\{\?name,label\}", ""
  $uri = "$uploadBase?name=$([uri]::EscapeDataString($Name))"
  Invoke-GitHubRaw "POST" $uri $token $ContentType $Path | Out-Null
  Write-Ok "Uploaded: $Name"
}

Write-Step "Uploading release assets"
Upload-Asset "dist\DicodeConfigChecker.exe" "DicodeConfigChecker-v1.0.0-windows.exe" "application/octet-stream"
Upload-Asset $sourceZip "DicodeConfigChecker-source-v1.0.0.zip" "application/zip"

Write-Step "Done"
Write-Ok "Repository: https://github.com/$Owner/$RepoName"
Write-Ok "Release:    https://github.com/$Owner/$RepoName/releases/tag/$Tag"
