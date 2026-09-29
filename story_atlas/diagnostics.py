"""Packaged smoke check: exercise bundled GUI resources using disposable data."""
import json
import platform
from pathlib import Path
import sys
import tempfile
import traceback
import sqlite3
from unittest.mock import patch


def run(data_folder, report_path):
    report = dict(ok=False, frozen=bool(getattr(sys, "frozen", False)), python=sys.version, platform=platform.platform())
    app = None
    try:
        from PIL import Image
        import matplotlib
        from .app import StoryAtlas
        from .sample_story import create_sample
        from .paths import resource
        from .backup import snapshot, restore_backup
        from .backup import backup_directory
        from .database import Database
        from .migrations import MIGRATIONS, CURRENT_VERSION
        from .version import APPLICATION_VERSION, about_text, build_identity
        from .onboarding import Welcome
        from .sample_story import new_sample
        from .settings import Settings
        with tempfile.TemporaryDirectory(prefix="self-test-", dir=data_folder) as temporary:
            folder = Path(temporary)
            settings_path = folder / 'settings.json'
            welcome = Welcome(folder, Settings(settings_path))
            with patch('story_atlas.onboarding.filedialog.asksaveasfilename', return_value=str(folder / 'new.db')):
                setup = welcome.start_empty()
                setup.fields[0].set('Packaged new story')
                setup.save()
            new_path = welcome.result
            new_db = Database(new_path)
            new_db.save_character({'name': 'First-launch character', 'goals': 'Keep this goal'})
            new_db.close()
            new_db = Database(new_path)
            assert new_db.characters()[0]['goals'] == 'Keep this goal'
            new_db.close()
            story = create_sample(folder / "Greyhaven.db")
            second_sample = new_sample(folder)
            assert second_sample != story and second_sample != new_path
            Settings(settings_path).save(mode='Advanced')
            app = StoryAtlas(story, settings_path=settings_path)
            app.withdraw()
            app.update()
            assert len(app.database.characters()) == 18
            assert app.database.chapters.list() and any(row['goals'] for row in app.database.characters())
            mode, fingerprint = build_identity()
            identity = about_text(app.database)
            assert f'Story Atlas {APPLICATION_VERSION}' in identity
            assert f'Supported database schema: {CURRENT_VERSION}' in identity
            assert f'Active database schema: {CURRENT_VERSION}' in identity
            assert (mode == 'Packaged') == bool(getattr(sys, 'frozen', False))
            assert len(fingerprint) == 64
            first_event = app.database.events.list()[0]
            app.events.reveal_event(first_event['id'], app.database.path)
            entry = app.events.connect_characters()
            assert entry.context_event_id == first_event['id'] and entry.use_context_event()
            labels = list(entry.choices)
            entry.variables['source'].set(labels[0])
            entry.variables['target'].set(labels[1])
            entry.variables['kind'].set('Release check bond')
            entry.variables['semantics'].set('Directional')
            entry.category.set('Support')
            assert entry.save() and entry.category.get() == 'Other'
            assert all(not value for key, value in entry.values().items() if key != 'category')
            assert next(row for row in app.database.relationships() if row['id'] == entry.last_saved_id)['category'] == 'Support'
            release_link = entry.last_saved_id
            entry.destroy()
            # Exercise the packaged event-centered workflow, beyond asset loading.
            editor = app.events.edit()
            editor.title_value.set('Packaged UX verification')
            participant = app.database.characters()[0]['id']
            editor.participants.query.set(str(participant))
            editor.participants.buttons[participant].invoke()
            editor.participants.query.set('no matches')
            assert participant in editor.participants.selected
            assert editor.save()
            new_event = int(app.events.tree.selection()[0])
            task = app.events.add_relationship_change()
            task.choice.set(next(label for label, row in task.choices.items() if row['id'] == release_link))
            state_editor = task.describe()
            state_editor.variables['kind'].set('Packaged changed bond')
            assert not state_editor.save() and state_editor.step == 'review'
            assert state_editor.save()
            assert task.editor is None
            task.choice.set(next(label for label, row in task.choices.items() if row['id'] == release_link))
            correction = task.review()
            correction.notes.insert('1.0', 'Packaged correction')
            correction.review_change()
            assert correction.commit()
            task.destroy()
            app.events.show_graph()
            app.graph.open_profile(participant)
            assert app.navigation.back() and app.navigation.back()
            assert app.events.tree.selection() == (str(new_event),)
            assert app.database.history.rows(release_link)[-1]['notes'] == 'Packaged correction'
            # Correct an ended state through the same graph route used in production.
            latest = app.database.history.rows(release_link)[-1]
            app.database.history.write(release_link, latest['event_id'], latest, False, latest['id'])
            before = app.database.history.rows(release_link)
            app.graph.as_of_id = latest['event_id']
            app.graph.changes_only.set(True)
            app.graph.refresh(force=True)
            app.graph.select_edge(release_link)
            with patch('story_atlas.graph_view.messagebox.askyesno', return_value=True):
                correction = app.graph.inspector.edit_selected()
            correction.notes.delete('1.0', 'end')
            correction.notes.insert('1.0', 'Ended correction')
            assert correction.save()
            correction.destroy()
            before[-1]['notes'] = 'Ended correction'
            assert app.database.history.rows(release_link) == before
            history = app.graph.inspector.history_selected()
            assert history.as_of_id == latest['event_id']
            assert history.tree.selection() == (str(latest['id']),)
            history.close()
            app.graph.changes_only.set(False)
            app.graph.refresh(force=True)
            app.graph.canvas.draw()
            app.graph.figure.savefig(folder / "graph.png")
            assert (folder / "graph.png").stat().st_size > 1000
            with patch('story_atlas.graph_actions.filedialog.asksaveasfilename', return_value=str(folder / 'historical.png')):
                app.graph.as_of_id = first_event['id']
                app.graph.refresh(force=True)
                app.graph.export()
            assert (folder / 'historical.png').is_file() and (folder / 'historical.json').is_file()
            metadata = json.loads((folder / 'historical.json').read_text(encoding='utf-8'))
            assert metadata['time_scope'].startswith('After: ')
            assert 'not historically versioned' in metadata['profile_scope']
            icon = resource("story-atlas.ico")
            app.iconbitmap(str(icon))
            portrait = folder / "portrait.png"
            Image.new("RGB", (32, 32), "teal").save(portrait)
            reference = app.database.assets.import_image(portrait)
            assert app.database.assets.thumbnail(reference) is not None
            backup = snapshot(app.database.connection, story)
            restored = Database(restore_backup(backup, folder / "restored.db"))
            assert len(restored.characters()) == 18
            assert restored.assets.thumbnail(reference) is not None
            restored.close()
            app.settings.save(theme='light')
            assert Settings(settings_path).values['theme'] == 'light'
            legacy_path = folder / 'version7.db'
            legacy_connection = sqlite3.connect(legacy_path)
            for migration in MIGRATIONS[:7]:
                migration(legacy_connection)
            legacy_connection.execute("INSERT INTO characters(id,name) VALUES (1,'Legacy')")
            legacy_connection.execute("PRAGMA user_version=7")
            legacy_connection.commit()
            legacy_connection.close()
            upgraded = Database(legacy_path)
            assert upgraded.connection.execute('PRAGMA user_version').fetchone()[0] == CURRENT_VERSION
            assert upgraded.characters()[0]['name'] == 'Legacy'
            upgraded.close()
            assert list(backup_directory(legacy_path).glob('pre-migration-v7*.db'))
            current = Database(story)
            assert current.connection.execute('PRAGMA user_version').fetchone()[0] == CURRENT_VERSION
            current.close()
            # Exercise the actual Simple pane tasks in the frozen application.
            app.mode.set('Simple')
            assert app.switch_mode()
            workspace = app.simple
            workspace.navigate(first_event['id'])
            workspace.new_character()
            profile = workspace.task
            profile.fields['name'].set('Packaged Simple character')
            profile.fields['character_type'].set('Player')
            assert all(not section[2] for section in profile.editor.collapsible_sections.values())
            assert -1 in workspace.graph.graph and profile.save()
            introduced = profile.character_id
            assert next(row for row in app.database.characters() if row['id'] == introduced)['classification'] == 'Player Ally'
            workspace.graph.ensure_current()  # Smoke host is deliberately withdrawn.
            assert -1 not in workspace.graph.graph
            old_point = list(workspace.graph.positions[introduced])
            assert workspace.close_task()
            workspace.new_character()
            assert workspace.graph.positions[-1] != old_point
            assert 'narrative_role' not in workspace.task.editor.field_widgets
            assert 'classification' not in workspace.task.editor.field_widgets
            assert workspace.close_task()
            workspace.ordered.ids = [introduced, participant, next(row['id'] for row in app.database.characters() if row['id'] not in (introduced, participant))]
            workspace.new_relationship()
            batch = workspace.task
            assert batch.step == 1
            original_targets = batch.targets.copy()
            batch.change_button.invoke()
            assert batch.step == 0 and batch.save_button not in batch.bar.items
            batch.boxes['source'].buttons[introduced].invoke()
            assert batch.step == 1 and batch.targets == original_targets
            assert batch.source_card.name['text'] == 'Packaged Simple character'
            batch.variables['kind'].set('Packaged Simple link')
            batch.variables['semantics'].set('Directional')
            assert not batch.save() and batch.save()
            assert not workspace.ordered.ids and all(not batch.variables[key].get() for key in ('source', 'target', 'kind', 'inverse_label'))
            assert batch.step == 0 and batch.variables['semantics'].get() == 'Mutual'
            assert workspace.task is batch and workspace.close_task()
            workspace.inspect_character(introduced)
            from .simple_summary import CharacterSummary
            assert isinstance(workspace.task, CharacterSummary) and workspace.can_leave()
            workspace.close_task()
            workspace.new_event()
            event_task = workspace.task
            event_task.title.set('Recovered packaged scene')
            event_task.draft.flush()
            payload = next(item['values'] for item in app.database.drafts.list() if item['key'] == 'task:event:new')
            workspace.remove_task()
            from .simple_event import EventPane
            recovered = workspace.mount(lambda: EventPane(workspace.host, workspace, recovered=payload))
            assert recovered.title.get() == 'Recovered packaged scene' and recovered.save()
            assert not any(item['key'] == 'task:event:new' for item in app.database.drafts.list())
            from .story_setup import story_filename, available_path
            assert story_filename('CON') == '_CON.db'
            assert available_path(story.parent, story.name) != story
            workspace.navigate(0)
            assert introduced not in workspace.graph.graph
            workspace.graph.show_planned.set(True)
            workspace.graph.refresh(force=True)
            assert workspace.graph.graph.nodes[introduced]['planned']
            assert not list(workspace.graph.graph.edges(introduced))
            # Use the same story-switch and saved-view actions as the desktop UI.
            assert app.projects.try_sample('prometheus')
            assert len(app.database.characters()) == 17 and len(app.database.events.list()) == 20
            from .graph_state import SavedViews
            for name, kind in (('03 · The glacier bargain', 'Conditional agreement'),
                               ('04 · The promise breaks', 'Broken promise')):
                workspace.graph.apply_state(SavedViews(app.database).load(name))
                app.update()
                assert any(data['kind'] == kind for *_, data in workspace.graph.graph.edges(data=True))
            legend_labels = [text.get_text() for text in workspace.graph.renderer.axes.get_legend().get_texts()]
            assert 'Merchant' in legend_labels and 'Support' in legend_labels
            doomed = next(row['id'] for row in app.database.characters() if row['name'] == 'Victor Frankenstein')
            attached = {row['id'] for row in app.database.relationship_records() if doomed in (row['source_id'], row['target_id'])}
            workspace.graph.select_node(doomed)
            with patch('story_atlas.simple_workspace.messagebox.askyesno', return_value=True):
                workspace.task.delete_button.invoke()
            workspace.graph.ensure_current()  # The smoke window is withdrawn.
            assert doomed not in workspace.graph.graph
            assert not attached & {row['id'] for row in app.database.relationship_records()}
            app.database.trash.restore('character', doomed)
            assert attached <= {row['id'] for row in app.database.relationship_records()}
            assert app.undo_controls.change()
            assert doomed not in {row['id'] for row in app.database.characters()}
            assert app.undo_controls.change(True)
            assert attached <= {row['id'] for row in app.database.relationship_records()}
            report.update(tcl=app.tk.call('info', 'patchlevel'), tk=app.tk.call('package', 'provide', 'Tk'),
                          tcl_library=app.tk.call('info', 'library'), matplotlib_data=matplotlib.get_data_path(),
                          matplotlib_cache=matplotlib.get_cachedir(), icon=str(icon), data_root=str(data_folder),
                          app_version=APPLICATION_VERSION, build_mode=mode, build_fingerprint=fingerprint,
                          schema=CURRENT_VERSION,
                          checks=['new-story first launch and reopen', 'separate expanded sample stories',
                                  'full app startup', 'About identity and active schema', 'Goals and Chapters',
                                  'contextual relationship entry and batch reset', 'TkAgg render and fonts',
                                  'event creation reveal and searchable participant retention',
                                  'contained record-review-correction task', 'Event-Graph-Profile return navigation',
                                  'ended graph correction preserves exact state', 'graph History retains time and entry',
                                  'historical time/display/profile export scopes',
                                  'historical graph snapshot PNG and JSON', 'window icon',
                                  'portrait import/cache', 'SQLite backup/restore with assets',
                                  'settings persistence', 'version-7 migration and backup', 'version-13 reopen', 'unified character type persistence and collapsed profile', 'nonoverlapping provisional placement', 'Simple summary inspection', 'Simple event draft recover and commit', 'title-derived filename safety', 'Simple provisional save and introduction visibility',
                                  'Simple source card advances and Change character preserves targets',
                                  'Simple full-batch review/commit/reset/stay-open', 'Simple planned cast without active links',
                                  'writable external data', 'the modern prometheus example and saved scenes',
                                  'combined dot and link legend', 'summary delete cascades to Trash and restores connections',
                                  'saved story undo and redo preserve character and connections'], ok=True)
            app.database.close()
            app.destroy()
            app = None
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if app is not None:
            app.database.close()
            app.destroy()
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1
