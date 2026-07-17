#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dicode Telegram Config Checker v1

Two-stage Telegram configuration collector and verifier.

Workflow:
1) Use your current connection method to reach Telegram previews.
2) Collect public channel candidates into all_configs_stage1.txt.
3) Disconnect the current connection method.
4) Verify candidates from the current network.

Verification:
- Preferred: start Xray-core for each supported config, expose a local SOCKS inbound,
  then request CHECK_URL through that tunnel and measure the real delay.
- Fallback: repeated TCP connect for Telegram proxies and unsupported configs.

Outputs:
- sub.txt                 Verified V2Ray/Xray configs; remarks can be preserved or renamed
- sub_base64.txt          Base64 subscription
- proxy.txt               Verified Telegram MTProto/SOCKS proxies
- all_configs_stage1.txt  Collected raw candidates before verification
- alive_report.txt        Readable V2Ray/Xray report
- proxy_report.txt        Readable Telegram proxy report
- report.json             Full machine-readable report
"""

from __future__ import annotations

import base64
import concurrent.futures
import html
import json
import os
import platform
import random
import re
import shutil
import socket
import ssl
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

APP_NAME = "Dicode Telegram Config Checker"
VERSION = "1.5.0"
IS_FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", ROOT)).resolve() if IS_FROZEN else ROOT
ENV_FILE = ROOT / ".env"
CHANNELS_FILE = ROOT / "channels.txt"
CORE_DIR = ROOT / "core"
XRAY_RELEASE_API = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"

STAGE1_FILE = ROOT / "all_configs_stage1.txt"
STAGE1_META_FILE = ROOT / "stage1_report.json"
SUB_FILE = ROOT / "sub.txt"
SUB_BASE64_FILE = ROOT / "sub_base64.txt"
PROXY_FILE = ROOT / "proxy.txt"
PROXY_BASE64_FILE = ROOT / "proxy_base64.txt"
ALIVE_REPORT_FILE = ROOT / "alive_report.txt"
PROXY_REPORT_FILE = ROOT / "proxy_report.txt"
REPORT_FILE = ROOT / "report.json"
LOG_FILE = ROOT / "run_log.txt"

DEFAULT_CHANNELS = """
t.me/Spotify_Porteghali
t.me/lightning6
t.me/shaxhabb
t.me/meliproxyy
t.me/ProxyMTProto
t.me/LonUp_M
t.me/sorenab2
t.me/ProxyDaemi
t.me/iMTProto
t.me/v2rayngvpn
t.me/ConfigX2ray
t.me/IraneAzad_Net
t.me/prrofile_purple
t.me/V2WRAY
t.me/TelMTProto
t.me/v2ryNG01
t.me/V2ray_official
t.me/TheAnilad
t.me/ProxyDotNet
t.me/NPROXY
t.me/mrsoulb
t.me/ConfigsHUB
t.me/orange_vpns
t.me/BugFreeNet
t.me/TeleProxyTele
t.me/iproxy_Meli
t.me/SimChin_ir
t.me/V2rayEnglish
t.me/v2nova8
t.me/NetAccount
t.me/qpshow
t.me/DarkHub_VPN
t.me/configmax
t.me/nufilter
t.me/V2RAY_SPATIAL
t.me/shankamil
t.me/PulseStore_ir
t.me/NETMelliAnti
t.me/Blue_star_Vip
t.me/Maznet
t.me/cpy_teeL
t.me/beshcan
t.me/Parsashonam
t.me/ProxySnipe
t.me/Merlin_ViP
t.me/ghalagyann
t.me/Free_Nettm
t.me/EzAccess1
t.me/ChinaPortGFW
t.me/filshekan_vip
t.me/ProxyPJ
t.me/AzadNet
t.me/ShabrangVPN
t.me/V2Ray_Tz
t.me/acccrd
t.me/DSR_TM
t.me/BestProxyTel1
t.me/configraygan
t.me/configshere
t.me/VpnQavi
t.me/v2ray_dalghak
t.me/v2rayng_fars
t.me/saka_net
t.me/config_npv
t.me/Outline_vpn
t.me/freakconfig
t.me/flyv2ray
t.me/PROXIS_FREE
t.me/chatnakonn
t.me/proxyxix
t.me/letsproxys
t.me/proxyy_1404
t.me/duckvp_n
t.me/proxy_kafee
t.me/WizProxy
t.me/ShadowProxy66
t.me/persianvpnhub
t.me/vasl_bashim
t.me/makvaslim
t.me/v2ray_free_conf
t.me/V2rayConfigList
t.me/vpnfail_v2ray
t.me/vlesskeys
t.me/oneclickvpnkeys
t.me/ConfingV2RaayNG
t.me/v2ray_fspeed
t.me/Daily_Configs
t.me/filembad
t.me/bored_vpn
t.me/Surfboardv2ray
t.me/outlineOpenKey
t.me/GH_v2rayng
t.me/mtproxy_lists
t.me/v2raysvmess
t.me/freewireguard
t.me/warpscanner
t.me/ConfigWireguard
t.me/v2nodes
t.me/GrizzlyVPN
t.me/mobilesignal
t.me/persianelon
t.me/Rayan_Config
t.me/v2ray_Extractor
t.me/vpnowl
t.me/kiava
t.me/azadi_az_inja_migzare
t.me/ELiV2RAY
t.me/PrivateVPNs
t.me/DirectVPN
t.me/Everyday_VPN
t.me/vpnstorefast
t.me/v2ray_configs_pool
t.me/V2Ray_Market11
t.me/v2Line
t.me/XV2ray
t.me/v2rayvpn_official
t.me/zedmodeonVPN
t.me/ArV2ray
t.me/redfree8
t.me/safeNet4All
t.me/freedom_guard_net
t.me/Begoo_VPN
t.me/FlexEtesal
t.me/capoit
t.me/foced
t.me/Proxi_ConFiGS
t.me/letsproxys1
t.me/blackRay
t.me/V2rayTun0
t.me/AzadInternet_TV
t.me/NetMeli9
t.me/i10VPN
t.me/Zed_NetMeli
t.me/Pruuxi
t.me/confignetmeliina
t.me/npvon
t.me/iicenet
t.me/PathToArrive
t.me/madzteam
t.me/YamYamProxy
t.me/Skyportall
t.me/eshgheabadii_facts
t.me/Masyakata
t.me/marambashi2
t.me/XIXVPN
t.me/xsfilternet
t.me/Vpn_Shield
t.me/payam_nsi
t.me/xixv2ray
t.me/confing_alski
t.me/SOSkeyNET
t.me/crayingroom
t.me/Fast1one
t.me/saministamm
t.me/netazadi
t.me/iranconnecting
t.me/proxymtprotoir
t.me/ParsiNetFree
t.me/SwagMeli
t.me/mitivpn
t.me/Npv_Tnnel
t.me/poroxybaz
t.me/v2rayNG_Matsuri
t.me/vmess_ir
t.me/An0nymousTeam
t.me/v2ray_cartel
t.me/proxy_Shadowsocks
t.me/V2rayng_Fast
t.me/V2RFA
t.me/Config_HATunnel
t.me/vpn_naji
t.me/V2ray_Alpha
t.me/confing_Costume
t.me/MARAMBASHI
t.me/VPNConnectd
t.me/iP_CF
t.me/DailyV2RY
t.me/ZibaNabz
t.me/vpn_ioss
t.me/ConfigV2rayNG
t.me/hi_proxi
t.me/Myporoxy
t.me/MTProxyStar
t.me/Gp_Config
t.me/abc_configs
t.me/ServerNett
t.me/v2rayvpnchannel
t.me/ProxyTyper
t.me/mtp4tg
t.me/openkeysfree
t.me/v2rayshare
t.me/cloudnet6000
t.me/shadowsockskeys
t.me/vless_vmess
t.me/armodchannel
t.me/keysOutline
t.me/warpplus
t.me/iSeqaro
t.me/v2rayNGconfig
t.me/IP_CF_Configs
t.me/V2rayNG3
t.me/VmessProtocol
""".strip()

CONFIG_REGEXES = [
    re.compile(r"\b(?:vmess|vless|trojan|ss|ssr|snell)://[^\s<>\"'`\\]+", re.I),
    re.compile(r"\b(?:hysteria2|hy2|tuic)://[^\s<>\"'`\\]+", re.I),
    re.compile(r"\b(?:tg://proxy\?[^\s<>\"'`\\]+|tg://socks\?[^\s<>\"'`\\]+)", re.I),
    re.compile(r"\b(?:https://t\.me/proxy\?[^\s<>\"'`\\]+|https://t\.me/socks\?[^\s<>\"'`\\]+)", re.I),
]


def load_env_file() -> dict[str, str]:
    env: dict[str, str] = {}
    if not ENV_FILE.exists():
        return env
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        env[key] = val
    return env

ENV = load_env_file()


def env_str(key: str, default: str) -> str:
    return os.environ.get(key, ENV.get(key, default)).strip()


def env_int(key: str, default: int) -> int:
    try:
        return int(env_str(key, str(default)))
    except Exception:
        return default


def env_float(key: str, default: float) -> float:
    try:
        return float(env_str(key, str(default)))
    except Exception:
        return default


def env_bool(key: str, default: bool) -> bool:
    raw = env_str(key, "1" if default else "0").lower()
    return raw not in {"0", "false", "no", "off", "disable", "disabled"}


PER_CHANNEL_LIMIT = env_int("PER_CHANNEL_LIMIT", 20)
MAIN_CHANNEL_LIMIT = env_int("MAIN_CHANNEL_LIMIT", 30)
MAIN_CHANNELS_RAW = env_str("MAIN_CHANNELS", env_str("MAIN_CHANNEL", "persianvpnhub"))
MAIN_CHANNEL = MAIN_CHANNELS_RAW.split(",")[0].strip() or "persianvpnhub"
MAIN_CHANNELS = {x.strip().replace("t.me/", "").replace("https://", "").replace("http://", "").split("/")[-1].lower() for x in re.split(r"[,\s]+", MAIN_CHANNELS_RAW) if x.strip()}
FETCH_WORKERS = env_int("FETCH_WORKERS", 8)
FETCH_TIMEOUT = env_float("FETCH_TIMEOUT", 15.0)

TEST_MODE = env_str("TEST_MODE", "auto").lower()  # auto | xray | tcp
XRAY_PATH = env_str("XRAY_PATH", "core/xray.exe" if platform.system().lower().startswith("win") else "core/xray")
XRAY_STARTUP_WAIT = env_float("XRAY_STARTUP_WAIT", 1.2)
XRAY_PROCESS_TIMEOUT = env_float("XRAY_PROCESS_TIMEOUT", 18.0)
CHECK_URL = env_str("CHECK_URL", "http://www.gstatic.com/generate_204")

PING_WORKERS = env_int("PING_WORKERS", 8)
TCP_FALLBACK_WORKERS = env_int("TCP_FALLBACK_WORKERS", 32)
SOCKET_TIMEOUT = env_float("SOCKET_TIMEOUT", 8.0)
TCP_TIMEOUT = env_float("TCP_TIMEOUT", 4.0)
PING_ATTEMPTS = env_int("PING_ATTEMPTS", 4)
MIN_SUCCESS = env_int("MIN_SUCCESS", 3)
ATTEMPT_GAP_SECONDS = env_float("ATTEMPT_GAP_SECONDS", 0.25)
SUB_TAG_PREFIX = env_str("SUB_TAG_PREFIX", "t.me/dicodeir")
RENAME_CONFIG_NAMES = env_bool("RENAME_CONFIG_NAMES", True)
CHECK_V2RAY_CONFIGS = env_bool("CHECK_V2RAY_CONFIGS", True)
AUTO_DOWNLOAD_XRAY = env_str("AUTO_DOWNLOAD_XRAY", "1").lower() not in {"0", "false", "no", "off"}
XRAY_DOWNLOAD_TIMEOUT = env_float("XRAY_DOWNLOAD_TIMEOUT", 60.0)
DOWNLOAD_PROXY = env_str("DOWNLOAD_PROXY", env_str("GITHUB_PROXY", ""))

CHECK_TELEGRAM_PROXIES = env_bool("CHECK_TELEGRAM_PROXIES", True)
WRITE_DEAD_TO_REPORT = env_str("WRITE_DEAD_TO_REPORT", "1") not in {"0", "false", "False", "no"}


@dataclass
class Endpoint:
    raw: str
    source: str
    kind: str
    protocol: str
    host: str
    port: int


@dataclass
class TestResult:
    raw: str
    source: str
    kind: str
    protocol: str
    host: str
    port: int
    ok: bool
    ping_ms: Optional[int]
    min_ms: Optional[int]
    avg_ms: Optional[int]
    attempts: int
    success_count: int
    samples_ms: list[int]
    tester: str
    error: str = ""


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


COLOR = supports_color()


def c(text: str, color: str) -> str:
    return f"{color}{text}{Colors.RESET}" if COLOR else text


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(line: str) -> None:
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")


def clear_old_outputs() -> None:
    for p in [STAGE1_FILE, STAGE1_META_FILE, SUB_FILE, SUB_BASE64_FILE, PROXY_FILE, PROXY_BASE64_FILE, ALIVE_REPORT_FILE, PROXY_REPORT_FILE, REPORT_FILE, LOG_FILE]:
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass


def banner() -> None:
    print()
    print(c("=" * 78, Colors.CYAN))
    print(c(f"  {APP_NAME} v{VERSION}", Colors.BOLD + Colors.CYAN if COLOR else ""))
    print(c("=" * 78, Colors.CYAN))
    print("  Stage 1: connect your own VPN/proxy, then collect Telegram public previews")
    print("  Stage 2: disconnect your own VPN/proxy, then verify through Xray-core when available")
    print(c("=" * 78, Colors.CYAN))
    print()


def ensure_files() -> None:
    if not CHANNELS_FILE.exists():
        bundled_channels = BUNDLE_DIR / "channels.txt"
        seed = bundled_channels.read_text(encoding="utf-8", errors="ignore") if bundled_channels.exists() else DEFAULT_CHANNELS + "\n"
        CHANNELS_FILE.write_text(seed, encoding="utf-8")
    if not ENV_FILE.exists():
        ENV_FILE.write_text(default_env_text(), encoding="utf-8")


def default_env_text() -> str:
    return """# Dicode Telegram Config Checker v1.0.1
# GitHub-friendly settings. Change values here without editing the code.

# Collection limits
PER_CHANNEL_LIMIT=20
MAIN_CHANNEL_LIMIT=30
MAIN_CHANNELS=
FETCH_WORKERS=8
FETCH_TIMEOUT=15

# Testing mode: auto | xray | tcp
# auto = use Xray core if available, otherwise fallback to repeated TCP connect.
# xray = only accept real Xray-core HTTP-through-config test for V2Ray/Xray configs.
# tcp  = repeated TCP connect only.
TEST_MODE=auto

# Xray-core. If AUTO_DOWNLOAD_XRAY=1 and XRAY_PATH is missing, the latest release is downloaded automatically.
AUTO_DOWNLOAD_XRAY=1
XRAY_PATH=core/xray.exe
XRAY_DOWNLOAD_TIMEOUT=60
XRAY_STARTUP_WAIT=1.2
XRAY_PROCESS_TIMEOUT=18

# HTTP URL used through the tested proxy. Keep http:// for fastest no-TLS check.
CHECK_URL=http://www.gstatic.com/generate_204

# Quality settings. Time is less important; higher attempts = stricter results.
PING_ATTEMPTS=4
MIN_SUCCESS=3
PING_WORKERS=8
TCP_FALLBACK_WORKERS=32
SOCKET_TIMEOUT=8
TCP_TIMEOUT=4
ATTEMPT_GAP_SECONDS=0.25

# Output naming
# RENAME_CONFIG_NAMES=1 rewrites remarks as SUB_TAG_PREFIX-N. Set it to 0 to keep original remarks.
RENAME_CONFIG_NAMES=1
SUB_TAG_PREFIX=t.me/dicodeir
CHECK_V2RAY_CONFIGS=1
CHECK_TELEGRAM_PROXIES=1
WRITE_DEAD_TO_REPORT=1
"""


def normalize_channel(value: str) -> Optional[str]:
    s = value.strip()
    if not s or s.startswith("#"):
        return None
    if re.search(r"(?:t|telegram)\.me/\+", s, re.IGNORECASE):
        return None
    m = re.search(r"(?:t|telegram)\.me/(?:s/)?([a-zA-Z0-9_]+)", s, re.IGNORECASE)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_]+", s):
        return s
    return None


def read_channels() -> list[str]:
    ensure_files()
    raw = CHANNELS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: list[str] = []
    seen: set[str] = set()
    skipped_private = 0
    for line in raw:
        if re.search(r"(?:t|telegram)\.me/\+", line, re.IGNORECASE):
            skipped_private += 1
            continue
        ch = normalize_channel(line)
        if not ch:
            continue
        key = ch.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(ch)
    if skipped_private:
        print(c(f"  Private invite links skipped: {skipped_private}", Colors.YELLOW))
    return out


def fetch_url(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DicodeTelegramConfigChecker/1.0",
            "Accept": "text/html,application/xhtml+xml,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.8,fa;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
        data = r.read()
        enc = r.headers.get_content_charset() or "utf-8"
        return data.decode(enc, errors="ignore")


def fetch_channel(channel: str) -> dict[str, Any]:
    limit = MAIN_CHANNEL_LIMIT if channel.lower() in MAIN_CHANNELS else PER_CHANNEL_LIMIT
    started = time.time()
    try:
        # t.me remains the normal path. The alternative host is used only when
        # the primary preview request genuinely fails on the user's network.
        preview_host = "t.me"
        try:
            page = fetch_url(f"https://t.me/s/{channel}")
        except Exception as primary_error:
            preview_host = "telegram.me"
            try:
                page = fetch_url(f"https://telegram.me/s/{channel}")
            except Exception as fallback_error:
                raise RuntimeError(
                    f"t.me unavailable ({primary_error}); telegram.me also failed ({fallback_error})"
                ) from fallback_error
        configs = extract_configs(page)
        picked = configs[:limit]
        return {
            "channel": channel,
            "ok": True,
            "found": len(configs),
            "picked": len(picked),
            "elapsed_ms": int((time.time() - started) * 1000),
            "configs": picked,
            "preview_host": preview_host,
            "error": "",
        }
    except Exception as e:
        return {
            "channel": channel,
            "ok": False,
            "found": 0,
            "picked": 0,
            "elapsed_ms": int((time.time() - started) * 1000),
            "configs": [],
            "preview_host": "",
            "error": str(e),
        }


def decode_text(s: str) -> str:
    s = html.unescape(s)
    s = s.replace("\\u0026", "&")
    s = s.replace("&amp;", "&")
    return s


def clean_config(s: str) -> str:
    s = decode_text(s).strip()
    s = re.sub(r"[\u200c\u200f\u202a-\u202e]", "", s)
    while s and re.search(r"[)\]}\"'<>،,.;]+$", s):
        s = s[:-1]
    return s.strip()


def normalize_config_key(raw: str) -> str:
    lower = raw.strip().lower()
    if lower.startswith("vmess://"):
        return raw.strip()
    return raw.strip().split("#", 1)[0]


def extract_configs(page: str) -> list[str]:
    if not page:
        return []
    text = decode_text(page)
    found: list[str] = []
    seen: set[str] = set()
    for rx in CONFIG_REGEXES:
        for m in rx.findall(text):
            cfg = clean_config(m)
            if not cfg:
                continue
            key = normalize_config_key(cfg)
            if key in seen:
                continue
            seen.add(key)
            found.append(cfg)
    found.reverse()
    return found


def stage1_collect() -> dict[str, Any]:
    channels = read_channels()
    print(c("[1/2] Stage 1: collecting configs from Telegram previews", Colors.BLUE))
    print(f"  Channels: {len(channels)}")
    print(f"  Rank 2 per channel: {PER_CHANNEL_LIMIT} | Rank 1 channels: {len(MAIN_CHANNELS)} | Rank 1 per channel: {MAIN_CHANNEL_LIMIT}")
    print()

    results: list[dict[str, Any]] = []
    collected: list[dict[str, str]] = []
    seen: set[str] = set()

    done = 0
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
        future_map = {ex.submit(fetch_channel, ch): ch for ch in channels}
        for fut in concurrent.futures.as_completed(future_map):
            res = fut.result()
            results.append(res)
            done += 1
            status = c("OK", Colors.GREEN) if res["ok"] else c("FAIL", Colors.RED)
            print(f"  [{done:>3}/{len(channels)}] {status} @{res['channel']:<24} found={res['found']:<3} picked={res['picked']:<2} {res['elapsed_ms']}ms")
            if res["error"]:
                log(f"FETCH FAIL @{res['channel']}: {res['error']}")
            for cfg in res["configs"]:
                key = normalize_config_key(cfg)
                if key in seen:
                    continue
                seen.add(key)
                collected.append({"source": res["channel"], "raw": cfg})

    elapsed = int(time.time() - start)
    lines = [x["raw"] for x in collected]
    STAGE1_FILE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    meta = {
        "generated_at": now_iso(),
        "stage": 1,
        "channels": len(channels),
        "per_channel_limit": PER_CHANNEL_LIMIT,
        "priority_one_channels": sorted(MAIN_CHANNELS),
        "main_channel_limit": MAIN_CHANNEL_LIMIT,
        "unique_configs": len(lines),
        "elapsed_seconds": elapsed,
        "results": results,
        "collected": collected,
    }
    STAGE1_META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(c("Stage 1 finished", Colors.GREEN))
    print(f"  Saved: {STAGE1_FILE.name}")
    print(f"  Unique configs: {len(lines)}")
    print(f"  Time: {elapsed}s")
    print()
    return meta


def wait_for_disconnect() -> None:
    print(c("IMPORTANT", Colors.YELLOW))
    print("  Now disconnect your current VPN/proxy/config completely.")
    print("  If v2rayN/Hiddify/Clash/NekoRay changed system proxy, close or disable it.")
    print("  After disconnecting, press Enter. Stage 2 will test from your current network.")
    print()
    input(c("Press Enter after disconnecting your own config... ", Colors.BOLD + Colors.YELLOW if COLOR else ""))
    print()


def read_stage1_configs() -> list[dict[str, str]]:
    if not STAGE1_FILE.exists():
        raise FileNotFoundError(f"Missing {STAGE1_FILE}")
    lines = [x.strip() for x in STAGE1_FILE.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]
    source_map: dict[str, str] = {}
    if STAGE1_META_FILE.exists():
        try:
            meta = json.loads(STAGE1_META_FILE.read_text(encoding="utf-8"))
            for item in meta.get("collected", []):
                source_map[item.get("raw", "")] = item.get("source", "unknown")
        except Exception:
            pass
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in lines:
        key = normalize_config_key(raw)
        if key in seen:
            continue
        seen.add(key)
        out.append({"raw": raw, "source": source_map.get(raw, "stage1")})
    return out


def b64_decode_text(s: str) -> str:
    s = s.strip().replace("-", "+").replace("_", "/")
    s += "=" * ((4 - len(s) % 4) % 4)
    return base64.b64decode(s).decode("utf-8", errors="ignore")


def b64_encode_text(s: str, urlsafe: bool = False) -> str:
    raw = s.encode("utf-8")
    enc = base64.urlsafe_b64encode(raw) if urlsafe else base64.b64encode(raw)
    return enc.decode("ascii").rstrip("=")


def valid_port(port: int) -> bool:
    return isinstance(port, int) and 0 < port <= 65535


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value))
    except Exception:
        return default


def parse_endpoint(raw: str, source: str) -> Optional[Endpoint]:
    lower = raw.lower().strip()
    try:
        if lower.startswith("vmess://"):
            return parse_vmess_endpoint(raw, source)
        if lower.startswith("ssr://"):
            return parse_ssr_endpoint(raw, source)
        if lower.startswith("ss://"):
            return parse_ss_endpoint(raw, source)
        if lower.startswith("vless://"):
            return parse_url_endpoint(raw, source, "vless", "v2ray")
        if lower.startswith("trojan://"):
            return parse_url_endpoint(raw, source, "trojan", "v2ray")
        if lower.startswith("snell://"):
            return parse_url_endpoint(raw, source, "snell", "v2ray")
        if lower.startswith("hysteria2://") or lower.startswith("hy2://"):
            return parse_url_endpoint(raw, source, "hy2", "v2ray")
        if lower.startswith("tuic://"):
            return parse_url_endpoint(raw, source, "tuic", "v2ray")
        if lower.startswith("tg://proxy?") or lower.startswith("tg://socks?") or lower.startswith("https://t.me/proxy?") or lower.startswith("https://t.me/socks?"):
            return parse_telegram_proxy(raw, source)
        return None
    except Exception as e:
        log(f"PARSE FAIL {raw[:120]}: {e}")
        return None


def parse_vmess_endpoint(raw: str, source: str) -> Optional[Endpoint]:
    obj = json.loads(b64_decode_text(raw[len("vmess://"):]))
    host = obj.get("add") or obj.get("address") or obj.get("host") or obj.get("server")
    port = parse_int(obj.get("port"))
    if not host or not valid_port(port):
        return None
    return Endpoint(raw, source, "v2ray", "vmess", str(host), port)


def parse_ssr_endpoint(raw: str, source: str) -> Optional[Endpoint]:
    decoded = b64_decode_text(raw[len("ssr://"):])
    main = decoded.split("/?", 1)[0]
    parts = main.split(":")
    if len(parts) < 2:
        return None
    host = parts[0]
    port = parse_int(parts[1])
    if not host or not valid_port(port):
        return None
    return Endpoint(raw, source, "v2ray", "ssr", host, port)


def parse_host_port(host_port: str) -> Optional[tuple[str, int]]:
    s = host_port.strip()
    if not s:
        return None
    if s.startswith("["):
        end = s.find("]")
        if end < 0:
            return None
        host = s[1:end]
        rest = s[end + 1:]
        if not rest.startswith(":"):
            return None
        port = parse_int(rest[1:])
        return (host, port) if host and valid_port(port) else None
    idx = s.rfind(":")
    if idx < 0:
        return None
    host = s[:idx]
    port = parse_int(s[idx + 1:])
    return (host, port) if host and valid_port(port) else None


def parse_ss_endpoint(raw: str, source: str) -> Optional[Endpoint]:
    body = raw[len("ss://"):].split("#", 1)[0].split("?", 1)[0]
    decoded = safe_unquote(body)
    if "@" not in decoded:
        decoded = b64_decode_text(decoded)
    hp = parse_host_port(decoded.split("@")[-1])
    if not hp:
        return None
    return Endpoint(raw, source, "v2ray", "ss", hp[0], hp[1])


def parse_url_endpoint(raw: str, source: str, protocol: str, kind: str) -> Optional[Endpoint]:
    u = urllib.parse.urlsplit(raw)
    host = u.hostname
    port = u.port or default_port(protocol)
    if not host or not valid_port(int(port)):
        return None
    return Endpoint(raw, source, kind, protocol, host, int(port))


def parse_telegram_proxy(raw: str, source: str) -> Optional[Endpoint]:
    u = urllib.parse.urlsplit(raw)
    q = urllib.parse.parse_qs(u.query)
    host = first(q, "server")
    port = parse_int(first(q, "port"))
    if not host or not valid_port(port):
        return None
    protocol = "telegram-socks" if "/socks" in raw.lower() or "tg://socks" in raw.lower() else "telegram-mtproto"
    return Endpoint(raw, source, "mtproto", protocol, host, port)


def default_port(protocol: str) -> int:
    return 443 if protocol in {"vless", "vmess", "trojan", "snell", "hy2", "tuic"} else 8388


def first(q: dict[str, list[str]], key: str, default: str = "") -> str:
    vals = q.get(key)
    return vals[0] if vals else default


def safe_unquote(s: str) -> str:
    try:
        return urllib.parse.unquote(s)
    except Exception:
        return s


def str_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def bool_from_query(q: dict[str, list[str]], *keys: str) -> bool:
    for key in keys:
        val = first(q, key, "")
        if val:
            return str_bool(val)
    return False


def csv_list(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def build_stream_settings_from_url(u: urllib.parse.SplitResult, q: dict[str, list[str]]) -> dict[str, Any]:
    network = first(q, "type", first(q, "net", "tcp")) or "tcp"
    security = first(q, "security", "none") or "none"
    stream: dict[str, Any] = {"network": network}

    if security and security != "none":
        stream["security"] = security
        sni = first(q, "sni", first(q, "serverName", first(q, "peer", "")))
        allow_insecure = bool_from_query(q, "allowInsecure", "insecure")
        alpn = csv_list(first(q, "alpn", ""))
        fp = first(q, "fp", first(q, "fingerprint", ""))
        if security == "tls":
            tls: dict[str, Any] = {}
            if sni:
                tls["serverName"] = sni
            if alpn:
                tls["alpn"] = alpn
            if fp:
                tls["fingerprint"] = fp
            tls["allowInsecure"] = allow_insecure
            stream["tlsSettings"] = tls
        elif security == "reality":
            reality: dict[str, Any] = {}
            if sni:
                reality["serverName"] = sni
            if fp:
                reality["fingerprint"] = fp
            pbk = first(q, "pbk", first(q, "publicKey", ""))
            sid = first(q, "sid", first(q, "shortId", ""))
            spx = first(q, "spx", first(q, "spiderX", ""))
            if pbk:
                reality["publicKey"] = pbk
            if sid:
                reality["shortId"] = sid
            if spx:
                reality["spiderX"] = safe_unquote(spx)
            stream["realitySettings"] = reality

    host = first(q, "host", "")
    path = safe_unquote(first(q, "path", first(q, "serviceName", "")))
    header_type = first(q, "headerType", first(q, "header", "none")) or "none"

    if network == "ws":
        ws: dict[str, Any] = {}
        if path:
            ws["path"] = path
        if host:
            ws["headers"] = {"Host": host}
        stream["wsSettings"] = ws
    elif network == "grpc":
        grpc: dict[str, Any] = {}
        if path:
            grpc["serviceName"] = path
        mode = first(q, "mode", "")
        if mode == "multi":
            grpc["multiMode"] = True
        stream["grpcSettings"] = grpc
    elif network in {"httpupgrade", "httpUpgrade"}:
        httpu: dict[str, Any] = {}
        if path:
            httpu["path"] = path
        if host:
            httpu["host"] = host
        stream["httpupgradeSettings"] = httpu
        stream["network"] = "httpupgrade"
    elif network in {"xhttp", "splithttp"}:
        xhttp: dict[str, Any] = {}
        if path:
            xhttp["path"] = path
        if host:
            xhttp["host"] = host
        mode = first(q, "mode", "")
        if mode:
            xhttp["mode"] = mode
        stream["xhttpSettings"] = xhttp
        stream["network"] = "xhttp"
    elif network in {"h2", "http"}:
        http_settings: dict[str, Any] = {}
        if path:
            http_settings["path"] = path
        if host:
            http_settings["host"] = [host]
        stream["httpSettings"] = http_settings
        stream["network"] = "http"
    elif network == "tcp":
        if header_type and header_type != "none":
            tcp: dict[str, Any] = {"header": {"type": header_type}}
            if header_type == "http":
                request: dict[str, Any] = {}
                if path:
                    request["path"] = [path]
                if host:
                    request["headers"] = {"Host": [host]}
                tcp["header"]["request"] = request
            stream["tcpSettings"] = tcp
    return stream


def build_stream_settings_from_vmess(obj: dict[str, Any]) -> dict[str, Any]:
    network = str(obj.get("net") or obj.get("type") or "tcp")
    security = str(obj.get("tls") or obj.get("security") or "none")
    fake_url = urllib.parse.SplitResult("vmess", "", "", "", "")
    q: dict[str, list[str]] = {
        "type": [network],
        "security": [security if security else "none"],
        "host": [str(obj.get("host") or "")],
        "path": [str(obj.get("path") or "")],
        "sni": [str(obj.get("sni") or obj.get("peer") or "")],
        "alpn": [str(obj.get("alpn") or "")],
        "headerType": [str(obj.get("type") or obj.get("headerType") or "none")],
        "allowInsecure": [str(obj.get("allowInsecure") or obj.get("allowinsecure") or "0")],
    }
    return build_stream_settings_from_url(fake_url, q)


def build_xray_outbound(raw: str) -> Optional[dict[str, Any]]:
    lower = raw.lower().strip()
    try:
        if lower.startswith("vless://"):
            u = urllib.parse.urlsplit(raw)
            q = urllib.parse.parse_qs(u.query)
            if not u.hostname or not u.username:
                return None
            user: dict[str, Any] = {
                "id": urllib.parse.unquote(u.username),
                "encryption": first(q, "encryption", "none") or "none",
            }
            flow = first(q, "flow", "")
            if flow:
                user["flow"] = flow
            return {
                "tag": "proxy",
                "protocol": "vless",
                "settings": {"vnext": [{"address": u.hostname, "port": u.port or 443, "users": [user]}]},
                "streamSettings": build_stream_settings_from_url(u, q),
            }

        if lower.startswith("vmess://"):
            obj = json.loads(b64_decode_text(raw[len("vmess://"):]))
            host = obj.get("add") or obj.get("address") or obj.get("host") or obj.get("server")
            port = parse_int(obj.get("port"), 443)
            user = {
                "id": str(obj.get("id") or ""),
                "alterId": parse_int(obj.get("aid"), 0),
                "security": str(obj.get("scy") or obj.get("security") or "auto"),
            }
            if not host or not user["id"]:
                return None
            return {
                "tag": "proxy",
                "protocol": "vmess",
                "settings": {"vnext": [{"address": str(host), "port": port, "users": [user]}]},
                "streamSettings": build_stream_settings_from_vmess(obj),
            }

        if lower.startswith("trojan://"):
            u = urllib.parse.urlsplit(raw)
            q = urllib.parse.parse_qs(u.query)
            if not u.hostname or not u.username:
                return None
            return {
                "tag": "proxy",
                "protocol": "trojan",
                "settings": {"servers": [{"address": u.hostname, "port": u.port or 443, "password": urllib.parse.unquote(u.username)}]},
                "streamSettings": build_stream_settings_from_url(u, q),
            }

        if lower.startswith("ss://"):
            parsed = parse_shadowsocks_share(raw)
            if not parsed:
                return None
            method, password, host, port = parsed
            return {
                "tag": "proxy",
                "protocol": "shadowsocks",
                "settings": {"servers": [{"address": host, "port": port, "method": method, "password": password}]},
            }

        # Xray does not support SSR/Snell as direct outbound in common builds.
        return None
    except Exception as e:
        log(f"XRAY OUTBOUND BUILD FAIL {raw[:120]}: {e}")
        return None


def parse_shadowsocks_share(raw: str) -> Optional[tuple[str, str, str, int]]:
    body = raw[len("ss://"):].split("#", 1)[0]
    u = urllib.parse.urlsplit("ss://" + body)
    if u.hostname and u.username and u.password:
        return (urllib.parse.unquote(u.username), urllib.parse.unquote(u.password), u.hostname, u.port or 8388)

    body_no_query = body.split("?", 1)[0]
    decoded = safe_unquote(body_no_query)
    if "@" not in decoded:
        decoded = b64_decode_text(decoded)
    if "@" not in decoded or ":" not in decoded:
        return None
    userinfo, host_port = decoded.rsplit("@", 1)
    if ":" not in userinfo:
        userinfo = b64_decode_text(userinfo)
    method, password = userinfo.split(":", 1)
    hp = parse_host_port(host_port)
    if not hp:
        return None
    return (method, password, hp[0], hp[1])


def set_config_display_name(raw: str, name: str) -> str:
    lower = raw.lower().strip()
    if lower.startswith("vmess://"):
        try:
            obj = json.loads(b64_decode_text(raw[len("vmess://"):]))
            obj["ps"] = name
            payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            return "vmess://" + b64_encode_text(payload, urlsafe=True)
        except Exception:
            return raw.split("#", 1)[0].rstrip() + "#" + name
    if lower.startswith("ssr://"):
        return raw
    return raw.split("#", 1)[0].rstrip() + "#" + name



def get_config_display_name(raw: str) -> str:
    lower = raw.lower().strip()
    if lower.startswith("vmess://"):
        try:
            obj = json.loads(b64_decode_text(raw[len("vmess://"):]))
            return str(obj.get("ps") or "").strip()
        except Exception:
            return ""
    if "#" in raw:
        fragment = raw.split("#", 1)[1].strip()
        return urllib.parse.unquote(fragment)
    return ""


def resolve_path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def resolve_bundle_path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else BUNDLE_DIR / p


def platform_xray_asset_keyword() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system.startswith("win"):
        if "arm" in machine or "aarch64" in machine:
            return "Xray-windows-arm64.zip"
        if "86" in machine and "64" not in machine and "amd64" not in machine:
            return "Xray-windows-32.zip"
        return "Xray-windows-64.zip"

    if system == "darwin":
        return "Xray-macos-arm64.zip" if ("arm" in machine or "aarch64" in machine) else "Xray-macos-64.zip"

    if system == "linux":
        if "arm" in machine or "aarch64" in machine:
            return "Xray-linux-arm64-v8a.zip"
        if "86" in machine and "64" not in machine and "amd64" not in machine:
            return "Xray-linux-32.zip"
        return "Xray-linux-64.zip"

    return "Xray-windows-64.zip"


def normalize_proxy_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = "http://" + value
    return value


def urlopen_with_optional_proxy(req: urllib.request.Request, timeout: float):
    proxy = normalize_proxy_url(DOWNLOAD_PROXY)
    if proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def download_url_to_file(url: str, target: Path, timeout: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DicodeConfigChecker/1.0",
            "Accept": "application/octet-stream,*/*",
        },
    )
    with urlopen_with_optional_proxy(req, timeout=timeout) as r, target.open("wb") as f:
        shutil.copyfileobj(r, f)


def get_latest_xray_asset() -> tuple[str, str]:
    headers = {
        "User-Agent": "DicodeConfigChecker/1.0",
        "Accept": "application/vnd.github+json",
    }
    # GitHub Actions supplies this short-lived token to the release build.  It
    # avoids anonymous API-rate-limit failures while keeping desktop users
    # entirely token-free.
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    req = urllib.request.Request(
        XRAY_RELEASE_API,
        headers=headers,
    )
    with urlopen_with_optional_proxy(req, timeout=XRAY_DOWNLOAD_TIMEOUT) as r:
        data = json.loads(r.read().decode("utf-8", errors="ignore"))

    wanted = platform_xray_asset_keyword().lower()
    assets = data.get("assets", []) or []

    for asset in assets:
        name = str(asset.get("name", ""))
        if name.lower() == wanted:
            url = asset.get("browser_download_url")
            if url:
                return name, str(url)

    # Fallback: choose the closest Windows 64 package when the exact name changes.
    fallbacks = [
        ("windows", "64"),
        ("linux", "64"),
        ("macos", "64"),
    ]
    for words in fallbacks:
        for asset in assets:
            name = str(asset.get("name", ""))
            lname = name.lower()
            if lname.endswith(".zip") and all(w in lname for w in words):
                url = asset.get("browser_download_url")
                if url:
                    return name, str(url)

    raise RuntimeError("No compatible Xray-core release asset found")


def extract_xray_from_zip(zip_path: Path, target_path: Path) -> None:
    import zipfile

    exe_name = "xray.exe" if platform.system().lower().startswith("win") else "xray"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        selected = None
        for name in names:
            if Path(name).name.lower() == exe_name.lower():
                selected = name
                break
        if selected is None:
            for name in names:
                base = Path(name).name.lower()
                if base.startswith("xray") and not name.endswith("/"):
                    selected = name
                    break
        if selected is None:
            raise RuntimeError("xray binary not found inside release zip")

        with z.open(selected) as src, target_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)

        for data_name in ("geoip.dat", "geosite.dat"):
            selected_data = None
            for name in names:
                if Path(name).name.lower() == data_name:
                    selected_data = name
                    break
            if selected_data:
                with z.open(selected_data) as src, (target_path.parent / data_name).open("wb") as dst:
                    shutil.copyfileobj(src, dst)

    try:
        target_path.chmod(0o755)
    except Exception:
        pass


def ensure_xray_binary() -> Optional[Path]:
    existing = find_xray_binary(check_download=False)
    if existing:
        return existing

    if not AUTO_DOWNLOAD_XRAY:
        return None

    configured = resolve_path(XRAY_PATH)
    CORE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_zip = CORE_DIR / "xray_latest.zip"

    try:
        print(c("  Xray core: not found; downloading latest release...", Colors.YELLOW))
        if DOWNLOAD_PROXY:
            print(f"  Download proxy: {normalize_proxy_url(DOWNLOAD_PROXY)}")
        name, url = get_latest_xray_asset()
        print(f"  Asset: {name}")
        download_url_to_file(url, tmp_zip, XRAY_DOWNLOAD_TIMEOUT)
        extract_xray_from_zip(tmp_zip, configured)
        try:
            tmp_zip.unlink(missing_ok=True)
        except Exception:
            pass
        print(c(f"  Xray core ready: {configured}", Colors.GREEN))
        return configured if configured.exists() else find_xray_binary(check_download=False)
    except Exception as e:
        log(f"XRAY AUTO DOWNLOAD FAIL: {e}")
        print(c(f"  Xray auto-download failed: {e}", Colors.RED))
        return None

def find_xray_binary(check_download: bool = True) -> Optional[Path]:
    exe_name = "xray.exe" if platform.system().lower().startswith("win") else "xray"
    candidates: list[Path] = []
    candidates.append(resolve_path(XRAY_PATH))
    candidates.append(CORE_DIR / exe_name)
    candidates.append(CORE_DIR / "xray.exe")
    candidates.append(CORE_DIR / "xray")
    candidates.append(resolve_bundle_path(XRAY_PATH))
    candidates.append(BUNDLE_DIR / "core" / exe_name)
    candidates.append(BUNDLE_DIR / "core" / "xray.exe")
    candidates.append(BUNDLE_DIR / "core" / "xray")

    for name in ["xray.exe", "xray"]:
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))

    seen: set[str] = set()
    for p in candidates:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.exists() and p.is_file():
            return p

    if check_download:
        return ensure_xray_binary()
    return None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def make_xray_config(outbound: dict[str, Any], socks_port: int) -> dict[str, Any]:
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "socks-in",
                "listen": "127.0.0.1",
                "port": socks_port,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
            }
        ],
        "outbounds": [
            outbound,
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
        ],
    }


ACTIVE_XRAY_PROCESSES: list[subprocess.Popen] = []


def _windows_creation_flags() -> int:
    if not platform.system().lower().startswith("win"):
        return 0
    flags = subprocess.CREATE_NO_WINDOW
    # CREATE_NEW_PROCESS_GROUP makes cleanup more reliable on Windows.
    flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return flags


def run_xray_process(xray_path: Path, config_path: Path) -> subprocess.Popen:
    # Xray's modern CLI uses: xray run -config file.json.
    proc = subprocess.Popen(
        [str(xray_path), "run", "-config", str(config_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="ignore",
        creationflags=_windows_creation_flags(),
    )
    ACTIVE_XRAY_PROCESSES.append(proc)
    return proc


def wait_port_open(host: str, port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.35):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def terminate_process(proc: subprocess.Popen) -> None:
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                if platform.system().lower().startswith("win"):
                    try:
                        subprocess.run(
                            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=3,
                        )
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                else:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        try:
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass
    except Exception:
        pass
    finally:
        try:
            if proc in ACTIVE_XRAY_PROCESSES:
                ACTIVE_XRAY_PROCESSES.remove(proc)
        except Exception:
            pass


def cleanup_xray_processes() -> None:
    """Terminate every Xray process launched by this app.

    The checker can spawn many short-lived Xray cores while testing. This cleanup
    keeps local ports free for v2rayN, V2Ray, and other clients after a scan.
    """
    for proc in list(ACTIVE_XRAY_PROCESSES):
        terminate_process(proc)


def socks5_http_delay_ms(socks_host: str, socks_port: int, url: str, timeout: float) -> tuple[Optional[int], str]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None, "bad_check_url"
    target_host = parsed.hostname
    target_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    started = time.perf_counter()
    s: Optional[socket.socket] = None
    try:
        s = socket.create_connection((socks_host, socks_port), timeout=timeout)
        s.settimeout(timeout)
        s.sendall(b"\x05\x01\x00")
        resp = recv_exact(s, 2)
        if len(resp) != 2 or resp[0] != 5 or resp[1] != 0:
            return None, "socks_auth_failed"
        host_bytes = target_host.encode("idna")
        req = b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + int(target_port).to_bytes(2, "big")
        s.sendall(req)
        head = recv_exact(s, 4)
        if len(head) != 4 or head[1] != 0:
            code = head[1] if len(head) >= 2 else "short"
            return None, f"socks_connect_failed_{code}"
        atyp = head[3]
        if atyp == 1:
            _ = recv_exact(s, 4)
        elif atyp == 3:
            ln = recv_exact(s, 1)
            _ = recv_exact(s, ln[0] if ln else 0)
        elif atyp == 4:
            _ = recv_exact(s, 16)
        _ = recv_exact(s, 2)

        raw_sock: socket.socket | ssl.SSLSocket = s
        if parsed.scheme == "https":
            ctx = ssl.create_default_context()
            raw_sock = ctx.wrap_socket(s, server_hostname=target_host)

        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {target_host}\r\n"
            "User-Agent: DicodeConfigChecker/1.0\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii", errors="ignore")
        raw_sock.sendall(request)
        data = raw_sock.recv(128)
        elapsed = int((time.perf_counter() - started) * 1000)
        if data.startswith(b"HTTP/"):
            return elapsed, ""
        return None, "bad_http_response"
    except Exception as e:
        return None, e.__class__.__name__
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass


def recv_exact(sock: socket.socket | ssl.SSLSocket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data


def xray_attempt(raw: str, xray_path: Path) -> tuple[Optional[int], str]:
    outbound = build_xray_outbound(raw)
    if outbound is None:
        return None, "unsupported_for_xray"
    socks_port = free_port()
    proc: Optional[subprocess.Popen] = None
    tmp_path: Optional[Path] = None
    try:
        cfg = make_xray_config(outbound, socks_port)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump(cfg, f, ensure_ascii=False, separators=(",", ":"))
            tmp_path = Path(f.name)
        proc = run_xray_process(xray_path, tmp_path)
        if not wait_port_open("127.0.0.1", socks_port, XRAY_STARTUP_WAIT):
            err = "xray_port_not_open"
            try:
                stderr = proc.stderr.read(800) if proc.stderr and proc.poll() is not None else ""
                if stderr:
                    err += ":" + stderr.strip().replace("\n", " ")[:300]
            except Exception:
                pass
            return None, err
        return socks5_http_delay_ms("127.0.0.1", socks_port, CHECK_URL, SOCKET_TIMEOUT)
    finally:
        if proc:
            terminate_process(proc)
        if tmp_path:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


def tcp_connect_delay_ms(host: str, port: int, timeout: float) -> tuple[Optional[int], str]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return int((time.perf_counter() - started) * 1000), ""
    except Exception as e:
        return None, e.__class__.__name__


def telegram_socks_delay_ms(host: str, port: int, timeout: float) -> tuple[Optional[int], str]:
    """Validate Telegram SOCKS proxies by creating a SOCKS5 tunnel to a Telegram DC."""
    target_host = "149.154.167.50"
    target_port = 443
    started = time.perf_counter()
    s: Optional[socket.socket] = None
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        s.sendall(b"\x05\x01\x00")
        resp = recv_exact(s, 2)
        if len(resp) != 2 or resp[0] != 5 or resp[1] != 0:
            return None, "socks_auth_failed"
        # Use the SOCKS5 IPv4 form rather than asking the proxy to resolve a
        # numeric address as a hostname.  A surprising number of otherwise
        # healthy Telegram SOCKS endpoints reject that less common form.
        host_bytes = socket.inet_aton(target_host)
        req = b"\x05\x01\x00\x01" + host_bytes + int(target_port).to_bytes(2, "big")
        s.sendall(req)
        head = recv_exact(s, 4)
        if len(head) != 4 or head[1] != 0:
            code = head[1] if len(head) >= 2 else "short"
            return None, f"socks_tunnel_failed_{code}"
        atyp = head[3]
        if atyp == 1:
            _ = recv_exact(s, 4)
        elif atyp == 3:
            ln = recv_exact(s, 1)
            _ = recv_exact(s, ln[0] if ln else 0)
        elif atyp == 4:
            _ = recv_exact(s, 16)
        _ = recv_exact(s, 2)
        return int((time.perf_counter() - started) * 1000), ""
    except Exception as e:
        return None, e.__class__.__name__
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass


def telegram_mtproto_delay_ms(host: str, port: int, timeout: float) -> tuple[Optional[int], str]:
    """Stable MTProto proxy reachability check.

    Telegram's full MTProto proxy auth is client-specific, so this check measures
    connect latency and rejects endpoints that immediately close the socket.
    It is stricter than a bare TCP connect and avoids accepting many dead ports.
    """
    started = time.perf_counter()
    s: Optional[socket.socket] = None
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(0.18)
        try:
            data = s.recv(1, socket.MSG_PEEK)
            if data == b"":
                return None, "immediate_close"
        except socket.timeout:
            pass
        except BlockingIOError:
            pass
        return int((time.perf_counter() - started) * 1000), ""
    except Exception as e:
        return None, e.__class__.__name__
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass


def telegram_proxy_delay_ms(ep: Endpoint) -> tuple[Optional[int], str]:
    if ep.protocol == "telegram-socks":
        return telegram_socks_delay_ms(ep.host, ep.port, TCP_TIMEOUT)
    return telegram_mtproto_delay_ms(ep.host, ep.port, TCP_TIMEOUT)


def summarize_samples(samples: list[int], ok: bool) -> tuple[Optional[int], Optional[int], Optional[int]]:
    if not samples or not ok:
        return None, None, None
    return int(statistics.median(samples)), min(samples), int(sum(samples) / len(samples))


def repeated_test(ep: Endpoint, xray_path: Optional[Path]) -> TestResult:
    samples: list[int] = []
    errors: list[str] = []
    tester = "tcp"

    use_xray = False
    if ep.kind == "v2ray" and TEST_MODE in {"auto", "xray"} and xray_path:
        if build_xray_outbound(ep.raw) is not None:
            use_xray = True

    if TEST_MODE == "xray" and ep.kind == "v2ray" and not use_xray:
        return TestResult(ep.raw, ep.source, ep.kind, ep.protocol, ep.host, ep.port, False, None, None, None, PING_ATTEMPTS, 0, [], "xray", "unsupported_or_missing_xray")

    for attempt in range(PING_ATTEMPTS):
        if use_xray:
            tester = "xray-http"
            ms, err = xray_attempt(ep.raw, xray_path)  # type: ignore[arg-type]
        else:
            if ep.kind == "mtproto":
                tester = "telegram-proxy-stable"
                ms, err = telegram_proxy_delay_ms(ep)
            else:
                tester = "tcp-fallback"
                ms, err = tcp_connect_delay_ms(ep.host, ep.port, TCP_TIMEOUT)
        if ms is not None:
            samples.append(ms)
        else:
            errors.append(err)
        if attempt < PING_ATTEMPTS - 1:
            time.sleep(ATTEMPT_GAP_SECONDS + random.uniform(0, 0.08))

    ok = len(samples) >= MIN_SUCCESS
    median_ms, min_ms, avg_ms = summarize_samples(samples, ok)
    error = "" if ok else (";".join(errors[-4:]) if errors else "not_enough_success")
    return TestResult(
        raw=ep.raw,
        source=ep.source,
        kind=ep.kind,
        protocol=ep.protocol,
        host=ep.host,
        port=ep.port,
        ok=ok,
        ping_ms=median_ms,
        min_ms=min_ms,
        avg_ms=avg_ms,
        attempts=PING_ATTEMPTS,
        success_count=len(samples),
        samples_ms=samples,
        tester=tester,
        error=error,
    )


def progress(done: int, total: int, alive: int, dead: int, unsupported: int) -> None:
    width = 28
    ratio = done / total if total else 1
    filled = int(ratio * width)
    bar = "#" * filled + "-" * (width - filled)
    print(f"\r  Testing [{bar}] {done}/{total} | alive={alive} dead={dead} unsupported={unsupported}", end="", flush=True)


def stage2_test() -> dict[str, Any]:
    print(c("[2/2] Stage 2: quality testing", Colors.BLUE))
    items = read_stage1_configs()
    endpoints: list[Endpoint] = []
    unsupported: list[str] = []
    skipped_configs: list[str] = []
    skipped_proxies: list[str] = []
    for item in items:
        ep = parse_endpoint(item["raw"], item.get("source", "stage1"))
        if ep:
            if ep.kind == "mtproto" and not CHECK_TELEGRAM_PROXIES:
                skipped_proxies.append(item["raw"])
                continue
            if ep.kind != "mtproto" and not CHECK_V2RAY_CONFIGS:
                skipped_configs.append(item["raw"])
                continue
            endpoints.append(ep)
        else:
            unsupported.append(item["raw"])

    if skipped_configs:
        print(c(f"  V2Ray/Xray config checking disabled; skipped {len(skipped_configs)} configs.", Colors.YELLOW))
    if skipped_proxies:
        print(c(f"  Telegram proxy checking disabled; skipped {len(skipped_proxies)} proxies.", Colors.YELLOW))

    xray_path = ensure_xray_binary()
    if TEST_MODE in {"auto", "xray"}:
        if xray_path:
            print(f"  Xray core: {xray_path}")
        else:
            msg = "  Xray core: not found"
            if TEST_MODE == "xray":
                print(c(msg + " | xray mode will reject V2Ray configs", Colors.RED))
            else:
                print(c(msg + " | auto mode will use repeated TCP fallback", Colors.YELLOW))

    print(f"  Test mode: {TEST_MODE}")
    print(f"  Check URL: {CHECK_URL}")
    print(f"  Loaded items: {len(items)}")
    print(f"  Testable endpoints: {len(endpoints)}")
    print(f"  Unsupported/skipped: {len(unsupported)}")
    print(f"  Attempts: {PING_ATTEMPTS} | required successes: {MIN_SUCCESS}")
    print(f"  Workers: {PING_WORKERS}")
    print()

    start = time.time()
    results: list[TestResult] = []
    done = alive_count = dead_count = 0
    total = len(endpoints)

    if total:
        progress(0, total, 0, 0, len(unsupported))
        with concurrent.futures.ThreadPoolExecutor(max_workers=PING_WORKERS) as ex:
            futs = [ex.submit(repeated_test, ep, xray_path) for ep in endpoints]
            for fut in concurrent.futures.as_completed(futs):
                res = fut.result()
                results.append(res)
                done += 1
                if res.ok:
                    alive_count += 1
                else:
                    dead_count += 1
                progress(done, total, alive_count, dead_count, len(unsupported))
        print()

    elapsed = int(time.time() - start)
    alive = sorted([r for r in results if r.ok], key=lambda r: r.ping_ms if r.ping_ms is not None else 999999)
    dead = [r for r in results if not r.ok]

    alive_configs = [r for r in alive if r.kind != "mtproto"]
    alive_proxies = [r for r in alive if r.kind == "mtproto"]
    dead_configs = [r for r in dead if r.kind != "mtproto"]
    dead_proxies = [r for r in dead if r.kind == "mtproto"]

    renamed_config_items: list[tuple[int, TestResult, str, str]] = []
    for idx, r in enumerate(alive_configs, 1):
        if RENAME_CONFIG_NAMES:
            display_name = f"{SUB_TAG_PREFIX}-{idx}"
            output_raw = set_config_display_name(r.raw, display_name)
        else:
            display_name = get_config_display_name(r.raw) or f"original-{idx}"
            output_raw = r.raw
        renamed_config_items.append((idx, r, output_raw, display_name))

    sub_lines = [x[2] for x in renamed_config_items]
    proxy_lines = [r.raw for r in alive_proxies]
    SUB_FILE.write_text("\n".join(sub_lines) + ("\n" if sub_lines else ""), encoding="utf-8")
    SUB_BASE64_FILE.write_text(base64.b64encode(("\n".join(sub_lines)).encode("utf-8")).decode("ascii"), encoding="utf-8")
    PROXY_FILE.write_text("\n".join(proxy_lines) + ("\n" if proxy_lines else ""), encoding="utf-8")
    PROXY_BASE64_FILE.write_text(base64.b64encode(("\n".join(proxy_lines)).encode("utf-8")).decode("ascii"), encoding="utf-8")

    write_reports(renamed_config_items, alive_proxies, dead_configs, dead_proxies, unsupported, elapsed, xray_path)

    full = {
        "generated_at": now_iso(),
        "version": VERSION,
        "mode": "two-stage-xray-like-quality-test",
        "notes": [
            "Stage 1 fetched Telegram public previews while your own proxy/VPN was active.",
            "Stage 2 tested after disconnecting your own proxy/VPN.",
            "For V2Ray/Xray configs, xray-http tester launches Xray core, creates local SOCKS, and requests CHECK_URL through the candidate config.",
            "Telegram MTProto/SOCKS proxy links are separated into proxy.txt, not sub.txt.",
            "TCP fallback is only host:port reachability, not full protocol validation.",
        ],
        "settings": {
            "per_channel_limit": PER_CHANNEL_LIMIT,
            "main_channel_limit": MAIN_CHANNEL_LIMIT,
            "priority_one_channels": sorted(MAIN_CHANNELS),
            "rename_config_names": RENAME_CONFIG_NAMES,
            "check_v2ray_configs": CHECK_V2RAY_CONFIGS,
            "check_telegram_proxies": CHECK_TELEGRAM_PROXIES,
            "sub_tag_prefix": SUB_TAG_PREFIX,
            "test_mode": TEST_MODE,
            "xray_path": str(xray_path) if xray_path else None,
            "check_url": CHECK_URL,
            "attempts": PING_ATTEMPTS,
            "min_success": MIN_SUCCESS,
            "ping_workers": PING_WORKERS,
        },
        "stats": {
            "loaded": len(items),
            "testable": total,
            "alive_total": len(alive),
            "dead_total": len(dead),
            "alive_configs": len(alive_configs),
            "alive_telegram_proxies": len(alive_proxies),
            "dead_configs": len(dead_configs),
            "dead_telegram_proxies": len(dead_proxies),
            "unsupported": len(unsupported),
            "elapsed_seconds": elapsed,
        },
        "alive_configs": [{**asdict(r), "subscription_raw": renamed_raw, "subscription_name": display_name} for _, r, renamed_raw, display_name in renamed_config_items],
        "alive_telegram_proxies": [asdict(r) for r in alive_proxies],
        "dead_configs": [asdict(r) for r in dead_configs] if WRITE_DEAD_TO_REPORT else [],
        "dead_telegram_proxies": [asdict(r) for r in dead_proxies] if WRITE_DEAD_TO_REPORT else [],
        "unsupported": unsupported if WRITE_DEAD_TO_REPORT else [],
    }
    REPORT_FILE.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(c("Done", Colors.GREEN))
    print(f"  Alive V2Ray/Xray configs: {len(alive_configs)} -> {SUB_FILE.name}")
    print(f"  Alive Telegram proxies:   {len(alive_proxies)} -> {PROXY_FILE.name}")
    print(f"  Dead total:               {len(dead)}")
    print(f"  Unsupported:              {len(unsupported)}")
    print()
    print(c("Files:", Colors.CYAN))
    print(f"  {SUB_FILE.name}             <- V2Ray/Xray subscription output ({'renamed' if RENAME_CONFIG_NAMES else 'original names preserved'})")
    print(f"  {SUB_BASE64_FILE.name}      <- base64 V2Ray/Xray subscription")
    print(f"  {PROXY_FILE.name}           <- Telegram MTProto/SOCKS proxies")
    print(f"  {PROXY_BASE64_FILE.name}    <- base64 Telegram proxies")
    print(f"  {ALIVE_REPORT_FILE.name}    <- readable V2Ray/Xray report")
    print(f"  {PROXY_REPORT_FILE.name}    <- readable Telegram proxy report")
    print(f"  {REPORT_FILE.name}          <- full json report")
    print()
    return full


def write_reports(config_items: list[tuple[int, TestResult, str, str]], alive_proxies: list[TestResult], dead_configs: list[TestResult], dead_proxies: list[TestResult], unsupported: list[str], elapsed: int, xray_path: Optional[Path]) -> None:
    config_report: list[str] = []
    config_report.append(f"{APP_NAME} v{VERSION}")
    config_report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    config_report.append("Mode: two-stage; fetch first, disconnect, then quality test")
    config_report.append(f"Tester: {TEST_MODE}; xray={xray_path if xray_path else 'not found'}")
    config_report.append(f"Rule: OK only if at least {MIN_SUCCESS}/{PING_ATTEMPTS} attempts succeed")
    config_report.append(f"Check URL: {CHECK_URL}")
    config_report.append("")
    config_report.append(f"Alive V2Ray/Xray configs: {len(config_items)}")
    config_report.append(f"Dead V2Ray/Xray configs: {len(dead_configs)}")
    config_report.append(f"Telegram proxies moved to: {PROXY_FILE.name}")
    config_report.append(f"Unsupported: {len(unsupported)}")
    config_report.append(f"Elapsed: {elapsed}s")
    config_report.append("")
    config_report.append("Alive V2Ray/Xray configs sorted by stable latency:")
    config_report.append("-" * 116)
    for idx, r, _, display_name in config_items:
        config_report.append(
            f"{idx:03d}. median={fmt_ms(r.ping_ms):>7} | min={fmt_ms(r.min_ms):>7} | avg={fmt_ms(r.avg_ms):>7} | "
            f"ok={r.success_count}/{r.attempts} | tester={r.tester:<12} | {r.protocol:<8} | {r.host}:{r.port} | @{r.source} | name={display_name}"
        )
    ALIVE_REPORT_FILE.write_text("\n".join(config_report) + "\n", encoding="utf-8")

    proxy_report: list[str] = []
    proxy_report.append(f"{APP_NAME} v{VERSION}")
    proxy_report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    proxy_report.append("These are Telegram MTProto/SOCKS proxies, not V2Ray/Xray configs.")
    proxy_report.append(f"Rule: OK only if at least {MIN_SUCCESS}/{PING_ATTEMPTS} TCP connects succeed")
    proxy_report.append("")
    proxy_report.append(f"Alive Telegram proxies: {len(alive_proxies)}")
    proxy_report.append(f"Dead Telegram proxies: {len(dead_proxies)}")
    proxy_report.append("")
    proxy_report.append("Alive Telegram proxies sorted by stable TCP latency:")
    proxy_report.append("-" * 100)
    for idx, r in enumerate(alive_proxies, 1):
        proxy_report.append(
            f"{idx:03d}. median={fmt_ms(r.ping_ms):>7} | min={fmt_ms(r.min_ms):>7} | avg={fmt_ms(r.avg_ms):>7} | "
            f"ok={r.success_count}/{r.attempts} | {r.protocol:<16} | {r.host}:{r.port} | @{r.source}"
        )
    PROXY_REPORT_FILE.write_text("\n".join(proxy_report) + "\n", encoding="utf-8")


def fmt_ms(value: Optional[int]) -> str:
    return "-" if value is None else f"{value} ms"


def main() -> int:
    try:
        ensure_files()
        if "--version" in sys.argv:
            print(VERSION)
            return 0
        if "--download-xray-only" in sys.argv:
            xray = ensure_xray_binary()
            if not xray:
                print(c("Xray core could not be prepared.", Colors.RED))
                return 1
            print(c(f"Xray core ready: {xray}", Colors.GREEN))
            return 0

        clear_old_outputs()
        banner()
        print("Before starting, connect the config/VPN/proxy that gives you Telegram access.")
        print("Xray-core will be prepared first while your current connection is still active.")
        print("Then the app collects Telegram public previews.")
        input(c("Press Enter when Telegram is reachable... ", Colors.BOLD + Colors.YELLOW if COLOR else ""))
        print()
        xray = ensure_xray_binary()
        if TEST_MODE in {"auto", "xray"}:
            if xray:
                print(c(f"  Xray core ready before collection: {xray}", Colors.GREEN))
            elif TEST_MODE == "xray":
                print(c("  Xray core is missing. Stage 2 cannot accept V2Ray configs in xray mode.", Colors.RED))
            else:
                print(c("  Xray core is missing. Auto mode will fallback where possible.", Colors.YELLOW))
        print()
        stage1_collect()
        wait_for_disconnect()
        stage2_test()
        return 0
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 130
    except Exception as e:
        print(c(f"\nERROR: {e}", Colors.RED))
        log("FATAL: " + traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
