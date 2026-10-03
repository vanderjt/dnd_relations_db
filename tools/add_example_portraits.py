"""Embed sourced character portraits, preserving existing portraits and story content.

Run --prepare to download and build review sheets, then --apply after visual review.
The manifest records attribution. Source images retain their original rights.
"""
import argparse
import base64
from datetime import datetime
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import urllib.request
import uuid
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from story_atlas.preview_store import PreviewStore

CACHE = ROOT/'build/portrait-downloads'
MANIFEST = ROOT/'examples/saved-stories/portrait-sources.json'

def prepare():
    CACHE.mkdir(parents=True,exist_ok=True)
    rows = json.loads(MANIFEST.read_text(encoding='utf-8'))['portraits']
    for r in rows:
        filename=hashlib.sha256(r['url'].encode()).hexdigest()[:16]+'.jpg'
        output=CACHE/filename
        if not output.exists():
            raw=urllib.request.urlopen(r['url'],timeout=30).read()
            with Image.open(BytesIO(raw)) as original:
                im=ImageOps.exif_transpose(original).convert('RGB')
                im.thumbnail((768,768))
                im.save(output,'JPEG',quality=90)
        r['cache']=str(output.relative_to(ROOT))
        r['sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
        print('Prepared',r['name'],flush=True)
    MANIFEST.write_text(json.dumps({'note':'Web-sourced reference portraits. Not a grant of redistribution rights. Frankenstein images are AI interpretations, not canonical likenesses. Safie’s father has no matching portrait in the chosen set and retains his existing placeholder.','portraits':rows},indent=2,ensure_ascii=False),encoding='utf-8')
    for story in ['Frankenstein','Cyberpunk Edgerunners S1']:
        selected=[r for r in rows if r['story']==story]
        sheet=Image.new('RGB',(1000,((len(selected)+4)//5)*240),'#20212a')
        draw=ImageDraw.Draw(sheet)
        for i,r in enumerate(selected):
            im=Image.open(ROOT/r['cache']);im.thumbnail((184,202))
            x=(i%5)*200;y=(i//5)*240
            sheet.paste(im,(x+(200-im.width)//2,y))
            draw.text((x+5,y+207),r['name'][:26],fill='white')
        sheet.save(CACHE/(story+'-review.jpg'))

def apply():
    rows=json.loads(MANIFEST.read_text(encoding='utf-8'))['portraits']
    default=Path(os.environ['LOCALAPPDATA'])/'StoryAtlasPreview/stories'
    for story in ['Frankenstein','Cyberpunk Edgerunners S1']:
        for folder in [default, ROOT/'examples/saved-stories']:
            path=folder/(story+'.atlas-preview')
            store=PreviewStore(path)
            try:
                before=[store.workspace(e['id']) for e in store.events()]
                backupdir=folder/'backups' if folder==default else ROOT/'build/portrait-backups'
                backupdir.mkdir(parents=True,exist_ok=True)
                backup=backupdir/(story+'-before-portraits-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.atlas-preview')
                store.backup(backup)
                cast={c['name']:c for c in before[0]['characters']}
                added=[]
                for r in rows:
                    if r['story']!=story:continue
                    c=cast[r['name']]
                    if c.get('portrait'):continue
                    raw=(ROOT/r['cache']).read_bytes()
                    assert hashlib.sha256(raw).hexdigest()==r['sha256']
                    store.write('save_portrait',dict(character_id=c['id'],image='data:image/jpeg;base64,'+base64.b64encode(raw).decode()),store.revision(),uuid.uuid4().hex)
                    # Attribution travels inside the story, separate from authored profile notes.
                    with store.connection:
                        store.connection.execute('INSERT INTO preferences VALUES(?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload',
                            (f"portrait-source:{c['id']}",json.dumps({k:r[k] for k in ('source','url','style','sha256')})))
                    added.append(r['name'])
                after=[store.workspace(e['id']) for e in store.events()]
                def narrative(w):
                    return {key:([{k:v for k,v in c.items() if k!='portrait'} for c in w[key]] if key=='characters' else w[key]) for key in ['chapters','events','participants','characters','connections','world','drafts','context']}
                assert [narrative(w) for w in before]==[narrative(w) for w in after]
                assert store.connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert not store.rows('PRAGMA foreign_key_check')
            finally:store.close()
            reopened=PreviewStore(path)
            try:
                assert [reopened.workspace(e['id']) for e in reopened.events()]==after
                for c in after[0]['characters']:
                    if c.get('portrait'):
                        Image.open(BytesIO(base64.b64decode(c['portrait'].split(',')[1]))).verify()
                print(json.dumps(dict(path=str(path),added=len(added),portraits=sum(bool(c.get('portrait')) for c in after[0]['characters']),missing=[c['name'] for c in after[0]['characters'] if not c.get('portrait')],backup=str(backup),reopen='passed',narrative='unchanged')),flush=True)
            finally:reopened.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--apply',action='store_true');args=p.parse_args()
    if args.prepare:prepare()
    if args.apply:apply()
