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
