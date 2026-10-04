from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH)
datas, binaries, hiddenimports = collect_all('webview')
datas += [(str(root / 'preview/dist'), 'preview/dist'),
          (str(root / 'story_atlas/resources/greyhaven.json'), 'story_atlas/resources'),
          (str(root / 'docs/USER_GUIDE.md'), 'documentation')]
for package in ('pywebview', 'pythonnet', 'clr_loader', 'bottle', 'proxy_tools', 'cffi'):
    datas += copy_metadata(package)
for name in ('sqlite3.dll', 'libffi-8.dll', 'ffi.dll'):
    dll = Path(sys.base_prefix) / 'Library/bin' / name
    if dll.exists():
        binaries.append((str(dll), '.'))
a = Analysis([str(root / 'preview_main.py')], pathex=[str(root)], datas=datas,
             binaries=binaries, hiddenimports=hiddenimports + ['webview.platforms.winforms', 'webview.platforms.edgechromium'],
             excludes=['PyQt5','PyQt6','PySide2','PySide6','qtpy','gtk','gi','matplotlib','numpy','tkinter','IPython','pytest'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='StoryAtlasPreview',
          console=False, upx=False, icon=str(root / 'story_atlas/resources/story-atlas.ico'))
coll = COLLECT(exe, a.binaries, a.datas, name='StoryAtlasPreview', upx=False)
