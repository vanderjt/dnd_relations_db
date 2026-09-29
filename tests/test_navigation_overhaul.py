"""Menu destinations and independent toolbar rows at supported narrow widths."""
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
from story_atlas.app import StoryAtlas
from story_atlas.widgets import ActionBar


def labels(menu):
    return [menu.entrycget(i, 'label') for i in range((menu.index('end') or 0) + 1) if menu.type(i) != 'separator']


class NavigationOverhaulTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = StoryAtlas(Path(self.temp.name) / 'story.db')
        self.addCleanup(self.cleanup)
        self.errors = []
        self.app.report_callback_exception = lambda *args: self.errors.append(args)
        self.app.update()

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def test_header_visible_at_minimum_large_text_and_long_story_title(self):
        title = 'A very long story title about a journey through distant kingdoms ' * 3
        self.app.database.connection.execute("INSERT OR REPLACE INTO story_metadata(key,value) VALUES('title',?)", (title,))
        self.app.set_appearance('dark', 16)
        self.app.geometry('760x480')
        for mode in ('Simple', 'Advanced', 'Simple'):
            self.app.mode.set(mode)
            self.app.apply_mode()
            self.app.update()
            self.assertIn(title, self.app.title())
            for widget in self.app.header.items:
                self.assertTrue(widget.winfo_viewable(), str(widget))
                self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), self.app.winfo_rootx() + self.app.winfo_width())
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), self.app.header.winfo_rooty() + self.app.header.winfo_height())
            self.assertTrue(self.app.search_button.winfo_viewable())
            self.assertTrue(self.app.mode_box.winfo_viewable())
        self.assertFalse(self.errors)

    def test_commands_grouped_and_callbacks_keep_original_routes(self):
        story = self.app.story_actions
        self.assertEqual(labels(story), ['New story', 'Open story…', 'Recent stories…', 'Sample stories', 'Export all data…', 'Undo saved change', 'Redo saved change'])
        help_menu = self.app.nametowidget(self.app.help_menu['menu'])
        self.assertEqual(labels(help_menu), ['Help and shortcuts', 'About Story Atlas', 'Artwork credits'])
        settings = self.app.nametowidget(self.app.settings_menu['menu'])
        self.assertEqual(labels(settings), ['Appearance…', 'Recovery, Trash, and drafts…', 'Activity log (Advanced)'])
        self.assertEqual(set(labels(self.app.simple.view_menu)), {'Fit view', 'Show planned cast', 'Graph filters', 'Legend · dots & links', 'Collapse / show information pane', 'Zoom rectangle', 'Pan tool'})
        self.assertEqual(set(labels(self.app.simple.more_menu)), {'New chapter', 'Edit selected event', 'Remove event and reassign references…', 'Saved graph views…', 'Export displayed graph…', 'Undo recent character creation'})
        with patch.object(self.app.projects, 'search') as search:
            self.app.search_button.invoke()
            search.assert_called_once()
        with patch.object(self.app.projects, 'choose') as choose:
            story.invoke(0)
            choose.assert_called_once_with(True)
        self.assertTrue(self.app.bind('<Control-k>'))
        self.assertTrue(self.app.bind('<F1>'))

    def test_fixed_width_font_change_reflows_and_minimal_clears_tab_art(self):
        self.app.geometry('760x480')
        self.app.update()
        self.app.set_appearance('light', 16, 'Minimal')
        self.app.update()
        for widget in self.app.header.items:
            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), self.app.winfo_rootx() + 760)
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), self.app.header.winfo_rooty() + self.app.header.winfo_height())
        self.assertEqual(self.app.tabs.atlas_images, [None, None])
        self.assertFalse(self.errors)

    def test_actionbar_rows_do_not_share_widths_and_recreate_destroyed_rows(self):
        window = tk.Toplevel(self.app)
        window.geometry('520x240')
        bar = ActionBar(window)
        bar.pack(fill='x')
        for text in ('Small', 'A significantly longer second control', 'A long first control in next row', 'Tiny'):
            bar.add(ttk.Button(bar, text=text))
        self.app.update()
        # Native Tab traversal follows Tk sibling stacking order, not grid cells.
        # Exercise multiple rows and a later reflow, as well as actual painting.
        for geometry in ('520x240', '760x240', '520x240'):
            window.geometry(geometry)
            self.app.update()
            for current, following in zip(bar.items, bar.items[1:]):
                self.assertIs(current.tk_focusNext(), following)
                self.assertIs(following.tk_focusPrev(), current)
        for widget in bar.items:
            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), bar.winfo_rootx() + bar.winfo_width())
            hit = self.app.winfo_containing(widget.winfo_rootx() + widget.winfo_width() // 2,
                                            widget.winfo_rooty() + widget.winfo_height() // 2)
            self.assertIs(hit, widget, 'Row geometry container must not occlude its button')
        for child in bar.winfo_children():
            child.destroy()
        bar.items.clear()
        bar.add(ttk.Button(bar, text='Recreated selection'))
        self.app.update()
        self.assertTrue(bar.items[0].winfo_viewable())
        self.assertFalse(self.errors)
