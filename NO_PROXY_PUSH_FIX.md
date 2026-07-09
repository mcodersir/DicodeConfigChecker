# No-proxy Git deploy fix

This package removes automatic proxy retries from the GitHub Actions deploy flow.

## What changed

- `deploy_via_github_actions_v1_0_1.bat` now uses direct Git by default.
- Leaving the proxy prompt empty means: do not use proxy.
- The script no longer tries common proxy ports after a successful direct push.
- `main` and `refs/tags/v1.0.1` are pushed in one Git command.
- `push_release_tag_v1_0_1_only.bat` was changed to the same direct-by-default behavior.

## Run this

```bat
deploy_via_github_actions_v1_0_1.bat
```

When it asks for proxy, leave it empty:

```text
Git proxy for push [empty = no proxy]:
```

If Git says `Could not resolve host: github.com`, the script did not use proxy. Fix your VPN/TUN/DNS and run again, or explicitly enter a proxy only if you want one.

## If source is already pushed and only the tag/release is missing

```bat
push_release_tag_v1_0_1_only.bat
```

Again, leave proxy empty for direct-only.
