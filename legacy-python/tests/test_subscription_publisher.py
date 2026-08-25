from unittest.mock import call, patch
import urllib.error

import subscription_publisher


def test_request_retries_temporary_dns_failure() -> None:
    attempts = 0

    def flaky(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise urllib.error.URLError("temporary name resolution failure")
        return {"login": "dicode"}

    with patch.object(subscription_publisher, "_request_once", flaky), patch.object(subscription_publisher.time, "sleep"):
        result = subscription_publisher._request("token", "GET", "/user")

    assert result == {"login": "dicode"}
    assert attempts == 3


def test_publish_skips_when_both_files_are_identical() -> None:
    repo = subscription_publisher.SubscriptionRepository("owner", "repo")
    with patch.object(subscription_publisher, "ensure_repository", return_value=(repo, False)), patch.object(
        subscription_publisher, "_read_remote_text", side_effect=[("sub", "a"), ("proxy", "b")]
    ), patch.object(subscription_publisher, "_atomic_publish") as atomic:
        result = subscription_publisher.publish("token", "owner/repo", "sub", "proxy")

    assert result.sub_changed is False
    assert result.proxy_changed is False
    atomic.assert_not_called()


def test_publish_updates_both_files_in_one_atomic_operation() -> None:
    repo = subscription_publisher.SubscriptionRepository("owner", "repo", "stable")
    with patch.object(subscription_publisher, "ensure_repository", return_value=(repo, False)), patch.object(
        subscription_publisher, "_read_remote_text", side_effect=[("old", "a"), ("proxy", "b")]
    ), patch.object(subscription_publisher, "_atomic_publish") as atomic:
        result = subscription_publisher.publish("token", "owner/repo", "sub", "proxy")

    assert result.repository == repo
    assert result.sub_changed is True
    assert result.proxy_changed is False
    atomic.assert_called_once_with("token", repo, {"sub.txt": "sub", "proxy.txt": "proxy"})


def test_atomic_publish_verifies_both_files() -> None:
    repo = subscription_publisher.SubscriptionRepository("owner", "repo")
    responses = {
        "/repos/owner/repo/git/commits/parent": {"tree": {"sha": "base-tree"}},
        "/repos/owner/repo/git/trees": {"sha": "new-tree"},
        "/repos/owner/repo/git/commits": {"sha": "new-commit"},
        "/repos/owner/repo/git/refs/heads/main": {},
    }

    def request(_token, method, path, body=None):
        if path.endswith("/git/blobs"):
            return {"sha": "blob-sub" if body["content"].startswith("c3Vi") else "blob-proxy"}
        return responses[path]

    with patch.object(subscription_publisher, "_wait_for_branch", return_value="parent"), patch.object(
        subscription_publisher, "_request", side_effect=request
    ), patch.object(subscription_publisher, "_read_remote_text", side_effect=[("sub", "x"), ("proxy", "y")]):
        subscription_publisher._atomic_publish("token", repo, {"sub.txt": "sub", "proxy.txt": "proxy"})
