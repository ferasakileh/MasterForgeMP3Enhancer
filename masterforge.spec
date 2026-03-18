# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for MasterForge 320 desktop build (Windows).
Build command:
    python -m PyInstaller --noconfirm masterforge.spec
"""

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

app_name = "MasterForge320"

# tkinterdnd2 needs its tkdnd binaries/data bundled for drag-and-drop to work.
datas = []
binaries = []
hiddenimports = []

try:
    datas += collect_data_files("tkinterdnd2")
    binaries += collect_dynamic_libs("tkinterdnd2")
except Exception:
    pass

# Matplotlib backend used by Tkinter canvas.
hiddenimports += [
    "matplotlib.backends.backend_tkagg",
]

a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)
