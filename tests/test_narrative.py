"""Fictional chronology, historical corrections, recovery and visible graph state."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
from story_atlas.database import Database
from story_atlas.migrations import MIGRATIONS, CURRENT_VERSION
from story_atlas.imports import read_export, import_payload, validate_payload
from story_atlas.backup import snapshot, restore_backup
from story_atlas.app import StoryAtlas
from story_atlas.event_view import EventDialog, EventRelationshipChangeDialog
from story_atlas.history_dialog import HistoryDialog, StateDialog, StoryChangeReviewDialog
from story_atlas.relationship_dialog import RelationshipDialog
from story_atlas.quick_event import QuickEventDialog
from story_atlas.global_search import SearchDialog
from story_atlas.graph_state import SavedViews


class NarrativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.db = Database(self.folder / "story.db")
        self.addCleanup(self.db.close)
        self.a, self.b = [self.db.save_character(dict(name=name)) for name in ("Mira", "Pip")]
        self.two = self.db.events.save("Chapter 2: Pact", "They become allies", 2, [self.a, self.b])
        self.five = self.db.events.save("Chapter 5: Betrayal", "The pact breaks", 5, [self.a, self.b])

    def timeline(self):
        ident = self.db.save_relationship(self.a, self.b, "Ally", "Old pact", semantics="mutual", start_event=self.two)
        data = dict(self.db.relationships()[0], kind="Enemy", notes="Betrayal", semantics="directional")
        change = self.db.history.write(ident, self.five, data)
        return ident, change

    def test_allies_two_enemies_five_corrections_end_and_current(self):
        ident, change = self.timeline()
        self.assertEqual(self.db.relationships(0), [])
        self.assertEqual(self.db.relationships(self.two)[0]["kind"], "Ally")
        self.assertEqual(self.db.relationships(self.two)[0]["semantics"], "mutual")
        self.assertEqual(self.db.relationships(self.five)[0]["kind"], "Enemy")
        self.assertEqual(self.db.relationships()[0]["semantics"], "directional")
        old = self.db.history.rows(ident)[0]
        self.db.history.write(ident, self.two, dict(old, notes="Corrected pact"), True, old["id"])
        self.assertEqual(self.db.relationships(self.two)[0]["notes"], "Corrected pact")
        self.assertEqual(self.db.relationships()[0]["notes"], "Betrayal")
        self.db.save_relationship(self.a, self.b, "Rival", "Correction, not new event", ident)
        self.assertEqual(len(self.db.history.rows(ident)), 2)
        self.assertEqual(self.db.relationships(self.two)[0]["kind"], "Ally")
        self.assertEqual(self.db.relationships()[0]["kind"], "Rival")
        final = self.db.events.save("Chapter 8: Farewell", "", 8)
        self.db.history.write(ident, final, self.db.relationships()[0], False)
        self.assertEqual(self.db.relationships(), [])
        self.assertEqual(self.db.relationships(self.five)[0]["kind"], "Rival")
        self.assertEqual(len(self.db.relationship_records()), 1)

    def test_reordering_and_correcting_event_dates_recalculates_current(self):
        ident, change = self.timeline()
        self.db.events.move(self.five, -1)
        self.assertEqual([row["id"] for row in self.db.events.list()], [self.five, self.two])
        self.assertEqual(self.db.relationships()[0]["kind"], "Ally")
        self.assertEqual(self.db.relationships(self.five)[0]["kind"], "Enemy")
        later = self.db.events.save("Later session", "", 10)
        row = next(row for row in self.db.history.rows(ident) if row["id"] == change)
        self.db.history.write(ident, later, row, True, change)
        self.assertEqual(self.db.relationships()[0]["kind"], "Enemy")
        self.assertEqual(self.db.relationships(self.two)[0]["kind"], "Ally")

    def test_overlapping_timeline_reorder_rolls_back(self):
        first = self.db.save_relationship(self.a, self.b, "Friend", semantics="mutual")
        state = self.db.relationships()[0]
        self.db.history.write(first, self.two, state, False)
        self.db.save_relationship(self.b, self.a, "Friend", semantics="mutual", start_event=self.five)
        before = self.db.events.list()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.db.events.move(self.five, -1)
        self.assertEqual(self.db.events.list(), before)
        with self.assertRaises(ValueError):
            self.db.history.write(first, self.two, state, True, self.db.history.rows(first)[0]["id"])
        self.assertEqual(len(self.db.relationships()), 1)

    def test_full_export_import_history_and_malformed_references(self):
        ident, _ = self.timeline()
        output = self.folder / "story.json"
        self.db.export_json(output)
        payload = read_export(output)
        restored = Database(import_payload(payload, self.folder / "import.db"))
        try:
            for event in (0, self.two, self.five, None):
                self.assertEqual(restored.relationships(event), self.db.relationships(event))
            self.assertEqual(restored.events.participants(), self.db.events.participants())
        finally:
            restored.close()
        bad = copy.deepcopy(payload)
        bad["relationship_history"][0]["event_id"] = 999
        with self.assertRaises(ValueError):
            import_payload(bad, self.folder / "bad.db")
        self.assertFalse((self.folder / "bad.db").exists())
        self.assertEqual(self.db.relationships()[0]["kind"], "Enemy")
        bad = copy.deepcopy(payload)
        bad["event_participants"][0]["character_id"] = 999
        with self.assertRaises(ValueError):
            validate_payload(dict(format_version=3, **bad))

    def test_consolidation_checks_past_states_not_only_current(self):
        first = self.db.save_relationship(self.a, self.b, "Ally")
        second = self.db.save_relationship(self.b, self.a, "Friend")
        historic = self.db.save_relationship(self.a, self.b, "Friend", start_event=self.two)
        row = next(row for row in self.db.relationships() if row["id"] == historic)
        self.db.history.write(historic, self.five, row, False)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.db.relationship_store.preview_consolidation(first, second, "Friend")
        self.assertEqual(len(self.db.relationships()), 2)
        self.assertEqual(self.db.trash.items(), [])

    def test_trash_restore_and_backups_keep_full_timeline(self):
        ident, _ = self.timeline()
        self.db.delete_character(self.b)
        self.assertEqual(self.db.relationships(self.two), [])
        self.assertEqual(len(self.db.history.rows(ident)), 2)
        self.db.trash.restore("character", self.b)
        self.assertEqual(self.db.relationships(self.two)[0]["kind"], "Ally")
        self.db.delete_relationship(ident)
        self.db.trash.restore("relationship", ident)
        restored = Database(restore_backup(snapshot(self.db.connection, self.db.path), self.folder / "restored.db"))
        try:
            self.assertEqual(restored.history.rows(), self.db.history.rows())
            self.assertEqual(restored.relationships(self.two), self.db.relationships(self.two))
        finally:
            restored.close()

    def test_legacy_migration_baseline_and_transactional_failures(self):
        path = self.folder / "legacy.db"
        con = sqlite3.connect(path)
        for migration in MIGRATIONS[:6]:
            migration(con)
        con.execute("INSERT INTO characters(id,name) VALUES (1,'A'),(2,'B')")
        con.execute("INSERT INTO relationships(source_id,target_id,kind,semantics) VALUES (1,2,'Friend','mutual')")
        con.execute("PRAGMA user_version=6")
        con.commit()
        con.close()
        legacy = Database(path)
        try:
            event = legacy.events.save("First event", "", 1)
            self.assertEqual(legacy.relationships(0), legacy.relationships(event))
            self.assertEqual(legacy.relationship_records()[0]["baseline_active"], 1)
            self.assertEqual(legacy.history.rows(), [])
            self.assertEqual(legacy.connection.execute("PRAGMA user_version").fetchone()[0], CURRENT_VERSION)
            self.assertEqual(len(list((self.folder / "backups" / path.name).glob("pre-migration-v6-*.db"))), 1)
        finally:
            legacy.close()
        with patch.object(self.db, "_log", side_effect=sqlite3.OperationalError("disk full")):
            with self.assertRaises(sqlite3.OperationalError):
                self.db.save_relationship(self.a, self.b, "Friend", start_event=self.two)
        self.assertEqual(self.db.relationship_records(), [])
        self.assertEqual(self.db.history.rows(), [])


class NarrativeUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        try:
            self.app = StoryAtlas(self.folder / "story.db")
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.cleanup)
        self.db = self.app.database
        self.a, self.b = [self.db.save_character(dict(name=name)) for name in ("Mira", "Pip")]
        self.two = self.db.events.save("Chapter 2", "Pact", 2, [self.a, self.b])
        self.five = self.db.events.save("Chapter 5", "Betrayal", 5)
        self.ident = self.db.save_relationship(self.a, self.b, "Ally", semantics="mutual", start_event=self.two)
        self.db.history.write(self.ident, self.five, dict(self.db.relationships()[0], kind="Enemy", semantics="directional"))
        self.app.refresh()
        self.app.update()

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def test_graph_as_of_export_saved_view_and_current_profiles(self):
        graph = self.app.graph
        self.app.tabs.select(graph)
        self.app.update()
        graph.as_of_id = self.two
        graph.refresh(force=True)
        self.assertEqual(next(iter(graph.graph.edges(data=True)))[2]["kind"], "Ally")
        self.assertEqual(self.app.relationships.rows[str(self.ident)]["kind"], "Enemy")
        output = self.folder / "chapter2.png"
        with patch("story_atlas.graph_actions.filedialog.asksaveasfilename", return_value=str(output)):
            graph.export()
        data = json.loads(output.with_suffix(".json").read_text())
        self.assertEqual(data["as_of_event"]["id"], self.two)
        self.assertEqual(data["as_of_event"]["title"], "Chapter 2")
        self.assertEqual(data["relationships"][0]["kind"], "Ally")
        self.assertEqual(data["relationships"][0]["baseline_active"], 1)
        SavedViews(self.db).save("Chapter 2", graph.capture_state())
        graph.as_of_id = None
        graph.apply_state(SavedViews(self.db).load("Chapter 2"))
        self.assertEqual(graph.as_of_id, self.two)
        self.db.events.move(self.five, -1)
        self.app.refresh()
        self.assertEqual(self.app.relationships.rows[str(self.ident)]["kind"], "Ally")
        self.assertIn("Chapter 2", graph.as_of.get())

    def test_history_correction_ui_and_batch_start_event_clear(self):
        dialog = HistoryDialog(self.app, self.db, self.app.refresh, self.ident)
        keys = dialog.tree.get_children()
        self.assertEqual(len(keys), 3)
        dialog.tree.selection_set(keys[1])
        editor = dialog.edit(True)
        editor.variables["kind"].set("Friend")
        self.assertFalse(editor.save())
        self.assertTrue(editor.save())
        self.assertEqual(self.db.relationships(self.two)[0]["kind"], "Friend")
        self.assertEqual(self.db.relationships()[0]["kind"], "Enemy")
        dialog.destroy()
        entry = RelationshipDialog(self.app, self.db, self.app.refresh)
        self.app.update()
        entry.focus_force()
        labels = list(entry.choices)
        for field, value in dict(source=labels[0], target=labels[1], kind="Mentor", semantics="Directional",
                                 inverse_label="Mentee", start_event=next(key for key, ident in entry.event_choices.items() if ident == self.five)).items():
            entry.variables[field].set(value)
        self.assertTrue(entry.save())
        self.app.update()
        self.assertEqual(entry.values()["category"], "Other")
        self.assertEqual({key: value for key, value in entry.values().items() if key != "category"}, {key: "" for key in entry.values() if key != "category"})
        self.assertIs(entry.focus_get(), entry.boxes["source"])
        self.assertEqual(len(self.db.relationships(self.two)), 1)
        entry.destroy()

    def test_event_editor_cancel_and_participants(self):
        dialog = EventDialog(self.app, self.db, self.app.refresh)
        dialog.title_value.set("Chapter 8")
        dialog.sequence.set("3")
        dialog.participants.buttons[self.a].invoke()
        with patch("story_atlas.event_view.messagebox.askyesnocancel", return_value=None):
            dialog.close()
        self.assertTrue(dialog.winfo_exists())
        self.assertTrue(dialog.save())
        self.app.update()
        self.assertEqual(self.db.events.list()[-1]["title"], "Chapter 8")
        self.assertEqual(len(self.app.events.rows), 3)
        self.assertNotIn("timestamp", self.db.events.list()[-1])

    def test_selected_event_details_show_recorded_present_and_ended_changes(self):
        self.db.save_character(dict(name="Mira", goals="Find the ledger"), self.a)
        ended = self.db.save_relationship(self.b, self.a, "Promise", "Will end")
        self.db.history.write(ended, self.five, next(row for row in self.db.relationships() if row["id"] == ended), active=False)
        empty = self.db.events.save("Chapter 8", "Quiet aftermath", 8, [self.a])
        self.app.refresh()
        events = self.app.events
        self.assertEqual(events.tree.item(str(self.two), "values"), ("Unassigned / Chapter 2",))
        events.tree.selection_set(str(self.two))
        events.show_details()
        self.assertNotIn("global order", events.detail_text.get().lower())
        self.assertIn("Pact", events.detail_text.get())
        self.assertEqual(events.cast_heading.get(), "Characters active in this event (2)")
        self.assertIn("• Mira", events.cast_body.get("1.0", "end"))
        self.assertIn("• Pip", events.cast_body.get("1.0", "end"))
        self.assertEqual(events.goals_heading.get(), "Current goals (2 characters)")
        goal_roots = events.goals_tree.get_children()
        self.assertEqual(len(goal_roots), 2)
        self.assertIn("Find the ledger", events.goals_tree.item(events.goals_tree.get_children(goal_roots[0])[0], "text"))
        events.goals_tree.item(goal_roots[0], open=False)
        self.assertFalse(events.goals_tree.item(goal_roots[0], "open"))
        self.assertEqual(events.changes_heading.get(), "Relationship changes (1)")
        roots = events.change_tree.get_children()
        self.assertEqual(len(roots), 2)
        self.assertTrue(all(len(events.change_tree.get_children(root)) == 1 for root in roots))
        events.tree.selection_set(str(self.five))
        events.show_details()
        self.assertIn("No characters marked active", events.cast_body.get("1.0", "end"))
        self.assertEqual(events.changes_heading.get(), "Relationship changes (2)")
        self.assertEqual(len(events.change_tree.get_children()), 2)
        self.assertTrue(any("Ended" in events.change_tree.item(child, "text")
                            for root in events.change_tree.get_children()
                            for child in events.change_tree.get_children(root)))
        events.tree.selection_set(str(empty))
        events.show_details()
        self.assertIn("• Mira", events.cast_body.get("1.0", "end"))
        self.assertEqual(events.changes_heading.get(), "Relationship changes (0)")
        root = events.change_tree.get_children()[0]
        self.assertIn("No relationship changes", events.change_tree.item(events.change_tree.get_children(root)[0], "text"))
        self.app.refresh()
        self.assertEqual(events.tree.selection(), (str(empty),))

    def test_event_change_chooser_uses_fixed_event_and_detects_existing_state(self):
        self.db.events.save("Chapter 5", "Betrayal", 5, [self.a, self.b], self.five)
        mutual = self.db.save_relationship(self.a, self.b, "Trust", semantics="mutual")
        ended = self.db.save_relationship(self.b, self.a, "Promise")
        self.db.history.write(ended, self.two, next(row for row in self.db.relationships() if row["id"] == ended), active=False)
        self.app.refresh()
        events = self.app.events
        events.tree.selection_set(str(self.five))
        flow = events.add_relationship_change()
        self.assertIsInstance(flow, EventRelationshipChangeDialog)
        mutual_label = next(label for label, row in flow.choices.items() if row["id"] == mutual)
        self.assertTrue(mutual_label.startswith("Participant connection"))
        flow.choice.set(mutual_label)
        flow.describe()
        state = flow.editor
        self.assertEqual(state.fixed_event_id, self.five)
        self.assertEqual(state.variables["semantics"].get(), "Mutual")
        self.assertFalse(state.save())  # Event-context save awaits explicit review.
        review = state
        review.record()
        self.app.update()
        self.assertTrue(any("Trust" in events.change_tree.item(child, "text")
                            for root in events.change_tree.get_children()
                            for child in events.change_tree.get_children(root)))
        flow = events.add_relationship_change()
        ended_label = next(label for label, row in flow.choices.items() if row["id"] == ended)
        flow.choice.set(ended_label)
        flow.describe()
        state = flow.editor
        self.assertEqual(state.variables["presence"].get(), "Ended")
        state.close()
        existing_label = next(label for label, row in flow.choices.items() if row["id"] == self.ident)
        flow.choice.set(existing_label)
        self.assertIn("already recorded", flow.status.get())
        self.assertIn("disabled", flow.continue_button.state())
        flow.destroy()

    def test_event_change_review_keeps_later_state_independent(self):
        relationship = self.db.save_relationship(self.a, self.b, "Pact", semantics="mutual", start_event=self.two)
        self.app.refresh()
        events = self.app.events
        events.tree.selection_set(str(self.five))
        flow = events.add_relationship_change()
        label = next(label for label, row in flow.choices.items() if row["id"] == relationship)
        flow.choice.set(label)
        flow.describe()
        editor = flow.editor
        editor.variables["kind"].set("Rival")
        review = editor.review_change()
        self.assertIsInstance(review, StoryChangeReviewDialog)
        text = review.review_content.get("1.0", "end-1c")
        self.assertIn("Immediately before", text)
        self.assertIn("Later recorded states remain independent", text)
        review.record()
        self.app.update()
        self.assertIn("Change recorded at Chapter 5", flow.status.get())
        self.assertEqual(next(row for row in self.db.relationships(self.five) if row["id"] == relationship)["kind"], "Rival")
        later = self.db.events.save("Chapter 8", "Aftermath", 8)
        state = next(row for row in self.db.relationships(self.five) if row["id"] == relationship)
        self.db.history.write(relationship, later, dict(state, kind="Friend"))
        self.assertEqual(next(row for row in self.db.relationships(self.five) if row["id"] == relationship)["kind"], "Rival")
        self.assertEqual(next(row for row in self.db.relationships() if row["id"] == relationship)["kind"], "Friend")
        self.assertEqual(flow.continue_button.cget("text"), "Add another change")
        self.assertNotIn("disabled", flow.graph_button.state())
        flow.destroy()

    def test_story_change_can_create_event_and_resume_without_committing_change(self):
        relationship = self.db.save_relationship(self.a, self.b, "Pact")
        row = dict(next(row for row in self.db.relationships() if row["id"] == relationship), active=True)
        editor = StateDialog(self.app, self.db, self.app.refresh, relationship, row, False)
        editor.variables["kind"].set("Rival")
        editor.notes.insert("1.0", "Pending relationship change")
        before = editor.values()
        quick = editor.create_event()
        self.assertIsInstance(quick, QuickEventDialog)
        quick.title_value.set("Bad order")
        quick.sequence.set("0")
        self.assertFalse(quick.save())
        self.assertEqual(editor.values(), before)
        self.assertTrue(quick.status.get())
        with patch("story_atlas.quick_event.messagebox.askyesnocancel", return_value=False):
            quick.close()
        quick = editor.create_event()
        quick.title_value.set("Chapter 8")
        quick.sequence.set("3")
        self.assertTrue(quick.save())
        self.app.update()
        self.assertEqual(editor.variables["kind"].get(), "Rival")
        self.assertEqual(editor.notes.get("1.0", "end-1c"), "Pending relationship change")
        self.assertIn("Chapter 8", editor.variables["event"].get())
        self.assertIn("not recorded", editor.creation_status.get())
        self.assertEqual([row["sequence"] for row in self.db.events.list()], [1, 2, 3])
        with patch("story_atlas.history_dialog.messagebox.askyesnocancel", return_value=False):
            editor.close()
        self.assertEqual(self.db.history.rows(relationship), [])
        self.assertTrue(any(row["title"] == "Chapter 8" for row in self.db.events.list()))

    def test_quick_event_close_routes_preserve_pending_change_and_modal_focus(self):
        editor = StateDialog(self.app, self.db, self.app.refresh, self.ident,
                             dict(self.db.relationships()[0], active=True), False)
        editor.variables["kind"].set("Unrecorded promise")
        editor.notes.insert("1.0", "Keep this exact draft")
        original = editor.values()
        before_events = len(self.db.events.list())

        for route in ("back", "escape", "window"):
            quick = editor.create_event()
            quick.title_value.set(f"Draft {route}")
            quick.sequence.set(str(before_events + 1))
            quick.title_entry.focus_force()
            self.app.update()
            if route == "back":
                trigger = lambda: next(button for bar in quick.winfo_children()[0].winfo_children()
                                       if isinstance(bar, ttk.Frame)
                                       for button in bar.winfo_children()
                                       if isinstance(button, ttk.Button) and button.cget("text") == "Back to relationship change").invoke()
            elif route == "escape":
                self.assertTrue(quick.bind("<Escape>"))
                trigger = quick.close  # Same callback bound to Escape; OS focus varies in the full suite.
            else:
                trigger = lambda: quick.tk.call(quick.protocol("WM_DELETE_WINDOW"))
            with patch("story_atlas.quick_event.messagebox.askyesnocancel", return_value=None) as prompt:
                trigger()
                self.app.update()
                self.assertEqual(prompt.call_count, 1, route)
            self.assertTrue(quick.winfo_exists())
            self.assertEqual(quick.title_value.get(), f"Draft {route}")
            self.assertEqual(quick.grab_current(), quick)
            self.assertEqual(editor.values(), original)
            with patch("story_atlas.quick_event.messagebox.askyesnocancel", return_value=False):
                quick.close()
            self.assertFalse(quick.winfo_exists())
            self.assertEqual(editor.grab_current(), editor)
            self.assertEqual(editor.values(), original)
        self.assertEqual(len(self.db.events.list()), before_events)
        self.assertEqual(self.db.history.rows(self.ident)[-1]["kind"], "Enemy")

        quick = editor.create_event()
        quick.title_value.set("Saved from close")
        quick.sequence.set(str(before_events + 1))
        with patch.object(quick, "created", wraps=quick.created) as created:
            with patch.object(self.db.chapters, "save_event", side_effect=sqlite3.OperationalError("locked")):
                with patch("story_atlas.quick_event.messagebox.askyesnocancel", return_value=True):
                    quick.close()
            self.assertTrue(quick.winfo_exists())
            self.assertEqual(quick.title_value.get(), "Saved from close")
            self.assertEqual(quick.grab_current(), quick)
            created.assert_not_called()
            with patch("story_atlas.quick_event.messagebox.askyesnocancel", return_value=True):
                quick.close()
            created.assert_called_once()
        self.assertFalse(quick.winfo_exists())
        self.assertEqual(editor.grab_current(), editor)
        self.assertEqual(editor.values()["kind"], original["kind"])
        self.assertEqual(editor.values()["notes"], original["notes"])
        self.assertIn("Saved from close", editor.values()["event"])
        self.assertEqual(len(self.db.events.list()), before_events + 1)
        with patch("story_atlas.history_dialog.messagebox.askyesnocancel", return_value=False):
            editor.close()

    def test_search_opens_chapter_event_baseline_and_ended_state_by_id(self):
        chapter = self.db.chapters.save('The return', 'Chapter-only phrase Ω')
        event = self.db.chapters.save_event('Hidden scene', 'Event-only phrase Ω', 1, chapter_id=chapter)
        self.app.refresh()
        for query, key, expected in (('Chapter-only phrase Ω', f'chapter:{chapter}', chapter),
                                     ('Event-only phrase Ω', f'event:{event}', event)):
            search = SearchDialog(self.app, {})
            search.query.set(query)
            search.refresh()
            search.tree.selection_set(key)
            search.open_selected()
            self.assertFalse(search.winfo_exists())
            if key.startswith('chapter'):
                self.assertEqual(self.app.events.chapter_id, expected)
            else:
                self.assertEqual(self.app.events.tree.selection(), (str(expected),))

        rel = self.db.save_relationship(self.b, self.a, 'Oath', 'Baseline-only phrase')
        current = next(row for row in self.db.relationships() if row['id'] == rel)
        changed = self.db.history.write(rel, self.two, dict(current, notes='Later phrase'))
        ended = self.db.history.write(rel, self.five, dict(current, notes='Ended-only phrase'), active=False)
        self.app.refresh()
        for query, key, selected in (('Baseline-only phrase', f'history:{rel}:baseline', 'baseline'),
                                     ('Ended-only phrase', f'history:{rel}:{ended}', str(ended))):
            search = SearchDialog(self.app, {})
            search.query.set(query)
            search.refresh()
            self.assertIn(key, search.results)
            self.assertIn('Historical', search.results[key]['title'])
            search.tree.selection_set(key)
            search.open_selected()
            history = next(child for child in self.app.winfo_children() if isinstance(child, HistoryDialog))
            self.assertEqual(history.tree.selection(), (selected,))
            self.assertEqual(history.choices[history.choice.get()]['id'], rel)
            history.destroy()
        self.assertEqual(self.db.history.rows(rel)[0]['id'], changed)

    def test_search_cancel_preserves_unsaved_profile_and_story_scope(self):
        chapter = self.db.chapters.save('Quiet', 'Find me in chapter')
        self.app.refresh()
        self.app.tabs.select(self.app.characters)
        self.app.characters.fields['name'].set('Uncommitted name')
        before = self.app.characters.values()
        search = SearchDialog(self.app, {})
        search.query.set('Find me in chapter')
        search.refresh()
        search.tree.selection_set(f'chapter:{chapter}')
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=None):
            search.open_selected()
        self.assertTrue(search.winfo_exists())
        self.assertEqual(self.app.characters.values(), before)
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=False):
            search.open_selected()
        self.assertFalse(search.winfo_exists())
        self.assertEqual(self.app.events.chapter_id, chapter)
        search = SearchDialog(self.app, {})
        search.query.set('Find me in chapter')
        search.refresh()
        search.tree.selection_set(f'chapter:{chapter}')
        other = Database(self.folder / 'other.db')
        other.close()
        # A result captured in another story cannot resolve a coincident ID here.
        self.app.projects.install(Database(self.folder / 'other.db'))
        search.open_selected()
        self.assertFalse(search.winfo_exists())
        self.assertEqual(self.app.database.chapters.list(), [])
