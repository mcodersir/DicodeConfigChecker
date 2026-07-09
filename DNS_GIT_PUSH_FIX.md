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


## Branch + tag push fix
The deploy script now creates the local tag before pushing and sends `main` plus `refs/tags/v1.0.1` in one `git push` command. This avoids the old case where the source push succeeded but the second tag push failed because Windows DNS broke between two separate Git connections. It also auto-retries direct mode and common local proxies.

If `main` is already pushed and only the tag failed, run:

```bat
push_release_tag_v1_0_1_only.bat
```


## No-proxy push fix

The deploy scripts are now direct-by-default. Leaving the proxy prompt empty means no proxy is used, and the script no longer auto-tries common proxy ports after a direct push. `main` and `refs/tags/v1.0.1` are pushed in one Git command.
