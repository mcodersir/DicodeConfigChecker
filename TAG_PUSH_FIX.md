# Tag push fix

The previous deploy script stopped after a successful source push because it tried to delete a local tag that did not exist:

```text
git tag -d v1.0.1
error: tag 'v1.0.1' not found
```

This package fixes it.

## What changed

- The script now fails only when a native git command exits with a non-zero status, not just because git writes a harmless stderr message.
- The script no longer deletes the local tag before creating it.
- The script uses `git tag -f -a ...` to create or replace the tag safely.
- The script pushes the exact tag ref with `--force`:

```text
git push origin refs/tags/v1.0.1 --force
```

## What to run

Run:

```bat
deploy_via_github_actions_v1_0_1.bat
```

Your previous source push already succeeded, so rerunning is safe. It will push `main` again and then push the `v1.0.1` tag.


## Branch + tag push fix
The deploy script now creates the local tag before pushing and sends `main` plus `refs/tags/v1.0.1` in one `git push` command. This avoids the old case where the source push succeeded but the second tag push failed because Windows DNS broke between two separate Git connections. It also auto-retries direct mode and common local proxies.

If `main` is already pushed and only the tag failed, run:

```bat
push_release_tag_v1_0_1_only.bat
```
