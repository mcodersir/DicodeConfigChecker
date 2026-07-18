"""Publish verified Dicode outputs into a user's own public GitHub repository."""
from __future__ import annotations

import base64
import json
import random
import string
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


API = "https://api.github.com"


@dataclass(frozen=True)
class SubscriptionRepository:
    owner: str
    name: str

    @property
    def ref(self) -> str:
        return f"{self.owner}/{self.name}"

    def raw_url(self, filename: str) -> str:
        return f"https://raw.githubusercontent.com/{self.owner}/{self.name}/refs/heads/main/{filename}"


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
            "User-Agent": "DicodeConfigChecker",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8")) if response.length != 0 else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API {error.code}: {detail[:220]}") from error


def _request(token: str, method: str, path: str, body: dict | None = None) -> dict:
    """Use bounded retries for DNS, transient TLS, and short GitHub outages."""
    delays = (1.0, 2.0, 4.0, 8.0)
    last_error: Exception | None = None
    for index, delay in enumerate(delays):
        try:
            return _request_once(token, method, path, body)
        except urllib.error.URLError as error:
            last_error = error
        except OSError as error:
            last_error = error
        except RuntimeError as error:
            # Authentication and validation errors are actionable and must not
            # be retried; 5xx / rate-limit responses can be transient.
            message = str(error)
            if not any(f"GitHub API {code}" in message for code in (429, 500, 502, 503, 504)):
                raise
            last_error = error
        if index < len(delays) - 1:
            time.sleep(delay)
    raise RuntimeError(
        "اتصال به GitHub موقتاً در دسترس نیست؛ برنامه انتشار را خودکار دوباره تلاش می‌کند. "
        f"({last_error})"
    ) from last_error


def _random_name() -> str:
    suffix = "".join(random.choice(string.digits) for _ in range(7))
    return f"dicode-{suffix}-DIC"


def _upsert_file(token: str, repo: SubscriptionRepository, filename: str, text: str) -> bool:
    path = f"/repos/{repo.ref}/contents/{filename}"
    sha = None
    try:
        current = _request(token, "GET", path)
        sha = current.get("sha")
        encoded = str(current.get("content") or "").replace("\n", "")
        if encoded and base64.b64decode(encoded).decode("utf-8", errors="replace") == text:
            return False
    except RuntimeError as error:
        if "GitHub API 404" not in str(error):
            raise
    payload = {
        "message": f"Update {filename} from Dicode Config Checker",
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    _request(token, "PUT", path, payload)
    return True


def ensure_repository(token: str, existing_ref: str) -> tuple[SubscriptionRepository, bool]:
    if not token or not token.strip():
        raise ValueError("توکن GitHub وارد نشده است.")
    profile = _request(token, "GET", "/user")
    owner = str(profile.get("login") or "")
    if not owner:
        raise RuntimeError("هویت GitHub از روی توکن خوانده نشد.")
    if existing_ref and "/" in existing_ref:
        return SubscriptionRepository(*existing_ref.split("/", 1)), False
    else:
        repo = SubscriptionRepository(owner, _random_name())
        created = _request(token, "POST", "/user/repos", {
            "name": repo.name,
            "description": "Personal Dicode Config Checker subscription output",
            "private": False,
            "auto_init": True,
            "has_issues": False,
            "has_projects": False,
            "has_wiki": False,
        })
        return SubscriptionRepository(str(created["owner"]["login"]), str(created["name"])), True


def publish(token: str, existing_ref: str, sub_text: str, proxy_text: str) -> PublishResult:
    repo, repository_created = ensure_repository(token, existing_ref)
    sub_changed = _upsert_file(token, repo, "sub.txt", sub_text)
    proxy_changed = _upsert_file(token, repo, "proxy.txt", proxy_text)
    return PublishResult(repo, repository_created, sub_changed, proxy_changed)
