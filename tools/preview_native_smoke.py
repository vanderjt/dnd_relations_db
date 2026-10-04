"""Real WebView2 UI/bridge smoke. Each stage runs in a fresh native process.

Use only a disposable --home. No mock bridge, browser storage, or production UI
test hooks. Test code enters through DOM events and pywebview's evaluate_js API.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preview_main import PreviewBridge
from story_atlas.preview_worker import PreviewWorker
import webview

parser = argparse.ArgumentParser()
parser.add_argument('--home', type=Path, required=True)
parser.add_argument('--stage', choices=['create', 'reopen', 'sample', 'layout', 'story-scroll', 'failure', 'crash', 'recover-crash', 'x-close', 'x-reopen', 'x-save', 'x-saved-reopen', 'x-clean'], required=True)
parser.add_argument('--width', type=int)
parser.add_argument('--height', type=int)
args = parser.parse_args()
worker = PreviewWorker(args.home, ROOT / 'story_atlas/resources/greyhaven.json')
bridge = PreviewBridge(worker)
window = webview.create_window('Story Atlas Preview — native smoke', str(ROOT / 'preview/dist/index.html'),
                              js_api=bridge, width=args.width or (900 if args.stage == 'layout' else 1280),
                              height=args.height or (600 if args.stage == 'layout' else 800), min_size=(760, 560), text_select=True)
bridge._window = window
window.events.closing += bridge._on_closing
finished = threading.Event()
result = {}

COMMON = r'''
const wait = async(test, description) => {for(let i=0;i<240;i++){if(test())return;await new Promise(r=>setTimeout(r,50));}throw Error('Timeout: '+description+' | '+document.body.innerText.slice(-1200));};
const ready=()=>!document.querySelector('.app-lock')?.disabled;
const assert=(value,message)=>{if(!value)throw Error(message);};
const buttons=()=>[...(document.querySelector('dialog[open]:last-of-type')||document).querySelectorAll('button')].filter(x=>x.getClientRects().length&&!x.disabled);
const button=(name)=>name==='+ Add event'?buttons().filter(x=>x.textContent.trim()===name).at(-1):buttons().find(x=>x.textContent.trim()===name);
const click=async(name)=>{await wait(()=>ready()&&button(name),'button '+name);button(name).click();await new Promise(r=>setTimeout(r,120));await wait(ready,'idle '+name);};
const input=(name,value)=>{const el=document.querySelector(`[aria-label="${name}"]`)||document.querySelector(`[name="${name}"]`);assert(el,'missing '+name);const setter=Object.getOwnPropertyDescriptor(el.tagName==='SELECT'?HTMLSelectElement.prototype:el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set;setter.call(el,value);el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}));};
const value=(name)=>document.querySelector(`[aria-label="${name}"]`)?.value;
const dialog=()=>document.querySelector('dialog[open]');
await wait(()=>window.previewReady&&ready(),'native bootstrap');
await new Promise(r=>setTimeout(r,300));
await wait(ready,'bootstrap settled');
'''

CREATE = r'''
input('title','Native acceptance story');
document.querySelector('.welcome form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
await wait(()=>document.querySelector('.story-detail')&&ready(),'new story');
input('Purpose','Introduce the witness');
await click('Save event');
await click('+ Chapter');input('Chapter title','Second chapter');await click('Save chapter');
await click('+ Add event');input('Event title','Arrival');
let select=document.querySelector('[aria-label="Chapter"]');select.value=select.options[1].value;select.dispatchEvent(new Event('change',{bubbles:true}));
await click('Save event');
await click('World');await click('Locations0');await click('+ Add entry');input('Entry name','Harbor');input('Description','A place to arrive');await click('Save world');
await click('Characters');await click('+ New character');input('Name','Native Mira');input('Short summary','The witness');await click('Save character');
input('Age','22');input('Location','@world:1');await click('Review changes');
const row=[...document.querySelectorAll('.change-row')].find(x=>x.querySelector('strong')?.textContent==='Age');row.querySelector('input').click();
await click('Save changes');assert(value('Age')==='22','saved age');assert(value('Location')==='@world:1','saved event-only location');
await click('Story');await click('+ Add event');input('Event title','Aftermath');await click('Save event');
await click('Characters');assert(value('Age')==='22','carry-forward age');assert(value('Location')==='','event-only must resume');
await click('Story');input('Find participants','Native Mira');await click('+ Native Mira');input('Author’s notes','Event notes');await click('Save event');
await click('Native Mira');await wait(()=>value('Age')==='22','participant profile');assert(button('← Back to event'),'return origin');await click('← Back to event');
assert(value('Author’s notes')==='Event notes','return retained event');
document.querySelector('.file-menu').open=true;await click('Back up story');
await click('Characters');
await click('+ New character');input('Name','Native Bryn');await click('Save character');
await click('Add connection');input('Connection type','Mentor');input('Connection notes','Continuing trust');document.querySelector('dialog[open] input[type=checkbox]').click();await click('Review connection');await click('Save changes');
await click('Relationships');assert(document.querySelectorAll('.graph-node').length===2,'graph cast');assert(document.querySelectorAll('[data-edge]').length===1,'graph connection');
document.querySelector('[role=switch]').click();await wait(()=>document.querySelector('[role=switch]').getAttribute('aria-checked')==='true','direct mode');
await click('Story');await click('+ Add event');input('Event title','Temporary rift');await click('Save event');
await click('Relationships');await click('Mentor ⌄');input('Connection type','Enemy');await click('Review connection');await click('Save changes');
let current=(await window.pywebview.api.command('workspace',{})).data;assert(current.connections[0].kind==='Enemy','connection override at event');
await click('Story');await click('+ Add event');input('Event title','Reunion');await click('Save event');
await click('Relationships');current=(await window.pywebview.api.command('workspace',{})).data;assert(current.connections[0].kind==='Mentor','continuing connection resumes');
await click('World');await click('Locations1');await click('HarborA place to arrive↗');input('Entry name','Old Harbor');await click('Save world');
document.querySelector('.file-menu').open=true;await click('Back up story');
await click('Characters');input('Goals','Recover this draft after closing');
await wait(()=>document.body.innerText.includes('Draft kept on disk'),'durable draft');
const w=await window.pywebview.api.command('workspace',{});assert(w.ok,'workspace read');
assert(w.data.chapters.length===2&&w.data.events.length===5,'complete outline');
assert(w.data.participants.length===1,'participant persisted');
window.dispatchEvent(new Event('preview-close'));await wait(()=>dialog()?.textContent.includes('Keep these changes?'),'close prompt');
return {passed:true,path:w.data.path,checks:['native new story','chapter/event creation','character creation','review both scopes','provenance returned','participant navigation','World identity and rename','directed connection','event-only connection resumes','graph direct/full navigation','backup','pending-close prompt']};
'''

REOPEN = r'''
await wait(()=>value('Goals')==='Recover this draft after closing'&&ready(),'recovered native draft');
const persisted=await window.pywebview.api.command('workspace',{});assert(persisted.data.characters.find(c=>c.name==='Native Mira').age==='22','committed carry-forward survived restart');
assert(value('Location')==='','event-only still resumed');
await click('Review changes');await click('Save changes');
const w=await window.pywebview.api.command('workspace',{});
assert(w.data.drafts.length===0,'own draft cleared');
assert(w.data.chapters.length===2&&w.data.events.length===5,'outline survived restart');
assert(w.data.participants.length===1,'participants survived restart');assert(w.data.connections[0].kind==='Mentor','connection survived restart');assert(w.data.world[0].name==='Old Harbor','World survived restart');
const requests=performance.getEntriesByType('resource').map(x=>x.name);
assert(requests.every(x=>new URL(x).hostname==='127.0.0.1'),'runtime loaded only local assets');
return {passed:true,path:w.data.path,checks:['native restart','draft recovered and saved','scope persisted','outline and participants persisted','only local runtime resources']};
'''

SAMPLE = r'''
await click('Try Greyhaven sample');await wait(()=>document.querySelector('.story-detail')&&ready(),'sample loaded');
const w=await window.pywebview.api.command('workspace',{});assert(w.data.characters.length===18&&w.data.events.length===10,'sample through bridge');
return {passed:true,path:w.data.path,checks:['native Greyhaven sample through bridge']};
'''

STORY_SCROLL = r'''
if(button('Try Greyhaven sample')) await click('Try Greyhaven sample');
await click('Story');
const main=document.querySelector('.story-main');
const outline=document.querySelector('.story-outline');
assert(main&&outline,'story scroll regions');
const originalHeading=document.querySelector('.story-page-heading h1').textContent;
for(const theme of ['storybook','gothic']){
  input('Theme',theme);await new Promise(r=>setTimeout(r,150));
  document.querySelector('.story-page-heading h1').textContent='Story of '+ 'A long story title '.repeat(12);
  main.scrollTop=0;
  assert(main.scrollHeight>main.clientHeight,'complete form exceeds viewport '+JSON.stringify({height:main.clientHeight,scroll:main.scrollHeight,viewport:innerHeight,detail:document.querySelector('.story-detail').getBoundingClientRect().height,overflow:getComputedStyle(main).overflowY}));
  const headingTop=document.querySelector('.story-page-heading').getBoundingClientRect().top;
  main.scrollTop=main.scrollHeight;
  await new Promise(r=>requestAnimationFrame(r));
  assert(main.scrollTop>0,'main page scrolls');
  assert(document.querySelector('.story-page-heading').getBoundingClientRect().top<headingTop,'heading scrolls with form');
  const save=[...main.querySelectorAll('button')].find(x=>x.textContent.trim()==='Save event');
  const saveRect=save.getBoundingClientRect(), mainRect=main.getBoundingClientRect();
  assert(mainRect.bottom<=innerHeight+1,'editor fits viewport height');
  assert(saveRect.top>=mainRect.top&&saveRect.bottom<=mainRect.bottom+1,'save action reachable '+JSON.stringify({save:saveRect.toJSON(),main:mainRect.toJSON(),scroll:main.scrollTop,height:main.clientHeight,total:main.scrollHeight}));
  assert(main.scrollWidth<=main.clientWidth+1,'editor has no horizontal overflow');
  assert(document.documentElement.scrollWidth<=innerWidth+1,'page fits window width');
  if(innerWidth<=800){
    assert(outline.getBoundingClientRect().bottom<=mainRect.top+1,'outline stacks above editor');
    assert(mainRect.width>innerWidth-30,'narrow editor uses window width');
  }else{
    assert(outline.getBoundingClientRect().right<=mainRect.left+1,'wide layout uses columns');
  }
}
document.querySelector('.story-page-heading h1').textContent=originalHeading;
return {passed:true,viewport:[innerWidth,innerHeight],checks:['whole story page scrolls','long title wraps','save actions reachable','responsive outline','Storybook and Gothic']};
'''

LAYOUT = r'''
const visible=(el)=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0&&r.left>=0&&r.right<=innerWidth+1&&r.top>=0&&r.bottom<=innerHeight+1;};
assert(innerWidth<950&&innerHeight<650,'small native window');
for(const theme of ['storybook','gothic']){
  input('Theme',theme);await new Promise(r=>setTimeout(r,150));
  for(const name of ['Story','Characters','Relationships','World']){
    await click(name);assert(document.documentElement.scrollWidth<=innerWidth+1,'horizontal clipping '+name);
    assert(Math.round(document.querySelector('.masthead').getBoundingClientRect().height)===78,'consistent masthead '+name);
    if(name==='Story'){
      assert(!document.querySelector('.timeline'),'Story uses outline instead of duplicate timeline');
      const outline=document.querySelector('.story-outline').getBoundingClientRect();
      assert(Math.abs(outline.bottom-innerHeight)<3,'full-height outline');
      assert(document.querySelector('.story-page-heading'),'story identity heading');
      assert(!document.querySelector('.participant-options'),'participant search starts compact');
    }
    if(name==='Relationships'){
      assert(document.querySelector('[role=switch]'),'binary graph scope');
      assert(document.querySelectorAll('.inspector-identity dt').length===3,'inspector age race role');
      assert(document.querySelectorAll('.chapter-labels>span').length>0,'chapter timeline groups');
      assert(!document.querySelector('.sidebar'),'no graph cast sidebar');
    }
    assert(visible(document.querySelector('.masthead')),'masthead visible '+name);if(name==='Characters'||name==='Relationships')assert(visible(document.querySelector('.workspace-toolbar')),'toolbar visible '+name);if(name==='Relationships'){assert(visible(document.querySelector('.graph-canvas>svg')),'whole graph fits '+JSON.stringify(document.querySelector('.graph-canvas>svg').getBoundingClientRect())+' viewport '+innerWidth+'x'+innerHeight);assert(visible(button('Add connection')),'graph actions fit');}
  }
}
await click('Characters');input('Age','Small window review');await click('Review changes');
assert(visible(button('Save changes')),'dialog save visible');assert(visible(button('Back to editing')),'dialog cancel visible');
await click('Back to editing');await click('Discard edits');
return {passed:true,checks:['900x600 native layout','Storybook and Gothic','all four pages','review controls accessible']};
'''

FAILURE = r'''
input('Author’s notes','Pending after failed storage');await click('Review changes');await click('Save changes');
await wait(()=>dialog()?.textContent.includes('injected storage failure'),'visible storage error');
const w=(await window.pywebview.api.command('workspace',{})).data;
assert(w.drafts.some(x=>x.payload.includes('Pending after failed storage')),'failed write keeps durable draft');
assert(w.characters.every(x=>x.notes!=='Pending after failed storage'),'committed values unchanged');
assert(dialog().textContent.includes('Pending after failed storage'),'pending review retained');
return {passed:true,checks:['injected native save failure','visible error','old facts and pending draft preserved']};
'''

RETRY_FAILURE = r'''
await click('Save changes');assert(value('Author’s notes')==='Pending after failed storage','retry saved original draft');
const w=(await window.pywebview.api.command('workspace',{})).data;assert(w.drafts.length===0,'successful retry cleared draft');
return {passed:true,checks:['injected native save failure','visible error','facts and draft preserved','successful retry']};
'''

CRASH = r'''
input('Author’s notes','Draft survives forced interruption');await wait(()=>document.body.innerText.includes('Draft kept on disk'),'draft committed before interruption');
const w=(await window.pywebview.api.command('workspace',{})).data;
assert(w.drafts.some(x=>x.payload.includes('Draft survives forced interruption')),'durable pending work');
return {passed:true,checks:['native draft persisted before forced process exit']};
'''

RECOVER_CRASH = r'''
await wait(()=>value('Author’s notes')==='Draft survives forced interruption','recovery after killed host');
await click('Review changes');await click('Save changes');
assert(value('Author’s notes')==='Draft survives forced interruption','recovered draft saved');
return {passed:true,checks:['native restart after forced exit','draft recovered and saved']};
'''

X_CLOSE = r"""
await click('Characters');
input('Author’s notes','Draft kept after native X');
document.querySelector('.sheet-scroll').scrollTop=420;
await wait(()=>document.body.innerText.includes('Draft kept on disk'),'draft ready');
return {passed:true};
"""
X_PROMPT = r"""
await wait(()=>dialog()?.textContent.includes('Keep these changes?'),'native X close prompt');
assert(button('Keep draft & close'),'keep draft action');
await click('Stay');assert(!dialog(),'Stay leaves editor open');
return {passed:true};
"""
X_REOPEN = r"""
await wait(()=>value('Author’s notes')==='Draft kept after native X','draft after X restart');
await wait(()=>document.querySelector('.sheet-scroll').scrollTop>350,'restored scroll');
assert(document.querySelector('.preview-app').dataset.page==='characters','restored page');
return {passed:true,checks:['native X restart','pending text restored','workspace and scroll restored']};
"""


def on_result(value):
    result.update(value if isinstance(value, dict) else {'error': str(value)})
    finished.set()


def smoke():
    try:
        if args.stage == 'failure':
            worker.call('bootstrap')
            worker._pool.submit(lambda: worker._store.connection.execute(
                "CREATE TEMP TRIGGER injected_failure BEFORE INSERT ON activity WHEN NEW.action='save_profile' BEGIN SELECT RAISE(ABORT,'injected storage failure'); END")).result()
        script = COMMON + {'create': CREATE, 'reopen': REOPEN, 'sample': SAMPLE, 'layout': LAYOUT, 'story-scroll': STORY_SCROLL,
                           'failure': FAILURE, 'crash': CRASH, 'recover-crash': RECOVER_CRASH, 'x-close': X_CLOSE, 'x-reopen': X_REOPEN, 'x-save': X_CLOSE.replace('Draft kept after native X','Saved after native X'), 'x-saved-reopen': X_REOPEN.replace('Draft kept after native X','Saved after native X').replace('return {passed:true,checks:', "const saved=(await window.pywebview.api.command('workspace',{})).data;assert(saved.drafts.length===0,'no uncommitted draft after Save and close');assert(saved.characters.some(c=>c.notes==='Saved after native X'),'saved facts survived exit');return {passed:true,checks:").replace('pending text restored','committed text restored'), 'x-clean': "return {passed:true,checks:['clean native X closes without prompt']};"}[args.stage]
        window.evaluate_js('(async()=>{try{' + script + '}catch(e){return {passed:false,error:e.stack};}})()', on_result)
        if not finished.wait(55):
            result.update(passed=False, error='Native smoke timed out')
        if result.get('passed') and args.stage == 'x-save':
            window.destroy()
            finished.clear()
            script = COMMON + "await wait(()=>dialog()?.textContent.includes('Keep these changes?'),'X save prompt');await click('Save');await wait(()=>button('Save changes'),'scope review before exit');return {passed:true,checks:['native X save prompt','scope review before save and close']};"
            window.evaluate_js('(async()=>{try{' + script + '}catch(e){return {passed:false,error:e.stack};}})()', on_result)
            if not finished.wait(20):
                result.update(passed=False, error='Native X save prompt timed out')
        if result.get('passed') and args.stage == 'x-close':
            # destroy() invokes the same native FormClosing route as title-bar X.
            window.destroy()
            finished.clear()
            window.evaluate_js('(async()=>{try{' + COMMON + X_PROMPT + '}catch(e){return {passed:false,error:e.stack};}})()', on_result)
            if not finished.wait(20):
                result.update(passed=False, error='Native X prompt timed out')
            if result.get('passed'):
                window.destroy()
                finished.clear()
                window.evaluate_js('(async()=>{try{' + COMMON + "await wait(()=>dialog()?.textContent.includes('Keep these changes?'),'second X'); return {passed:true,checks:['native FormClosing','Stay cancels close','repeat X prompts again','keep draft and exit']};" + '}catch(e){return {passed:false,error:e.stack};}})()', on_result)
                if not finished.wait(20):
                    result.update(passed=False, error='Second native X timed out')
        if result.get('passed') and args.stage == 'failure':
            worker._pool.submit(lambda: worker._store.connection.execute('DROP TRIGGER injected_failure')).result()
            finished.clear()
            window.evaluate_js('(async()=>{try{' + COMMON + RETRY_FAILURE + '}catch(e){return {passed:false,error:e.stack};}})()', on_result)
            if not finished.wait(25):
                result.update(passed=False, error='Retry timed out')
        if result.get('passed') and args.stage == 'crash':
            print(json.dumps(result), flush=True)
            (args.home / 'crash-result.json').write_text(json.dumps(result), encoding='utf-8')
            os._exit(23)  # Deliberately bypass application/SQLite shutdown.
        if result.get('passed') and args.stage in ('create', 'x-close'):
            window.run_js("[...document.querySelectorAll('dialog[open] button')].find(x=>x.textContent==='Keep draft & close').click()")
        elif result.get('passed') and args.stage == 'x-clean':
            window.destroy()
        elif result.get('passed') and args.stage == 'x-save':
            window.run_js("[...document.querySelectorAll('dialog[open] button')].find(x=>x.textContent==='Save changes').click()")
        else:
            bridge._allow_close = True
            window.destroy()
    except Exception as error:
        result.update(passed=False, error=str(error))
        bridge._allow_close = True
        window.destroy()


try:
    webview.start(smoke, gui='edgechromium')
finally:
    worker.close()
    print(json.dumps(result, indent=2), flush=True)
    args.home.mkdir(parents=True, exist_ok=True)
    (args.home / f'{args.stage}-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
if not result.get('passed'):
    raise SystemExit(1)
