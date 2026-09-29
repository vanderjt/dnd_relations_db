"""Regressions for the latest three-pane, collapsible event overview."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from story_atlas.app import StoryAtlas


class EventLayoutReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = StoryAtlas(Path(self.temp.name) / 'story.db')
        self.addCleanup(self.cleanup)
        self.db = self.app.database
        self.a = self.db.save_character(dict(name='Same', goals='Keep the promise\n  Find Ω'))
        self.b = self.db.save_character(dict(name='Same'))
        self.event = self.db.events.save('Pact', 'Description', 1, [self.a, self.b])
        self.link = self.db.save_relationship(self.a, self.b, 'Friend')
        self.db.history.write(self.link, self.event, dict(self.db.relationships()[0], notes='A secret promise.\nOnly one witness.'))
        self.app.refresh()
        self.view = self.app.events
        self.view.reveal_event(self.event)
        self.app.update()

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def test_collapsed_groups_and_selection_survive_unrelated_save(self):
        for tree in (self.view.goals_tree, self.view.change_tree):
            key = tree.get_children()[0]
            tree.item(key, open=False)
            tree.selection_set(key)
            tree.focus(key)
        row = next(r for r in self.db.characters() if r['id'] == self.b)
        self.db.save_character(dict(row, location='Elsewhere'), self.b)
        self.app.refresh()
        self.app.update()
        for tree in (self.view.goals_tree, self.view.change_tree):
            key = f'character:{self.a}'
            self.assertFalse(tree.item(key, 'open'))
            self.assertEqual(tree.selection(), (key,))
        self.assertNotIn('(#', self.view.cast_body.get('1.0', 'end'))

    def test_saved_notes_and_goal_indentation_are_displayed(self):
        parent = self.view.change_tree.get_children()[0]
        change = self.view.change_tree.get_children(parent)[0]
        notes = [self.view.change_tree.item(key, 'text') for key in self.view.change_tree.get_children(change)]
        self.assertEqual(notes, ['A secret promise.', 'Only one witness.'])
        goal = self.view.goals_tree.get_children(f'character:{self.a}')[1]
        self.assertEqual(self.view.goals_tree.item(goal, 'text'), '  Find Ω')

    def test_narrow_detail_pane_uses_reachable_menu(self):
        self.app.geometry('1180x720')
        self.app.set_appearance('dark', 16)
        self.app.update()
        self.view.workspace.sashpos(1, self.view.workspace.winfo_width() - 190)
        self.app.update()
        self.assertTrue(self.view.detail_action_menu.winfo_ismapped())
        self.assertFalse(self.view.detail_actions.winfo_ismapped())
        self.view.workspace.sashpos(1, self.view.workspace.winfo_width() // 2)
        self.app.update()
        self.assertTrue(self.view.detail_actions.winfo_ismapped())

    def test_correction_stays_in_task_and_selects_event_state(self):
        flow = self.view.add_relationship_change()
        flow.choice.set(next(key for key, row in flow.choices.items() if row['id'] == self.link))
        history = flow.review()
        state = history.row
        self.assertEqual(state['event_id'], self.event)
        history.close()
        self.app.update()
        self.assertEqual(self.app.grab_current(), flow)
        flow.destroy()

    def test_tree_wheel_does_not_scroll_outer_details_too(self):
        scroller = self.view.detail_scroller
        with patch.object(scroller, 'winfo_containing', return_value=self.view.goals_tree), patch.object(scroller.canvas, 'yview_scroll') as scroll:
            scroller.on_wheel(SimpleNamespace(x_root=0, y_root=0, delta=-120))
            scroll.assert_not_called()

    def test_quick_entry_destroy_cancels_pending_focus(self):
        from story_atlas.quick_event import QuickEventDialog
        from story_atlas.quick_character import QuickCharacterDialog
        from story_atlas.relationship_dialog import RelationshipDialog

        for dialog in (QuickEventDialog(self.app, self.db, lambda _: None),
                       QuickCharacterDialog(self.app, self.db, lambda _: None, lambda: None)):
            job = dialog.focus_job
            self.assertIn(job, self.app.tk.call('after', 'info'))
            dialog.destroy()
            self.assertNotIn(job, self.app.tk.call('after', 'info'))
        dialog = RelationshipDialog(self.app, self.db, self.app.refresh)
        dialog.create_character('source')
        dialog.character_step.cancel()
        job = dialog.focus_job
        dialog.destroy()
        self.assertNotIn(job, self.app.tk.call('after', 'info'))
        self.app.update()
