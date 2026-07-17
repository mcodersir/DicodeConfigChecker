"""Publish verified Dicode outputs into a user's own public GitHub repository."""
from __future__ import annotations

import base64
import json
import random
import string
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


def _request(token: str, method: str, path: str, body: dict | None = None) -> dict:
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


def _random_name() -> str:
    suffix = "".join(random.choice(string.digits) for _ in range(7))
    return f"dicode-{suffix}-DIC"


def _upsert_file(token: str, repo: SubscriptionRepository, filename: str, text: str) -> None:
    path = f"/repos/{repo.ref}/contents/{filename}"
    sha = None
    try:
        sha = _request(token, "GET", path).get("sha")
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


def publish(token: str, existing_ref: str, sub_text: str, proxy_text: str) -> SubscriptionRepository:
    if not token or not token.strip():
        raise ValueError("توکن GitHub وارد نشده است.")
    profile = _request(token, "GET", "/user")
    owner = str(profile.get("login") or "")
    if not owner:
        raise RuntimeError("هویت GitHub از روی توکن خوانده نشد.")
    if existing_ref and "/" in existing_ref:
        repo = SubscriptionRepository(*existing_ref.split("/", 1))
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
        repo = SubscriptionRepository(str(created["owner"]["login"]), str(created["name"]))
    _upsert_file(token, repo, "sub.txt", sub_text)
    _upsert_file(token, repo, "proxy.txt", proxy_text)
    return repo
