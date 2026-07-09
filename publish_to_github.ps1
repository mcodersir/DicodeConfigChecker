param(
  [string]$RepoName = "DicodeConfigChecker",
  [string]$Owner = "mcodersir",
  [string]$Tag = "v1.0.1",
  [string]$PreviousTag = "v1.0.0",
  [string]$Description = "Dicode Config Checker - Telegram config checker with Xray based quality testing",
  [string]$Proxy = "",
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$script:RestProxy = $null
if ($Proxy -and $Proxy.Trim().Length -gt 0) {
  $Proxy = $Proxy.Trim()
  $env:HTTP_PROXY = $Proxy
  $env:HTTPS_PROXY = $Proxy
  $env:ALL_PROXY = $Proxy
  $env:NO_PROXY = "localhost,127.0.0.1"
  if ($Proxy -match '^https?://') {
    $script:RestProxy = $Proxy
  }
}

function Write-Step($Text) {
  Write-Host "`n==> $Text" -ForegroundColor Cyan
}

function Write-Info($Text) {
  Write-Host $Text -ForegroundColor DarkGray
}

function Get-Token {
  if ($env:GITHUB_TOKEN -and $env:GITHUB_TOKEN.Trim().Length -gt 0) {
    return $env:GITHUB_TOKEN.Trim()
  }
  if ($env:GH_TOKEN -and $env:GH_TOKEN.Trim().Length -gt 0) {
    return $env:GH_TOKEN.Trim()
  }
  $secure = Read-Host "Paste GitHub token with repo scope (input is hidden)" -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Invoke-GitHubJson($Method, $Uri, $Token, $Body = $null) {
  $headers = @{
    "Authorization" = "Bearer $Token"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "DicodeConfigCheckerReleaseScript"
  }

  $params = @{
    Method = $Method
    Uri = $Uri
    Headers = $headers
    ErrorAction = "Stop"
  }
  if ($Body -ne $null) {
    $params.Body = ($Body | ConvertTo-Json -Depth 20)
    $params.ContentType = "application/json; charset=utf-8"
  }
  if ($script:RestProxy) {
    $params.Proxy = $script:RestProxy
  }

  for ($attempt = 1; $attempt -le 3; $attempt++) {
    try {
      return Invoke-RestMethod @params
    } catch {
      $msg = $_.Exception.Message
      if ($attempt -ge 3) {
        if ($msg -like "*remote name could not be resolved*" -or $msg -like "*NameResolutionFailure*" -or $msg -like "*api.github.com*") {
          throw "Cannot reach api.github.com. This is a DNS/proxy/VPN problem, not a build problem. Run deploy_release_v1_0_1_with_proxy.bat and enter a local HTTP proxy like http://127.0.0.1:7890 or http://127.0.0.1:10809. Original error: $msg"
        }
        throw
      }
      Start-Sleep -Seconds (2 * $attempt)
    }
  }
}

function Test-Command($Name) {
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-GitCommand {
  param([string[]]$Arguments)
  $allArgs = @()
  if ($Proxy -and $Proxy.Trim().Length -gt 0) {
    $allArgs += @("-c", "http.proxy=$Proxy", "-c", "https.proxy=$Proxy")
  }
  $allArgs += $Arguments
  & git @allArgs
  if ($LASTEXITCODE -ne 0) {
    throw "git command failed."
  }
}

function Remove-ReleaseAndTag($Owner, $RepoName, $Tag, $Token) {
  Write-Step "Cleaning GitHub release/tag $Tag"
  try {
    $rel = Invoke-GitHubJson "GET" "https://api.github.com/repos/$Owner/$RepoName/releases/tags/$Tag" $Token
    Invoke-GitHubJson "DELETE" "https://api.github.com/repos/$Owner/$RepoName/releases/$($rel.id)" $Token | Out-Null
    Write-Host "Deleted release: $Tag" -ForegroundColor Yellow
  } catch {
    Write-Host "Release not found or already removed: $Tag" -ForegroundColor DarkGray
  }
  try {
    Invoke-GitHubJson "DELETE" "https://api.github.com/repos/$Owner/$RepoName/git/refs/tags/$Tag" $Token | Out-Null
    Write-Host "Deleted remote tag: $Tag" -ForegroundColor Yellow
  } catch {
    Write-Host "Remote tag not found or already removed: $Tag" -ForegroundColor DarkGray
  }
}

$Version = $Tag.TrimStart("v")
$token = Get-Token
if (-not $token) { throw "GitHub token is empty." }
$env:GITHUB_TOKEN = $token
$env:GH_TOKEN = $token

Write-Step "Testing GitHub API connection"
try {
  $me = Invoke-GitHubJson "GET" "https://api.github.com/user" $token
  Write-Host "GitHub auth OK: $($me.login)" -ForegroundColor Green
} catch {
  Write-Host "GitHub API connection failed." -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  Write-Host ""
  Write-Host "Fix: run deploy_release_v1_0_1_with_proxy.bat and enter your local proxy." -ForegroundColor Yellow
  Write-Host "Common ports: http://127.0.0.1:7890  or  http://127.0.0.1:10809" -ForegroundColor Yellow
  throw
}

if (-not $SkipBuild) {
  Write-Step "Building Windows executable"
  & .\build_exe.bat
  if ($LASTEXITCODE -ne 0) { throw "build_exe.bat failed." }
} else {
  Write-Step "Skipping build because -SkipBuild was passed"
}

$exeAsset = "release\DicodeConfigChecker-v$Version-windows.exe"
if (-not (Test-Path $exeAsset)) { throw "$exeAsset was not found. Run deploy_release_v1_0_1_with_proxy.bat once without -SkipBuild." }

if (-not (Test-Command git)) { throw "Git was not found in PATH." }

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
  Write-Host "Created repository: $($repo.html_url)" -ForegroundColor Green
} catch {
  Write-Host "Repository may already exist. Trying to use $Owner/$RepoName ..." -ForegroundColor Yellow
  $repo = Invoke-GitHubJson "GET" "https://api.github.com/repos/$Owner/$RepoName" $token
}

Remove-ReleaseAndTag $Owner $RepoName $PreviousTag $token
Remove-ReleaseAndTag $Owner $RepoName $Tag $token

Write-Step "Preparing local git repository"
if (-not (Test-Path ".git")) { git init | Out-Host }

git config user.name "Dicode Release"
git config user.email "release@dicode.local"
git add .
$hasChanges = git status --porcelain
if ($hasChanges) {
  git commit -m "Release $Version" | Out-Host
} else {
  Write-Host "No source changes to commit." -ForegroundColor Yellow
}

git branch -M main
$remoteUrl = "https://github.com/$Owner/$RepoName.git"
$remotes = git remote
if ($remotes -contains "origin") { git remote set-url origin $remoteUrl } else { git remote add origin $remoteUrl }

Write-Step "Pushing source code"
Invoke-GitCommand -Arguments @("-c", "http.extraHeader=Authorization: Bearer $token", "push", "-u", "origin", "main", "--force")

Write-Step "Creating local tag"
git tag -d $Tag 2>$null | Out-Null
git tag -a $Tag -m "Dicode Config Checker $Version"
Invoke-GitCommand -Arguments @("-c", "http.extraHeader=Authorization: Bearer $token", "push", "origin", $Tag, "--force")

Write-Step "Creating source archive"
New-Item -ItemType Directory -Force -Path release | Out-Null
$sourceZip = "release\DicodeConfigChecker-source-v$Version.zip"
if (Test-Path $sourceZip) { Remove-Item $sourceZip -Force }
$exclude = @(".git", "build", "dist", "release", "__pycache__", ".pytest_cache")
$files = Get-ChildItem -Force | Where-Object { $exclude -notcontains $_.Name }
Compress-Archive -Path $files.FullName -DestinationPath $sourceZip -Force

Write-Step "Creating GitHub release $Tag"
$body = @"
# Dicode Config Checker $Tag

## فارسی
- لیست کامل جدید کانال‌های رتبه دوم جایگزین شد.
- خروجی‌ها از تنظیمات جدا شدند: ساخت sub.txt برای کانفیگ‌ها و ساخت proxy.txt برای پروکسی‌ها مستقل است.
- حالت فقط پروکسی: گزینه «بررسی کانفیگ‌های V2Ray/Xray» را خاموش و «بررسی پروکسی‌های تلگرام» را روشن بگذار.
- نسخه قبلی v1.0.0 و تگ آن قبل از انتشار نسخه جدید حذف می‌شود.
- اسکریپت دیپلوی اکنون حالت پروکسی دارد تا خطای DNS/فیلترینگ api.github.com را رد کند.

## English
- Updated Rank 2 channel list.
- Added independent output toggles for V2Ray/Xray configs and Telegram proxies.
- Added proxy-only mode.
- Deletes old v1.0.0 release/tag before publishing v1.0.1.
- Deployment script now supports proxy mode for api.github.com connectivity problems.

### Assets
- DicodeConfigChecker-v$Version-windows.exe
- DicodeConfigChecker-source-v$Version.zip
"@

$release = Invoke-GitHubJson "POST" "https://api.github.com/repos/$Owner/$RepoName/releases" $token @{
  tag_name = $Tag
  target_commitish = "main"
  name = "Dicode Config Checker $Tag"
  body = $body
  draft = $false
  prerelease = $false
}

function Upload-Asset($Path, $Name, $ContentType) {
  $uploadBase = $release.upload_url -replace "\{\?name,label\}", ""
  $uri = "$uploadBase?name=$([uri]::EscapeDataString($Name))"
  $headers = @{
    "Authorization" = "Bearer $token"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "DicodeConfigCheckerReleaseScript"
  }
  $params = @{
    Method = "POST"
    Uri = $uri
    Headers = $headers
    ContentType = $ContentType
    InFile = $Path
    ErrorAction = "Stop"
  }
  if ($script:RestProxy) {
    $params.Proxy = $script:RestProxy
  }
  for ($attempt = 1; $attempt -le 3; $attempt++) {
    try {
      Invoke-RestMethod @params | Out-Null
      Write-Host "Uploaded: $Name" -ForegroundColor Green
      return
    } catch {
      if ($attempt -ge 3) { throw }
      Start-Sleep -Seconds (2 * $attempt)
    }
  }
}

Write-Step "Uploading release assets"
Upload-Asset $exeAsset "DicodeConfigChecker-v$Version-windows.exe" "application/octet-stream"
Upload-Asset $sourceZip "DicodeConfigChecker-source-v$Version.zip" "application/zip"

Write-Step "Done"
Write-Host "Repository: https://github.com/$Owner/$RepoName" -ForegroundColor Green
Write-Host "Release:    https://github.com/$Owner/$RepoName/releases/tag/$Tag" -ForegroundColor Green
