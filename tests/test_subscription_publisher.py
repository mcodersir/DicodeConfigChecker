from unittest.mock import patch
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


def test_upsert_file_skips_identical_remote_content() -> None:
    repo = subscription_publisher.SubscriptionRepository("owner", "repo")
    remote = {"sha": "abc", "content": "c2FtZSB0ZXh0"}

    with patch.object(subscription_publisher, "_request", return_value=remote) as request:
        changed = subscription_publisher._upsert_file("token", repo, "sub.txt", "same text")

    assert changed is False
    request.assert_called_once_with("token", "GET", "/repos/owner/repo/contents/sub.txt")


def test_publish_returns_per_file_change_status() -> None:
    repo = subscription_publisher.SubscriptionRepository("owner", "repo")
    with patch.object(subscription_publisher, "ensure_repository", return_value=(repo, False)), patch.object(
        subscription_publisher, "_upsert_file", side_effect=[True, False]
    ):
        result = subscription_publisher.publish("token", "owner/repo", "sub", "proxy")

    assert result.repository == repo
    assert result.repository_created is False
    assert result.sub_changed is True
    assert result.proxy_changed is False
