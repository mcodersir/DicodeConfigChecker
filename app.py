#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import base64
import concurrent.futures
import json
import os
import sys
import time
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import Any, Optional

from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer, QPropertyAnimation, QEasingCurve, QPointF
from PySide6.QtGui import QIcon, QPixmap, QFont, QAction, QPainter, QPen, QBrush, QColor, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

import engine

APP_TITLE = "Dicode Config Checker"
APP_VERSION = engine.VERSION


@dataclass
class RunSettings:
    per_channel_limit: int
    main_channel_limit: int
    main_channel: str
    fetch_workers: int
    fetch_timeout: float
    test_mode: str
    ping_attempts: int
    min_success: int
    ping_workers: int
    tcp_timeout: float
    socket_timeout: float
    xray_startup_wait: float
    xray_process_timeout: float
    check_url: str
    sub_tag_prefix: str
    rename_config_names: bool
    prefilter_enabled: bool
    prefilter_workers: int
    channels_text: str


class CheckerWorker(QThread):
    log_line = Signal(str)
    stage_text = Signal(str)
    progress = Signal(int, int)
    counters = Signal(int, int, int, int)
    ask_disconnect = Signal()
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, settings: RunSettings) -> None:
        super().__init__()
        self.settings = settings
        self._continue_event = Event()
        self._stop_requested = False

    def continue_after_disconnect(self) -> None:
        self._continue_event.set()

    def request_stop(self) -> None:
        self._stop_requested = True
        self._continue_event.set()

    def emit_log(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_line.emit(f"[{stamp}] {text}")

    def run(self) -> None:
        try:
            self.apply_runtime_settings()
            engine.ensure_files()
            engine.clear_old_outputs()

            self.stage_text.emit("آماده‌سازی Xray")
            self.progress.emit(0, 100)
            self.emit_log("اتصال فعلی را روشن نگه دارید؛ آماده‌سازی Xray شروع شد.")
            xray_path = engine.ensure_xray_binary()
            if xray_path:
                self.emit_log(f"Xray آماده است: {xray_path}")
            elif self.settings.test_mode == "xray":
                self.emit_log("Xray پیدا نشد؛ در حالت Xray-only تایید انجام نمی‌شود.")
            else:
                self.emit_log("Xray پیدا نشد؛ در حالت auto از TCP fallback استفاده می‌شود.")

            if self._stop_requested:
                return

            self.collect_stage1()
            if self._stop_requested:
                return

            self.stage_text.emit("منتظر قطع اتصال")
            self.emit_log("مرحله دریافت تمام شد. اتصال فعلی را کامل قطع کنید، سپس ادامه را بزنید.")
            self.ask_disconnect.emit()
            self._continue_event.wait()
            if self._stop_requested:
                return

            final_report = self.test_stage2(xray_path)
            self.finished_ok.emit(final_report)
        except Exception as exc:
            try:
                engine.log("GUI FATAL: " + repr(exc))
            except Exception:
                pass
            self.failed.emit(str(exc))

    def apply_runtime_settings(self) -> None:
        s = self.settings
        engine.PER_CHANNEL_LIMIT = s.per_channel_limit
        engine.MAIN_CHANNEL_LIMIT = s.main_channel_limit
        engine.MAIN_CHANNEL = s.main_channel.strip() or "persianvpnhub"
        engine.FETCH_WORKERS = s.fetch_workers
        engine.FETCH_TIMEOUT = s.fetch_timeout
        engine.TEST_MODE = s.test_mode
        engine.PING_ATTEMPTS = s.ping_attempts
        engine.MIN_SUCCESS = s.min_success
        engine.PING_WORKERS = s.ping_workers
        engine.TCP_TIMEOUT = s.tcp_timeout
        engine.SOCKET_TIMEOUT = s.socket_timeout
        engine.XRAY_STARTUP_WAIT = s.xray_startup_wait
        engine.XRAY_PROCESS_TIMEOUT = s.xray_process_timeout
        engine.CHECK_URL = s.check_url.strip() or "http://www.gstatic.com/generate_204"
        engine.SUB_TAG_PREFIX = s.sub_tag_prefix.strip() or "t.me/dicodeir"
        engine.RENAME_CONFIG_NAMES = bool(s.rename_config_names)

        channel_lines = self.normalize_channel_text(s.channels_text)
        engine.CHANNELS_FILE.write_text("\n".join(channel_lines) + "\n", encoding="utf-8")
        self.write_env_file(s)

    @staticmethod
    def normalize_channel_text(text: str) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for raw in text.replace(",", "\n").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            ch = engine.normalize_channel(line)
            if not ch:
                continue
            key = ch.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(f"t.me/{ch}")
        return out

    @staticmethod
    def write_env_file(s: RunSettings) -> None:
        text = f"""# Dicode Config Checker v1 settings
PER_CHANNEL_LIMIT={s.per_channel_limit}
MAIN_CHANNEL_LIMIT={s.main_channel_limit}
MAIN_CHANNEL={s.main_channel}
FETCH_WORKERS={s.fetch_workers}
FETCH_TIMEOUT={s.fetch_timeout}
TEST_MODE={s.test_mode}
AUTO_DOWNLOAD_XRAY=1
XRAY_PATH=core/xray.exe
XRAY_DOWNLOAD_TIMEOUT=90
XRAY_STARTUP_WAIT={s.xray_startup_wait}
XRAY_PROCESS_TIMEOUT={s.xray_process_timeout}
CHECK_URL={s.check_url}
PING_ATTEMPTS={s.ping_attempts}
MIN_SUCCESS={s.min_success}
PING_WORKERS={s.ping_workers}
TCP_FALLBACK_WORKERS=48
SOCKET_TIMEOUT={s.socket_timeout}
TCP_TIMEOUT={s.tcp_timeout}
ATTEMPT_GAP_SECONDS=0.12
SUB_TAG_PREFIX={s.sub_tag_prefix}
RENAME_CONFIG_NAMES={1 if s.rename_config_names else 0}
WRITE_DEAD_TO_REPORT=1
"""
        engine.ENV_FILE.write_text(text, encoding="utf-8")

    def collect_stage1(self) -> dict[str, Any]:
        self.stage_text.emit("دریافت از تلگرام")
        channels = engine.read_channels()
        total = max(len(channels), 1)
        self.progress.emit(0, total)
        self.emit_log(f"کانال‌ها: {len(channels)} | هر کانال: {engine.PER_CHANNEL_LIMIT} | اصلی: {engine.MAIN_CHANNEL_LIMIT}")

        results: list[dict[str, Any]] = []
        collected: list[dict[str, str]] = []
        seen: set[str] = set()
        start = time.time()
        done = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=engine.FETCH_WORKERS) as ex:
            future_map = {ex.submit(engine.fetch_channel, ch): ch for ch in channels}
            for fut in concurrent.futures.as_completed(future_map):
                if self._stop_requested:
                    break
                res = fut.result()
                results.append(res)
                done += 1
                status = "OK" if res.get("ok") else "FAIL"
                self.emit_log(f"{status} @{res['channel']} | found={res['found']} | picked={res['picked']} | {res['elapsed_ms']}ms")
                for cfg in res.get("configs", []):
                    key = engine.normalize_config_key(cfg)
                    if key in seen:
                        continue
                    seen.add(key)
                    collected.append({"source": res["channel"], "raw": cfg})
                self.progress.emit(done, total)
                self.counters.emit(0, 0, 0, 0)

        elapsed = int(time.time() - start)
        lines = [x["raw"] for x in collected]
        engine.STAGE1_FILE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        meta = {
            "generated_at": engine.now_iso(),
            "stage": 1,
            "channels": len(channels),
            "per_channel_limit": engine.PER_CHANNEL_LIMIT,
            "main_channel": engine.MAIN_CHANNEL,
            "main_channel_limit": engine.MAIN_CHANNEL_LIMIT,
            "unique_configs": len(lines),
            "elapsed_seconds": elapsed,
            "results": results,
            "collected": collected,
        }
        engine.STAGE1_META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self.emit_log(f"مرحله اول تمام شد: {len(lines)} کانفیگ یکتا در all_configs_stage1.txt ذخیره شد.")
        return meta

    def tcp_prefilter(self, endpoints: list[Any]) -> tuple[list[Any], list[Any]]:
        if not self.settings.prefilter_enabled:
            return endpoints, []
        self.stage_text.emit("پیش‌فیلتر TCP")
        self.emit_log("اول TCP سریع اجرا می‌شود تا تست Xray روی سرورهای مرده انجام نشود.")
        total = max(len(endpoints), 1)
        kept: list[Any] = []
        rejected: list[Any] = []
        done = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.settings.prefilter_workers) as ex:
            futs = {ex.submit(engine.tcp_connect_delay_ms, ep.host, ep.port, min(engine.TCP_TIMEOUT, 2.2)): ep for ep in endpoints}
            for fut in concurrent.futures.as_completed(futs):
                ep = futs[fut]
                ms, _ = fut.result()
                if ms is not None:
                    kept.append(ep)
                else:
                    rejected.append(ep)
                done += 1
                self.progress.emit(done, total)
                if done % 10 == 0 or done == total:
                    self.emit_log(f"Prefilter {done}/{total} | قابل تست={len(kept)} | رد شده={len(rejected)}")
        return kept, rejected

    def test_stage2(self, xray_path: Optional[Path]) -> dict[str, Any]:
        self.stage_text.emit("تست واقعی")
        items = engine.read_stage1_configs()
        endpoints: list[Any] = []
        unsupported: list[str] = []

        for item in items:
            ep = engine.parse_endpoint(item["raw"], item.get("source", "stage1"))
            if ep:
                endpoints.append(ep)
            else:
                unsupported.append(item["raw"])

        self.emit_log(f"خوانده‌شده: {len(items)} | قابل تست: {len(endpoints)} | پشتیبانی‌نشده: {len(unsupported)}")
        endpoints, prefiltered_dead = self.tcp_prefilter(endpoints)

        total = max(len(endpoints), 1)
        self.progress.emit(0, total)
        results: list[Any] = []
        done = 0
        dead_count = len(prefiltered_dead)
        start = time.time()

        prefilter_results = [
            engine.TestResult(
                raw=ep.raw,
                source=ep.source,
                kind=ep.kind,
                protocol=ep.protocol,
                host=ep.host,
                port=ep.port,
                ok=False,
                ping_ms=None,
                min_ms=None,
                avg_ms=None,
                attempts=1,
                success_count=0,
                samples_ms=[],
                tester="tcp-prefilter",
                error="tcp_prefilter_failed",
            )
            for ep in prefiltered_dead
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=engine.PING_WORKERS) as ex:
            futs = [ex.submit(engine.repeated_test, ep, xray_path) for ep in endpoints]
            for fut in concurrent.futures.as_completed(futs):
                if self._stop_requested:
                    break
                res = fut.result()
                results.append(res)
                done += 1
                if res.ok:
                    self.emit_log(f"OK {res.protocol} {res.host}:{res.port} | {engine.fmt_ms(res.ping_ms)} | {res.success_count}/{res.attempts} | {res.tester}")
                else:
                    dead_count += 1
                alive_configs_live = len([r for r in results if r.ok and r.kind != "mtproto"])
                alive_proxies_live = len([r for r in results if r.ok and r.kind == "mtproto"])
                self.progress.emit(done, total)
                self.counters.emit(alive_configs_live, alive_proxies_live, dead_count, len(unsupported))

        results.extend(prefilter_results)
        elapsed = int(time.time() - start)
        alive = sorted([r for r in results if r.ok], key=lambda r: r.ping_ms if r.ping_ms is not None else 999999)
        dead = [r for r in results if not r.ok]

        alive_configs = [r for r in alive if r.kind != "mtproto"]
        alive_proxies = [r for r in alive if r.kind == "mtproto"]
        dead_configs = [r for r in dead if r.kind != "mtproto"]
        dead_proxies = [r for r in dead if r.kind == "mtproto"]

        renamed_config_items: list[tuple[int, Any, str, str]] = []
        for idx, r in enumerate(alive_configs, 1):
            if engine.RENAME_CONFIG_NAMES:
                display_name = f"{engine.SUB_TAG_PREFIX}-{idx}"
                output_raw = engine.set_config_display_name(r.raw, display_name)
            else:
                display_name = engine.get_config_display_name(r.raw) or f"original-{idx}"
                output_raw = r.raw
            renamed_config_items.append((idx, r, output_raw, display_name))

        sub_lines = [x[2] for x in renamed_config_items]
        proxy_lines = [r.raw for r in alive_proxies]
        engine.SUB_FILE.write_text("\n".join(sub_lines) + ("\n" if sub_lines else ""), encoding="utf-8")
        engine.SUB_BASE64_FILE.write_text(base64.b64encode(("\n".join(sub_lines)).encode("utf-8")).decode("ascii"), encoding="utf-8")
        engine.PROXY_FILE.write_text("\n".join(proxy_lines) + ("\n" if proxy_lines else ""), encoding="utf-8")
        engine.PROXY_BASE64_FILE.write_text(base64.b64encode(("\n".join(proxy_lines)).encode("utf-8")).decode("ascii"), encoding="utf-8")

        engine.write_reports(renamed_config_items, alive_proxies, dead_configs, dead_proxies, unsupported, elapsed, xray_path)

        full = {
            "generated_at": engine.now_iso(),
            "version": APP_VERSION,
            "mode": "gui-two-stage-xray-real-delay",
            "settings": {
                "per_channel_limit": engine.PER_CHANNEL_LIMIT,
                "main_channel_limit": engine.MAIN_CHANNEL_LIMIT,
                "main_channel": engine.MAIN_CHANNEL,
                "rename_config_names": engine.RENAME_CONFIG_NAMES,
                "sub_tag_prefix": engine.SUB_TAG_PREFIX,
                "test_mode": engine.TEST_MODE,
                "prefilter_enabled": self.settings.prefilter_enabled,
                "xray_path": str(xray_path) if xray_path else None,
                "check_url": engine.CHECK_URL,
                "attempts": engine.PING_ATTEMPTS,
                "min_success": engine.MIN_SUCCESS,
                "ping_workers": engine.PING_WORKERS,
            },
            "stats": {
                "loaded": len(items),
                "testable_after_prefilter": len(endpoints),
                "prefilter_rejected": len(prefiltered_dead),
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
            "dead_configs": [asdict(r) for r in dead_configs] if engine.WRITE_DEAD_TO_REPORT else [],
            "dead_telegram_proxies": [asdict(r) for r in dead_proxies] if engine.WRITE_DEAD_TO_REPORT else [],
            "unsupported": unsupported if engine.WRITE_DEAD_TO_REPORT else [],
        }
        engine.REPORT_FILE.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")
        self.counters.emit(len(alive_configs), len(alive_proxies), len(dead), len(unsupported))
        self.emit_log(f"تمام شد: sub.txt={len(alive_configs)} | proxy.txt={len(alive_proxies)} | dead={len(dead)} | unsupported={len(unsupported)}")
        return full


def resource_path(*parts: str) -> Path:
    root_candidate = engine.ROOT.joinpath(*parts)
    if root_candidate.exists():
        return root_candidate
    bundle_candidate = engine.BUNDLE_DIR.joinpath(*parts)
    if bundle_candidate.exists():
        return bundle_candidate
    return root_candidate



class LogoMark(QWidget):
    def __init__(self, size: int = 44) -> None:
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(2, 2, -2, -2)
        painter.setPen(QPen(QColor("#24527a"), 1.4))
        painter.setBrush(QBrush(QColor("#07101b")))
        painter.drawRoundedRect(r, 12, 12)
        inner = self.rect().adjusted(9, 9, -9, -9)
        painter.setPen(QPen(QColor("#2a9fff"), 1.2))
        painter.setBrush(QBrush(QColor("#0d2134")))
        painter.drawRoundedRect(inner, 8, 8)
        w = self.width()
        h = self.height()
        bolt = QPolygonF([
            QPointF(w * 0.55, h * 0.18),
            QPointF(w * 0.34, h * 0.52),
            QPointF(w * 0.50, h * 0.52),
            QPointF(w * 0.43, h * 0.82),
            QPointF(w * 0.68, h * 0.44),
            QPointF(w * 0.51, h * 0.44),
        ])
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#68e8ff")))
        painter.drawPolygon(bolt)

class IconButton(QPushButton):
    def __init__(self, text: str, icon_name: str = "", primary: bool = False) -> None:
        super().__init__(text)
        if icon_name:
            icon_path = resource_path("assets", f"{icon_name}.svg")
            if icon_path.exists():
                self.setIcon(QIcon(str(icon_path)))
                self.setIconSize(QSize(18, 18))
        if primary:
            self.setObjectName("PrimaryButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)


class NavButton(QToolButton):
    def __init__(self, text: str, icon_name: str, index: int) -> None:
        super().__init__()
        self.index = index
        self.setText(text)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        icon_path = resource_path("assets", f"{icon_name}.svg")
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        self.setIconSize(QSize(20, 20))
        self.setMinimumHeight(44)


class StatCard(QFrame):
    def __init__(self, title: str, icon_name: str) -> None:
        super().__init__()
        self.setObjectName("StatCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        icon = QLabel()
        icon.setObjectName("CardIcon")
        icon.setFixedSize(38, 38)
        icon.setAlignment(Qt.AlignCenter)
        icon_path = resource_path("assets", f"{icon_name}.svg")
        if icon_path.exists():
            icon.setPixmap(QPixmap(str(icon_path)).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        text_box = QVBoxLayout()
        self.value = QLabel("0")
        self.value.setObjectName("CardValue")
        label = QLabel(title)
        label.setObjectName("CardLabel")
        text_box.addWidget(self.value)
        text_box.addWidget(label)
        layout.addWidget(icon)
        layout.addLayout(text_box, 1)

    def set_value(self, value: int | str) -> None:
        self.value.setText(str(value))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: Optional[CheckerWorker] = None
        self.compact_nav = False
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.setMinimumSize(980, 680)
        icon_path = resource_path("assets", "app.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.build_ui()
        self.load_initial_values()
        self.apply_style()
        self.update_channel_count()
        QTimer.singleShot(80, self.apply_responsive_mode)

    def build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(14)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(176)
        nav_layout = QVBoxLayout(self.sidebar)
        nav_layout.setContentsMargins(12, 12, 12, 12)
        nav_layout.setSpacing(8)

        brand = QFrame()
        brand.setObjectName("BrandBox")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(10, 10, 10, 10)
        self.brand_icon = LogoMark(44)
        self.brand_text = QLabel("Dicode\nChecker")
        self.brand_text.setObjectName("BrandText")
        brand_layout.addWidget(self.brand_icon)
        brand_layout.addWidget(self.brand_text, 1)
        nav_layout.addWidget(brand)

        self.nav_dashboard = NavButton("داشبورد", "dashboard", 0)
        self.nav_settings = NavButton("تنظیمات", "sliders", 1)
        self.nav_channels = NavButton("کانال‌ها", "list", 2)
        self.nav_dashboard.setChecked(True)
        for btn in (self.nav_dashboard, self.nav_settings, self.nav_channels):
            nav_layout.addWidget(btn)
            btn.clicked.connect(lambda checked=False, b=btn: self.switch_page(b.index))

        nav_layout.addStretch(1)
        self.btn_open_side = IconButton("پوشه خروجی", "folder")
        self.btn_open_side.clicked.connect(self.open_output_folder)
        nav_layout.addWidget(self.btn_open_side)
        outer.addWidget(self.sidebar)

        main = QFrame()
        main.setObjectName("MainPanel")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)
        outer.addWidget(main, 1)

        header = QFrame()
        header.setObjectName("TopHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(12)
        self.header_logo = LogoMark(42)
        header_layout.addWidget(self.header_logo)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        self.title_label = QLabel("Dicode Config Checker")
        self.title_label.setObjectName("Title")
        self.subtitle_label = QLabel("جمع‌آوری کانفیگ، تست واقعی با Xray و ساخت sub.txt / proxy.txt")
        self.subtitle_label.setObjectName("Subtitle")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        header_layout.addLayout(title_box, 1)
        self.stage_label = QLabel("آماده")
        self.stage_label.setObjectName("StagePill")
        self.stage_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.stage_label)
        main_layout.addWidget(header)

        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages, 1)
        self.build_dashboard_page()
        self.build_settings_page()
        self.build_channels_page()

    def build_dashboard_page(self) -> None:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(14)

        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(12)
        self.card_alive_configs = StatCard("کانفیگ سالم", "check")
        self.card_alive_proxies = StatCard("پروکسی سالم", "bolt")
        self.card_dead = StatCard("ناموفق", "x")
        self.card_unsupported = StatCard("پشتیبانی‌نشده", "alert")
        self.stat_cards = [self.card_alive_configs, self.card_alive_proxies, self.card_dead, self.card_unsupported]
        for i, card in enumerate(self.stat_cards):
            self.cards_grid.addWidget(card, 0, i)
        page_layout.addLayout(self.cards_grid)

        progress_panel = QFrame()
        progress_panel.setObjectName("Panel")
        pp = QVBoxLayout(progress_panel)
        pp.setContentsMargins(16, 14, 16, 14)
        pp.setSpacing(10)
        top = QHBoxLayout()
        self.progress_title = QLabel("وضعیت اجرا")
        self.progress_title.setObjectName("SectionTitle")
        self.progress_meta = QLabel("برای شروع روی دکمه شروع بزن")
        self.progress_meta.setObjectName("Muted")
        top.addWidget(self.progress_title)
        top.addStretch(1)
        top.addWidget(self.progress_meta)
        pp.addLayout(top)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_anim = QPropertyAnimation(self.progress_bar, b"value", self)
        self.progress_anim.setDuration(260)
        self.progress_anim.setEasingCurve(QEasingCurve.OutCubic)
        pp.addWidget(self.progress_bar)
        page_layout.addWidget(progress_panel)

        log_panel = QFrame()
        log_panel.setObjectName("Panel")
        lp = QVBoxLayout(log_panel)
        lp.setContentsMargins(16, 14, 16, 14)
        lp.setSpacing(10)
        log_header = QHBoxLayout()
        log_title = QLabel("لاگ زنده")
        log_title.setObjectName("SectionTitle")
        self.btn_clear_log = IconButton("پاک کردن", "trash")
        self.btn_clear_log.clicked.connect(lambda: self.log_box.clear())
        log_header.addWidget(log_title)
        log_header.addStretch(1)
        log_header.addWidget(self.btn_clear_log)
        lp.addLayout(log_header)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setObjectName("LogBox")
        lp.addWidget(self.log_box, 1)
        page_layout.addWidget(log_panel, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.btn_start = IconButton("شروع بررسی", "play", primary=True)
        self.btn_continue = IconButton("ادامه بعد از قطع اتصال", "next")
        self.btn_continue.setEnabled(False)
        self.btn_stop = IconButton("توقف", "stop")
        self.btn_open = IconButton("پوشه خروجی", "folder")
        actions.addWidget(self.btn_start, 2)
        actions.addWidget(self.btn_continue, 2)
        actions.addWidget(self.btn_stop, 1)
        actions.addWidget(self.btn_open, 1)
        page_layout.addLayout(actions)

        self.btn_start.clicked.connect(self.start_run)
        self.btn_continue.clicked.connect(self.continue_run)
        self.btn_stop.clicked.connect(self.stop_run)
        self.btn_open.clicked.connect(self.open_output_folder)
        self.pages.addWidget(page)

    def build_settings_page(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("TransparentScroll")
        page = QWidget()
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(14)

        header = self.page_header("تنظیمات قبل از شروع", "عددها را قبل از اجرای تست تغییر بده؛ همه تنظیمات در .env ذخیره می‌شوند.", "sliders")
        layout.addWidget(header)

        box = QFrame()
        box.setObjectName("Panel")
        grid = QGridLayout(box)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        layout.addWidget(box)

        self.per_channel = self.spin(1, 200, 20)
        self.main_limit = self.spin(1, 300, 30)
        self.fetch_workers = self.spin(1, 64, 10)
        self.ping_workers = self.spin(1, 32, 4)
        self.attempts = self.spin(1, 6, 2)
        self.min_success = self.spin(1, 6, 1)
        self.prefilter_workers = self.spin(1, 128, 64)
        self.main_channel = QLineEdit("persianvpnhub")
        self.test_mode = QComboBox()
        self.test_mode.addItems(["auto", "xray", "tcp"])
        self.check_url = QLineEdit("http://www.gstatic.com/generate_204")
        self.tag_prefix = QLineEdit("t.me/dicodeir")
        self.rename_names = QCheckBox("بازنویسی نام کانفیگ بعد از #")
        self.rename_names.setChecked(True)
        self.rename_names.setToolTip("اگر خاموش باشد، نام اصلی کانفیگ‌ها حفظ می‌شود. اگر روشن باشد، متن زیر با شماره‌گذاری اعمال می‌شود.")
        self.prefilter = QCheckBox("پیش‌فیلتر سریع TCP قبل از Xray")
        self.prefilter.setChecked(True)

        row = 0
        self.add_field(grid, row, 0, "تعداد هر کانال", self.per_channel)
        self.add_field(grid, row, 1, "تعداد کانال اصلی", self.main_limit)
        self.add_field(grid, row, 2, "نام کانال اصلی", self.main_channel)
        row += 1
        self.add_field(grid, row, 0, "Fetch workers", self.fetch_workers)
        self.add_field(grid, row, 1, "Ping workers", self.ping_workers)
        self.add_field(grid, row, 2, "Prefilter workers", self.prefilter_workers)
        row += 1
        self.add_field(grid, row, 0, "تعداد تلاش", self.attempts)
        self.add_field(grid, row, 1, "حداقل موفقیت", self.min_success)
        self.add_field(grid, row, 2, "حالت تست", self.test_mode)
        row += 1
        self.add_field(grid, row, 0, "متن نام کانفیگ", self.tag_prefix)
        self.add_field(grid, row, 1, "URL تست", self.check_url, colspan=2)
        row += 1
        grid.addWidget(self.rename_names, row, 0, 1, 3)
        row += 1
        grid.addWidget(self.prefilter, row, 0, 1, 3)

        hint = QLabel("پیشنهاد Release: حالت auto، پیش‌فیلتر روشن، Ping workers روی 4، تعداد تلاش 2. اگر کیفیت مهم‌تر از زمان است، تلاش را 3 یا 4 کن.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        self.attempts.valueChanged.connect(self.fix_min_success)
        self.rename_names.toggled.connect(self.tag_prefix.setEnabled)
        self.tag_prefix.setEnabled(self.rename_names.isChecked())
        self.pages.addWidget(scroll)

    def build_channels_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        header = self.page_header("لیست کانال‌ها", "هر خط یک کانال؛ لینک t.me یا یوزرنیم ساده را می‌پذیرد.", "list")
        layout.addWidget(header)

        toolbar = QFrame()
        toolbar.setObjectName("Panel")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(14, 12, 14, 12)
        tb.setSpacing(10)
        self.channel_count = QLabel("0 کانال")
        self.channel_count.setObjectName("StagePill")
        self.btn_save_channels = IconButton("ذخیره", "save", primary=True)
        self.btn_dedupe = IconButton("پاکسازی تکراری", "clean")
        self.btn_default = IconButton("پیش‌فرض", "reset")
        self.btn_load_file = IconButton("واردکردن فایل", "import")
        tb.addWidget(self.channel_count)
        tb.addStretch(1)
        tb.addWidget(self.btn_save_channels)
        tb.addWidget(self.btn_dedupe)
        tb.addWidget(self.btn_default)
        tb.addWidget(self.btn_load_file)
        layout.addWidget(toolbar)

        editor_panel = QFrame()
        editor_panel.setObjectName("Panel")
        ep = QVBoxLayout(editor_panel)
        ep.setContentsMargins(14, 14, 14, 14)
        self.channels_editor = QPlainTextEdit()
        self.channels_editor.setPlaceholderText("هر خط یک کانال. مثال:\nt.me/v2rayngvpn\nConfigX2ray")
        self.channels_editor.textChanged.connect(self.update_channel_count)
        ep.addWidget(self.channels_editor, 1)
        layout.addWidget(editor_panel, 1)

        self.btn_save_channels.clicked.connect(self.save_channels_from_editor)
        self.btn_dedupe.clicked.connect(self.dedupe_channels)
        self.btn_default.clicked.connect(self.load_default_channels)
        self.btn_load_file.clicked.connect(self.import_channels_file)
        self.pages.addWidget(page)

    def page_header(self, title: str, subtitle: str, icon_name: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("PageHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        icon = QLabel()
        icon.setObjectName("LargeIcon")
        icon.setFixedSize(44, 44)
        icon.setAlignment(Qt.AlignCenter)
        icon_path = resource_path("assets", f"{icon_name}.svg")
        if icon_path.exists():
            icon.setPixmap(QPixmap(str(icon_path)).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        texts = QVBoxLayout()
        t = QLabel(title)
        t.setObjectName("PageTitle")
        s = QLabel(subtitle)
        s.setObjectName("Subtitle")
        s.setWordWrap(True)
        texts.addWidget(t)
        texts.addWidget(s)
        layout.addWidget(icon)
        layout.addLayout(texts, 1)
        return frame

    @staticmethod
    def spin(minimum: int, maximum: int, value: int) -> QSpinBox:
        s = QSpinBox()
        s.setRange(minimum, maximum)
        s.setValue(value)
        s.setMinimumHeight(42)
        s.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        s.setAlignment(Qt.AlignCenter)
        s.setCursor(Qt.PointingHandCursor)
        return s

    @staticmethod
    def add_field(grid: QGridLayout, row: int, col: int, label_text: str, widget: QWidget, colspan: int = 1) -> None:
        wrapper = QFrame()
        wrapper.setObjectName("FieldBox")
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        lay.addWidget(label)
        lay.addWidget(widget)
        grid.addWidget(wrapper, row, col, 1, colspan)

    def switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        page = self.pages.currentWidget()
        if page is not None:
            effect = QGraphicsOpacityEffect(page)
            page.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(180)
            anim.setStartValue(0.82)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.finished.connect(lambda p=page: p.setGraphicsEffect(None))
            self._page_anim = anim
            anim.start()
        for btn in (self.nav_dashboard, self.nav_settings, self.nav_channels):
            btn.setChecked(btn.index == index)

    def fix_min_success(self) -> None:
        if self.min_success.value() > self.attempts.value():
            self.min_success.setValue(self.attempts.value())
        self.min_success.setMaximum(self.attempts.value())

    def load_initial_values(self) -> None:
        engine.ensure_files()
        if engine.CHANNELS_FILE.exists():
            self.channels_editor.setPlainText(engine.CHANNELS_FILE.read_text(encoding="utf-8", errors="ignore"))
        else:
            self.load_default_channels()
        self.per_channel.setValue(getattr(engine, "PER_CHANNEL_LIMIT", 20))
        self.main_limit.setValue(getattr(engine, "MAIN_CHANNEL_LIMIT", 30))
        self.fetch_workers.setValue(getattr(engine, "FETCH_WORKERS", 8))
        self.ping_workers.setValue(getattr(engine, "PING_WORKERS", 4))
        self.attempts.setValue(min(max(getattr(engine, "PING_ATTEMPTS", 2), 1), 6))
        self.min_success.setValue(min(max(getattr(engine, "MIN_SUCCESS", 1), 1), self.attempts.value()))
        self.main_channel.setText(getattr(engine, "MAIN_CHANNEL", "persianvpnhub"))
        idx = self.test_mode.findText(getattr(engine, "TEST_MODE", "auto"))
        self.test_mode.setCurrentIndex(idx if idx >= 0 else 0)
        self.check_url.setText(getattr(engine, "CHECK_URL", "http://www.gstatic.com/generate_204"))
        self.tag_prefix.setText(getattr(engine, "SUB_TAG_PREFIX", "t.me/dicodeir"))
        self.rename_names.setChecked(bool(getattr(engine, "RENAME_CONFIG_NAMES", True)))
        self.fix_min_success()

    def load_default_channels(self) -> None:
        self.channels_editor.setPlainText(engine.DEFAULT_CHANNELS.strip())
        self.update_channel_count()

    def save_channels_from_editor(self) -> None:
        lines = CheckerWorker.normalize_channel_text(self.channels_editor.toPlainText())
        engine.CHANNELS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.channels_editor.setPlainText("\n".join(lines))
        self.update_channel_count()
        self.append_log(f"لیست کانال‌ها ذخیره شد: {len(lines)} مورد")

    def dedupe_channels(self) -> None:
        lines = CheckerWorker.normalize_channel_text(self.channels_editor.toPlainText())
        self.channels_editor.setPlainText("\n".join(lines))
        self.update_channel_count()
        self.append_log(f"لیست پاکسازی شد: {len(lines)} کانال یکتا")

    def import_channels_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل کانال‌ها", str(engine.ROOT), "Text files (*.txt);;All files (*.*)")
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        current = self.channels_editor.toPlainText().strip()
        merged = (current + "\n" + text).strip() if current else text
        self.channels_editor.setPlainText(merged)
        self.dedupe_channels()

    def update_channel_count(self) -> None:
        if not hasattr(self, "channel_count"):
            return
        lines = CheckerWorker.normalize_channel_text(self.channels_editor.toPlainText())
        self.channel_count.setText(f"{len(lines)} کانال")

    def current_settings(self) -> RunSettings:
        return RunSettings(
            per_channel_limit=self.per_channel.value(),
            main_channel_limit=self.main_limit.value(),
            main_channel=self.main_channel.text().strip() or "persianvpnhub",
            fetch_workers=self.fetch_workers.value(),
            fetch_timeout=15.0,
            test_mode=self.test_mode.currentText(),
            ping_attempts=self.attempts.value(),
            min_success=self.min_success.value(),
            ping_workers=self.ping_workers.value(),
            tcp_timeout=4.0,
            socket_timeout=8.0,
            xray_startup_wait=1.0,
            xray_process_timeout=14.0,
            check_url=self.check_url.text().strip() or "http://www.gstatic.com/generate_204",
            sub_tag_prefix=self.tag_prefix.text().strip() or "t.me/dicodeir",
            rename_config_names=self.rename_names.isChecked(),
            prefilter_enabled=self.prefilter.isChecked(),
            prefilter_workers=self.prefilter_workers.value(),
            channels_text=self.channels_editor.toPlainText(),
        )

    def start_run(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.save_channels_from_editor()
        self.log_box.clear()
        self.switch_page(0)
        self.set_running(True)
        self.btn_continue.setEnabled(False)
        self.update_counters(0, 0, 0, 0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")
        self.progress_meta.setText("شروع شد")
        self.worker = CheckerWorker(self.current_settings())
        self.worker.log_line.connect(self.append_log)
        self.worker.stage_text.connect(self.set_stage)
        self.worker.progress.connect(self.update_progress)
        self.worker.counters.connect(self.update_counters)
        self.worker.ask_disconnect.connect(self.on_ask_disconnect)
        self.worker.finished_ok.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def continue_run(self) -> None:
        if self.worker:
            self.btn_continue.setEnabled(False)
            self.append_log("ادامه تست شروع شد.")
            self.worker.continue_after_disconnect()

    def stop_run(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.request_stop()
            self.append_log("درخواست توقف ثبت شد.")
            self.set_running(False)

    def set_running(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.nav_settings.setEnabled(not running)
        self.nav_channels.setEnabled(not running)

    def on_ask_disconnect(self) -> None:
        self.btn_continue.setEnabled(True)
        self.progress_meta.setText("منتظر ادامه")
        QMessageBox.information(
            self,
            "مرحله دوم",
            "کانفیگ/فیلترشکن فعلی را کامل قطع کن. بعد داخل برنامه روی ادامه بزن تا تست واقعی از اینترنت خودت انجام شود.",
        )

    def on_finished(self, report: dict) -> None:
        self.set_running(False)
        self.btn_continue.setEnabled(False)
        self.set_stage("تمام شد")
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_meta.setText("خروجی ساخته شد")
        stats = report.get("stats", {})
        QMessageBox.information(
            self,
            "خروجی ساخته شد",
            f"sub.txt: {stats.get('alive_configs', 0)} کانفیگ\nproxy.txt: {stats.get('alive_telegram_proxies', 0)} پروکسی\nناموفق: {stats.get('dead_total', 0)}",
        )

    def on_failed(self, error: str) -> None:
        self.set_running(False)
        self.btn_continue.setEnabled(False)
        self.set_stage("خطا")
        self.progress_meta.setText("خطا")
        self.append_log(f"ERROR: {error}")
        QMessageBox.critical(self, "خطا", error)

    def set_stage(self, text: str) -> None:
        self.stage_label.setText(text)
        self.progress_title.setText(text)

    def update_progress(self, done: int, total: int) -> None:
        total = max(total, 1)
        value = min(done, total)
        self.progress_bar.setRange(0, total)
        percent = int((value / total) * 100)
        self.progress_bar.setFormat(f"{percent}%  |  {done}/{total}")
        self.progress_meta.setText(f"{done}/{total}")
        if hasattr(self, "progress_anim"):
            self.progress_anim.stop()
            self.progress_anim.setStartValue(self.progress_bar.value())
            self.progress_anim.setEndValue(value)
            self.progress_anim.start()
        else:
            self.progress_bar.setValue(value)

    def update_counters(self, alive_configs: int, alive_proxies: int, dead: int, unsupported: int) -> None:
        self.card_alive_configs.set_value(alive_configs)
        self.card_alive_proxies.set_value(alive_proxies)
        self.card_dead.set_value(dead)
        self.card_unsupported.set_value(unsupported)

    def append_log(self, line: str) -> None:
        if not hasattr(self, "log_box"):
            return
        self.log_box.append(line)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def open_output_folder(self) -> None:
        path = str(engine.ROOT)
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            webbrowser.open(f"file://{path}")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.apply_responsive_mode()

    def apply_responsive_mode(self) -> None:
        width = self.width()
        compact = width < 1120
        if compact != self.compact_nav:
            self.compact_nav = compact
            self.sidebar.setFixedWidth(74 if compact else 176)
            self.brand_text.setVisible(not compact)
            self.btn_open_side.setText("" if compact else "پوشه خروجی")
            for btn, text in (
                (self.nav_dashboard, "داشبورد"),
                (self.nav_settings, "تنظیمات"),
                (self.nav_channels, "کانال‌ها"),
            ):
                btn.setText("" if compact else text)
                btn.setToolButtonStyle(Qt.ToolButtonIconOnly if compact else Qt.ToolButtonTextBesideIcon)
        # Cards become 2x2 on narrower windows.
        columns = 2 if width < 1240 else 4
        for i, card in enumerate(self.stat_cards):
            self.cards_grid.removeWidget(card)
            self.cards_grid.addWidget(card, i // columns, i % columns)

    def apply_style(self) -> None:
        app_instance = QApplication.instance()
        if app_instance is not None:
            app_instance.setFont(QFont("Vazirmatn", 10))
        self.setLayoutDirection(Qt.LeftToRight)
        self.setStyleSheet("""
            * {
                outline: none;
            }
            QWidget {
                background: transparent;
                color: #eef6ff;
                font-family: Vazirmatn, Vazir, Segoe UI, Arial;
                font-size: 13px;
            }
            QLabel, QFrame > QLabel, QWidget > QLabel {
                background: transparent;
            }
            #AppRoot {
                background: #020409;
            }
            #Sidebar {
                background: #050912;
                border: 1px solid #132033;
                border-radius: 22px;
            }
            #BrandBox {
                background: #070d17;
                border: 1px solid #17263c;
                border-radius: 18px;
            }
            #BrandText {
                font-size: 15px;
                font-weight: 900;
                line-height: 120%;
                color: #ffffff;
            }
            #MainPanel {
                background: #04070d;
                border: 1px solid #101b2b;
                border-radius: 24px;
            }
            #TopHeader, #PageHeader, #Panel, #StatCard {
                background: #070b13;
                border: 1px solid #152238;
                border-radius: 20px;
            }
            QStackedWidget, QStackedWidget > QWidget, QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
                background: transparent;
                border: none;
            }
            #Title {
                font-size: 24px;
                font-weight: 900;
                color: #ffffff;
                background: transparent;
            }
            #PageTitle {
                font-size: 20px;
                font-weight: 900;
                color: #ffffff;
                background: transparent;
            }
            #Subtitle, #Muted, #CardLabel, #FieldLabel {
                color: #8fa3bd;
                font-size: 12px;
                background: transparent;
            }
            #SectionTitle {
                color: #f2f8ff;
                font-size: 15px;
                font-weight: 900;
                background: transparent;
            }
            #StagePill {
                background: #081729;
                color: #76e9ff;
                border: 1px solid #1e5a83;
                border-radius: 14px;
                padding: 8px 13px;
                font-weight: 900;
            }
            #CardIcon, #LargeIcon {
                background: #081a2d;
                border: 1px solid #1f5d87;
                border-radius: 13px;
            }
            #CardValue {
                color: #70e8ff;
                font-size: 27px;
                font-weight: 900;
                background: transparent;
            }
            #FieldBox {
                background: #050912;
                border: 1px solid #14233a;
                border-radius: 16px;
            }
            QToolButton {
                background: transparent;
                color: #9fb2c9;
                border: 1px solid transparent;
                border-radius: 14px;
                padding: 9px 10px;
                text-align: left;
                font-weight: 900;
            }
            QToolButton:hover {
                background: #0b1422;
                border-color: #1d314d;
                color: #ffffff;
            }
            QToolButton:checked {
                background: #0d2949;
                border-color: #2a75bd;
                color: #ffffff;
            }
            QPushButton {
                background: #0b1422;
                border: 1px solid #1b2d47;
                border-radius: 14px;
                padding: 10px 14px;
                color: #eff7ff;
                font-weight: 900;
            }
            QPushButton:hover {
                background: #101d31;
                border-color: #30608f;
            }
            QPushButton:pressed {
                background: #07101c;
                padding-top: 11px;
                padding-bottom: 9px;
            }
            QPushButton:disabled {
                color: #536278;
                border-color: #111b2b;
                background: #060a11;
            }
            QPushButton#PrimaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1f6feb, stop:0.55 #00aaff, stop:1 #37f5d0);
                border: 1px solid #58b8ff;
                color: white;
            }
            QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
                background: #03060b;
                border: 1px solid #172842;
                border-radius: 12px;
                padding: 9px;
                color: #f2f8ff;
                selection-background-color: #1f6feb;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
                border-color: #2f9fff;
                background: #050a12;
            }
            QSpinBox {
                padding-right: 9px;
                padding-left: 9px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
            }
            QComboBox::drop-down {
                width: 28px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background: #050912;
                border: 1px solid #1f3552;
                color: #eef6ff;
                selection-background-color: #0d2949;
                outline: none;
            }
            QTextEdit#LogBox, QPlainTextEdit {
                font-family: Consolas, Vazirmatn, monospace;
                font-size: 12px;
                line-height: 145%;
            }
            QProgressBar {
                background: #03060b;
                border: 1px solid #18304d;
                border-radius: 14px;
                min-height: 30px;
                text-align: center;
                font-weight: 900;
                color: #ffffff;
            }
            QProgressBar::chunk {
                border-radius: 13px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f6feb, stop:0.45 #00b7ff, stop:1 #4dffd8);
            }
            QCheckBox {
                color: #dcecff;
                font-weight: 900;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 1px solid #2a496e;
                background: #03060b;
            }
            QCheckBox::indicator:checked {
                background: #0f7cff;
                border: 1px solid #76e9ff;
            }
            #Hint {
                background: #070b13;
                border: 1px solid #152238;
                border-radius: 16px;
                color: #9fb2ce;
                padding: 14px;
            }
            QScrollBar:vertical {
                background: #03060b;
                width: 10px;
                margin: 0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #1b2d47;
                border-radius: 5px;
                min-height: 34px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2a496e;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                height: 0;
                background: transparent;
            }
            QMessageBox {
                background: #050912;
            }
        """)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
