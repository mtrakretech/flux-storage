# Release gates & packaging roadmap

## Current stage: source preview

Source, branded docs, local safety controls, storage/port improvements, tests and CI are available. Development version is centralized in `app_info.py`; frontend package metadata must match. No stable installer release exists.

The manually dispatched `draft-package.yml` workflow builds a draft PyInstaller one-directory EXE distribution and portable ZIP, includes license/notices and SHA-256 checksums, and uploads temporary Actions artifacts. It **never** creates a release. Build success alone is not executable validation. Do not advertise those artifacts as production-ready.

## Next stage: EXE / custom setup / MSI / portable ZIP

- [ ] Validate bundled runtime, resource lookup, UAC, single instance and auto-port behavior on clean machines without Python/Bun.
- [ ] Design modern MTR Soft setup branding, accessible controls and explicit destination selection.
- [ ] Choose installer toolchain and implement MSI/EXE, stable product/upgrade IDs and Start-menu shortcuts.
- [ ] Define per-user/per-machine install permissions; test spaces/Unicode/restricted destinations.
- [ ] Uninstall removes program files/shortcuts, **preserves personal snapshots/history by default**. Any optional data purge requires separate explicit confirmation.
- [ ] Test upgrade, downgrade refusal, interrupted install, rollback, running-instance handling and repair.
- [ ] Portable ZIP: document writable per-user state location; “portable binaries” does not mean all data stays beside the EXE.
- [ ] Browser helper remains opt-in, reports offline/winget/installer failures, and is not a prerequisite for uninstall.
- [ ] Audit transitive dependency licenses and generate artifact-level component inventory/notices.
- [ ] Acquire signing identity, sign/timestamp executables and MSI; verify hashes/signatures. Never store signing secrets in source.
- [ ] Complete physical compatibility checklist, performance measurements and accessibility review.
- [ ] Publish versioned release notes, SHA-256 sums, supported builds and known issues only after review.

Open decisions for the release stage: signing identity/budget, installer technology, install scope and minimum hardware targets. These are not needed to publish source, and have not been silently chosen or purchased.
