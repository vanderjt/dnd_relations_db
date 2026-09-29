"""Exercise the user paths that escaped the initial Sol implementation tests."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from story_atlas.app import StoryAtlas
from story_atlas.database import Database
from story_atlas.global_search import SearchDialog
from story_atlas.relationship_dialog import RelationshipDialog
from story_atlas.chronology_preview import ChronologyPreview


class SeniorFixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.app = StoryAtlas(self.folder / 'a.db')
        self.addCleanup(self.cleanup)
        self.db = self.app.database
        self.a = self.db.save_character({'name': 'Original'})
        self.b = self.db.save_character({'name': 'Other'})
        self.chapter = self.db.chapters.save('Chapter needle')
        self.events = [self.db.chapters.save_event(f'Event {i} needle', '', i, chapter_id=self.chapter) for i in range(1, 4)]
        self.app.refresh()
        self.app.update()

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def test_discard_search_navigation_resets_existing_and_new_drafts(self):
        rel = self.db.save_relationship(self.a, self.b, 'Friend', 'history needle')
        self.db.history.write(rel, self.events[-1], dict(self.db.relationships()[0], notes='new'), active=False)
        for ident in (self.a, None):
            for result in (f'chapter:{self.chapter}', f'event:{self.events[0]}', f'history:{rel}:baseline'):
                view = self.app.characters
                row = next((r for r in self.db.characters() if r['id'] == ident), None)
                view.load(row)
                view.fields['name'].set('Discard me')
                view.draft.flush()
                dialog = SearchDialog(self.app, {})
                dialog.query.set('needle')
                dialog.refresh()
                dialog.tree.selection_set(result)
                with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=False):
                    dialog.open_selected()
                self.assertEqual(view.values(), view.original)
                self.assertEqual(view.fields['name'].get(), 'Original' if ident else '')
                view.draft.flush()
                self.assertEqual(self.db.drafts.list(), [])
                if ident:
                    view.save()
                    self.assertEqual(next(r for r in self.db.characters() if r['id'] == ident)['name'], 'Original')
                for child in self.app.winfo_children():
                    if child.winfo_class() == 'Toplevel':
                        child.destroy()

    def test_inspection_selects_effective_state_not_only_exact_event(self):
        for beginning, origin, ended, label in ((None, 1, False, 'Present'), (0, 1, False, 'Present'),
                                               (1, 1, False, 'Present'), (2, 1, False, 'Not yet begun'),
                                               (0, 2, True, 'Ended')):
            dialog = RelationshipDialog(self.app.events, self.db, self.app.refresh, context_event_id=self.events[origin])
            rel = self.db.save_relationship(self.a, self.b, f'Kind {beginning} {origin} {ended}',
                                            start_event=None if beginning is None else self.events[beginning])
            if ended:
                row = next(r for r in self.db.relationships() if r['id'] == rel)
                self.db.history.write(rel, self.events[1], row, active=False)
            dialog.last_saved_id = rel
            history = dialog.inspect_saved()
            selected = history.tree.selection()[0]
            expected_event = self.events[1] if ended else self.events[beginning] if beginning is not None and beginning <= origin else None
            self.assertEqual(history.states[selected]['event_id'], expected_event)
            self.assertIn(f': {label}.', history.context.get())
            history.destroy()
            self.assertEqual(self.app.grab_current(), dialog)
            dialog.destroy()

    def test_story_switch_restores_ids_without_cross_story_leak(self):
        path = self.db.path
        self.app.events.reveal_event(self.events[1])
        other = self.folder / 'b.db'
        db = Database(other)
        c = db.chapters.save('Different chapter')
        db.chapters.save_event('Different event', '', 1, chapter_id=c)
        db.close()
        self.app.projects.switch(other)
        self.assertEqual(self.app.events.chapter_id, 'all')
        self.assertEqual(self.app.events.tree.selection(), ())
        self.app.events.reveal_chapter(None)
        self.app.projects.switch(path)
        self.assertEqual(self.app.events.chapter_id, self.chapter)
        self.assertEqual(self.app.events.tree.selection(), (str(self.events[1]),))
        self.app.projects.switch(other)
        self.assertIsNone(self.app.events.chapter_id)
        self.app.events.restore_selection(999, ('999',))
        self.assertEqual(self.app.events.chapter_id, 'all')
        self.assertEqual(self.app.events.tree.selection(), ())

    def test_large_chronology_preview_is_scrollable_with_visible_actions(self):
        preview = {'old_chapters': [(1, 'Chapter one'), (2, 'Empty')], 'new_chapters': [(2, 'Empty'), (1, 'Chapter one')],
                   'old_events': [(i, f'Event {i}', 1 if i < 300 else None) for i in range(1, 301)]}
        preview['new_events'] = preview['old_events']
        for mode in ('dark', 'light'):
            self.app.set_appearance(mode, 16)
            dialog = ChronologyPreview(self.app.events, preview)
            dialog.geometry('760x480')
            self.app.update()
            for text in dialog.texts:
                self.assertLess(text.yview()[1], 1)
                self.assertIn('Unassigned', text.get('1.0', 'end'))
                self.assertIn('No events', text.get('1.0', 'end'))
            for button in (dialog.confirm_button, dialog.cancel_button):
                self.assertTrue(button.winfo_ismapped())
                self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), dialog.winfo_rooty() + dialog.winfo_height())
            dialog.focus_force()
            dialog.texts[0].focus_set()
            dialog.texts[0].event_generate('<Tab>')
            self.app.update()
            self.assertNotEqual(self.app.focus_get(), dialog.texts[0])
            dialog.cancel_button.invoke()
            self.assertFalse(dialog.result)
        dialog = ChronologyPreview(self.app.events, preview)
        dialog.confirm_button.invoke()
        self.assertTrue(dialog.result)
