# Changelog

## 1.1.0-preview

### Added
- Native Android application written with Kotlin and Jetpack Compose.
- Linux x86_64 portable desktop build using the existing PySide6 interface.
- Unified GitHub Actions pipeline for Windows, Linux, Android, source archive, and checksums.
- Two-stage Android workflow: collect while Telegram is reachable, disconnect, then test endpoints.
- Android exports for configs, Telegram proxies, Base64 subscriptions, and JSON reports.
- Python parser regression tests.

### Improved
- Desktop High-DPI defaults.
- Platform-aware Xray path selection.
- Retry handling for transient Telegram preview failures.
- Release reproducibility and SHA-256 verification.

### Changed
- v1.1.0 is published as a prerelease.
- Legacy v1.0.1 workflow is manual-only and no longer runs on every push.

### Preserved
- GitHub release v1.0.1 and its assets remain untouched.
