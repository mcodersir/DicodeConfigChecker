# Fix for `remote: invalid credentials`

The previous deploy script used a Bearer header for `git push`. GitHub HTTPS git authentication expects a personal access token to be used as the password. This package now sends an in-memory Basic auth header:

`x-access-token:<YOUR_TOKEN>`

It also disables cached Git Credential Manager credentials for the push command, so old or wrong Windows credentials cannot override the token.

## Required token permissions

For a classic GitHub token, enable:

- `repo`
- `workflow`

`workflow` is required because the deploy pushes `.github/workflows/release-windows.yml`.

For a fine-grained token, select the target repository and allow:

- Contents: Read and write
- Workflows: Read and write

## Correct command

Run:

```bat
deploy_via_github_actions_v1_0_1.bat
```

Do not run the old proxy deploy unless you specifically want local REST release creation.

## v1.0.1 tag fix

If the source push succeeds but the deploy stops at:

```text
error: tag 'v1.0.1' not found.
```

use this fixed package. The deploy script no longer deletes the local tag first. It creates or replaces it with:

```text
git tag -f -a v1.0.1 -m "Dicode Config Checker v1.0.1"
git push origin refs/tags/v1.0.1 --force
```

This makes rerunning the release safe even when the local tag does not exist yet.
