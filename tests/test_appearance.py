"""Preference persistence and Tk geometry/theme/navigation integration checks."""
import json
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from matplotlib.backend_bases import MouseEvent
from matplotlib.colors import to_hex
from story_atlas.app import StoryAtlas
from story_atlas.settings import Settings, DEFAULTS
from story_atlas.relationship_dialog import RelationshipDialog


class SettingsTests(unittest.TestCase):
    def test_persistence_and_invalid_file_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            Settings(path).save(theme="light", text_size=14, roster_width=320)
            self.assertEqual(Settings(path).values["text_size"], 14)
            path.write_text('{"theme":"invalid","text_size":999}', encoding="utf-8")
            self.assertEqual(Settings(path).values, DEFAULTS)
            path.write_text('{"graph_inspector_width":9999}', encoding='utf-8')
            self.assertEqual(Settings(path).values['graph_inspector_width'], DEFAULTS['graph_inspector_width'])
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(Settings(path).values, DEFAULTS)


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        try:
            self.app = StoryAtlas(Path(self.temp.name) / "test.db")
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")
        self.addCleanup(self.cleanup_app)
        self.app.update()
        self.callback_errors = []
        self.app.report_callback_exception = lambda *args: self.callback_errors.append(args)

    def cleanup_app(self):
        if self.app.winfo_exists():
            self.app.database.close()
            self.app.destroy()

    def assert_inside(self, widget, container):
        self.assertTrue(widget.winfo_ismapped(), str(widget))
        x = widget.winfo_rootx() - container.winfo_rootx()
        y = widget.winfo_rooty() - container.winfo_rooty()
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)
        self.assertLessEqual(x + widget.winfo_width(), container.winfo_width() + 2)
        self.assertLessEqual(y + widget.winfo_height(), container.winfo_height() + 2)

    def test_theme_text_and_roster_width_survive_restart(self):
        self.app.set_appearance("light", 14)
        self.app.update()
        self.app.characters.panes.sashpos(0, 310)
        self.app.update()
        self.app.close()
        self.app = StoryAtlas(Path(self.temp.name) / "test.db")
        self.app.update()
        self.assertEqual(self.app.atlas_text_size, 14)
        self.assertEqual(self.app.settings.values["theme"], "light")
        self.assertAlmostEqual(self.app.characters.panes.sashpos(0), 310, delta=5)
        self.assertEqual(self.app.characters.fields["notes"].cget("bg"), "#ffffff")
        self.assertEqual(to_hex(self.app.graph.figure.get_facecolor()), "#f3f6fa")

    def test_graph_inspector_drag_width_survives_resize_and_restart(self):
        graph = self.app.graph
        self.app.tabs.select(graph)
        self.app.update()
        width = graph.body.winfo_width()
        graph.body.sashpos(0, width - 375)
        graph.remember_inspector_width()
        self.app.update()
        dragged = graph.body.sashpos(0)
        self.assertAlmostEqual(width - dragged, 375, delta=12)
        self.app.geometry('900x600')
        self.app.update()
        self.assertAlmostEqual(graph.body.winfo_width() - graph.body.sashpos(0), 375, delta=12)
        self.app.close()
        self.app = StoryAtlas(Path(self.temp.name) / 'test.db')
        self.app.tabs.select(self.app.graph)
        self.app.update()
        restored = self.app.graph.body.winfo_width() - self.app.graph.body.sashpos(0)
        self.assertAlmostEqual(restored, self.app.settings.values['graph_inspector_width'], delta=12)

    def test_chapter_outline_long_duplicate_titles_and_empty_state_at_large_text(self):
        first = self.app.database.chapters.save('An unusually long chapter title ' * 4)
        second = self.app.database.chapters.save('An unusually long chapter title ' * 4)
        for mode in ('dark', 'light'):
            for geometry in ('900x600', '1280x720'):
                self.app.geometry(geometry)
                self.app.set_appearance(mode, 16)
                self.app.tabs.select(self.app.events)
                self.app.events.reveal_chapter(second, self.app.database.path)
                self.app.update()
                view = self.app.events
                self.assertIn(f'#{first}', view.outline.item(f'chapter:{first}', 'values')[0])
                self.assertIn(f'#{second}', view.outline.item(f'chapter:{second}', 'values')[0])
                self.assertEqual(view.outline.selection(), (f'chapter:{second}',))
                self.assertGreaterEqual(view.tree.winfo_height(), 100)
                self.assertGreaterEqual(view.outline.winfo_width(), 100)
                self.assertIn('No chapter summary', view.detail_text.get())

    def test_laptop_geometry_at_simulated_scaling(self):
        # Tk points-to-pixels simulation, not a change to Windows monitor DPI.
        for scale in (1, 1.25, 1.5):
            for mode in ("dark", "light"):
                self.app.tk.call("tk", "scaling", (96 / 72) * scale)
                self.app.geometry("1280x720")
                self.app.set_appearance(mode, 14)
                self.app.update()
                self.app.tabs.select(self.app.characters)
                self.app.update()
                for button in self.app.characters.buttons.items:
                    self.assert_inside(button, self.app)
                self.assertLess(self.app.characters.scroller.canvas.yview()[1], 1)
                self.app.tabs.select(self.app.events)
                self.app.update()
                detail_controls = (self.app.events.detail_action_menu,) if self.app.events._compact_detail else self.app.events.detail_actions.items
                for button in (*self.app.events.actions.items, *detail_controls):
                    self.assert_inside(button, self.app)
                if self.app.events._compact_detail:
                    self.assertEqual([self.app.events.detail_menu.entrycget(i, 'label') for i in range(3)],
                                     ['Record change', 'Start relationship', 'Graph at event'])
                self.assertGreaterEqual(self.app.events.tree.winfo_height(), 100)
                self.assertEqual(self.app.events.detail_body.cget("bg"), self.app.atlas_palette["detail"])
                self.app.tabs.select(self.app.graph)
                self.app.update()
                self.app.graph.controls.reflow()
                self.app.update()
                for button in self.app.graph.controls.items:
                    self.assert_inside(button, self.app)
                self.assertGreater(self.app.graph.canvas.get_tk_widget().winfo_height(), 100)
        self.assertEqual(self.callback_errors, [])

    def test_small_dialog_scrolls_with_visible_actions_and_live_theme(self):
        for name in ("Mira", "Pip"):
            self.app.database.save_character({"name": name})
        dialog = RelationshipDialog(self.app, self.app.database, self.app.refresh)
        dialog.geometry("460x360")
        self.app.set_appearance("light", 16)
        self.app.update()
        self.assert_inside(dialog.save_button, dialog)
        self.assert_inside(dialog.close_button, dialog)
        self.assertLess(dialog.scroller.canvas.yview()[1], 1)
        self.assertEqual(dialog.notes.cget("bg"), "#ffffff")
        dialog.focus_force()
        dialog.boxes["kind"].focus_set()
        self.app.update()
        self.assert_inside(dialog.boxes["kind"], dialog.scroller.canvas)
        dialog.destroy()

    def test_compact_window_large_text_controls_remain_accessible(self):
        self.app.tk.call("tk", "scaling", 96 / 72)
        self.app.geometry("760x480")
        self.app.set_appearance("dark", 16)
        self.app.update()
        for view in self.app.views:
            self.app.tabs.select(view)
            self.app.update()
            if view is self.app.graph:
                for button in view.controls.items:
                    self.assert_inside(button, self.app)
            elif view is self.app.characters:
                for button in view.buttons.items:
                    self.assert_inside(button, self.app)
            elif view is self.app.events:
                for button in view.actions.items:
                    self.assert_inside(button, self.app)
                self.assert_inside(view.detail_action_menu, self.app)
                self.assertGreaterEqual(view.tree.winfo_height(), 100)
                self.assertGreaterEqual(view.detail_body.winfo_height(), 50)
        self.assertEqual(self.callback_errors, [])

    def test_navigation_zoom_pan_fit_and_logged_export(self):
        first = self.app.database.save_character({"name": "Mira"})
        second = self.app.database.save_character({"name": "Pip"})
        self.app.database.save_relationship(first, second, "Ally")
        self.app.refresh()
        graph = self.app.graph
        self.app.tabs.select(graph)
        self.app.update()
        graph.canvas.draw()
        axes = graph.figure.axes[0]
        original = axes.get_xlim()
        graph.controls.toggle("zoom")
        x, y, width, height = axes.bbox.bounds
        for name, px, py in (("button_press_event", x + width * .2, y + height * .2),
                             ("motion_notify_event", x + width * .8, y + height * .8),
                             ("button_release_event", x + width * .8, y + height * .8)):
            event = MouseEvent(name, graph.canvas, px, py, button=1)
            graph.canvas.callbacks.process(name, event)
        self.assertNotEqual(axes.get_xlim(), original)
        graph.controls.fit()
        self.assertEqual(axes.get_xlim(), original)
        graph.controls.toggle("pan")
        self.assertEqual(graph.toolbar.mode.name, "PAN")
        graph.reset_layout()
        self.assertFalse(graph.toolbar.mode)
        output = Path(self.temp.name) / "snapshot.png"
        with patch("story_atlas.graph_actions.filedialog.asksaveasfilename", return_value=str(output)):
            graph.export()
        self.assertTrue(output.exists())
        self.assertEqual(len(json.loads(output.with_suffix(".json").read_text())["relationships"]), 1)
        self.assertEqual(self.app.database.activity()[0]["action"], "Graph snapshot exported")
        self.assertEqual(self.callback_errors, [])
