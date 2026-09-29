"""Independent regression checks for artwork fallback and real editing sessions."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from story_atlas.app import StoryAtlas
from story_atlas.ui_assets import UIAssetCache


class ArtworkReviewTests(unittest.TestCase):
    def test_oversized_decorative_images_fall_back(self):
        # No Tk root or huge allocation is needed: failure precedes PhotoImage.
        for error in (Image.DecompressionBombError, Image.DecompressionBombWarning):
            with self.subTest(error=error.__name__):
                cache = UIAssetCache(None)
                with patch('story_atlas.ui_assets.Image.open', side_effect=error('oversized')):
                    self.assertIsNone(cache.get('section.story'))
        cache = UIAssetCache(None)
        with patch('story_atlas.ui_assets.Image.open') as opened:
            image = opened.return_value.__enter__.return_value
            image.width, image.height = 2049, 16
            self.assertIsNone(cache.get('section.story'))
            image.convert.assert_not_called()

    def test_actual_dirty_profiles_and_portraits_survive_appearance(self):
        for mode in ('Advanced', 'Simple'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                app = StoryAtlas(folder / 'story.db')
                errors = []
                app.report_callback_exception = lambda *args: errors.append(args)
                try:
                    path = folder / 'portrait.png'
                    Image.new('RGB', (80, 100), 'navy').save(path)
                    portrait = app.database.assets.import_image(path)
                    ident = app.database.save_character(dict(name='Saved name', summary='Saved prose', portrait=portrait))
                    app.refresh()
                    if mode == 'Simple':
                        app.mode.set(mode)
                        self.assertTrue(app.switch_mode())
                        app.simple.inspect_character(ident)
                        app.update()
                        identity = app.simple.task.identity
                        self.assertIsNotNone(identity.photo)
                        app.set_appearance('light', 12, 'Minimal')
                        self.assertIsNotNone(identity.photo)
                        app.simple.edit_character(ident)
                        task = app.simple.task
                        editor = task.editor
                    else:
                        app.characters.open_character(ident)
                        app.characters.edit_profile()
                        task = app.characters
                        editor = task.editor
                    app.update()
                    editor.fields['name'].set('Unsaved name')
                    editor.fields['summary'].insert('end', ' unsaved prose')
                    before = task.values()
                    original = task.original.copy()
                    for theme, size, art in (('light', 16, 'Minimal'), ('dark', 10, 'Illustrated')):
                        app.set_appearance(theme, size, art)
                        app.update()
                        self.assertIs(task.editor, editor)
                        if mode == 'Simple':
                            self.assertIs(app.simple.task, task)
                        self.assertEqual(task.values(), before)
                        self.assertEqual(task.original, original)
                        saved = next(row for row in app.database.characters() if row['id'] == ident)
                        self.assertEqual(saved['name'], 'Saved name')
                        self.assertEqual(saved['summary'], 'Saved prose')
                        self.assertEqual(saved['portrait'], portrait)
                    self.assertEqual(errors, [])
                finally:
                    app.database.close()
                    app.destroy()
