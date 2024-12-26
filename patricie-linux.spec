# -*- mode: python ; coding: utf-8 -*-

# write runtime constants

# write runtime constants
import git

_repo = git.Repo(search_parent_directories=True)
_commit_sha = _repo.head.object.hexsha

with open("src/_constants.py", "w") as f:
    f.write(f'COMMIT_SHA = "{_commit_sha[:8]}"\n')
# end constants


datas = [
    ("assets", "assets"),
    (
        "../venvl/lib/python3.10/site-packages/fake_useragent/data/browsers.jsonl",
        "fake_useragent/data",
    ),
    # required by urllib
    ("../venvl/lib/python3.10/site-packages/certifi/cacert.pem", "certifi"),
]

a = Analysis(
    ["src/main.py", "src/_constants.py"],
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
    name="patricie",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[],
)
