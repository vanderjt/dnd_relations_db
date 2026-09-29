"""Exercise the visible guided connection buttons, including early validation."""
import unittest
from matplotlib.backend_bases import MouseEvent
import test_simple_mode as baseline


class ConnectionFlowTests(unittest.TestCase):
    setUp = baseline.SimpleUITests.setUp
    cleanup = baseline.SimpleUITests.cleanup
    cast = baseline.SimpleUITests.cast

    def start(self):
        ids = self.cast()
        self.ws.clear_selection()
        task = self.ws.new_relationship()
        self.app.update()
        return task, ids

    def test_source_cards_mouse_keyboard_duplicates_and_focus(self):
        a = self.db.save_character(dict(name='Robin', role='Healer', faction='Dawn'))
        b = self.db.save_character(dict(name='Robin', role='Guard', species='Elf'))
        self.app.refresh()
        task = self.ws.new_relationship()
        self.app.update()
        self.assertEqual(task.heading.get(), 'Who are you connecting?')
        self.assertFalse(task.save_button.winfo_viewable())
        picker = task.boxes['source']
        self.assertIn('Healer', picker.buttons[a].context['text'])
        self.assertIn('Guard', picker.buttons[b].context['text'])
        picker.query.set('Elf')
        self.app.update()
        self.assertFalse(picker.buttons[a].winfo_manager())
        self.assertTrue(picker.buttons[b].winfo_manager())
        picker.query.set('')
        for key in ('Return', 'space'):
            card = picker.buttons[a]
            card.focus_force()
            self.app.update()
            self.assertEqual(task.step, 0)
            card.event_generate(f'<KeyPress-{key}>')
            card.event_generate(f'<KeyRelease-{key}>')
            self.app.update()
            self.assertEqual(task.step, 1)
            self.assertEqual(task.targets, [])
            self.assertEqual(self.app.focus_get(), task.boxes['target'].search)
            self.assertEqual(task.source_card.name['text'], 'Robin')
            task.change_button.invoke()
            self.app.update()
        picker.buttons[b].name.event_generate('<ButtonPress-1>', x=5, y=5)
        picker.buttons[b].name.event_generate('<ButtonRelease-1>', x=5, y=5)
        self.app.update()
        self.assertEqual(task.step, 1)
        self.assertEqual(task.variables['source'].get(), task.label(b))
        self.assertEqual(self.errors, [])

    def test_real_graph_gesture_advances_once(self):
        task, (a, b, c) = self.start()
        graph = self.ws.graph
        for ident in (a, b):
            x, y = graph.renderer.axes.transData.transform(graph.positions[ident])
            for event in ('button_press_event', 'button_release_event'):
                graph.canvas.callbacks.process(event, MouseEvent(event, graph.canvas, x, y, button=1))
            self.app.update()
            self.assertEqual(task.step, 1)
            self.assertEqual(task.targets, [] if ident == a else [b])
        self.assertEqual(task.variables['source'].get(), task.label(a))
        self.assertEqual(self.errors, [])

    def test_change_character_preserves_details_targets_and_recovers(self):
        from story_atlas.simple_batch import BatchPane
        task, (a, b, c) = self.start()
        task.boxes['source'].buttons[a].invoke()
        for ident in (b, c):
            task.toggle_target(ident)
        task.advance()
        task.variables['kind'].set('Mentor')
        task.variables['semantics'].set('Directional')
        task.variables['inverse_label'].set('Student')
        task.category.set('Support')
        task.notes.insert('1.0', 'Keep these details')
        details = task.values()
        task.back()
        task.change_button.invoke()
        task.boxes['source'].buttons[b].invoke()
        self.assertEqual(task.targets, [c])
        for key in ('kind', 'semantics', 'inverse_label', 'event', 'category', 'notes'):
            self.assertEqual(task.values()[key], details[key])
        payload = task.draft_payload()
        self.ws.remove_task()
        recovered = self.ws.mount(lambda: BatchPane(self.ws.host, self.ws, recovered=payload))
        self.app.update()
        self.assertEqual(recovered.step, 1)
        self.assertEqual(recovered.targets, [c])
        self.assertEqual(recovered.source_card.name['text'], 'Bryn')
        self.assertEqual(recovered.values(), payload['values'])
        self.assertEqual(self.errors, [])

    def test_context_connect_and_persistent_card_in_compact_layout(self):
        task, (a, b, c) = self.start()
        self.ws.remove_task()
        self.ws.connect(b)
        task = self.ws.task
        for theme in ('light', 'dark'):
            self.app.geometry('900x600')
            self.app.set_appearance(theme, 14)
            self.app.update()
            self.assertEqual(task.step, 1)
            self.assertEqual(task.source_card.name['text'], 'Bryn')
            top = task.source_card.winfo_rooty()
            task.boxes['target'].list.canvas.yview_moveto(1)
            self.app.update()
            self.assertEqual(task.source_card.winfo_rooty(), top)
            self.assertTrue(task.change_button.winfo_viewable())
            self.assertGreaterEqual(task.boxes['target'].list.canvas.winfo_height(), 40)
            self.assertLessEqual(task.change_button.winfo_rootx() + task.change_button.winfo_width(), task.winfo_rootx() + task.winfo_width())
            self.assertFalse(self.ws.selection_toggle.winfo_manager())
        self.assertEqual(self.errors, [])

    def test_direct_choices_steps_review_and_commit(self):
        task, (a, b, c) = self.start()
        self.assertEqual(task.step, 0)
        self.assertIn('disabled', task.save_button.state())
        self.assertFalse(self.ws.selection_toggle.winfo_manager())
        task.boxes['source'].buttons[a].invoke()
        self.assertEqual(task.step, 1)
        self.assertFalse(task.boxes['target'].buttons[a].winfo_manager())
        self.assertIn('disabled', task.save_button.state())
        task.boxes['target'].buttons[b].invoke()
        task.boxes['target'].query.set('no match')
        self.assertEqual(task.targets, [b])
        self.assertIn('Bryn', task.summary.get())
        task.save_button.invoke()
        self.assertEqual(task.step, 2)
        self.assertIn('disabled', task.save_button.state())
        task.variables['kind'].set('Friend')
        task.category.set('Personal')
        self.assertNotIn('disabled', task.save_button.state())
        task.save_button.invoke()
        self.assertEqual(task.step, 3)
        self.assertEqual(self.db.relationships(), [])
        self.assertIn('Alden ↔ Bryn: Friend', task.review_text.get('1.0', 'end'))
        self.ws.choose_node(c)
        self.assertEqual(task.targets, [b])
        task.save_button.invoke()
        self.assertEqual(task.step, 0)
        row = self.db.relationships()[0]
        self.assertEqual((row['source_id'], row['target_id'], row['category']), (a, b, 'Personal'))
        self.assertEqual(task.targets, [])
        self.assertEqual(self.errors, [])

    def test_graph_selection_obeys_step_back_keeps_inputs_and_keyboard_selects(self):
        task, (a, b, c) = self.start()
        self.ws.choose_node(a)
        self.assertEqual(task.step, 1)
        self.assertEqual(task.targets, [])
        task.change_button.invoke()
        self.ws.choose_node(b)
        self.assertEqual(task.variables['source'].get(), task.label(b))
        self.ws.choose_node(c)
        self.assertEqual(task.targets, [c])
        self.ws.choose_node(c)
        self.assertEqual(task.targets, [])
        self.app.update()
        button = task.boxes['target'].buttons[a]
        button.focus_force()
        self.app.update()
        button.event_generate('<KeyPress-space>')
        button.event_generate('<KeyRelease-space>')
        self.app.update()
        self.assertEqual(task.targets, [a])
        task.save_button.invoke()
        task.variables['kind'].set('Mentor')
        task.variables['semantics'].set('Directional')
        task.variables['inverse_label'].set('Student')
        task.back_button.invoke()
        task.back_button.invoke()
        self.ws.choose_node(a)
        self.assertEqual(task.targets, [])
        task.boxes['target'].buttons[c].invoke()
        task.save_button.invoke()
        self.assertEqual(task.variables['kind'].get(), 'Mentor')
        self.assertEqual(task.variables['inverse_label'].get(), 'Student')
        self.assertEqual(self.errors, [])

    def test_invalid_timing_and_duplicates_are_visible_before_review(self):
        task, (a, b, c) = self.start()
        later = self.db.events.save('Later', '', 2)
        values = next(row for row in self.db.characters() if row['id'] == b)
        self.db.save_character(dict(values, introduction_event_id=later), b)
        task.boxes['source'].buttons[a].invoke()
        task.save_button.invoke()
        task.boxes['target'].buttons[b].invoke()
        task.save_button.invoke()
        task.variables['kind'].set('Friend')
        self.assertIn('disabled', task.save_button.state())
        self.assertIn('introduced', task.detail_hint.get())
        self.assertEqual(task.step, 2)
        task.back_button.invoke()
        task.boxes['target'].buttons[b].invoke()
        task.boxes['target'].buttons[c].invoke()
        task.save_button.invoke()
        self.assertNotIn('disabled', task.save_button.state())
        self.db.save_relationship(a, c, 'Rival', semantics='mutual')
        task.variables['kind'].set('Rival')
        self.assertIn('disabled', task.save_button.state())
        self.assertIn('already exists', task.detail_hint.get())
        self.assertEqual(self.errors, [])

    def test_nested_creation_auto_selects_and_draft_recovers_confirmed_ids(self):
        task, (a, b, c) = self.start()
        task.boxes['source'].buttons[a].invoke()
        task.save_button.invoke()
        nested = task.create_character('target')
        nested.name.set('New friend')
        self.assertTrue(nested.save())
        created = next(row['id'] for row in self.db.characters() if row['name'] == 'New friend')
        self.assertEqual(task.targets, [created])
        self.assertEqual(task.variables['target'].get(), '')
        saved = task.draft_payload()
        task.targets.clear()
        task.restore_draft(saved)
        self.assertEqual(task.targets, [created])
        self.assertEqual(self.errors, [])

    def test_compact_steps_keep_navigation_visible_and_no_duplicate_controls(self):
        task, (a, b, c) = self.start()
        self.app.geometry('900x650')
        self.app.set_appearance('dark', 14)
        task.boxes['source'].buttons[a].invoke()
        for step in (0, 1, 2, 3):
            if step == 1:
                task.toggle_target(b)
            if step == 2:
                task.variables['kind'].set('Friend')
            task.show_step(step)
            self.app.update()
            button = task.save_button
            self.assertEqual(bool(button.winfo_viewable()), step != 0)
            if step == 0:
                button = task.navigation[-1]
            self.assertGreaterEqual(button.winfo_rooty(), task.winfo_rooty())
            self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), task.winfo_rooty() + task.winfo_height())
            self.assertFalse(self.ws.selection_controls.winfo_manager())
            self.assertFalse(self.ws.selection_scroll.winfo_manager())
        self.assertEqual(self.errors, [])

    def test_legacy_pending_target_and_nested_draft_recovery(self):
        from story_atlas.simple_batch import BatchPane
        task, (a, b, c) = self.start()
        task.boxes['source'].buttons[a].invoke()
        task.save_button.invoke()
        payload = task.draft_payload()
        payload['pending_target_id'] = b
        payload['values']['target'] = task.label(b)
        payload['values']['pending_creation'] = 'Unfinished friend'
        payload['pending_creation_field'] = 'target'
        self.ws.remove_task()
        recovered = self.ws.mount(lambda: BatchPane(self.ws.host, self.ws, recovered=payload))
        self.app.update()
        self.assertEqual(recovered.targets, [b])
        self.assertEqual(recovered.nested.name.get(), 'Unfinished friend')
        self.assertFalse(recovered.scroller.winfo_manager())
        self.assertIn('disabled', recovered.back_button.state())
        self.assertTrue(recovered.nested.save())
        self.assertEqual(recovered.step, 1)
        self.assertEqual(len(recovered.targets), 2)
        self.assertEqual(self.errors, [])
