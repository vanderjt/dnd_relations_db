"""Independent checks for user portraits across appearance and story boundaries."""
from pathlib import Path
import unittest

from PIL import Image
from tests import test_workspace_art as baseline
from story_atlas.database import Database
from story_atlas.tree_art import portrait_photo


class WorkspaceReviewTests(unittest.TestCase):
    setUp = baseline.WorkspaceArtTests.setUp
    cleanup = baseline.WorkspaceArtTests.cleanup

    def test_compact_saved_profile_exposes_identity_and_real_dirty_status(self):
        app, view = self.app, self.app.characters
        app.geometry('760x480')
        app.set_appearance('dark', 16)
        view.open_character(self.ident)
        app.update()
        self.assertEqual(view.overview.context.cget('text'), 'Current saved profile')
        self.assertFalse(view.draft_status_label.winfo_manager())
        canvas = view.overview.scroller.canvas
        name = view.overview.name
        self.assertLessEqual(name.winfo_rooty() + name.winfo_height(), canvas.winfo_rooty() + canvas.winfo_height())
        self.assertTrue(view.tree.bbox(str(self.ident)), 'At least the selected cast row must be visible')
        view.edit_profile()
        view.fields['name'].set('Unsaved Aster')
        app.update()
        self.assertEqual(view.draft_status_label.cget('text'), 'Unsaved changes')
        self.assertTrue(view.draft_status_label.winfo_viewable())
        self.assertEqual(app.database.characters()[0]['name'], 'Aster')
        self.assertTrue(view.save())
        app.update()
        self.assertFalse(view.draft_status_label.winfo_manager())
        app.geometry('1180x720')
        app.update()
        self.assertIn('not historically versioned', view.overview.context.cget('text'))
        self.assertFalse(self.errors)

    def test_minimal_retains_row_portrait_without_cross_story_cache_leak(self):
        path = Path(self.temp.name) / 'portrait.png'
        Image.new('RGB', (24, 24), 'purple').save(path)
        reference = self.app.database.assets.import_image(path)
        saved = dict(self.app.database.characters()[0], portrait=reference)
        self.app.database.save_character(saved, self.ident)
        self.app.refresh()
        tree = self.app.characters.tree
        tree.selection_set(str(self.ident))
        values = tree.item(str(self.ident), 'values')
        photo = tree.atlas_row_images[str(self.ident)]
        self.assertIsNotNone(photo)
        self.app.set_appearance('light', 16, 'Minimal')
        self.app.update()
        self.assertIs(tree.atlas_row_images[str(self.ident)], photo)
        self.assertEqual(tree.item(str(self.ident), 'values'), values)
        self.assertEqual(tree.selection(), (str(self.ident),))
        other = Database(Path(self.temp.name) / 'other.db')
        try:
            # Same reference in a different story has no authoritative bytes.
            self.assertIsNone(portrait_photo(tree, other, reference))
        finally:
            other.close()
        self.assertFalse(self.errors)
