"""Capture disposable GUI review cases, never an existing story or user settings.

Run serially with other GUI work. Screenshots capture the visible client window;
do not interact with the desktop during the run. Review images manually because
geometry candidates are observations, not accessibility or clipping assertions.
"""
import argparse
import json
import platform
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageGrab
from story_atlas.app import StoryAtlas
from story_atlas.version import APPLICATION_VERSION, source_fingerprint


def populate(db, portrait=False):
    """Small repeatable fictional fixture; no import of user content."""
    reference = ''
    if portrait:
        path = db.path.parent / 'synthetic-portrait.png'
        image = Image.new('RGB', (160, 160), '#28485d')
        draw = ImageDraw.Draw(image)
        draw.ellipse((50, 25, 110, 85), fill='#d9bc8c')
        draw.rectangle((35, 95, 125, 160), fill='#60b6a7')
        image.save(path)
        reference = db.assets.import_image(path)
    first = db.save_character(dict(name='Alden · keeper of the harbour chronicle', portrait=reference,
                                  role='Archivist', summary='A patient keeper of stories and promises.',
                                  goals='Discover what happened to the missing expedition.',
                                  inventory='Notebook, brass compass, weathered map',
                                  notes='A neutral missing-portrait case.'))
    second = db.save_character(dict(name='Bryn', role='Navigator'))
    db.save_relationship(first, second, 'Travels with')
    db.events.save('The expedition departs', 'A beginning beside the harbour.', 1, [first, second])
    return first


def geometry_candidates(app):
    """Flag controls outside the client; scrolling descendants may be intentional."""
    findings = []
    skipped = {'unviewable_controls': 0, 'scrollable_controls': 0}
    left, top = app.winfo_rootx(), app.winfo_rooty()
    width, height = app.winfo_width(), app.winfo_height()
    def visit(parent):
        for widget in parent.winfo_children():
            if widget.winfo_class() in ('TButton', 'TMenubutton', 'TCombobox'):
                ancestor = widget.master
                in_canvas = False
                while ancestor is not None:
                    in_canvas = in_canvas or ancestor.winfo_class() == 'Canvas'
                    ancestor = ancestor.master
                if not widget.winfo_viewable():
                    skipped['unviewable_controls'] += 1
                    visit(widget)
                    continue
                if in_canvas:
                    skipped['scrollable_controls'] += 1
                    visit(widget)
                    continue
                x, y = widget.winfo_rootx() - left, widget.winfo_rooty() - top
                w, h = widget.winfo_width(), widget.winfo_height()
                if x < 0 or y < 0 or x + w > width + 2 or y + h > height + 2:
                    findings.append(dict(widget=str(widget), widget_class=widget.winfo_class(),
                                         text=str(widget.cget('text')) if 'text' in widget.keys() else '',
                                         rect=[x, y, w, h]))
            visit(widget)
    visit(app)
    return dict(outside_client_candidates=findings, skipped=skipped,
                scope='Visible non-scrolling buttons, menus, and comboboxes; not a text-clipping test.')


def settle(app):
    # Allow scheduled reflow and graph drawing to finish before capture.
    end = time.monotonic() + 0.7
    while time.monotonic() < end:
        app.update()
        time.sleep(0.02)


def prepare_release_state(app, state, mode):
    """Configure only the newly generated Greyhaven fixture through app services."""
    db = app.database
    mira = next(row for row in db.characters() if row['name'] == 'Mira Vale')
    ident = mira['id']
    events = db.events.list()
    metadata = dict(fixture='Bundled Greyhaven sample copied into a new disposable database',
                    selected_character_id=ident, destination=state)
    graph = app.simple.graph if mode == 'Simple' else app.graph
    if state == 'missing-portrait':
        # Valid-shaped reference without stored bytes exercises unavailable-image fallback.
        db.save_character(dict(mira, portrait='0' * 64 + '.png'), ident)
        app.refresh()
    if state in ('overview', 'missing-portrait'):
        if mode == 'Simple':
            app.simple.inspect_character(ident)
        else:
            app.tabs.select(app.characters)
            app.characters.open_character(ident)
    elif state == 'relationships':
        app.tabs.select(app.relationships)
        link = next(row for row in db.relationships() if row['source_id'] == ident and row['semantics'] == 'directional')
        assert app.relationships.select_relationship(link['id'])
        metadata['selected_relationship_id'] = link['id']
    elif state == 'events':
        app.tabs.select(app.events)
        event = events[len(events) // 2]
        app.events.reveal_event(event['id'], db.path)
        metadata['selected_event_id'] = event['id']
    elif state in ('historical', 'planned', 'filtered-empty'):
        if mode == 'Advanced':
            app.tabs.select(app.graph)
        if state == 'planned':
            planned = db.save_character(dict(name='Planned visual review witness', introduction_event_id=events[-1]['id']))
            graph.show_planned.set(True)
            metadata['planned_character_id'] = planned
        if state == 'filtered-empty':
            graph.kind.set('No matching review relationship')
            graph.isolates.set(False)
        elif mode == 'Simple':
            assert app.simple.navigate(events[0]['id']), 'Historical navigation was declined'
        else:
            graph.as_of_id = events[0]['id']
        graph.refresh(force=True)
        if mode == 'Simple':
            app.simple.refresh()
            timeline_id = app.simple.timeline.choices[app.simple.timeline.event.get()]
            assert timeline_id == graph.as_of_id, 'Timeline and graph disagree'
            metadata['timeline_event_id'] = timeline_id
            metadata['timeline_event_label'] = app.simple.timeline.event.get()
        metadata.update(as_of_id=graph.as_of_id, show_planned=graph.show_planned.get(),
                        relationship_filter=graph.kind.get(), graph_node_count=len(graph.graph))
        if state == 'filtered-empty':
            assert len(graph.graph) == 0, 'Filtered-empty fixture did not produce an empty graph'
        if state == 'planned':
            assert planned in graph.graph and graph.graph.nodes[planned].get('planned'), 'Planned node missing or not marked planned'
            graph.select_node(planned)
            assert graph.selection == ('node', planned), 'Planned node selection did not persist'
            metadata['selected_graph_node_id'] = planned
    elif state == 'validation':
        app.simple.new_character()
        assert not app.simple.task.save(), 'Blank-name validation unexpectedly saved'
        metadata['validation_text'] = app.simple.task.error.get()
        metadata['selected_character_id'] = None
    else:
        raise ValueError(f'Unsupported release state: {state}')
    return metadata


def capture(output, theme, mode, size, text_size, scaling=None, state='overview', portrait=False, illustrations='Illustrated', release=False):
    name = f'{mode.lower()}-{theme}-{size}-{text_size}pt'
    if state != 'overview' or portrait:
        name += f'-{state}-' + ('portrait' if portrait else 'no-portrait')
    if scaling is not None:
        name += f'-simulated-tk-{scaling}'
    if release:
        name = 'greyhaven-' + name
    fingerprint_before = source_fingerprint()
    with tempfile.TemporaryDirectory(prefix='fixture-', dir=output) as temporary:
        folder = Path(temporary)
        (folder / 'settings.json').write_text(json.dumps(dict(theme=theme, mode=mode, text_size=text_size, illustrations=illustrations)), encoding='utf-8')
        if release:
            from story_atlas.sample_story import create_sample
            create_sample(folder / 'review.db')
        app = StoryAtlas(folder / 'review.db', settings_path=folder / 'settings.json')
        errors = []
        app.report_callback_exception = lambda kind, value, trace: errors.append(f'{kind.__name__}: {value}')
        try:
            if scaling is not None:
                app.tk.call('tk', 'scaling', scaling)
                app.set_appearance(theme, text_size)
            ident = None if release else populate(app.database, portrait)
            app.refresh()
            app.geometry(size + '+20+20')
            state_metadata = {}
            if release:
                state_metadata = prepare_release_state(app, state, mode)
                ident = state_metadata.get('selected_character_id')
            elif mode == 'Simple':
                (app.simple.edit_character if state == 'editor' else app.simple.inspect_character)(ident)
            else:
                app.tabs.select(app.characters)
                app.characters.open_character(ident)
                if state == 'editor':
                    app.characters.edit_profile()
            # A foreground editor can otherwise occlude screenshots on Windows.
            app.attributes('-topmost', True)
            app.lift()
            settle(app)
            x, y = app.winfo_rootx(), app.winfo_rooty()
            w, h = app.winfo_width(), app.winfo_height()
            if sys.platform == 'win32':
                captured = ImageGrab.grab(window=app.winfo_id())
                capture_method = 'Pillow Windows window capture (Tk client HWND)'
            else:
                captured = ImageGrab.grab(bbox=(x, y, x+w, y+h), all_screens=True)
                capture_method = 'Desktop bounding box; manual occlusion inspection required'
            captured.save(output / (name + '.png'))
            return dict(name=name, theme=theme, mode=mode, requested_size=size, state=state,
                        state_metadata=state_metadata, source_fingerprint_before=fingerprint_before,
                        capture_method=capture_method, captured_pixels=list(captured.size),
                        source_fingerprint_after=source_fingerprint(),
                        requested_illustrations=illustrations,
                        actual_illustrations=app.settings.values.get('illustrations', 'unsupported'),
                        imported_synthetic_portrait=portrait, selected_character_id=ident,
                        actual_client_size=[w, h], text_size=text_size,
                        tk_scaling=float(app.tk.call('tk', 'scaling')),
                        simulated_tk_scaling=scaling,
                        screen_pixels=[app.winfo_screenwidth(), app.winfo_screenheight()],
                        geometry_candidates=geometry_candidates(app), callback_errors=errors,
                        screenshot=name + '.png')
        finally:
            if app.backup_timer:
                app.after_cancel(app.backup_timer)
                app.backup_timer = None
            try:
                app.database.close()
            finally:
                app.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default='baseline')
    parser.add_argument('--tk-scaling', type=float, help='Simulated Tk scaling, NOT a physical Windows DPI test')
    parser.add_argument('--pilot', action='store_true', help='Also capture imported portrait overview and editor cases')
    parser.add_argument('--illustrations', choices=('Illustrated', 'Minimal'), default='Illustrated')
    parser.add_argument('--release', action='store_true', help='Add disposable Greyhaven core-screen, historical, fallback, and validation cases')
    parser.add_argument('--minimum-only', action='store_true', help='Capture only 760x480/16pt cases (four baseline, plus six with --release)')
    args = parser.parse_args()
    if args.minimum_only and args.pilot:
        parser.error('--minimum-only cannot be combined with --pilot')
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.label):
        parser.error('label must contain only letters, digits, underscores, or hyphens')
    output = ROOT / 'build-verification' / 'gui-overhaul' / f'{args.label}-{time.strftime("%Y%m%d-%H%M%S")}'
    output.mkdir(parents=True, exist_ok=False)
    report = dict(version=APPLICATION_VERSION, source_fingerprint=source_fingerprint(),
                  python=sys.version, platform=platform.platform(),
                  dpi_scope='Current desktop only. Physical Windows scaling and per-monitor changes not tested.',
                  fixture='Two fictional characters, one connection, one event; optional synthetic portrait.', cases=[])
    for mode in ('Simple', 'Advanced'):
        for theme in ('dark', 'light'):
            dimensions = (('760x480', 16),) if args.minimum_only else (('1180x720', 10), ('760x480', 16))
            for size, text_size in dimensions:
                report['cases'].append(capture(output, theme, mode, size, text_size, args.tk_scaling, illustrations=args.illustrations))
                (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            if args.pilot:
                for state in ('overview', 'editor'):
                    report['cases'].append(capture(output, theme, mode, '1180x720', 10, args.tk_scaling, state, True, args.illustrations))
                    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if args.release:
        release_cases = [('Simple', 'overview'), ('Advanced', 'overview'),
                         ('Advanced', 'relationships'), ('Advanced', 'events'),
                         ('Simple', 'historical'), ('Advanced', 'planned'),
                         ('Simple', 'filtered-empty'), ('Advanced', 'missing-portrait'),
                         ('Simple', 'validation')]
        for theme in ('dark', 'light'):
            for mode, state in ([] if args.minimum_only else release_cases):
                report['cases'].append(capture(output, theme, mode, '900x600', 10, args.tk_scaling,
                                               state, illustrations=args.illustrations, release=True))
                (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            for state in ('relationships', 'events', 'planned'):
                report['cases'].append(capture(output, theme, 'Advanced', '760x480', 16, args.tk_scaling,
                                               state, illustrations=args.illustrations, release=True))
                (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(output)
    fingerprints = {report['source_fingerprint']}
    for case in report['cases']:
        fingerprints.update((case['source_fingerprint_before'], case['source_fingerprint_after']))
    if len(fingerprints) != 1:
        raise SystemExit('Source changed during capture; mixed-source images are not valid release evidence')
    if any(case['callback_errors'] for case in report['cases']):
        raise SystemExit('GUI callback errors recorded; review report.json')


if __name__ == '__main__':
    main()
