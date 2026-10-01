"""Export only a newly created Greyhaven sample, never an existing user story."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from story_atlas.sample_story import create_sample
from story_atlas.database import Database

with tempfile.TemporaryDirectory(prefix='greyhaven-prototype-') as temporary:
    path = create_sample(Path(temporary) / 'Greyhaven.db')
    db = Database(path)
    try:
        events = db.events.list()
        payload = dict(title='Greyhaven', characters=db.characters(),
                       chapters=db.chapters.list(), events=events,
                       relationships={str(event['id']): db.relationships(event['id']) for event in events},
                       opening_relationships=db.relationships(0),
                       provenance='Generated from create_sample in story_atlas/sample_story.py. Character profiles are template starting points, not reconstructed historical profiles. Relationship snapshots retain the sample event history. Age and numerical statistics are deliberately unspecified.')
        Path(__file__).with_name('greyhaven.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        db.close()
