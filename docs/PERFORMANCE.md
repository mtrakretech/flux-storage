# Performance and size

Flux uses metadata scans, not file-content hashing. Device probes run on bounded daemon threads (up to eight in flight); a slow probe is marked unresponsive without waiting in HTTP status handling. Windows device calls cannot reliably be cancelled in a Python thread: a stuck call retains its slot until it returns or Flux restarts. Discovery itself runs off the HTTP thread.

Folder trees, item tables and manifests are paginated. The previous snapshot loads asynchronously at startup. The UI is built/minified once and served locally, with no remote fonts required.

Limits: a large completed snapshot/index remains in RAM; scan duration depends on file count, disk, antivirus, access failures and hardware. Live previews enumerate every descendant, so large selections can take time. No fixed completion-time or universal memory bound is promised. A request timeout is not permission to assume deletion failed or retry blindly: check Activity first.

## Build-size policy

- Ship no Python/node development environment, test fixtures, reports or source maps inside future packages.
- Bundle Python/runtime only; use installed browsers rather than embedding Chromium.
- Prefer a one-directory runtime + portable ZIP over one-file extraction overhead; benchmark before choosing a final layout.
- Do not use unsafe compression/antivirus exclusions or remove dependencies solely for headline size.
- Record compressed/uncompressed size, cold/warm startup, idle/scan memory and scan throughput on representative hardware before release.

Current frontend size is reported by `bun run build`. This is **not** the future EXE/MSI size. No small-build or speed guarantee is published until packaged artifacts are measured.
