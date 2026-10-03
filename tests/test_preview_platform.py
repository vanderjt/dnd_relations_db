"""Check platform startup without opening a native window or touching stories."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

import preview_main


class PreviewPlatformTests(unittest.TestCase):
    def test_mac_home_uses_application_support_even_with_windows_env(self):
        with patch.object(preview_main.sys, 'platform', 'darwin'), \
                patch.dict(preview_main.os.environ, {'LOCALAPPDATA': 'windows-data'}):
            self.assertEqual(preview_main.default_preview_home(),
                             Path.home() / 'Library' / 'Application Support' / 'StoryAtlasPreview')

    def test_windows_home_preserves_existing_location(self):
        with patch.object(preview_main.sys, 'platform', 'win32'), \
                patch.dict(preview_main.os.environ, {'LOCALAPPDATA': 'windows-data'}):
            self.assertEqual(preview_main.default_preview_home(),
                             Path('windows-data') / 'StoryAtlasPreview')

    def test_startup_selects_native_mac_renderer_and_preserves_windows_renderer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            assets = root / 'preview' / 'dist'
            assets.mkdir(parents=True)
            (assets / 'index.html').write_text('<html></html>')
            for platform in ('darwin', 'win32'):
                with self.subTest(platform=platform):
                    webview = Mock()
                    webview.create_window.return_value.events.closing = MagicMock()
                    worker = Mock()
                    with patch.object(preview_main.sys, 'platform', platform), \
                            patch.object(preview_main.sys, 'argv', ['preview_main.py', '--home', folder]), \
                            patch.object(preview_main, '__file__', str(root / 'preview_main.py')), \
                            patch.object(preview_main, 'PreviewWorker', return_value=worker) as factory, \
                            patch.dict('sys.modules', {'webview': webview}):
                        preview_main.main()
                    factory.assert_called_once_with(root, root / 'prototypes' / 'phase2' / 'greyhaven.json')
                    if platform == 'darwin':
                        webview.start.assert_called_once_with(debug=False)
                    else:
                        webview.start.assert_called_once_with(gui='edgechromium', debug=False)
                    worker.close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
