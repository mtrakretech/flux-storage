# Release artifact component inventory

This is a source-based inventory of the `2.2.0-dev.1` Windows x64 artifacts. It describes the build definitions; it is not a substitute for auditing the exact resolved binary payload and licenses for each release.

## Shared application payload

- `FluxStorage.exe`: PyInstaller bootloader and Python application entry point (`app.py`), built as a console-mode, `asInvoker` executable without UPX.
- `_internal/`: PyInstaller one-directory Python runtime, resolved Python packages and native dependencies.
- `static/ui/`: compiled React/Vite interface.
- `windows/`: Windows integration code used by the application.
- `LICENSE`, `THIRD_PARTY_NOTICES.md`, and frontend third-party notices.
- No browser, browser installer, Python installer, database, signing certificate, or user inventory is bundled.

The Python runtime dependency declaration is `requirements.txt` (`Flask>=3.1,<4`); the build bundles the environment resolved at build time. Frontend direct dependencies and lockfile are in `frontend/package.json` and `frontend/bun.lock`. Build/test tools, including Bun, PyInstaller and Playwright, are not application runtime features.

## Published artifacts

| Artifact | Added packaging components | Install/data behavior |
|---|---|---|
| `FluxStorage-2.2.0-dev.1-setup.exe` | Inno Setup 6 wizard, MIT license page, destination/shortcut tasks, uninstaller | Per-user default; uninstall removes installed program files and shortcuts. `%LOCALAPPDATA%\FluxStorage` is retained unless the user explicitly chooses the purge prompt. |
| `FluxStorage-2.2.0-dev.1-per-user.msi` | WiX 3 Windows Installer package, license UI, destination selection, Start-menu shortcut | Tested as per-user unmanaged without elevation under a standard local account. Default and custom destinations tested; uninstall removed program files and preserved a data sentinel. Windows Installer created an HKLM uninstall metadata entry during install despite reporting `USERUNMANAGED`; uninstall removed it. App startup separately requires administrator approval. |
| `FluxStorage-2.2.0-dev.1-windows-x64-portable.zip` | ZIP wrapper containing the one-directory application tree | No installer or uninstaller. User state remains in `%LOCALAPPDATA%\FluxStorage`, not beside the extracted binaries. |

Both published files are unsigned preview builds. The release SHA-256 manifest identifies the exact uploaded artifacts.

## MSI validation notes

`dist/setup/FluxStorage-2.2.0-dev.1-per-user.msi` is built with WiX 3 and passes ICE38/ICE64 using HKCU component keypaths and explicit directory-removal components. A genuine non-admin local account installed it without elevation; Windows Installer's `MsiEnumProductsEx` reported `USERUNMANAGED`. The install was verified at the default and a custom destination; uninstall removed the custom program tree and preserved a sentinel under the test account's `%LOCALAPPDATA%\FluxStorage`.

During the standard-user test, Windows Installer also created an HKLM uninstall metadata entry; the per-user context API still reported `USERUNMANAGED`, and uninstall removed the entry. The MSI does not remove `%LOCALAPPDATA%\FluxStorage`. App launch separately requests administrator approval for protected operations; a standard account without admin credentials cannot complete that UAC flow. `packaging/wix_keypaths.py` transforms the `heat.exe` harvest into per-user keypaths and directory-removal entries; regenerate `files_keyed.wxs` from `files.wxs` when the harvested payload changes.

## Remaining audit work

- Resolve and review the exact transitive runtime dependency/license set represented by the shipped `_internal` directory, and confirm all required notices are present in each artifact.
- Run the compatibility/install matrix on a clean standard-user Windows 10/11 x64 machine, including upgrade, custom destination and interrupted-install behavior.
- Keep code signing and hardware/performance claims separate from this inventory; neither is implied by a successful package build.
