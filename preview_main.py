"""Windows React/pywebview preview. The Tkinter main.py remains independent."""
import argparse
import logging
import os
from pathlib import Path
import threading

from story_atlas.preview_worker import PreviewWorker


class PreviewBridge:
    def __init__(self, worker):
        self._worker = worker
        self._window = None
        self._allow_close = False
        self._close_lock = threading.Lock()
        self._close_dispatching = False
        self._close_timer = None

    def command(self, name, args=None):
        """The only exposed bridge entry point; an explicit command allowlist."""
        allowed = {'bootstrap', 'workspace', 'profile', 'write', 'new_story',
                   'save_draft', 'get_draft', 'discard_draft', 'preference', 'backup'}
        if name == 'close':
            self._schedule_close()
            return {'ok': True, 'data': None}
        if name in ('open_story', 'restore'):
            import webview
            try:
                directory = self._worker.home.resolve() / ('backups' if name == 'restore' else 'stories')
                paths = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False,
                    directory=str(directory if directory.is_dir() else Path.home()),
                    # pywebview 6.1 rejects hyphenated extensions in filters.
                    # Keep existing filenames; PreviewStore validates the format.
                    file_types=('Story files (*.*)',))
                if not paths:
                    return {'ok': True, 'data': None}
                return self._worker.call(name, {'path': paths[0]})
            except Exception as error:
                return {'ok': False, 'error': {'code': 'picker', 'message': str(error)}}
        if name not in allowed:
            return {'ok': False, 'error': {'code': 'validation', 'message': 'Unknown preview command.'}}
        return self._worker.call(name, args)

    def _on_closing(self):
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
        with self._close_lock:
            if self._allow_close:
                return
            self._allow_close = True
            self._close_timer = threading.Timer(0.2, self._window.destroy)
            self._close_timer.daemon = True
            self._close_timer.start()

    def _request_close(self):
        try:
            ready = self._window.evaluate_js('Boolean(window.previewReady)')
            if ready:
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, default=Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'StoryAtlasPreview')
    parser.add_argument('--story', type=Path)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    assets = root / 'preview' / 'dist' / 'index.html'
    if not assets.exists():
        raise SystemExit('Preview assets are missing. Run: cd preview && npm ci && npm run build')
    try:
        import webview
    except ImportError:
        raise SystemExit('Preview host missing. Install requirements-preview.txt into .build-env.')
    worker = PreviewWorker(args.home, root / 'prototypes' / 'phase2' / 'greyhaven.json')
    if args.story:
        result = worker.call('open_story', {'path': str(args.story)})
        if not result['ok']:
            worker.close()
            raise SystemExit(result['error']['message'])
    bridge = PreviewBridge(worker)
    window = webview.create_window('Story Atlas Preview', str(assets), js_api=bridge,
                                  width=1360, height=900, min_size=(760, 560), text_select=True)
    bridge._window = window
    window.events.closing += bridge._on_closing
    try:
        webview.start(gui='edgechromium', debug=args.debug)
    finally:
        worker.close()


if __name__ == '__main__':
    main()
