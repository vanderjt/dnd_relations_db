"""Close callbacks must release the Windows UI thread before calling JS."""
import threading
import unittest
from preview_main import PreviewBridge


class PreviewCloseTests(unittest.TestCase):
    def test_native_callback_does_not_wait_for_renderer_and_coalesces_clicks(self):
        entered, release, dispatched = threading.Event(), threading.Event(), threading.Event()
        class Window:
            calls = 0
            def evaluate_js(self, script):
                self.calls += 1
                entered.set()
                release.wait(2)
                return True
            def run_js(self, script):
                dispatched.set()
        bridge = PreviewBridge(None)
        bridge._window = Window()
        try:
            self.assertFalse(bridge._on_closing())
            self.assertTrue(entered.wait(1))
            self.assertFalse(bridge._on_closing())
            self.assertEqual(bridge._window.calls, 1)
            self.assertFalse(dispatched.is_set())
        finally:
            release.set()
        self.assertTrue(dispatched.wait(1))

    def test_confirmed_close_is_idempotent(self):
        destroyed = threading.Event()
        class Window:
            calls = 0
            def destroy(self):
                self.calls += 1
                destroyed.set()
        bridge = PreviewBridge(None)
        bridge._window = Window()
        bridge.command('close')
        bridge.command('close')
        self.assertTrue(bridge._on_closing())
        self.assertTrue(destroyed.wait(1))
        self.assertEqual(bridge._window.calls, 1)


if __name__ == '__main__':
    unittest.main()
