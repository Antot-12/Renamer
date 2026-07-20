# Renamer.spec - PyInstaller spec for minimal size (~15-20 MB)
# -*- mode: python ; coding: utf-8 -*-
#
# Usage: pyinstaller --noconfirm Renamer.spec
# With UPX: pyinstaller --noconfirm --upx-dir=upx Renamer.spec

import sys
from pathlib import Path

block_cipher = None

# Exclude heavy/unused modules to reduce size
EXCLUDES = [
    # Data science (not needed)
    'matplotlib', 'numpy', 'pandas', 'scipy',
    # Testing/dev tools
    'pytest', '_pytest', 'setuptools', 'wheel', 'pip',
    'unittest', 'doctest', 'pdb', 'test', 'tests',
    # IDE/debug tools
    'pygments', 'IPython', 'jedi', 'parso',
    # Unused stdlib
    'pydoc', 'xmlrpc', 'ftplib', 'lib2to3', 'distutils',
    'pkg_resources', 'curses', 'asyncio', 'concurrent',
    'multiprocessing', 'multiprocessing.popen_spawn_win32',
    'sqlite3', 'idlelib', 'email.test', 'tkinter.test',
    'http.server', 'socketserver', 'ssl', 'telnetlib',
    'cgi', 'cgitb', 'imaplib', 'nntplib', 'poplib', 'smtplib',
    'sndhdr', 'sunau', 'wave', 'aifc', 'audioop',
    'ensurepip', 'venv', 'turtledemo', 'turtle',
    # Windows specific we don't need
    'win32com', 'pywin32',
    # PIL modules we don't need
    'PIL.ImageQt', 'PIL.ImageDraw2', 'PIL.SpiderImagePlugin',
    'PIL.MicImagePlugin', 'PIL.FpxImagePlugin', 'PIL.McIdasImagePlugin',
    'PIL.PixarImagePlugin', 'PIL.SunImagePlugin', 'PIL.IptcImagePlugin',
    'PIL.DcxImagePlugin', 'PIL.CurImagePlugin', 'PIL.FliImagePlugin',
]

# Only include PIL formats we actually use
PIL_INCLUDES = [
    'PIL._tkinter_finder', 'PIL.Image', 'PIL.ImageTk',
    'PIL.JpegImagePlugin', 'PIL.PngImagePlugin', 'PIL.GifImagePlugin',
    'PIL.BmpImagePlugin', 'PIL.WebPImagePlugin', 'PIL.TiffImagePlugin',
    'PIL.IcoImagePlugin',
]

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('ico.ico', '.')],  # Include icon file
    hiddenimports=PIL_INCLUDES + ['mutagen'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove unnecessary data files to reduce size
EXCLUDE_DATA = [
    'tcl/tzdata', 'tcl/msgs', 'tk/msgs', 'tcl/encoding',
    'share/locale', 'share/doc', 'share/man', 'share/info',
    'lib/tcl8', 'lib/tk8', '.dist-info',
]
a.datas = [d for d in a.datas if not any(x in d[0] for x in EXCLUDE_DATA)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Renamer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,       # Strip debug symbols
    upx=True,         # Compress with UPX (if available)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,    # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ico.ico',   # Application icon
)
