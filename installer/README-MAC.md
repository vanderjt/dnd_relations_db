# Story Atlas on macOS

The repository includes a Mac source launcher: **Launch Story Atlas.command**
in the repository's main folder. The `.exe` in this folder is for Windows.
There is no standalone macOS installer yet. The launcher and platform changes
have been checked on Windows, but a native Mac launch has not been tested.

## First setup

1. Install [Python 3.13 for macOS](https://www.python.org/downloads/macos/)
   and [Node.js LTS](https://nodejs.org/). These are needed to set up the source app.
2. Clone the branch in Terminal. Mac users can skip downloading the Windows
   installer by setting `GIT_LFS_SKIP_SMUDGE` for the clone:

   ```bash
   GIT_LFS_SKIP_SMUDGE=1 git clone --branch codex/repo-housekeeping https://github.com/vanderjt/dnd_relations_db.git
   cd dnd_relations_db
   ```

3. Double-click **Launch Story Atlas.command** in Finder, or run it in Terminal:

   ```bash
   bash "Launch Story Atlas.command"
   ```

The launcher creates a Python environment in `.mac-env`, downloads the native
Mac dependencies, and builds the frontend. Initial setup needs internet access.
The app uses macOS's built-in WebKit through pywebview; it does not need Windows
WebView2. See the [pywebview platform guide](https://pywebview.flowrl.com/guide/web_engine.html).

## Run preview_main.py directly (without a launcher)

Open Terminal in the repository's main folder. Install dependencies into a
Mac-created environment and build the frontend once:

```bash
python3.13 -m venv .mac-env
.mac-env/bin/python -m pip install -r requirements-preview-macos.txt
cd preview
npm ci
npm run build
cd ..
```

Run the Python source directly:

```bash
.mac-env/bin/python preview_main.py
```

Use that same command on later launches. After pulling frontend updates, run
`npm run build` inside `preview` before launching again. After requirements
change, rerun the pip install command above.

If you received a copied repository folder from someone else, create your
Python environment on your own Mac. Do not reuse their `.build-env` or
`.mac-env`: Python environments are not portable between computers. If a
copied `.mac-env` already exists, rename it before creating a fresh one:

```bash
mv .mac-env ".mac-env-copied-$(date +%Y%m%d-%H%M%S)"
python3.13 -m venv .mac-env
```

The `.cmd` launcher, `.exe` installer, and `dist/StoryAtlasPreview` Windows
package are not used by this source command. If importing the host fails,
run this with the same environment and use the resulting error to diagnose it:

```bash
.mac-env/bin/python -c "import webview; print('Preview host ready')"
```

## Later launches and updates

Double-click the same launcher. Dependencies and frontend assets are reused.
After a Git update, changed requirements or frontend sources trigger setup
again as needed. Node.js is only used when the frontend needs rebuilding.

Stories and backups are stored outside the repository, in:

```text
~/Library/Application Support/StoryAtlasPreview
```

Open the example stories from `examples/saved-stories` using the app's file
picker. The launcher forwards arguments; for example:

```bash
bash "Launch Story Atlas.command" --home "$HOME/My Story Atlas Data"
```

## If launching fails

The Terminal window displays setup and startup errors. If Finder says the
launcher is not executable, run this once from the repository folder:

```bash
chmod +x "Launch Story Atlas.command"
```

If macOS blocks opening the script, run the `bash` command above in Terminal
to see the error. Install Python 3.13 if requested; the launcher intentionally
uses that version to match the Windows build. To select a particular Python:

```bash
STORY_ATLAS_PYTHON=/path/to/python3.13 bash "Launch Story Atlas.command"
```

If dependency installation fails, check the pip error and your connection.
If an existing `.mac-env` was copied from another computer or uses a different
Python version, rename that folder and launch again to create a fresh one.
