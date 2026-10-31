# PyInstaller one-directory application payload used by the unsigned preview
# EXE, Inno Setup installer, portable ZIP, and experimental WiX MSI candidate.
# This spec does not sign artifacts or establish MSI installation context.
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / 'app.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / 'static' / 'ui'), 'static/ui'),
        (str(root / 'windows'), 'windows'),
        (str(root / 'LICENSE'), '.'),
        (str(Path(__import__('sys').base_prefix) / 'LICENSE.txt'), '.'),
        (str(root / 'THIRD_PARTY_NOTICES.md'), '.'),
        (str(root / 'frontend' / 'THIRD-PARTY-NOTICES.md'), 'notices'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # bcrypt is present in the build environment but unused by Flux; excluding
    # it also avoids shipping an irrelevant native extension.
    excludes=['tkinter', 'bcrypt'],
    noarchive=False,
)
pyz = PYZ(a.pure)
# asInvoker: the server starts without elevation; cleanup consent controls and the
# session-scoped full-control unlock handle elevation per session (privileges.py).
# No unconditional UAC prompt on launch.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FluxStorage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    uac_admin=False,
    icon=[str(root / 'packaging' / 'flux.ico')],
    version=str(root / 'packaging' / 'version.txt'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FluxStorage')
