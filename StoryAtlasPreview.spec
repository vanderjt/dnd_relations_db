"""Freeze the supported Windows host and current frontend into one app folder."""
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH)
frontend = root / "preview" / "dist"
for filename in ("index.html", "app.js", "app.css"):
    if not (frontend / filename).is_file():
        raise SystemExit("Build the frontend before packaging: cd preview && npm ci && npm run build")

# The build script creates dist from a clean staging folder. Do not package the
# source tree, browser prototypes, node_modules, or local story data.
datas, binaries, hiddenimports = collect_all("webview")
datas += [
    (str(frontend), "preview/dist"),
    (str(root / "story_atlas/resources/greyhaven.json"), "story_atlas/resources"),
    (str(root / "docs/USER_GUIDE.md"), "documentation"),
    (str(root / "VERSION"), "."),
]
for package in ("pywebview", "pythonnet", "clr_loader", "bottle", "proxy_tools", "cffi"):
    datas += copy_metadata(package)

# Conda keeps these DLLs outside the interpreter directory; ordinary Python
# installations let PyInstaller find the equivalent dependencies automatically.
for name in ("sqlite3.dll", "libffi-8.dll", "ffi.dll"):
    dll = Path(sys.base_prefix) / "Library/bin" / name
    if dll.exists():
        binaries.append((str(dll), "."))

analysis = Analysis(
    [str(root / "preview_main.py")],
    pathex=[str(root)],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports + ["webview.platforms.winforms", "webview.platforms.edgechromium"],
    excludes=[
        "PyQt5", "PyQt6", "PySide2", "PySide6", "qtpy", "gtk", "gi",
        "matplotlib", "numpy", "tkinter", "IPython", "pytest",
    ],
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="StoryAtlasPreview",
    console=False,
    upx=False,
    icon=str(root / "story_atlas/resources/story-atlas.ico"),
)
collection = COLLECT(
    executable, analysis.binaries, analysis.datas, name="StoryAtlasPreview", upx=False
)
