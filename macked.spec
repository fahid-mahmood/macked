# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['macked.py'],
    pathex=[],
    binaries=[],
    datas=[('macked.icns', '.'), ('version.json', '.')],
    hiddenimports=['PIL', 'requests', 'bs4', 'lxml'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Macked',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['macked.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Macked',
)
app = BUNDLE(
    coll,
    name='Macked.app',
    icon='macked.icns',
    bundle_identifier='com.yourcompany.macked.v1_1_8',
)
