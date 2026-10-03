"""Exercise filters against the real pywebview parser, not a permissive mock."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from webview.util import parse_file_type
from preview_main import PreviewBridge


class PickerTests(unittest.TestCase):
    def test_open_and_restore_use_valid_filters_and_preserve_selected_path(self):
        selected = str(Path('examples/saved-stories/Frankenstein.atlas-preview').resolve())
        for command in ('open_story', 'restore'):
            with self.subTest(command=command):
                worker = SimpleNamespace(home=Path('.'), call=Mock(return_value={'ok': True}))
                bridge = PreviewBridge(worker)
                def dialog(*args, **kwargs):
                    for item in kwargs['file_types']:
                        parse_file_type(item)
                    return (selected,)
                bridge._window = SimpleNamespace(create_file_dialog=dialog)
                self.assertTrue(bridge.command(command)['ok'])
                worker.call.assert_called_once_with(command, {'path': selected})

    def test_cancel_does_not_open_or_create_a_story(self):
        worker = SimpleNamespace(home=Path('.'), call=Mock())
        bridge = PreviewBridge(worker)
        bridge._window = SimpleNamespace(create_file_dialog=lambda *args, **kwargs: None)
        self.assertEqual(bridge.command('open_story'), {'ok': True, 'data': None})
        worker.call.assert_not_called()
