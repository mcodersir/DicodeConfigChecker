from __future__ import annotations

import base64
import json
from unittest.mock import patch

import engine


def test_extract_configs_deduplicates_and_decodes_html() -> None:
    page = """
    <div>vless://id@example.com:443?security=tls&amp;type=ws#one</div>
    <div>vless://id@example.com:443?security=tls&amp;type=ws#two</div>
    <div>https://t.me/proxy?server=1.2.3.4&amp;port=443&amp;secret=abc</div>
    """
    values = engine.extract_configs(page)
    assert len(values) == 2
    assert any(value.startswith("vless://") for value in values)
    assert any("t.me/proxy" in value for value in values)


def test_parse_vmess_endpoint() -> None:
    payload = {
        "v": "2",
        "ps": "test",
        "add": "example.com",
        "port": "443",
        "id": "00000000-0000-0000-0000-000000000000",
        "aid": "0",
        "net": "ws",
        "tls": "tls",
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    endpoint = engine.parse_endpoint("vmess://" + encoded, "unit")
    assert endpoint is not None
    assert endpoint.host == "example.com"
    assert endpoint.port == 443
    assert endpoint.protocol == "vmess"


def test_parse_telegram_proxy() -> None:
    endpoint = engine.parse_endpoint(
        "tg://proxy?server=149.154.167.50&port=443&secret=abcdef",
        "unit",
    )
    assert endpoint is not None
    assert endpoint.kind == "mtproto"
    assert endpoint.port == 443


def test_config_name_rewrite() -> None:
    raw = "vless://id@example.com:443?security=tls#old"
    renamed = engine.set_config_display_name(raw, "t.me/dicodeir-1")
    assert renamed.endswith("#t.me/dicodeir-1")


def test_telegram_me_channel_is_accepted() -> None:
    assert engine.normalize_channel("https://telegram.me/example_channel") == "example_channel"
    assert engine.normalize_channel("telegram.me/s/example_channel") == "example_channel"


def test_preview_uses_telegram_me_only_after_t_me_fails() -> None:
    calls: list[str] = []

    def fake_fetch(url: str) -> str:
        calls.append(url)
        if "t.me/" in url and "telegram.me" not in url:
            raise OSError("DNS lookup failed")
        return "<div>vless://id@example.com:443?security=tls</div>"

    with patch.object(engine, "fetch_url", fake_fetch):
        result = engine.fetch_channel("example_channel")

    assert result["ok"] is True
    assert result["preview_host"] == "telegram.me"
    assert calls == ["https://t.me/s/example_channel", "https://telegram.me/s/example_channel"]
