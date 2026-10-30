# Support & troubleshooting

## Local data

State lives in `%LOCALAPPDATA%\FluxStorage`: snapshot, activity/history, preferences, runtime record and preview manifests. These contain private filesystem paths. Back up the directory with Flux stopped if needed. Do not attach it to a public issue. The repository excludes personal reports, maintenance scripts, backups and generated runtime state.

## Common problems

| Symptom | Action |
|---|---|
| Browser cannot connect | Relaunch via `Start Flux Storage.cmd`; ports are dynamic. Do not bookmark an old port. Keep the server window open. |
| Port occupied | Default is automatic; a configured preferred port falls back. Check the printed/dashboard URL. |
| UAC denied | No security bypass is attempted. Approve normal Windows elevation or ask your administrator. |
| Blank/missing frontend | Build `frontend` using the README. Serve through Flux, not by opening `index.html` directly. |
| Device checking/unavailable | Reconnect/unlock it and wait for the next background refresh. A permanently stuck OS probe may require restarting Flux. |
| Mapped drive missing | Elevated Windows can have different mappings. Remote scanning is not supported. |
| Checkbox selected but removal blocked | Review the policy explanation. Mode changes do not silently grant deletion rights. |
| Preview expired or contents changed | Close related applications and prepare a new preview. Rescan if the location changed. |
| Cleanup reports an error | Check Activity. Some earlier items may already be removed; deletion is not transactional. Do not blindly retry. |
| Missing dependencies | Source bootstrap offers an isolated `.venv` install with consent. Python/Bun installation is manual. |
| No browser / no winget | Use the optional setup chooser, or install from the browser publisher's official installer, then reopen Flux. No automatic download occurs without consent. |
| Disk full / state not writable | Free space through supported Windows tools or fix directory permissions; preserve existing state before troubleshooting. |

Ctrl+C stops the local server; the UI also provides a shutdown action. No background service or auto-start task is installed by the source checkout.

## Report a bug

Use a repository issue with Windows build/architecture, Flux version, browser version, steps, expected/actual behavior and a minimal synthetic example. Replace names, exact personal paths and screenshots exposing private data. Do not post credentials, signing keys, runtime tokens, inventories or deletion manifests. Security issues belong in private reporting; see `SECURITY.md`.
