# Reproducible inputs: CPython 3.13.9 x64 and requirements-build.lock.txt.
from pathlib import Path
import os
import sys
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH)
# A venv based on Anaconda keeps Tcl/SQLite DLLs in the base Library/bin.
# Make these dependencies discoverable without requiring Conda on the target PC.
conda_bin = Path(sys.base_prefix) / 'Library' / 'bin'
binaries = []
if conda_bin.is_dir():
    os.environ['PATH'] = str(conda_bin) + os.pathsep + os.environ.get('PATH', '')
    for name in ('ffi.dll', 'libmpdec-4.dll', 'tcl86t.dll', 'tk86t.dll', 'sqlite3.dll'):
        if (conda_bin / name).is_file():
            binaries.append((str(conda_bin / name), '.'))
datas = [(str(root / 'story_atlas' / 'resources'), 'story_atlas/resources'),
         (str(root / 'story_atlas' / 'build_metadata.json'), 'story_atlas'),
         (str(root / 'docs/legacy/README.md'), 'documentation'),
         (str(root / 'docs/legacy/DISTRIBUTION.md'), 'documentation')]
for name in ('LICENSE_PYTHON.txt', 'LICENSE.txt'):
    license_file = Path(sys.base_prefix) / name
    if license_file.is_file():
        datas.append((str(license_file), 'licenses'))
for package in ('Pillow', 'matplotlib', 'networkx', 'numpy', 'contourpy', 'cycler',
                'fonttools', 'kiwisolver', 'packaging', 'pyparsing', 'python-dateutil', 'six', 'PyInstaller'):
    datas += copy_metadata(package)
a = Analysis([str(root / 'main.py')], pathex=[str(root)], binaries=binaries, datas=datas,
             hiddenimports=['PIL._tkinter_finder'], hookspath=[], runtime_hooks=[],
             hooksconfig={'matplotlib': {'backends': ['TkAgg']}},
             excludes=['PyQt5','PyQt6','PySide2','PySide6','IPython','pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='StoryAtlas',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False,
          icon=str(root / 'story_atlas' / 'resources' / 'story-atlas.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='StoryAtlas')
