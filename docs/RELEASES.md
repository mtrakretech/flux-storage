# Release gates & packaging roadmap

## Current stage: v2.2.0 stable-channel release (unsigned)

Source, branded docs, local safety controls, storage/port improvements, tests and CI are available. Development version is centralized in `app_info.py`; frontend package metadata must match.

Validated so far (2026-10-31, development machine + CI):

- PyInstaller one-dir build with product icon, version metadata (`Flux Storage`, `MTR Soft`, MIT) and **asInvoker** manifest (no unconditional UAC; elevation stays consent-gated per session).
- Frozen server smoke test: dynamic OS-assigned port, `/api/health` + `/api/status` correct, per-user state load, drive discovery, instance discovery no longer requires elevation (non-admin installs are admitted).
- Portable ZIP (`FluxStorage-2.2.0-dev.1-windows-x64-portable.zip`) with sha256sum file.
- Inno Setup 6 installer: per-user default with privilege choice, destination selection, MIT license page, Start-menu + optional desktop shortcut, post-install launch, silent install/uninstall cycle verified — registry + shortcuts + program files removed, `%LOCALAPPDATA%\FluxStorage` preserved; optional purge requires an explicit interactive answer.
- Published unsigned pre-release `v2.2.0-dev.1` includes the custom setup EXE and portable ZIP; their downloaded hashes match `SHA256SUMS.txt`, and the downloaded portable ZIP passed a fresh-extract smoke test.
- WiX MSI installed without elevation under a temporary non-admin local account; Windows Installer reported `USERUNMANAGED` context. Default and custom-folder installs were tested; custom-folder uninstall removed program files and preserved a test sentinel in `%LOCALAPPDATA%\FluxStorage`. Product uninstall removed the MSI registration. A standard non-admin cannot launch the app without administrative credentials because app startup requests UAC for protected operations.
- WiX emitted a transient HKLM uninstall metadata entry during the per-user test; Windows Installer's product-context API identified the install as per-user unmanaged, and uninstall removed the entry. This registry behavior is recorded rather than represented as "no HKLM metadata".
- Artifact component inventory documented in `docs/ARTIFACT_INVENTORY.md`.
- Corrected setup EXE and portable ZIP rebuilt with Python 3.13.14 `LICENSE.txt`; unused bcrypt extension excluded. Updated MSI was built but intentionally not tested or published; the release retains its prior MSI.
- Stable tag `v2.2.0` packages app version 2.2.0 in setup EXE, portable ZIP, and MSI. MSI was built but installation testing was intentionally skipped. Assets are unsigned; stable channel labeling does not imply clean-machine certification or signing.
- Known quirk recorded: uninstalling immediately after install on an AV-active machine can defer deletion of a handful of freshly written binaries until a later delete/reboot; no user data is involved.

Still not done or not implied:

- [ ] Fresh-machine testing is intentionally skipped per user request. Current dev PC is Windows 10 22H2 (build 19045); Windows 11 and representative hardware matrix remain unverified.
- [ ] Code signing: no certificate exists; builds are unsigned and SmartScreen will warn. Never store signing secrets in source.
- [ ] Upgrade/repair/running-instance/rollback/interrupted-install handling (the silent cycle above covers one replace pass only).
- [x] v2.2.0 MSI installation testing is skipped by user request; package was built and released with that limitation disclosed.
- [ ] Run a Windows 11 clean-machine and representative hardware matrix when another machine/VM is available.
- [ ] Hardware/SSD/SMART claims - intentionally absent; physical compatibility, performance and accessibility reviews remain.

The manually dispatched `draft-package.yml` workflow builds the same distribution and portable ZIP on a clean Windows runner, including license/notices and SHA-256 checksums, and uploads temporary Actions artifacts. It **never** creates a release. Build success alone is not executable validation. Clean-runner artifacts are a build cross-check, not a different reliability tier.

Open decisions for the release stage: signing identity/budget and minimum hardware targets. These are not needed for source publishing and were not silently chosen or purchased.
