# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve()

a = Analysis(
    [str(ROOT / 'launcher.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'core' / 'ui'), 'core/ui'),
        (str(ROOT / 'license'), 'license'),
        (str(ROOT / 'SOT.md'), 'license'),
    ],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='BUS-Core',
    # Canonical Windows release format: a self-contained onefile executable.
    # Keep these explicit so a future PyInstaller default cannot change the contract.
    exclude_binaries=False,
    append_pkg=True,
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
    icon=str(ROOT / 'core' / 'ui' / 'Logo.png'),
    version=str(ROOT / 'scripts' / '_win_version_info.txt'),
)
