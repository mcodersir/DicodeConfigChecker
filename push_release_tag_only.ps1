param(
  [string]$RepoName = "DicodeConfigChecker",
  [string]$Owner = "mcodersir",
  [string]$Tag = "v1.0.1",
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
function Convert-ToBasicAuthHeader([string]$Token) {
  $pair = "x-access-token:$Token"
  $bytes = [Text.Encoding]::ASCII.GetBytes($pair)
  return "Authorization: Basic $([Convert]::ToBase64String($bytes))"
}
function Normalize-ProxyUrl([string]$ProxyUrl) {
  if (-not $ProxyUrl) { return "" }
  $p = $ProxyUrl.Trim(); if (-not $p) { return "" }
  if ($p -notmatch '^(http|https|socks5|socks5h)://') { $p = "http://$p" }
  return $p
}
function Invoke-GitAuthRaw([string[]]$Arguments, [string]$Token, [string]$ProxyUrl) {
  $proxy = Normalize-ProxyUrl $ProxyUrl
  $prefix = @("-c", "credential.helper=", "-c", "http.extraHeader=$(Convert-ToBasicAuthHeader $Token)")
  if ($proxy) { $prefix += @("-c", "http.proxy=$proxy", "-c", "https.proxy=$proxy") }
  $envNames = @('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy','GIT_TERMINAL_PROMPT')
  $old = @{}
  foreach ($name in $envNames) {
    $old[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
  }
  try {
    $env:GIT_TERMINAL_PROMPT="0"
    if ($proxy) { $env:HTTP_PROXY=$proxy; $env:HTTPS_PROXY=$proxy; $env:ALL_PROXY=$proxy; $env:http_proxy=$proxy; $env:https_proxy=$proxy; $env:all_proxy=$proxy }
    $oldEap=$ErrorActionPreference; $ErrorActionPreference="Continue"
    try { & git @prefix @Arguments; $code=$LASTEXITCODE } finally { $ErrorActionPreference=$oldEap }
    return $code
  } finally {
    foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $old[$name], 'Process') }
  }
}
function Candidates([string]$Preferred) {
  $items = @()
  $p=Normalize-ProxyUrl $Preferred; if ($p) { $items += $p }
  $items += ""
  $items += @('socks5h://127.0.0.1:10808','http://127.0.0.1:10809','http://127.0.0.1:7890','socks5h://127.0.0.1:7891','socks5h://127.0.0.1:1080','http://127.0.0.1:8080')
  $seen=@{}; $out=@()
  foreach($i in $items){ $key=if($i){$i.ToLowerInvariant()}else{'<direct>'}; if(-not $seen[$key]){$seen[$key]=$true; $out+=$i} }
  return $out
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git was not found in PATH." }
$token = Get-Token
if (-not (Test-Path ".git")) { throw "No .git folder found. Run deploy_via_github_actions_v1_0_1.bat first." }
& git remote set-url origin "https://github.com/$Owner/$RepoName.git"
& git tag -f -a $Tag -m "Dicode Config Checker $Tag"
Write-Step "Pushing only release tag $Tag"
foreach($proxy in (Candidates $GitProxy)) {
  if($proxy){ Write-Host "Trying tag push via $proxy" -ForegroundColor DarkCyan } else { Write-Host "Trying tag push direct" -ForegroundColor DarkCyan }
  $code = Invoke-GitAuthRaw @("push", "origin", "refs/tags/$Tag", "--force") $token $proxy
  if($code -eq 0){ Write-Ok "Tag pushed. Release workflow should start."; Write-Host "https://github.com/$Owner/$RepoName/actions" -ForegroundColor Green; exit 0 }
}
throw "Tag push failed after direct/proxy retries."
