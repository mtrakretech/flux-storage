# Third-party components

Flux's original source is MIT licensed. This summary is not a replacement for upstream licenses; redistributed packages must include the licenses for their resolved components and bundled runtime.

| Component | License family / notice |
|---|---|
| Python 3.13.14 runtime | Python Software Foundation license and bundled notices in `_internal/LICENSE.txt` |
| Flask, Werkzeug, Jinja2, itsdangerous, Click, Blinker, MarkupSafe | BSD-style licenses; see resolved distributions |
| React / React DOM | MIT |
| Vite, Tailwind CSS, TypeScript, Radix UI, class-variance-authority, clsx, tailwind-merge, get-nonce | MIT; check resolved transitive components |
| lucide-react | ISC |
| shadcn/ui component patterns | MIT |
| Beautiful UI interaction patterns | MIT; full copyright/license notice in `frontend/THIRD-PARTY-NOTICES.md` |
| PyInstaller (draft build tool) | GPL with bundling exception; preserve applicable notices |
| Playwright (development testing) | Apache-2.0; browser binaries are test tooling, not application payload |

Theme styling follows the supplied tweakcn light/dark design; product hero artwork is original synthetic MTR Soft artwork. System fonts use the user's installed font stack; no fonts are redistributed. Microsoft, Edge, Chrome, Firefox, Brave and Windows names identify third-party products only. Browser installers are not bundled.

Frontend production dependency audit for `frontend/bun.lock` resolves 84 packages: 81 MIT, one ISC, one Apache-2.0, and one 0BSD (`tslib`). Upstream package notices remain available in the frontend distribution. Exact Python runtime package versions and their license files are inventoried in `docs/ARTIFACT_INVENTORY.md`.
