from __future__ import annotations

import base64
import json

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
