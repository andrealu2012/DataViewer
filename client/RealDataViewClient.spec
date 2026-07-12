# -*- mode: python ; coding: utf-8 -*-

import os
import sys


client_dir = os.path.abspath(SPECPATH)

a = Analysis(
    [os.path.join(client_dir, 'main.py')],
    pathex=[client_dir],
    binaries=[],
    datas=[
        (os.path.join(client_dir, 'config.json'), '.'),
        (os.path.join(client_dir, 'icons', 'apply.svg'), 'icons'),
        (os.path.join(client_dir, 'icons', 'save.svg'), 'icons'),
        (os.path.join(client_dir, 'icons', 'tray.png'), 'icons'),
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

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='DataViewer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name='DataViewer',
    )
    app = BUNDLE(
        coll,
        name='DataViewer.app',
        icon=None,
        bundle_identifier='com.realdataview.dataviewer',
        info_plist={
            'CFBundleDisplayName': 'DataViewer',
            'CFBundleName': 'DataViewer',
            'NSHighResolutionCapable': True,
            'LSUIElement': True,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='DataViewer',
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
