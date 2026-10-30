# Compatibility contract

## Target, not a universal guarantee

First-release target: Windows 10/11 x64 with Python 3.12+ for source checkouts and a modern browser. Windows 10 deployments remain subject to Microsoft's lifecycle/security policies. GitHub Windows runners do not represent every Windows 10/11 build or physical device.

| Capability | Current scope |
|---|---|
| Drive discovery | Windows drive letters and mounted local volumes; folder mounts included |
| Media | Fixed/removable/USB/optical/RAM volumes where mounted and accessible |
| Network | Mapped drives listed, never automatically probed/scanned; UNC scans rejected |
| Filesystems | Metadata via Windows/Python APIs; NTFS/exFAT/FAT32 require physical validation |
| Links/cloud | Reparse links and placeholders skipped; incomplete linked trees cannot be deleted |
| Permissions | Normal UAC elevation; no ownership takeover; access-denied paths reported |
| Encryption | Unlocked accessible volumes only; no unlocking or recovery feature |
| Hardware health | No SMART/SSD-health or physical-disk diagnosis |
| Inventory | One active completed snapshot; choosing a different volume does not change the scanned inventory |

Mapped drives can differ between normal and elevated Windows sessions. USB SSDs can be classified as fixed disks. No drive-type label should be interpreted as a physical bus or SSD/HDD guarantee.

## Outstanding manual validation

- Windows 10 22H2 / supported Windows 11 builds, x64 clean machines.
- Standard user → UAC accept/cancel, managed policy denial.
- NTFS, exFAT, FAT32, removable SSD/USB stick, folder mount, optical empty tray.
- Device removal during scan/preview/removal, locked BitLocker and access-denied paths.
- Long/Unicode names, hardlinks, sparse/compressed files, cloud placeholders.
- Browsers: Edge/Chrome/Firefox/Brave; no browser; winget missing/offline/failing.
- Low memory, large inventories, full/unwritable state disk, interrupted writes.

Not supported: raw or unmounted partitions, recovery/system device editing, remote scanning, Windows 7/8.1, native ARM64 packages, macOS/Linux. Report reproducible issues without personal paths or credentials.
