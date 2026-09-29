"""Deleting an inspected character cascades through the existing Trash service."""
import unittest
from unittest.mock import patch
import test_simple_mode as baseline


class SummaryDeleteTests(unittest.TestCase):
    setUp = baseline.SimpleUITests.setUp
    cleanup = baseline.SimpleUITests.cleanup

    def test_button_trashes_exact_character_all_connections_and_restores_history(self):
        a, b, c = [self.db.save_character(dict(name=name)) for name in ('Same name', 'Same name', 'Other')]
        outgoing = self.db.save_relationship(a, b, 'Mentor', inverse_label='Student')
        incoming = self.db.save_relationship(c, a, 'Friend', semantics='mutual')
        ended = self.db.save_relationship(a, c, 'Former colleague')
        self.db.history.write(ended, self.first, dict(source_id=a, target_id=c, kind='Former colleague'), active=False)
        unrelated = self.db.save_relationship(b, c, 'Family', semantics='mutual')
        history = self.db.history.rows()
        self.app.refresh()
        self.ws.graph.select_node(a)
        self.app.update()
        panel = self.ws.task
        self.assertEqual([w['text'] for w in panel.delete_button.master.items][-2:], ['Connect…', 'Delete'])
        self.assertTrue(panel.delete_button.winfo_viewable())
        with patch('story_atlas.simple_workspace.messagebox.askyesno', return_value=True):
            panel.delete_button.invoke()
        self.app.update()
        self.assertIsNone(self.ws.task)
        self.assertNotIn(a, self.ws.graph.graph)
        self.assertNotIn(a, self.ws.ordered.ids)
        self.assertEqual({r['id'] for r in self.db.characters()}, {b, c})
        self.assertEqual({r['id'] for r in self.db.relationship_records()}, {unrelated})
        self.assertEqual({r['id'] for r in self.db.relationships(0)}, {unrelated})
        trash = {(r['type'], r['id']) for r in self.db.trash.items()}
        self.assertEqual(trash, {('character', a), *(('relationship', ident) for ident in (outgoing, incoming, ended))})
        self.assertEqual(self.db.history.rows(), history)
        self.db.trash.restore('character', a)
        self.app.refresh()
        self.assertEqual({r['id'] for r in self.db.relationship_records()}, {outgoing, incoming, ended, unrelated})
        self.assertNotIn(ended, {r['id'] for r in self.db.relationships(self.first)})
        self.assertIn(a, self.ws.graph.graph)
        self.assertEqual(self.errors, [])

    def test_cancel_and_database_failure_keep_summary_and_records(self):
        a, b = [self.db.save_character(dict(name=name)) for name in ('Keep', 'Neighbor')]
        connection = self.db.save_relationship(a, b, 'Friend')
        self.app.refresh()
        self.ws.graph.select_node(a)
        panel = self.ws.task
        with patch('story_atlas.simple_workspace.messagebox.askyesno', return_value=False):
            panel.delete_button.invoke()
        self.assertIs(self.ws.task, panel)
        self.assertEqual(self.db.trash.items(), [])
        self.db.connection.execute("CREATE TRIGGER reject_trash BEFORE UPDATE OF deleted_at ON relationships BEGIN SELECT RAISE(ABORT, 'Simulated write failure'); END")
        with patch('story_atlas.simple_workspace.messagebox.askyesno', return_value=True), patch('story_atlas.simple_workspace.messagebox.showerror') as error:
            panel.delete_button.invoke()
            error.assert_called_once()
        self.assertIs(self.ws.task, panel)
        self.assertEqual(self.db.trash.items(), [])
        self.assertEqual({r['id'] for r in self.db.characters()}, {a, b})
        self.assertEqual(self.db.relationship_records()[0]['id'], connection)
        self.assertEqual(self.errors, [])
