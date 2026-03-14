# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('/Users/mostafakamal/youtube-downloader/venv/lib/python3.14/site-packages/static_ffmpeg/bin/darwin_arm64/ffmpeg', '.')],
    datas=[('templates', 'templates'), ('static', 'static')],
    hiddenimports=['yt_dlp', 'webview', 'static_ffmpeg'],
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
    name='YT Downloader',
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
    icon=['YTDownloader.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YT Downloader',
)
app = BUNDLE(
    coll,
    name='YT Downloader.app',
    icon='YTDownloader.icns',
    bundle_identifier=None,
)
