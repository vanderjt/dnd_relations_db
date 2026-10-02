import {createWorldView} from './world-view.mjs?v=15';
import {graphMarkup,installGraphZoom} from './graph-view.mjs?v=15';
import {createConnectionEditor} from './connection-editor.mjs?v=15';
import {SUGGESTED_FIELDS, uniqueOptions, installSuggestions} from './suggestions.mjs?v=15';
import {FIELDS, resolveField, resolveProfile, changesBetween, commitChanges, validRecords} from './model.mjs?v=15';
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const initials = name => name.split(/\s+/).slice(0,2).map(s=>s[0]).join('');
const STORAGE = 'story-atlas-phase2-greyhaven-v1';
let world, worldDescriptions={}, pageView='characters', graphMode='full', deletedCharacters=[], templateCharacters=[], addedCharacters=[], connections, optionLibrary={}, closeSuggestions=()=>{}, data, records=[], selected, eventIndex=4, saved={}, draft={}, pending=null, toastTimer, storageAvailable=true, storagePending=false;
const event = () => data.events[eventIndex];
const base = () => data.characters.find(c=>c.id===selected);
const changes = () => [...changesBetween(saved,draft),...(connections?.changes()||[])];
function tell(message) { $('#toast').textContent=message; $('#toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),4200); }
function field(key, area=false) {
  const source=resolveField(base(),records,selected,key,eventIndex+1).source;
  const badge=source ? (source.event===eventIndex+1 ? (source.persist?'Carries forward':'This event only') : `From event ${source.event}`) : '';
  const suggested=SUGGESTED_FIELDS.has(key);
  return `<label class="field"><span class="field-label">${FIELDS[key]} <span class="field-state" id="state-${key}"></span></span>${area?`<textarea rows="2" aria-describedby="state-${key} source-${key}" data-field="${key}" aria-label="${FIELDS[key]}" placeholder="${key==='summary'?esc(`Write a sentence describing who ${draft.name} is and what they want`):`Add ${FIELDS[key].toLowerCase()}…`}">${esc(draft[key])}</textarea>`:`<span class="field-control"><input ${suggested?'role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="field-options" autocomplete="off"':''} aria-describedby="state-${key} source-${key}" data-field="${key}" aria-label="${FIELDS[key]}" value="${esc(draft[key])}" placeholder="${suggested?'Choose or type…':'Not set'}">${suggested?`<button type="button" class="options-toggle" data-options-for="${key}" aria-label="Show ${FIELDS[key].toLowerCase()} options" tabindex="-1">⌄</button>`:''}</span>`}<span class="field-source" id="source-${key}">${badge}</span></label>`;
}
function renderCast() {
  const query=$('#cast-search').value.toLowerCase();
  const cast=data.characters.map(c=>({...resolveProfile(c,records,eventIndex+1),id:c.id})).filter(c=>[c.name,c.role,c.faction].join(' ').toLowerCase().includes(query));
  $('#cast-count').textContent=cast.length;
  $('#cast-total').textContent=`${data.characters.length} CHARACTERS`;
  $('#cast-list').innerHTML=cast.map(c=>`<div class="cast-entry"><button class="cast-row" data-character="${c.id}" aria-current="${c.id===selected}"><span class="avatar">${esc(initials(c.name))}</span><span class="cast-details"><strong class=cast-name>${esc(c.name)}</strong><small class=cast-role>${esc(c.role)}</small></span><span class="cast-arrow">↗</span></button><button class="cast-menu-button" data-cast-menu="${c.id}" aria-label="Options for ${esc(c.name)}" title="Character options">⋯</button></div>`).join('') || '<p class="empty-cast">No characters match your search.</p>';
}
function relationshipTone(kind) {
  const label=kind.trim().toLowerCase();
  if(['ally','political ally','friend','friendly'].includes(label))return 'friendly';
  if(['distrust','distrusts','distrusted by','rival'].includes(label))return 'wary';
  if(['enemy','hostile toward','target of hostility','blackmailer','captor'].includes(label))return 'hostile';
  return 'neutral';
}
function renderGraphView(){
  if(pageView!=='relationships'||!data.characters.length)return;
  $('#sheet').innerHTML=graphMarkup({characters:data.characters,connections:connections.state(),removed:connections.removed(),selected,mode:graphMode,eventTitle:event().title,profile:resolveProfile(base(),records,eventIndex+1),name:id=>resolveProfile(data.characters.find(c=>c.id===id),records,eventIndex+1).name,esc,tone:relationshipTone})+'<div class="sheet-actions"><span id="bottom-save-state" class="muted"></span><button id="bottom-review-button" class="primary" disabled>Review changes ↗</button></div>';
  installGraphZoom($('#sheet'));$('#graph-scope-toggle').onclick=()=>{graphMode=graphMode==='full'?'direct':'full';renderGraphView();};$('#graph-character').onchange=e=>chooseCharacter(Number(e.target.value));updateDirty();
}
function switchPage(view, mode='full', character=selected){navigate(()=>{pageView=view;graphMode=mode;selected=character;render();$('#sheet-scroll').scrollTo({top:0,behavior:'instant'});});}
function renderSheet() {
  $('#sheet').innerHTML=`<div class="sheet-eyebrow"><span>THE CAST / ${esc(draft.name)}</span><span>Click a field to edit</span></div><section class="hero"><div class="portrait" aria-label="Portrait placeholder"><span class="portrait-initials">${esc(initials(draft.name))}</span><small class=portrait-caption>PORTRAIT TO COME</small></div><div class="identity"><div class="identity-top"><span class="eyebrow">A PERSON IN YOUR STORY</span><span class="tag">${esc(base().character_type || 'Character')}</span></div><div class="name-field"><input class="name-input" data-field="name" aria-label="Name" aria-describedby="state-name" value="${esc(draft.name)}"><span class="field-state" id="state-name"></span></div><div class="identity-grid">${['species','role','age'].map(k=>field(k)).join('')}</div><div class="identity-grid secondary-info">${['status','location','faction'].map(k=>field(k)).join('')}</div></div></section><div class="summary-field">${field('summary',true)}</div><div class="panels"><section class="card"><div class="card-heading"><h2>At this moment</h2><span>STATISTICS</span></div><div class="stat-grid">${['health','armor','mana'].map(k=>field(k)).join('')}</div></section><section class="card"><div class="card-heading"><h2>What they carry</h2><span>EQUIPMENT & KEEPSAKES</span></div>${field('inventory',true)}</section></div><section class="section-block"><div class="section-top"><span class="section-number">01</span><h2>Skills & abilities</h2></div>${field('skills',true)}</section><section class="section-block"><div class="section-top"><span class="section-number">02</span><h2>Character details</h2><span>BACKGROUND & PERSONALITY</span></div><div class="story-grid"><div class="detail-card">${field('goals',true)}</div><div class="detail-card">${field('traits',true)}</div><div class="detail-card">${field('backstory',true)}</div><div class="detail-card">${field('notes',true)}</div></div></section><section class="section-block"><div class="section-top"><span class="section-number">03</span><h2>Connections at this event</h2><span>RECORDED RELATIONSHIPS</span></div><div class="connections">${connections.markup()}</div></section><div class="sheet-actions"><button type="button" class="secondary discard-button delete-character" data-delete-character>Delete character</button><span id="bottom-save-state" class="muted"></span><button id="bottom-review-button" class="primary" disabled>Review changes <span aria-hidden="true">↗</span></button></div><p class="provenance">Profiles begin with the Greyhaven template. Character and connection edits stay in this browser.</p>`;
}
function renderTimeline() {
  const chapter=data.chapters.find(c=>c.id===event().chapter_id);
  $('#event-context').textContent=`${chapter?.title || 'Greyhaven'} · ${event().title}`;
  $('#event-position').textContent=`${eventIndex+1} / ${data.events.length}`;
  $('#previous-event').disabled=eventIndex===0; $('#next-event').disabled=eventIndex===data.events.length-1;
  $('#chapter-labels').innerHTML=data.chapters.map((c,i)=>`<span style="grid-column:span ${data.events.filter(e=>e.chapter_id===c.id).length}">${['I','II','III'][i]} · ${esc(c.title)}</span>`).join('');
  $('#timeline-events').innerHTML=data.events.map((e,i)=>`<button data-event="${i}" class="event-step ${(records.some(r=>r.character===selected&&r.event===i+1)||connections.hasRecord(selected,i+1))?'has-record':''}" aria-current="${i===eventIndex?'step':'false'}" aria-label="Event ${i+1}: ${esc(e.title)}" title="${esc(e.title)}"><span class="event-dot">${i+1}</span><span class="event-name">${esc(e.title)}</span></button>`).join('');
}
function fitTextArea(el) {
  if(el.tagName!=='TEXTAREA') return;
  // Measure natural content height, retaining a bounded editor for long passages.
  const scroll=$('#sheet-scroll'), top=scroll.scrollTop, pageTop=window.scrollY;
  el.style.height='0px';
  const border=el.offsetHeight-el.clientHeight;
  el.style.height=`${Math.min(240,el.scrollHeight+border)}px`;
  scroll.scrollTop=top;
  if(window.scrollY!==pageTop) window.scrollTo(0,pageTop);
}
function fitTextAreas() { document.querySelectorAll('#sheet textarea').forEach(fitTextArea); }
function updateDirty() {
  const count=changes().length;
  $('#save-state').textContent=count?`${count} unsaved ${count===1?'change':'changes'}`:(storagePending?'Session only — browser storage unavailable':'All changes saved');
  $('#review-button').disabled=!count;
  $('#bottom-review-button').disabled=!count;
  $('#bottom-save-state').textContent=$('#save-state').textContent;
  document.querySelectorAll('[data-field]').forEach(el=>{
    const dirty=draft[el.dataset.field]!==saved[el.dataset.field];
    el.classList.toggle('dirty',dirty);
    const state=$('#state-'+el.dataset.field);
    if(state) {state.textContent=dirty?'Unsaved':'';state.classList.toggle('is-dirty',dirty);}
  });
}
function render() { closeSuggestions(); connections.reset();
  document.querySelectorAll('[data-page]').forEach(el=>el.setAttribute('aria-current',el.dataset.page===pageView?'page':'false'));
  document.querySelector('.workspace-toolbar').hidden=pageView==='world';
  document.querySelector('.timeline').hidden=pageView==='world';
  $('#app').classList.toggle('world-view',pageView==='world');
  $('#sheet').classList.toggle('world-sheet',pageView==='world');
  document.querySelector('.workspace-toolbar .eyebrow').textContent=pageView==='relationships'?'RELATIONSHIP WORKSPACE':'CHARACTER WORKSPACE';
  document.querySelector('.workspace-toolbar [data-delete-character]').hidden=pageView==='relationships';
  $('#sheet').classList.toggle('graph-sheet',pageView==='relationships');$('#app').classList.toggle('relationships-view',pageView==='relationships');
  document.querySelectorAll('.workspace-toolbar [data-delete-character]').forEach(el=>el.disabled=!data.characters.length);
  if(pageView==='world'){saved={};draft={};world.render();return;}
  if(!data.characters.length){selected=null;saved={};draft={};renderCast();renderTimeline();
    $('#sheet').innerHTML='<section class="card empty-profile"><h2>No characters yet</h2><p>Create a character using New character below the cast search.</p></section>';
    $('#review-button').disabled=true;$('#save-state').textContent=storagePending?'Session only — browser storage unavailable':'All changes saved';return;}
  saved=resolveProfile(base(),records,eventIndex+1); draft={...saved}; renderCast(); if(pageView==='relationships')renderGraphView();else renderSheet(); renderTimeline(); updateDirty(); fitTextAreas(); }
function navigate(action) { if(changes().length) {pending=action; $('#leave-dialog').showModal();} else action(); }
function chooseCharacter(id) { if(id!==selected) navigate(()=>{selected=id;render();$('#sheet-scroll').scrollTop=0;}); }
function chooseEvent(index) { if(index>=0&&index<data.events.length&&index!==eventIndex) navigate(()=>{eventIndex=index;render();}); }
function openReview() {
  closeSuggestions();
  if(!changes().length) return;
  if(!draft.name.trim()) {tell('Give this character a name before saving.');pending=null;$('[data-field="name"]').focus();return;}
  $('#review-context').textContent=`${draft.name} · Event ${eventIndex+1}: ${event().title}`;
  $('#review-count').textContent=`${changes().length} changes to review`;
  $('#change-list').innerHTML=changes().map(c=>`<div class="change-row"><div class="change-heading"><strong class=cast-name>${esc(c.label||FIELDS[c.field])}</strong><label class="carry-toggle"><input type="checkbox" name="carry" value="${c.field}" checked> Carry forward</label></div><div class="change-values"><div><span>BEFORE</span><p>${esc(c.before)||'Not set'}</p></div><div><span>AFTER</span><p>${esc(c.after)||'Not set'}</p></div></div></div>`).join('');
  $('#review-dialog').showModal();
}
function saveRecords(next) { records=next; for(const key of SUGGESTED_FIELDS) optionLibrary[key]=uniqueOptions([...(optionLibrary[key]||[]),...records.filter(r=>r.field===key).map(r=>r.value)]);try{localStorage.setItem(STORAGE,JSON.stringify({version:1,records,options:optionLibrary,connections:connections.records(),characters:addedCharacters,deletedCharacters,worldDescriptions}));storageAvailable=true;storagePending=false;}catch{storageAvailable=false;storagePending=true;} }
async function boot() {
  const response=await fetch('./greyhaven.json');if(!response.ok)throw new Error('Template unavailable');data=await response.json();data.events.sort((a,b)=>a.sequence-b.sequence);selected=data.characters.find(c=>c.name==='Mira Vale')?.id || data.characters[0].id;
  templateCharacters=[...data.characters];
  connections=createConnectionEditor({data,context:()=>({character:selected,event:eventIndex+1}),name:id=>id===selected?draft.name||base().name:resolveProfile(data.characters.find(c=>c.id===id),records,eventIndex+1).name,esc,tone:relationshipTone,changed:()=>{if(pageView==='relationships')renderGraphView();else updateDirty();}});
  try{const stored=JSON.parse(localStorage.getItem(STORAGE)||'null');if(stored?.version===1){
    const ids=new Set(templateCharacters.map(c=>c.id));
    if(Array.isArray(stored.characters))for(const c of stored.characters){
      if(!c||!Number.isSafeInteger(c.id)||c.id<1||ids.has(c.id)||typeof c.name!=='string'||!c.name.trim())continue;
      const character={...Object.fromEntries(Object.keys(FIELDS).map(k=>[k,typeof c[k]==='string'?c[k]:''])),id:c.id,character_type:'Character'};
      addedCharacters.push(character);data.characters.push(character);ids.add(character.id);
    }
    deletedCharacters=Array.isArray(stored.deletedCharacters)?[...new Set(stored.deletedCharacters.filter(id=>Number.isSafeInteger(id)&&id>0))]:[];
    data.characters=data.characters.filter(c=>!deletedCharacters.includes(c.id));
    addedCharacters=addedCharacters.filter(c=>!deletedCharacters.includes(c.id));
    selected=data.characters.find(c=>c.name==='Mira Vale')?.id||data.characters[0]?.id||null;
    if(stored.worldDescriptions&&typeof stored.worldDescriptions==='object'&&!Array.isArray(stored.worldDescriptions))worldDescriptions=stored.worldDescriptions;
    for(const key of ['language','belief','title'])optionLibrary[key]=uniqueOptions(Array.isArray(stored.options?.[key])?stored.options[key]:[]);
    records=validRecords(stored.records,data.characters,data.events.length);connections.load(stored.connections);for(const key of SUGGESTED_FIELDS)optionLibrary[key]=uniqueOptions(Array.isArray(stored.options?.[key])?stored.options[key]:[]);}}catch{storageAvailable=false;}
  closeSuggestions=installSuggestions($('#sheet'),key=>[...data.characters.map(c=>c[key]),...records.filter(r=>r.field===key).map(r=>r.value),...(optionLibrary[key]||[])]);
  world=createWorldView({root:$('#sheet'),esc,options:key=>uniqueOptions([...data.characters.map(c=>c[key]),...records.filter(r=>r.field===key).map(r=>r.value),...(optionLibrary[key]||[])]),description:(key,name)=>typeof worldDescriptions[key]?.[name]==='string'?worldDescriptions[key][name]:'',save:(key,name,description)=>{optionLibrary[key]=uniqueOptions([...(optionLibrary[key]||[]),name]);worldDescriptions[key]={...(worldDescriptions[key]||{}),[name]:description};saveRecords(records);tell(storageAvailable?'World entry saved.':'Saved for this session only: browser storage is unavailable.');}});
  render();
  let sheetWidth=0;
  new ResizeObserver(([entry])=>{if(entry.contentRect.width!==sheetWidth){sheetWidth=entry.contentRect.width;fitTextAreas();}}).observe($('#sheet'));
  $('#theme-stylesheet').addEventListener('load',fitTextAreas);
  $('#cast-search').addEventListener('input',renderCast);
  let menuCharacter=null;
  const openCastMenu=id=>{menuCharacter=id;$('#cast-menu-title').textContent=resolveProfile(data.characters.find(c=>c.id===id),records,eventIndex+1).name;const anchor=document.querySelector(`[data-cast-menu="${id}"]`).getBoundingClientRect();const menu=$('#cast-context-menu');menu.style.left=Math.max(8,Math.min(anchor.right+8,innerWidth-288))+'px';menu.style.top=Math.max(8,Math.min(anchor.top,innerHeight-250))+'px';menu.showModal();};
  $('#cast-list').addEventListener('contextmenu',e=>{const row=e.target.closest('[data-character]');if(row){e.preventDefault();openCastMenu(Number(row.dataset.character));}});
  $('#cast-list').addEventListener('click',e=>{const button=e.target.closest('[data-cast-menu]');if(button)openCastMenu(Number(button.dataset.castMenu));});
  $('#cast-list').addEventListener('keydown',e=>{const row=e.target.closest('[data-character]');if(row&&(e.key==='ContextMenu'||e.shiftKey&&e.key==='F10')){e.preventDefault();openCastMenu(Number(row.dataset.character));}});
  $('#cast-direct').onclick=()=>{$('#cast-context-menu').close();switchPage('relationships','direct',menuCharacter);};
  $('#cast-open-profile').onclick=()=>{$('#cast-context-menu').close();switchPage('characters','full',menuCharacter);};
  $('#cast-menu-close').onclick=()=>$('#cast-context-menu').close();
  $('#cast-context-menu').addEventListener('click',e=>{if(e.target===$('#cast-context-menu')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  $('#new-character-button').onclick=()=>navigate(()=>{
    render();closeSuggestions();$('#new-character-form').reset();$('#new-character-name').setCustomValidity('');
    $('#new-character-dialog').showModal();$('#new-character-name').focus();
  });
  $('#cancel-delete-character').onclick=()=>$('#delete-character-dialog').close();
  $('#confirm-delete-character').onclick=()=>{
    const id=selected,name=draft.name||base().name;
    connections.removeCharacter(id);deletedCharacters.push(id);
    data.characters=data.characters.filter(c=>c.id!==id);addedCharacters=addedCharacters.filter(c=>c.id!==id);
    saveRecords(records.filter(r=>r.character!==id));selected=data.characters[0]?.id||null;pending=null;
    $('#delete-character-dialog').close();$('#cast-search').value='';render();$('#sheet-scroll').scrollTo({top:0,behavior:'instant'});
    tell(storageAvailable?`${name} deleted throughout the story.`:'Deleted for this session only: browser storage is unavailable.');
  };
  $('#cancel-new-character').onclick=()=>$('#new-character-dialog').close();
  $('#new-character-name').oninput=()=>$('#new-character-name').setCustomValidity('');
  $('#new-character-form').onsubmit=e=>{
    e.preventDefault();const name=$('#new-character-name').value.trim();
    if(!name){$('#new-character-name').setCustomValidity('Enter a character name.');$('#new-character-name').reportValidity();return;}
    const character={...Object.fromEntries(Object.keys(FIELDS).map(k=>[k,''])),id:Math.max(0,...templateCharacters.map(c=>c.id),...data.characters.map(c=>c.id),...deletedCharacters)+1,name,summary:$('#new-character-summary').value.trim(),character_type:'Character'};
    addedCharacters.push(character);data.characters.push(character);selected=character.id;pageView='characters';
    saveRecords(records);$('#new-character-dialog').close();$('#cast-search').value='';render();
    $('#sheet-scroll').scrollTo({top:0,behavior:'instant'});window.scrollTo({top:0,behavior:'instant'});
    $('[data-field=name]').focus({preventScroll:true});
    document.querySelector('.cast-row[aria-current=true]')?.scrollIntoView({block:'nearest'});
    tell(storageAvailable?`${name} created. Fill out their profile.`:'Character created for this session only: browser storage is unavailable.');
  };
  document.addEventListener('click',e=>{
    const page=e.target.closest('[data-page]'),mode=e.target.closest('[data-graph-mode]'),node=e.target.closest('[data-graph-node]'),edge=e.target.closest('[data-graph-edge]');
    if(page)switchPage(page.dataset.page);
    if(mode){graphMode=mode.dataset.graphMode;renderGraphView();}
    if(node)chooseCharacter(Number(node.dataset.graphNode));
    if(e.target.closest('[data-open-profile]'))switchPage('characters');
    if(edge){const id=Number(edge.dataset.source),key=edge.dataset.graphEdge;if(id===selected)connections.open(key);else navigate(()=>{selected=id;render();connections.open(key);});}
if(e.target.closest('[data-delete-character]')&&base()){closeSuggestions();$('#delete-character-description').textContent=`Delete ${draft.name||base().name} from this story?`;$('#delete-character-dialog').showModal();$('#cancel-delete-character').focus();}if(e.target.closest('#bottom-review-button')){pending=null;openReview();}const c=e.target.closest('[data-character]'),t=e.target.closest('[data-event]'),close=e.target.closest('[data-close]');if(c)chooseCharacter(Number(c.dataset.character));if(t)chooseEvent(Number(t.dataset.event));if(close)$('#'+close.dataset.close).close();});
  $('#sheet').addEventListener('input',e=>{if(e.target.dataset.field){draft[e.target.dataset.field]=e.target.value;if(e.target.dataset.field==='name')$('[data-field=summary]').placeholder=`Write a sentence describing who ${draft.name} is and what they want`;updateDirty();fitTextArea(e.target);}});
  $('#review-button').onclick=()=>{pending=null;openReview();};
  $('#cancel-review').onclick=()=>{$('#review-dialog').close();pending=null;};$('#review-dialog').oncancel=()=>{pending=null;};
  for(const [id,value] of [['select-all',true],['deselect-all',false]])$('#'+id).onclick=()=>document.querySelectorAll('[name="carry"]').forEach(c=>c.checked=value);
  $('#review-form').onsubmit=e=>{e.preventDefault();const list=changes(),carry=new Set([...document.querySelectorAll('[name="carry"]:checked')].map(c=>c.value));connections.commit(carry);saveRecords(commitChanges(records,selected,eventIndex+1,list.filter(c=>!c.key),carry));$('#review-dialog').close();const next=pending;pending=null;render();if(next)next();tell(storageAvailable?`${list.length} changes saved · ${carry.size} carry forward`:'Saved for this session only: browser storage is unavailable.');};
  $('#stay').onclick=()=>{pending=null;$('#leave-dialog').close();};$('#leave-dialog').oncancel=()=>{pending=null;};
  $('#discard').onclick=()=>{$('#leave-dialog').close();const next=pending;pending=null;if(next)next();};
  $('#leave-review').onclick=()=>{$('#leave-dialog').close();openReview();};
  $('#previous-event').onclick=()=>chooseEvent(eventIndex-1);$('#next-event').onclick=()=>chooseEvent(eventIndex+1);
  $('#context-button').onclick=()=>{$('#context-chapter').textContent=data.chapters.find(c=>c.id===event().chapter_id)?.title || 'Greyhaven';$('#context-title').textContent=event().title;$('#context-description').textContent=event().summary || event().description || '';$('#context-dialog').showModal();};
  for(const id of ['about-button','about-brand'])$('#'+id).onclick=e=>{e.preventDefault();$('#about-dialog').showModal();};
  $('#reset-button').onclick=()=>{$('#about-dialog').close();$('#reset-dialog').showModal();};
  $('#confirm-reset').onclick=()=>{optionLibrary={};worldDescriptions={};connections.clear();deletedCharacters=[];addedCharacters=[];data.characters=[...templateCharacters];selected=data.characters.find(c=>c.name==='Mira Vale')?.id||data.characters[0].id;saveRecords([]);pending=null;$('#reset-dialog').close();render();tell(storagePending?'Reset for this session only. Browser storage could not be cleared.':'Original Greyhaven template restored.');};
  document.addEventListener('keydown',e=>{if(document.querySelector('dialog[open]'))return;if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();pending=null;openReview();}if(pageView==='characters'&&e.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('#cast-search').focus();}});
  window.addEventListener('beforeunload',e=>{if(changes().length||storagePending){e.preventDefault();e.returnValue='';}});
}
boot().catch(error=>{$('#sheet').textContent='Greyhaven could not open. Start the local prototype server, then reload this page.';console.error(error);});
