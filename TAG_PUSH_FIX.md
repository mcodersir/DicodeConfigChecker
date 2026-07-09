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
