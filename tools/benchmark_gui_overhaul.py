"""Repeated disposable GUI timings, with and without 100 managed portraits.

Run serially with GUI tests. --source-root can compare an extracted source
revision without switching the working checkout. Times include Tk idle layout;
they exclude imports, fixture creation and process startup. No user data is used.
"""
import argparse
import json
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeat', type=int, default=5)
    args = parser.parse_args()
    if args.repeat < 2:
        parser.error('--repeat must be at least 2')
    sys.path.insert(0, str(args.source_root.resolve()))
    from PIL import Image
    from story_atlas.app import StoryAtlas
    from story_atlas.database import Database
    from story_atlas.settings import Settings
    from story_atlas.version import APPLICATION_VERSION, source_fingerprint

    def fixture(path, portraits):
        db = Database(path)
        try:
            references = []
            for i in range(100):
                reference = ''
                if portraits:
                    portrait = path.parent / f'portrait-{i}.png'
                    Image.new('RGB', (96, 96), (30 + i * 2, 80, 180 - i)).save(portrait)
                    reference = db.assets.import_image(portrait)
                references.append(reference)
            # Fixture population is deliberately outside timing/undo history.
            with db.connection:
                db.connection.executemany('INSERT INTO characters(id,name,portrait) VALUES (?,?,?)',
                                         ((i + 1, f'Character {i:03d}', references[i]) for i in range(100)))
            for i in range(100):
                for step in (1, 7, 13):
                    db.save_relationship(i + 1, (i + step) % 100 + 1, 'Travels with')
        finally:
            db.close()

    def timed(app, operation):
        started = time.perf_counter()
        operation()
        app.update()
        return (time.perf_counter() - started) * 1000

    def measure(operation):
        operation()  # one warm-up
        samples = [operation() for _ in range(args.repeat)]
        return {'median_ms': statistics.median(samples), 'samples_ms': samples}

    results = {}
    with tempfile.TemporaryDirectory(prefix='atlas-gui-benchmark-') as temporary:
        folder = Path(temporary)
        for portraits in (False, True):
            case = folder / ('portraits' if portraits else 'no-portraits')
            case.mkdir()
            path = case / 'story.db'
            fixture(path, portraits)
            settings = case / 'settings.json'
            Settings(settings).save(mode='Simple', theme='dark', text_size=10)
            paint = []
            callback_errors = []
            app = None
            try:
                # Fresh Tk roots, same process and database; first sample warm-up.
                for _ in range(args.repeat + 1):
                    if app is not None:
                        try:
                            app.database.close()
                        finally:
                            app.destroy()
                    started = time.perf_counter()
                    app = StoryAtlas(path, settings_path=settings)
                    app.report_callback_exception = lambda kind, value, trace: callback_errors.append(f'{kind.__name__}: {value}')
                    app.update()
                    paint.append((time.perf_counter() - started) * 1000)
                def switch_modes():
                    def switch():
                        for mode in ('Advanced', 'Simple'):
                            app.mode.set(mode)
                            assert app.switch_mode(), 'Fixture unexpectedly blocked mode change'
                            app.update()
                    return timed(app, switch)
                def switch_themes():
                    def switch():
                        for theme in ('light', 'dark'):
                            app.set_appearance(theme, 10)
                            app.update()
                    return timed(app, switch)
                def redraw():
                    return timed(app, lambda: app.simple.graph.refresh(force=True))
                results[case.name] = {
                    'first_paint': {'median_ms': statistics.median(paint[1:]), 'samples_ms': paint[1:]},
                    'mode_round_trip': measure(switch_modes),
                    'theme_round_trip': measure(switch_themes),
                    'graph_refresh': measure(redraw),
                    'callback_errors': callback_errors,
                }
            finally:
                if app is not None:
                    try:
                        app.database.close()
                    finally:
                        app.destroy()
    report = {
        'version': APPLICATION_VERSION, 'fingerprint': source_fingerprint(args.source_root),
        'platform': platform.platform(), 'python': sys.version,
        'dataset': {'characters': 100, 'relationships': 300, 'unique_portraits_when_enabled': 100},
        'repeat': args.repeat, 'warmup': 1, 'results': results,
        'limits': 'Same-process Tk first paint, not cold process startup; includes Tk rendering, excludes fixture/imports. No memory or physical DPI measurement.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if any(case['callback_errors'] for case in results.values()):
        raise SystemExit('GUI callback failures recorded; timings are not valid acceptance evidence')


if __name__ == '__main__':
    main()
