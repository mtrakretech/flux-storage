# Security & safety

Flux is a development-preview local administrator tool with permanent file deletion. No bug bounty, universal safety guarantee or enterprise hardening certification is implied.

## Report privately

Please use GitHub private vulnerability reporting if enabled for this repository. If unavailable, open an issue asking for a private reporting channel **without exploit details or sensitive data**. Do not attach personal inventories, session tokens, manifests or credentials publicly.

## Boundaries

- Bind to `127.0.0.1` only. Never expose Flux through a public tunnel, reverse proxy, port-forward or LAN bind.
- Validate Host and mutating-request Origin; mutating API calls require a per-session token. CSP, frame denial and no-store headers protect the local interface.
- Browser installs use a shipped helper with four allowlisted winget identifiers and explicit consent. No remote script is fetched and executed by Flux.
- Deletion requires known inventory IDs, fresh expiring previews, mode permission, identity/metadata checks and exact confirmation. Risky permissions reset on server restart.
- Critical system/app/runtime paths, volume roots, links and incomplete trees remain protected. Full control deliberately permits sensitive user-data deletion.

## Important limitations

Metadata fingerprints are not file-content backups or an atomic transaction. Files can change between validation and removal; hostile concurrent local processes are outside the safety model. Do not clean actively modified trees. A failure midway can leave some selections already removed. Nothing is moved to the Recycle Bin and there is no undelete feature.

Any process/browser with the same administrator/user privileges may access local data; loopback is not an isolation boundary against local malware. UAC under a different administrator account can use that account's profile/state. Review the running identity before scanning.

Use backups, inspect manifests and never treat a “safe” classification or absence of errors as proof that data is disposable. Only the current development branch receives best-effort fixes; no stable support window is declared yet.
