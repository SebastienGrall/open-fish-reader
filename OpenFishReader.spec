# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
project_root = Path(SPEC).resolve().parent
src_root = project_root / "src"
sys.path.insert(0, str(src_root))
icon_path = src_root / "open_fish_reader" / "resources" / "icons" / "open_fish_reader.ico"
resources_path = src_root / "open_fish_reader" / "resources"
version_path = project_root / "build_tools" / "windows_version_info.txt"
a = Analysis(
        [
            str(
                project_root
                / "build_tools"
                / "pyinstaller_entry.py"
            )
        ],
    pathex=[str(src_root)], binaries=[],
    datas=[(str(resources_path), "resources")],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["tkinter", "unittest"], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="OpenFishReader",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
    icon=str(icon_path), version=str(version_path),
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[],
    name="Open Fish Reader",
)
