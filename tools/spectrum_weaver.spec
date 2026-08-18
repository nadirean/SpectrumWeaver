# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SpectrumWeaver.

The app deliberately avoids librosa/scipy: decoding uses soundfile (WAV/FLAC/OGG)
with an audioread -> FFmpeg fallback for lossy formats (FFmpeg binary bundled via
imageio-ffmpeg). Build from the project root with:

    uv run pyinstaller tools/spectrum_weaver.spec
"""

import os
import sys
from pathlib import Path

project_root = Path(os.getcwd())
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

main_script = src_path / "spectrum_weaver.py"

hidden_imports = [
    # PySide6/Qt modules
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets',
    # PyQtGraph
    'pyqtgraph.exporters',
    'pyqtgraph.graphicsItems',
    'pyqtgraph.widgets',
    # Other (the imageio_ffmpeg hook collects the current platform's FFmpeg binary)
    'imageio_ffmpeg',
    'mutagen',
]

# Data files to include
datas = [
    (str(src_path / "assets" / "icon.png"), "assets"),
    (str(src_path / "assets" / "styles.qss"), "assets"),
    (str(project_root / "images" / "icon.ico"), "images"),
]

# Binary files to exclude (to reduce size)
excludes = [
    'tkinter',
    'matplotlib',
    'IPython',
    'jupyter',
    'notebook',
    'pandas',
    'sklearn',
    'scipy',
    'librosa',
    'numba',
    'PIL',
    'cv2',
    'torch',
    'tensorflow',
    # Unused Qt modules (kept out to shrink the bundle)
    'PySide6.QtQml',
    'PySide6.QtQuick',
    'PySide6.QtNetwork',
    'PySide6.QtDBus',
    'PySide6.QtSql',
    'PySide6.QtTest',
    'PySide6.QtPrintSupport',
    'PySide6.QtXml',
    'PySide6.QtConcurrent',
]

block_cipher = None

a = Analysis(
    [str(main_script)],
    pathex=[str(src_path)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Drop Qt translation files (not used)
a.datas = [d for d in a.datas if not d[0].startswith("PySide6/translations")]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='spectrum_weaver',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "images" / "icon.ico"),
    version=None,
)
