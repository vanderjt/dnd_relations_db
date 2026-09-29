"""Windows/source startup; writable data never defaults to the program folder."""
from pathlib import Path
import argparse
import json
import os
import sqlite3
import sys
from story_atlas.paths import prepare_data
from story_atlas.settings import Settings


def main():
    parser = argparse.ArgumentParser(description="Story Atlas character manager")
    parser.add_argument("--database", type=Path, help="Explicit story path (new or existing)")
    parser.add_argument("--data-dir", type=Path, help="Override the per-user data directory")
    parser.add_argument("--welcome", action="store_true", help="Show startup choices again")
    parser.add_argument("--self-test", type=Path, metavar="REPORT", help="Run isolated packaging checks and write a JSON report")
    args = parser.parse_args()
    if getattr(sys, 'frozen', False):
        # Conda's Tcl 8.6.15 fails to initialize when its library is supplied
        # as a long absolute Windows path. Resolve CLI paths first, then keep
        # the bundled libraries reachable by short paths relative to the EXE.
        for name in ('database', 'data_dir', 'self_test'): 
            value = getattr(args, name)
            if value is not None:
                setattr(args, name, value.expanduser().resolve())
        os.chdir(Path(sys.executable).resolve().parent)
        bundle = Path(sys._MEIPASS)
        os.environ['TCL_LIBRARY'] = os.path.relpath(bundle / '_tcl_data', Path.cwd()).replace('\\', '/')
        os.environ['TK_LIBRARY'] = os.path.relpath(bundle / '_tk_data', Path.cwd()).replace('\\', '/')
    try:
        folder = prepare_data(args.data_dir)
        if args.self_test:
            from story_atlas.diagnostics import run
            return run(folder, args.self_test)
        # Set Matplotlib's writable cache before importing the renderer.
        from story_atlas.app import StoryAtlas
        from story_atlas.onboarding import Welcome, resume_path
        settings = Settings(folder / "settings.json")
        path = None if args.welcome else resume_path(settings, args.database)
        while True:
            if path is None:
                legacy = Path(__file__).parent / "data" / "story_atlas.db" if not getattr(sys, "frozen", False) else None
                welcome = Welcome(folder, settings, legacy)
                welcome.mainloop()
                path = welcome.result
                if path is None:
                    return 0
            try:
                app = StoryAtlas(path, settings_path=folder / "settings.json")
                break
            except (ValueError, OSError, sqlite3.Error) as error:
                report_error(str(error))
                path = None
        app.mainloop()
        return 0
    except (ValueError, OSError, sqlite3.Error) as error:
        if args.self_test:
            args.self_test.write_text(json.dumps(dict(ok=False, error=str(error))), encoding="utf-8")
        else:
            report_error(str(error))
        return 1


def report_error(text):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Cannot start Story Atlas", text, parent=root)
    root.destroy()


if __name__ == "__main__":
    raise SystemExit(main())
