# Publish Troubleshooting

## github.com is not reachable

This means PowerShell/Git cannot reach GitHub. Your browser may work because only the browser is using a proxy, but PowerShell and Git do not automatically use it.

### Quick fix for v2rayN

Turn on your proxy, then run:

```powershell
$env:GITHUB_PROXY="http://127.0.0.1:10809"
$env:HTTP_PROXY=$env:GITHUB_PROXY
$env:HTTPS_PROXY=$env:GITHUB_PROXY
.\publish_to_github.ps1
```

If your v2rayN HTTP port is different, replace `10809`.

### Quick fix for Clash

```powershell
$env:GITHUB_PROXY="http://127.0.0.1:7890"
$env:HTTP_PROXY=$env:GITHUB_PROXY
$env:HTTPS_PROXY=$env:GITHUB_PROXY
.\publish_to_github.ps1
```

### Test connection

```powershell
Invoke-WebRequest https://api.github.com -Proxy http://127.0.0.1:10809 -UseBasicParsing
```

### Token

Use a fresh GitHub token. If a token was pasted in a public place or chat, revoke it and create a new one.
