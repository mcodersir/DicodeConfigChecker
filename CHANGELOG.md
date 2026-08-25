# Changelog

## 2.0.0 — 2026-08-25

### Added

- C#/.NET 8 desktop application and WPF user interface.
- Batched real-HTTP latency engine with per-profile local SOCKS isolation.
- Dual-runtime profile routing for modern TCP- and UDP-based protocols.
- Median, minimum, average, success-count and tester metadata.
- Failed-only retry pass, bounded concurrency and cancellation.
- Version-pinned GeoFiles and runtime packaging.
- Reproducible Windows/Linux/macOS/Android release workflow with checksums and provenance.
- Bundled Vazirmatn font so the Persian desktop UI renders identically everywhere.
- Android GitHub subscription publishing (auto-publish sub.txt/proxy.txt after a successful test).

### Changed

- Android collection and profile tests now run concurrently with bounded workers.
- Android reports median latency rather than a mean distorted by outliers.
- Version code/name moved to `200` / `2.0.0`.
- Active desktop implementation moved from Python/PySide to C#/WPF.

### Removed

- One-process-per-attempt latency testing path.
- TCP fallback being presented as a successful real-config test.
- Legacy automatic release workflows.
