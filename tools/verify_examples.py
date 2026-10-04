"""Read-only validation of the saved examples, including temporal facts."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from story_atlas.preview_store import PreviewStore


def verify_literary(path):
    store = PreviewStore(path)
    try:
        assert store.connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not store.rows('PRAGMA foreign_key_check')
        workspaces = [store.workspace(e['id']) for e in store.events()]
        for w in workspaces:
            ids = {c['id'] for c in w['characters']}
            assert all(c['source_id'] in ids and c['target_id'] in ids for c in w['connections'])
            assert all(e['summary'] and e['purpose'] and e['location_id'] and e['notes'] for e in w['events'])
            assert all(any(p['event_id'] == e['id'] for p in w['participants']) for e in w['events'])
            assert not w['drafts']
        def character(event, name):
            return next(c for c in workspaces[event-1]['characters'] if c['name'] == name)
        def relationship(event, source, target):
            ids = {character(event, name)['id'] for name in (source, target)}
            return next(c for c in workspaces[event-1]['connections'] if {c['source_id'], c['target_id']} == ids)
        if path.stem == 'Frankenstein':
            assert len(workspaces) == 20 and len(workspaces[0]['characters']) == 17
            assert character(1,'The creature')['status'] == 'Not yet created'
            assert character(4,'The creature')['status'] == 'Alive'
            assert character(8,'Justine Moritz')['status'] == 'Alive'
            assert character(9,'Justine Moritz')['status'] == 'Executed'
            assert character(18,'Victor Frankenstein')['status'] == 'Alive'
            assert character(19,'Victor Frankenstein')['status'] == 'Dead'
            assert character(20,'The creature')['status'] == 'Departed; death unconfirmed'
            assert relationship(10,'Victor Frankenstein','The creature')['kind'] == 'Conditional agreement'
            assert relationship(12,'Victor Frankenstein','The creature')['kind'] == 'Broken agreement'
            assert relationship(14,'Victor Frankenstein','Elizabeth Lavenza')['kind'] == 'Spouses'
            assert relationship(15,'Victor Frankenstein','Elizabeth Lavenza')['kind'] == 'Bereaved marriage'
        else:
            assert len(workspaces) == 19 and len(workspaces[0]['characters']) == 13
            assert character(9,'Lucy Westenra')['species'] == 'Human'
            assert character(10,'Lucy Westenra')['status'] == 'Undead'
            assert character(11,'Lucy Westenra')['status'] == 'At rest; vampirism ended'
            assert character(14,'Mina Harker')['species'] == 'Human'
            assert character(14,'Mina Harker')['status'] == 'Under vampiric influence'
            assert character(18,'Mina Harker')['status'] == 'Freed from vampiric influence'
            assert character(17,'Count Dracula')['status'] == 'Undead'
            assert character(18,'Count Dracula')['status'] == 'Destroyed'
            assert character(18,'Quincey Morris')['status'] == 'Dead'
            assert relationship(7,'Mina Harker','Jonathan Harker')['kind'] == 'Spouses'
        counts = dict(story=path.stem, chapters=len(workspaces[0]['chapters']), events=len(workspaces),
                      characters=len(workspaces[0]['characters']), connections=len(workspaces[-1]['connections']),
                      profile_changes=len(store.rows('SELECT * FROM profile_history')))
    finally:
        store.close()
    # A second connection must reproduce all saved event snapshots exactly.
    reopened = PreviewStore(path)
    try:
        assert [reopened.workspace(e['id']) for e in reopened.events()] == workspaces
    finally:
        reopened.close()
    return dict(**counts, integrity='ok', temporal_checks='passed', close_reopen='passed')


def verify_edgerunners(path):
    with_store = PreviewStore(path)
    try:
        assert with_store.connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not with_store.rows('PRAGMA foreign_key_check')
        snapshots=[with_store.workspace(e['id']) for e in with_store.events()]
        assert len(snapshots)==21
        assert len(snapshots[0]['chapters'])==10 and len(snapshots[0]['characters'])==18
        for w in snapshots:
            assert w['theme']=='cyberpunk' and not w['drafts']
            assert all(c['category'] in ('Personal','Support','Conflict','Other') for c in w['connections'])
            assert all(e['summary'] and e['purpose'] and e['location_id'] for e in w['events'])
            assert all(any(p['event_id']==e['id'] for p in w['participants']) for e in w['events'])
        def person(event,name):
            return next(c for c in snapshots[event-1]['characters'] if c['name']==name)
        for name,before,after in [('Gloria Martinez',1,2),('Maine',11,12),('David Martinez',19,20),('Rebecca',19,20),('Kiwi',18,19)]:
            assert person(before,name)['status']=='Alive'
            assert person(after,name)['status']=='Dead'
        assert person(16,'Lucy (Lucyna Kushinada)')['status']=='Captive'
        assert person(21,'Lucy (Lucyna Kushinada)')['location']=='Moon'
        assert person(21,'Lucy (Lucyna Kushinada)')['status']=='Alive'
    finally:
        with_store.close()
    reopened=PreviewStore(path)
    try:
        assert snapshots==[reopened.workspace(e['id']) for e in reopened.events()]
    finally:
        reopened.close()
    return dict(path=str(path),chapters=10,events=21,characters=18,connections=len(snapshots[-1]['connections']),integrity='ok',close_reopen='passed')

if __name__ == "__main__":
    folder = ROOT / "examples/saved-stories"
    results = [verify_literary(folder / f"{name}.atlas-preview") for name in ("Frankenstein", "Dracula")]
    results.append(verify_edgerunners(folder / "Cyberpunk Edgerunners S1.atlas-preview"))
    print(json.dumps(results, indent=2))
