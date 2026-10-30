# Draft build preparation only. No MSI/custom installer or signing is implied.
from pathlib import Path
root=Path(SPECPATH).parent
a=Analysis([str(root/'app.py')],pathex=[str(root)],
    binaries=[],datas=[(str(root/'static'/'ui'),'static/ui'),(str(root/'windows'),'windows'),
                       (str(root/'LICENSE'),'.'),(str(root/'THIRD_PARTY_NOTICES.md'),'.'),
                       (str(root/'frontend'/'THIRD-PARTY-NOTICES.md'),'notices')],
    hiddenimports=[],hookspath=[],hooksconfig={},runtime_hooks=[],
    excludes=['tkinter'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='FluxStorage',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=True,uac_admin=True)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='FluxStorage')
