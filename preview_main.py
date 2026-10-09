"""Native React/pywebview host for Story Atlas."""

import argparse
import logging
import os
import sys
from pathlib import Path
import threading

from story_atlas.preview_worker import PreviewWorker


class PreviewBridge:
    """Expose approved commands and coordinate native/frontend shutdown."""

    def __init__(self, worker):
        self._worker = worker
        self._window = None
        self._allow_close = False
        self._close_lock = threading.Lock()
        self._close_dispatching = False
        self._close_timer = None

    def command(self, name, args=None):
        """The only exposed bridge entry point; an explicit command allowlist."""
        allowed_commands = {
            'bootstrap',
            'workspace',
            'profile',
            'write',
            'new_story',
            'save_draft',
            'get_draft',
            'discard_draft',
            'preference',
            'backup',
        }
        if name == 'close':
            self._schedule_close()
            return {'ok': True, 'data': None}
        if name in ('open_story', 'restore'):
            import webview

            try:
                picker_directory = self._worker.home.resolve() / (
                    'backups' if name == 'restore' else 'stories'
                )
                selected_paths = self._window.create_file_dialog(
                    webview.FileDialog.OPEN,
                    allow_multiple=False,
                    directory=str(
                        picker_directory if picker_directory.is_dir() else Path.home()
                    ),
                    # pywebview 6.1 rejects hyphenated extensions in filters.
                    # Keep existing filenames; PreviewStore validates the format.
                    file_types=('Story files (*.*)',),
                )
                if not selected_paths:
                    return {'ok': True, 'data': None}
                return self._worker.call(name, {'path': selected_paths[0]})
            except Exception as error:
                return {'ok': False, 'error': {'code': 'picker', 'message': str(error)}}
        if name not in allowed_commands:
            return {
                'ok': False,
                'error': {'code': 'validation', 'message': 'Unknown preview command.'},
            }
        return self._worker.call(name, args)

    def _on_closing(self):
        """Defer native close until the frontend has handled pending editors."""
        if self._allow_close:
            return True
        # FormClosing runs synchronously on the renderer's UI thread. Never
        # evaluate JavaScript here: WebView2 needs that same thread to reply.
        with self._close_lock:
            if not self._close_dispatching:
                self._close_dispatching = True
                threading.Thread(target=self._request_close, daemon=True).start()
        return False

    def _schedule_close(self):
        """Destroy the window once, after the bridge response can return."""
        with self._close_lock:
            if self._allow_close:
                return
            self._allow_close = True
            self._close_timer = threading.Timer(0.2, self._window.destroy)
            self._close_timer.daemon = True
            self._close_timer.start()

    def _request_close(self):
        try:
            frontend_ready = self._window.evaluate_js('Boolean(window.previewReady)')
            if frontend_ready:
                self._window.run_js('window.dispatchEvent(new Event("preview-close"))')
            else:
                # No editors exist before the frontend is ready.
                self._schedule_close()
        except Exception:
            logging.exception('Could not request preview shutdown')
            # Do not discard potentially pending work on a renderer error.
        finally:
            with self._close_lock:
                self._close_dispatching = False


def default_preview_home():
    """Keep stories and app settings in their established platform location."""
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'StoryAtlasPreview'
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'StoryAtlasPreview'


def main():
    """Open the built frontend and keep the database worker alive with it."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, default=default_preview_home())
    parser.add_argument('--story', type=Path)
    parser.add_argument('--debug', action='store_true')
    options = parser.parse_args()
    project_root = Path(__file__).resolve().parent
    frontend_entry = project_root / 'preview' / 'dist' / 'index.html'
    if not frontend_entry.exists():
        raise SystemExit(
            'Preview assets are missing. Run: cd preview && npm ci && npm run build'
        )
    try:
        import webview
    except ImportError:
        raise SystemExit(
            'Preview host missing. Use the launcher for your platform to set up dependencies.'
        )
    worker = PreviewWorker(
        options.home, project_root / 'story_atlas' / 'resources' / 'greyhaven.json'
    )
    if options.story:
        result = worker.call('open_story', {'path': str(options.story)})
        if not result['ok']:
            worker.close()
            raise SystemExit(result['error']['message'])
    bridge = PreviewBridge(worker)
    window = webview.create_window(
        'Story Atlas Preview',
        str(frontend_entry),
        js_api=bridge,
        width=1360,
        height=900,
        min_size=(760, 560),
        text_select=True,
    )
    bridge._window = window
    window.events.closing += bridge._on_closing
    try:
        if sys.platform == 'win32':
            webview.start(gui='edgechromium', debug=options.debug)
        else:
            webview.start(debug=options.debug)
    finally:
        worker.close()


if __name__ == '__main__':
    main()
