"""Publish verified Dicode outputs into a user's own public GitHub repository."""
from __future__ import annotations

import base64
import json
import random
import string
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

API = "https://api.github.com"


@dataclass(frozen=True)
class SubscriptionRepository:
    owner: str
    name: str
    branch: str = "main"

    @property
    def ref(self) -> str:
        return f"{self.owner}/{self.name}"

    def raw_url(self, filename: str) -> str:
        branch = urllib.parse.quote(self.branch, safe="")
        return f"https://raw.githubusercontent.com/{self.owner}/{self.name}/refs/heads/{branch}/{filename}"


@dataclass(frozen=True)
class PublishResult:
    repository: SubscriptionRepository
    repository_created: bool
    sub_changed: bool
    proxy_changed: bool


def _request_once(token: str, method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={
            "Authorization": f"Bearer {token.strip()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DicodeConfigChecker/1.5.1",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            payload = response.read()
            return json.loads(payload.decode("utf-8")) if payload else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API {error.code}: {detail[:500]}") from error


def _request(token: str, method: str, path: str, body: dict | None = None) -> dict:
    delays = (0.8, 1.6, 3.2, 6.4)
    last_error: Exception | None = None
    for index, delay in enumerate(delays):
        try:
            return _request_once(token, method, path, body)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
        except RuntimeError as error:
            message = str(error)
            if not any(f"GitHub API {code}" in message for code in (409, 422, 429, 500, 502, 503, 504)):
                raise
            last_error = error
        if index < len(delays) - 1:
            time.sleep(delay)
    raise RuntimeError(
        "اتصال به GitHub موقتاً در دسترس نیست؛ انتشار بدون حذف خروجی محلی متوقف شد. "
        f"({last_error})"
    ) from last_error


def _random_name() -> str:
    suffix = "".join(random.choice(string.digits) for _ in range(7))
    return f"dicode-{suffix}-DIC"


def _repo_path(repo: SubscriptionRepository, suffix: str) -> str:
    owner = urllib.parse.quote(repo.owner, safe="")
    name = urllib.parse.quote(repo.name, safe="")
    return f"/repos/{owner}/{name}{suffix}"


def _read_remote_text(token: str, repo: SubscriptionRepository, filename: str) -> tuple[str | None, str | None]:
    encoded_name = urllib.parse.quote(filename, safe="/")
    branch = urllib.parse.quote(repo.branch, safe="")
    try:
        current = _request(token, "GET", _repo_path(repo, f"/contents/{encoded_name}?ref={branch}"))
    except RuntimeError as error:
        if "GitHub API 404" in str(error):
            return None, None
        raise
    encoded = str(current.get("content") or "").replace("\n", "")
    text = base64.b64decode(encoded).decode("utf-8", errors="replace") if encoded else ""
    return text, str(current.get("sha") or "")


def _wait_for_branch(token: str, repo: SubscriptionRepository) -> str:
    branch = urllib.parse.quote(repo.branch, safe="")
    last_error: Exception | None = None
    for delay in (0.0, 0.5, 1.0, 2.0, 4.0):
        if delay:
            time.sleep(delay)
        try:
            ref = _request(token, "GET", _repo_path(repo, f"/git/ref/heads/{branch}"))
            sha = str((ref.get("object") or {}).get("sha") or "")
            if sha:
                return sha
        except RuntimeError as error:
            last_error = error
            if "GitHub API 404" not in str(error) and "GitHub API 409" not in str(error):
                raise
    raise RuntimeError(f"شاخهٔ GitHub پس از ساخت ریپازیتوری آماده نشد: {last_error}")


def _create_blob(token: str, repo: SubscriptionRepository, text: str) -> str:
    result = _request(token, "POST", _repo_path(repo, "/git/blobs"), {
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "encoding": "base64",
    })
    sha = str(result.get("sha") or "")
    if not sha:
        raise RuntimeError("GitHub blob ساخته نشد.")
    return sha


def _atomic_publish(token: str, repo: SubscriptionRepository, files: dict[str, str]) -> None:
    parent_sha = _wait_for_branch(token, repo)
    parent = _request(token, "GET", _repo_path(repo, f"/git/commits/{parent_sha}"))
    base_tree = str((parent.get("tree") or {}).get("sha") or "")
    if not base_tree:
        raise RuntimeError("درخت پایهٔ ریپازیتوری GitHub خوانده نشد.")

    entries = []
    for filename, text in files.items():
        entries.append({
            "path": filename,
            "mode": "100644",
            "type": "blob",
            "sha": _create_blob(token, repo, text),
        })
    tree = _request(token, "POST", _repo_path(repo, "/git/trees"), {
        "base_tree": base_tree,
        "tree": entries,
    })
    tree_sha = str(tree.get("sha") or "")
    commit = _request(token, "POST", _repo_path(repo, "/git/commits"), {
        "message": "Update Dicode subscription outputs",
        "tree": tree_sha,
        "parents": [parent_sha],
    })
    commit_sha = str(commit.get("sha") or "")
    if not commit_sha:
        raise RuntimeError("GitHub commit ساخته نشد.")
    branch = urllib.parse.quote(repo.branch, safe="")
    _request(token, "PATCH", _repo_path(repo, f"/git/refs/heads/{branch}"), {
        "sha": commit_sha,
        "force": False,
    })

    # Do not report success until both files are visible with exactly the requested content.
    for filename, expected in files.items():
        actual, _ = _read_remote_text(token, repo, filename)
        if actual != expected:
            raise RuntimeError(f"راستی‌آزمایی انتشار GitHub برای {filename} ناموفق بود.")


def ensure_repository(token: str, existing_ref: str) -> tuple[SubscriptionRepository, bool]:
    if not token or not token.strip():
        raise ValueError("توکن GitHub وارد نشده است.")
    profile = _request(token, "GET", "/user")
    owner = str(profile.get("login") or "")
    if not owner:
        raise RuntimeError("هویت GitHub از روی توکن خوانده نشد.")

    if existing_ref and "/" in existing_ref:
        existing_owner, name = existing_ref.strip().split("/", 1)
        metadata = _request(token, "GET", f"/repos/{urllib.parse.quote(existing_owner, safe='')}/{urllib.parse.quote(name, safe='')}")
        branch = str(metadata.get("default_branch") or "main")
        return SubscriptionRepository(existing_owner, name, branch), False

    requested = _random_name()
    created = _request(token, "POST", "/user/repos", {
        "name": requested,
        "description": "Personal Dicode Config Checker subscription output",
        "private": False,
        "auto_init": True,
        "has_issues": False,
        "has_projects": False,
        "has_wiki": False,
    })
    repo = SubscriptionRepository(
        str((created.get("owner") or {}).get("login") or owner),
        str(created.get("name") or requested),
        str(created.get("default_branch") or "main"),
    )
    _wait_for_branch(token, repo)
    return repo, True


def publish(token: str, existing_ref: str, sub_text: str, proxy_text: str) -> PublishResult:
    repo, repository_created = ensure_repository(token, existing_ref)
    current_sub, _ = _read_remote_text(token, repo, "sub.txt")
    current_proxy, _ = _read_remote_text(token, repo, "proxy.txt")
    sub_changed = current_sub != sub_text
    proxy_changed = current_proxy != proxy_text
    if sub_changed or proxy_changed:
        _atomic_publish(token, repo, {"sub.txt": sub_text, "proxy.txt": proxy_text})
    return PublishResult(repo, repository_created, sub_changed, proxy_changed)
