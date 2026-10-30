# Release gates & packaging roadmap

## Current stage: source preview + unsigned pre-release binaries

Source, branded docs, local safety controls, storage/port improvements, tests and CI are available. Development version is centralized in `app_info.py`; frontend package metadata must match.

Validated so far (2026-10-30, dev machine + CI):

- PyInstaller one-dir build with product icon, version metadata (`Flux Storage`, `MTR Soft`, MIT) and **asInvoker** manifest (no unconditional UAC; elevation stays consent-gated per session).
- Frozen server smoke test: dynamic OS-assigned port, `/api/health` + `/api/status` correct, per-user state load, drive discovery, instance discovery no longer requires elevation (non-admin installs are admitted).
- Portable ZIP (`FluxStorage-2.2.0-dev.1-windows-x64-portable.zip`) with sha256sum file.
- Inno Setup 6 installer: per-user default with privilege choice, destination selection, MIT license page, Start-menu + optional desktop shortcut, post-install launch, silent install/uninstall cycle verified — registry + shortcuts + program files removed, `%LOCALAPPDATA%\FluxStorage` preserved; optional purge requires an explicit interactive answer.
- Known quirk recorded: uninstalling immediately after install on an AV-active machine can defer deletion of a handful of freshly written binaries until a later delete/reboot; no user data is involved.

Still not done or not implied:

- [ ] Clean-machine compatibility matrix (no Python/Bun machines: first-run, UAC, single instance, auto-port, spaces/Unicode/restricted destinations, upgrade/rollback, interrupted install).
- [ ] Code signing: no certificate exists; builds are unsigned and SmartScreen will warn. Never store signing secrets in source.
- [ ] MSI package (Inno EXE-based setup only at this stage).
- [ ] Upgrade/repair/running-instance/rollback/interrupted-install handling (the silent cycle above covers one replace pass only).
- [ ] Artifact-level transitive dependency license audit and component inventory per artifact.
- [ ] Hardware/SSD/SMART claims — intentionally absent; physical compatibility, performance and accessibility reviews remain.

The manually dispatched `draft-package.yml` workflow builds the same distribution and portable ZIP on a clean Windows runner, including license/notices and SHA-256 checksums, and uploads temporary Actions artifacts. It **never** creates a release. Build success alone is not executable validation. Clean-runner artifacts are a build cross-check, not a different reliability tier.

Open decisions for the release stage: signing identity/budget, MSI, minimum hardware targets. These are not needed for source publishing and were not silently chosen or purchased.
