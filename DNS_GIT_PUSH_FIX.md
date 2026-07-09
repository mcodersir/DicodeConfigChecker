# DNS / Git push fix

This package fixes this deploy error:

```text
fatal: unable to access 'https://github.com/...': Could not resolve host: github.com
```

The release workflow still avoids calling `api.github.com` from your PC, but the source and tag must be pushed to GitHub. That requires Git to reach `github.com`.

## Use the fixed deploy file

Run:

```bat
deploy_via_github_actions_v1_0_1.bat
```

When it asks for Git proxy, use one of these values depending on your VPN/proxy app:

```text
http://127.0.0.1:10809
http://127.0.0.1:7890
socks5h://127.0.0.1:10808
socks5h://127.0.0.1:7891
```

If your proxy app shows a different local port, use that port.

## Diagnose first

Run:

```bat
diagnose_git_github_dns_proxy.bat
```

It checks DNS and common local proxy ports.

## Clear wrong Git proxy

If Git was previously configured with a wrong proxy, run:

```bat
clear_bad_git_proxy.bat
```

Then deploy again.
