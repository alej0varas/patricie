# -*- mode: python ; coding: utf-8 -*-

# could not manage to make python-git work so hash will be only
# generated by linux build

datas = [
    ("assets", "assets"),
    (
        "../venvw/Lib/site-packages/fake_useragent/data/browsers.jsonl",
        "fake_useragent/data",
    ),
    ("../venvw/Lib/site-packages/certifi/cacert.pem", "certifi"),
]

a = Analysis(
    ["src\\main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
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
    name="Patricie",
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
    icon=["assets\\patricie.ico"],
)
