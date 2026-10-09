# Story Atlas on macOS

Mac support currently means running the source through
**Launch Story Atlas.command** at the repository root. There is no standalone
Mac installer. The Windows EXE and frozen Windows package cannot run on Mac.
Native Mac validation remains pending; platform-selection unit tests are not
proof of a successful Mac launch.

## First setup

Install [Python 3.13 for macOS](https://www.python.org/downloads/macos/) and
[Node.js with npm](https://nodejs.org/). Initial dependency setup needs internet
access. Skip the large Windows installer when cloning:

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --branch codex/repo-housekeeping https://github.com/vanderjt/dnd_relations_db.git
cd dnd_relations_db
bash "Launch Story Atlas.command"
```

You can also double-click the `.command` file in Finder. It creates a local
`.mac-env`, installs `requirements-preview-macos.txt`, and builds the frontend.
Later launches reuse unchanged dependencies and assets. Changed requirements
or frontend sources trigger setup again. Node/npm are needed for rebuilding.

The host uses macOS's WebKit through pywebview, rather than Windows WebView2.
See the [pywebview platform guide](https://pywebview.flowrl.com/guide/web_engine.html).

## Direct Python launch or VS Code

From a terminal at the repository root:

```bash
python3.13 -m venv .mac-env
.mac-env/bin/python -m pip install -r requirements-preview-macos.txt
cd preview
npm ci
npm run build
cd ..
.mac-env/bin/python preview_main.py
```

In VS Code, select `.mac-env/bin/python` as the interpreter. Use that same
Python launch command later. After frontend changes, run `npm run build` in
`preview`; run `npm ci` first if its lockfile changed. Reinstall Python
requirements when they change. The launcher automates these refreshes when
used instead of the direct command.

Create the environment on this Mac. Copied `.build-env` or `.mac-env` folders
are not portable between computers. If a copied environment already exists,
rename it before creating a fresh one:

```bash
mv .mac-env ".mac-env-copied-$(date +%Y%m%d-%H%M%S)"
python3.13 -m venv .mac-env
```

## Stories and isolated testing

Default stories, backups, and settings live outside the repository:

```text
~/Library/Application Support/StoryAtlasPreview
```

Open copies of the examples from `examples/saved-stories` using the app's
file picker. Opening a file edits that original file. The launcher forwards
all normal CLI options; for disposable development data:

```bash
bash "Launch Story Atlas.command" --home "$PWD/build-verification/mac-dev"
```

`--home` does not isolate an external file selected with `--story` or **Open
story**. Use copied fixtures and keep real campaign data out of tests. See
[Using Story Atlas](../docs/USER_GUIDE.md) for backups and draft recovery.

## Troubleshooting

The Terminal window shows setup and startup errors. If Finder reports that
the launcher is not executable, use the `bash` command above, or make the
checked-out script executable:

```bash
chmod +x "Launch Story Atlas.command"
```

The launcher requires Python 3.13. To choose a specific installation:

```bash
STORY_ATLAS_PYTHON=/path/to/python3.13 bash "Launch Story Atlas.command"
```

If the environment was copied or uses another Python version, rename it and
relaunch. If dependency setup fails, read the pip error and check connectivity.
To inspect a host-import failure in the same environment:

```bash
.mac-env/bin/python -c "import webview; print('Preview host import succeeded')"
```

An import success does not verify the native window. Record the actual error
and platform when reporting a launch issue. Do not bypass an operating-system
security warning to run an untrusted download.
