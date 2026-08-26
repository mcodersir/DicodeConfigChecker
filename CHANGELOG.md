# Changelog

## 2.0.0 — 2026-08-26

### Added

- C#/.NET 8 desktop application with an Avalonia Persian RTL interface (dashboard, outputs, settings).
- Batched real-HTTP latency engine with per-profile local SOCKS isolation.
- Dual-runtime profile routing for modern TCP- and UDP-based protocols.
- Median, minimum, average, success-count and tester metadata.
- Failed-only retry pass, bounded concurrency and cancellation.
- Version-pinned GeoFiles and runtime packaging.
- Reproducible Windows/Linux/macOS/Android release workflow with checksums and provenance.
- Bundled Vazirmatn font so the desktop UI renders identically everywhere.
- Android GitHub subscription publishing (auto-publish sub.txt/proxy.txt after a successful test).
- Android light/dark/system theme toggle with minimal vector navigation icons.
- Android persistent settings, channel lists and theme across app restarts.
- Android Vazirmatn typography served from the shared repository assets.

### Changed

- Android collection and profile tests run concurrently with bounded workers.
- Android reports median latency rather than a mean distorted by outliers.
- Mobile network core access is wrapped behind a single neutral facade.
- Pinned cores refreshed: sing-box `1.13.15 → 1.13.19`, GeoFiles `→ 202608252219`, mobile core rebuilt from a newer pinned commit.
- Cross-OS publishing fixed by enabling `EnableWindowsTargeting` (Linux/macOS runners can now build the desktop package).
- Version code/name moved to `200` / `2.0.0`.
- Active desktop implementation moved from Python/PySide to C#/Avalonia.

### Removed

- One-process-per-attempt latency testing path.
- TCP fallback being presented as a successful real-config test.
- Legacy automatic release workflows.
