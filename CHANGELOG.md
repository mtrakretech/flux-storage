# Changelog

## 2.2.0-dev.1 — source preview

- MTR Soft identity and public-safe documentation/artwork.
- Background drive-letter/folder-volume discovery, availability, capacity and filesystem dashboard.
- Automatic loopback ports, preferred-port fallback and per-user instance discovery.
- Persistent theme/startup preferences and opt-in native browser setup.
- Source bootstrap with consent-based local dependency setup.
- Portability regression tests, fixture-only browser tests and Windows CI.
- Unsigned setup EXE, per-user MSI and portable ZIP preview artifacts are published. MSI install context and custom-folder uninstall were verified under a standard Windows account; the full clean-machine matrix remains open.
- Read-only API requests retry once on a dropped loopback connection; tree read failures state the actual reason next to Retry and unexpected server errors are logged for diagnosis.

## 2.2.0-dev.1 — first pre-release build (unsigned)

- Branded PyInstaller one-dir build `FluxStorage.exe`: product icon, Windows version metadata (`Flux Storage`, `MTR Soft`, MIT) and an asInvoker manifest — no unconditional UAC prompt; elevation stays consent-gated per session.
- Instance discovery now accepts non-elevated instances, so re-launching focuses the running window for per-user installs.
- Portable ZIP for Windows 10/11 x64 with a sha256sum file.
- Custom MTR Soft setup (Inno Setup 6): per-user default without UAC, privilege choice, destination selection, MIT license page, Start-menu and optional desktop shortcuts, launch-after-install; uninstall keeps `%LOCALAPPDATA%\FluxStorage` by default, with deletion offered only after an explicit answer.
- No code signing yet: SmartScreen will warn for this publisher; builds are called previews until the full clean-machine compatibility matrix, signing and an MSI are done.

## Earlier local development

Explorer tree/list/icon views, three cleanup modes, explicit risky-session unlock, exact deletion manifests, CSV export, live metadata checks and approval-first permanent removal. Earlier machine-specific inventories and cleanup records are not part of the public repository.
