#!/bin/bash
set -euo pipefail

# Finder opens .command files in Terminal; preserve errors long enough to read.
on_exit() {
  result=$?
  if [ "$result" -ne 0 ]; then
    printf '\nStory Atlas could not start. See the error above.\n'
    if [ -t 0 ]; then read -r -p 'Press Return to close this window.' || true; fi
  fi
}
trap on_exit EXIT

cd -- "$(dirname -- "$0")"
if [ "$(uname -s)" != 'Darwin' ]; then
  echo 'This launcher is for macOS. On Windows, use Launch Story Atlas.cmd.'
  exit 1
fi

# Finder may omit the PATH entries used by Homebrew and python.org installers.
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:$PATH"
python_bin="${STORY_ATLAS_PYTHON:-python3.13}"
if [ -z "${STORY_ATLAS_PYTHON:-}" ] && ! command -v "$python_bin" >/dev/null 2>&1; then python_bin=python3; fi
if ! command -v "$python_bin" >/dev/null 2>&1 || ! "$python_bin" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 13) else 1)'; then
  echo 'Install Python 3.13 for macOS from https://www.python.org/downloads/macos/ and try again.'
  echo 'You can set STORY_ATLAS_PYTHON to the full path of a Python 3.13 executable.'
  exit 1
fi

if [ ! -x '.mac-env/bin/python' ]; then
  echo 'Creating the local Mac Python environment...'
  "$python_bin" -m venv .mac-env
fi
python='.mac-env/bin/python'
if ! "$python" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 13) else 1)'; then
  echo 'The .mac-env folder uses a different Python version. Rename it and relaunch with Python 3.13.'
  exit 1
fi
if [ ! -f '.mac-env/requirements-installed.txt' ] || ! cmp -s requirements-preview-macos.txt .mac-env/requirements-installed.txt; then
  echo 'Installing Mac app dependencies (internet required on first run)...'
  "$python" -m pip install -r requirements-preview-macos.txt
  cp requirements-preview-macos.txt .mac-env/requirements-installed.txt
fi

# Rebuild after relevant source changes, but reuse assets on subsequent launches.
frontend_hash=$("$python" - <<'PY'
import hashlib
from pathlib import Path
digest = hashlib.sha256()
for name in ('preview/package.json', 'preview/package-lock.json', 'preview/build.mjs',
             'preview/index.html', 'preview/tsconfig.json', 'preview/src',
             'prototypes/phase2/studio.css', 'prototypes/phase2/refinements.css',
             'prototypes/phase2/type.css', 'prototypes/phase2/themes',
             'prototypes/phase2/ornaments'):
    root = Path(name)
    files = sorted(p for p in root.rglob('*') if p.is_file()) if root.is_dir() else [root]
    for file in files:
        digest.update(str(file).encode())
        digest.update(file.read_bytes())
print(digest.hexdigest())
PY
)
previous_hash=''
if [ -f '.mac-env/frontend.sha256' ]; then previous_hash=$(cat .mac-env/frontend.sha256); fi
if [ ! -f 'preview/dist/index.html' ] || [ ! -f 'preview/dist/app.js' ] || [ "$frontend_hash" != "$previous_hash" ]; then
  if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo 'Install Node.js LTS from https://nodejs.org/ and try again.'
    exit 1
  fi
  echo 'Building the frontend (internet required to download dependencies)...'
  (cd preview && npm ci && npm run build)
  printf '%s\n' "$frontend_hash" > .mac-env/frontend.sha256
fi

echo 'Starting Story Atlas...'
"$python" preview_main.py "$@"
