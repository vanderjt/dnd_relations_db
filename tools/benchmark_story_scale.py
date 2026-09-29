"""Disposable, deterministic chapter/event/history benchmark; separate from correctness tests."""
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from story_atlas.app import StoryAtlas
from story_atlas.history_dialog import HistoryDialog
from story_atlas.retrieval import search

SEED = 24092026


def populate(db):
    pairs = [(a, b) for a in range(1, 101) for b in range(a + 1, 101)][:300]
    with db.connection:
        db.connection.executemany('INSERT INTO characters(id,name) VALUES (?,?)',
                                  ((i, f'Character {i:03d}') for i in range(1, 101)))
        db.connection.executemany('INSERT INTO chapters(id,title,summary,sequence) VALUES (?,?,?,?)',
                                  ((i, f'Chapter {i:02d}', 'Deterministic summary', i) for i in range(1, 31)))
        db.connection.executemany('INSERT INTO story_events(id,title,summary,sequence,chapter_id) VALUES (?,?,?,?,?)',
                                  ((i, f'Event {i:03d}', f'Summary marker {i:03d}', i, (i - 1) // 10 + 1)
                                   for i in range(1, 301)))
        db.connection.executemany('INSERT INTO event_participants(event_id,character_id) VALUES (?,?)',
                                  ((i, i % 100 + 1) for i in range(1, 301)))
        db.connection.executemany('''INSERT INTO relationships(id,source_id,target_id,kind,notes,semantics,
                                  inverse_label,baseline_active) VALUES (?,?,?,?,?,?,?,?)''',
                                  ((i, a, b, 'Friend', f'Baseline {i}', 'directional', '', 1)
                                   for i, (a, b) in enumerate(pairs, 1)))
        db.connection.executemany('''INSERT INTO relationship_history(relationship_id,event_id,active,source_id,
                                  target_id,kind,notes,semantics,inverse_label) VALUES (?,?,?,?,?,?,?,?,?)''',
                                  ((i, event, 1, a, b, 'Friend' if j % 2 else 'Rival',
                                    f'History marker {i} state {j}', 'directional', '')
                                   for i, (a, b) in enumerate(pairs, 1)
                                   for j, event in enumerate((20, 100, 200, 300), 1)))
    db.history.validate()


def measure(fn, repeat=5):
    fn()  # warm-up
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return {'median_seconds': statistics.median(times), 'slowest_seconds': max(times), 'runs': repeat}


def run():
    with tempfile.TemporaryDirectory(prefix='story-atlas-scale-') as temporary:
        root = Path(temporary)
        app = StoryAtlas(root / 'scale.db', settings_path=root / 'settings.json')
        try:
            populate(app.database)
            app.update_idletasks()
            switches = iter((17, 18) * 4)
            def switch_chapter():
                app.events.reveal_chapter(next(switches), app.database.path)
                app.update_idletasks()
            operations = {
                'initial_chapter_display': lambda: (app.events.refresh(), app.update_idletasks()),
                'chapter_switch': switch_chapter,
                'search': lambda: search(app.database, 'History marker 299'),
                'exact_history_open': lambda: open_history(app),
                'chapter_move_preview': lambda: app.database.chapters.preview_move(17, -1),
            }
            results = {name: measure(fn) for name, fn in operations.items()}
            return {'seed': SEED, 'dataset': {'chapters': 30, 'events': 300, 'characters': 100,
                                             'relationships': 300, 'history_states': 1200},
                    'environment': {'python': sys.version, 'platform': platform.platform(),
                                    'processor': platform.processor(), 'logical_cpus': os.cpu_count()},
                    'warmup': 1, 'rendering': 'Tk widgets and idle layout included for chapter display/switch/history; search and preview are storage-only',
                    'results': results}
        finally:
            app.database.close()
            app.destroy()


def open_history(app):
    dialog = HistoryDialog(app, app.database, app.refresh, 299)
    key = next(key for key, row in dialog.states.items() if row.get('event_id') == 200)
    dialog.tree.selection_set(key)
    dialog.tree.see(key)
    app.update_idletasks()
    dialog.destroy()


if __name__ == '__main__':
    report = run()
    output = Path('build-verification/scale-benchmark-2026-09-24.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
