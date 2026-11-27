# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

project_root = Path(SPEC).resolve().parent
src_root = project_root / "src"
sys.path.insert(0, str(src_root))

resources = src_root / "open_fish_reader" / "resources"
entry = project_root / "build_tools" / "pyinstaller_entry.py"

a = Analysis(
    [str(entry)],
    pathex=[str(src_root)],
    binaries=[],
    datas=[(str(resources), "resources")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="open-fish-reader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="open-fish-reader",
)
