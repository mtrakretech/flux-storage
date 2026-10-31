# Release artifact component inventory

This inventory covers the `2.2.0` Windows x64 payload and its resolved application dependencies. It does not claim clean-machine or hardware validation.

## Shared application payload

- `FluxStorage.exe`: PyInstaller bootloader and Python application entry point (`app.py`), built as a console-mode, `asInvoker` executable without UPX.
- `_internal/`: PyInstaller one-directory Python 3.13.14 runtime, resolved Python packages and native dependencies; Python's `LICENSE.txt` is included.
- `static/ui/`: compiled React/Vite interface.
- `windows/`: Windows integration code used by the application.
- `LICENSE`, `THIRD_PARTY_NOTICES.md`, and frontend third-party notices.
- No browser, browser installer, Python installer, database, signing certificate, or user inventory is bundled.

The Python runtime dependency declaration is `requirements.txt` (`Flask>=3.1,<4`); the audited frozen build has Flask 3.1.2, Werkzeug 3.1.3, itsdangerous 2.2.0, Click 8.4.2, cryptography 46.0.3, importlib_metadata 8.7.1, and MarkupSafe 3.0.3. All seven distributions include their license files. The unused `bcrypt` extension was excluded from the corrected build. Frontend production lock resolves 84 packages (81 MIT, one ISC, one Apache-2.0, one 0BSD); package license files are checked in `frontend/node_modules` and frontend source notices. Build/test tools, including Bun, PyInstaller and Playwright, are not application runtime features.

## Published artifacts

| Artifact | Added packaging components | Install/data behavior |
|---|---|---|
| `FluxStorage-2.2.0-setup.exe` | Inno Setup 6 wizard, MIT license page, destination/shortcut tasks, uninstaller | Per-user default; uninstall removes installed program files and shortcuts. `%LOCALAPPDATA%\FluxStorage` is retained unless the user explicitly chooses the purge prompt. |
| `FluxStorage-2.2.0-per-user.msi` | WiX 3 Windows Installer package, license UI, destination selection, Start-menu shortcut | Packaged but not installation-tested for v2.2.0, per user request. The prior dev MSI's per-user context and HKLM metadata behavior are documented below but do not constitute validation of this MSI build. |
| `FluxStorage-2.2.0-windows-x64-portable.zip` | ZIP wrapper containing the one-directory application tree | No installer or uninstaller. User state remains in `%LOCALAPPDATA%\FluxStorage`, not beside the extracted binaries. |

Both published files are unsigned preview builds. The release SHA-256 manifest identifies the exact uploaded artifacts.

## MSI validation notes

The earlier `2.2.0-dev.1` MSI was built with WiX 3 and passed ICE38/ICE64 using HKCU component keypaths and explicit directory-removal components. A genuine non-admin local account installed it without elevation; Windows Installer's `MsiEnumProductsEx` reported `USERUNMANAGED`. The install was verified at the default and a custom destination; uninstall removed the custom program tree and preserved a sentinel under the test account's `%LOCALAPPDATA%\FluxStorage`. The v2.2.0 MSI was rebuilt from corrected payload but was not installed or tested.

During that earlier test, Windows Installer also created an HKLM uninstall metadata entry; the per-user context API still reported `USERUNMANAGED`, and uninstall removed the entry. The MSI does not remove `%LOCALAPPDATA%\FluxStorage`. App launch separately requests administrator approval for protected operations; a standard account without admin credentials cannot complete that UAC flow. `packaging/wix_keypaths.py` transforms the `heat.exe` harvest into per-user keypaths and directory-removal entries; regenerate `files_keyed.wxs` from `files.wxs` when the harvested payload changes.

## Remaining audit work

- Corrected setup EXE and portable ZIP include Python 3.13.14's `LICENSE.txt` and exclude the unused bcrypt 5.0.0 native extension (whose Apache-2.0 notice was missing). The Python license bundle includes notices for bzip2, libffi, OpenSSL, expat, zlib and other incorporated software; Python describes its incorporated-software list as incomplete, so this is not a complete native SBOM.
- Corrected local MSI candidate links, but it was deliberately not installed/tested or published. The release continues to use the earlier, previously tested MSI.
- Run the compatibility/install matrix on a clean standard-user Windows 10/11 x64 machine, including upgrade, custom destination and interrupted-install behavior.
- Keep code signing and hardware/performance claims separate from this inventory; neither is implied by a successful package build.
