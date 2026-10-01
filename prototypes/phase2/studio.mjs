import {FIELDS, resolveField, resolveProfile, changesBetween, commitChanges, validRecords} from './model.mjs';
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const initials = name => name.split(/\s+/).slice(0,2).map(s=>s[0]).join('');
const STORAGE = 'story-atlas-phase2-greyhaven-v1';
let data, records=[], selected, eventIndex=4, saved={}, draft={}, pending=null, toastTimer, storageAvailable=true, storagePending=false;
const event = () => data.events[eventIndex];
const base = () => data.characters.find(c=>c.id===selected);
const changes = () => changesBetween(saved,draft);
function tell(message) { $('#toast').textContent=message; $('#toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),4200); }
function field(key, area=false) {
  const source=resolveField(base(),records,selected,key,eventIndex+1).source;
  const badge=source ? (source.event===eventIndex+1 ? (source.persist?'Carries forward':'This event only') : `From event ${source.event}`) : '';
  return `<label class="field"><span class="field-label">${FIELDS[key]} ${badge?`<span class="field-source">${badge}</span>`:''}</span>${area?`<textarea rows="3" data-field="${key}" aria-label="${FIELDS[key]}" placeholder="Add ${FIELDS[key].toLowerCase()}…">${esc(draft[key])}</textarea>`:`<input data-field="${key}" aria-label="${FIELDS[key]}" value="${esc(draft[key])}" placeholder="Not set">`}</label>`;
}
function renderCast() {
  const query=$('#cast-search').value.toLowerCase();
  const cast=data.characters.map(c=>({...resolveProfile(c,records,eventIndex+1),id:c.id})).filter(c=>[c.name,c.role,c.faction].join(' ').toLowerCase().includes(query));
  $('#cast-count').textContent=cast.length;
  $('#cast-list').innerHTML=cast.map(c=>`<button class="cast-row" data-character="${c.id}" aria-current="${c.id===selected}"><span class="avatar">${esc(initials(c.name))}</span><span class="cast-details"><strong class=cast-name>${esc(c.name)}</strong><small class=cast-role>${esc(c.role)}</small></span><span class="cast-arrow">↗</span></button>`).join('') || '<p class="empty-cast">No characters match your search.</p>';
}
function relationshipsMarkup() {
  return (data.relationships[String(event().id)]||[]).filter(r=>r.source_id===selected||r.target_id===selected).map(r=>{
    const other=data.characters.find(c=>c.id===(r.source_id===selected?r.target_id:r.source_id));
    if(!other) return '';
    const name=resolveProfile(other,records,eventIndex+1).name;
    const kind=r.source_id===selected || r.semantics==='mutual' ? r.kind : (r.inverse_label || r.kind);
    return `<button class="relationship-card" data-character="${other.id}"><span class="relationship-avatar">${esc(initials(name))}</span><span><strong class=cast-name>${esc(name)}</strong><small class=cast-role>${esc(r.notes || '')}</small></span><span class="relationship-kind">${esc(kind)}</span></button>`;
  }).join('') || '<p class="muted">No recorded connections at this event.</p>';
}
function renderSheet() {
  $('#sheet').innerHTML=`<div class="sheet-eyebrow"><span>THE CAST / ${esc(draft.name)}</span><span>Click a field to shape this character</span></div><section class="hero"><div class="portrait" aria-label="Portrait placeholder"><span class="portrait-initials">${esc(initials(draft.name))}</span><small class=portrait-caption>PORTRAIT TO COME</small></div><div class="identity"><div class="identity-top"><span class="eyebrow">A PERSON IN YOUR STORY</span><span class="tag">${esc(base().character_type || 'Character')}</span></div><input class="name-input" data-field="name" aria-label="Name" value="${esc(draft.name)}"><div class="identity-grid">${['species','role','age'].map(k=>field(k)).join('')}</div><div class="identity-grid secondary-info">${['status','location','faction'].map(k=>field(k)).join('')}</div></div></section><div class="summary-field">${field('summary',true)}</div><div class="panels"><section class="card"><div class="card-heading"><h2>At this moment</h2><span>OPTIONAL STATISTICS</span></div><div class="stat-grid">${['health','armor','mana'].map(k=>field(k)).join('')}</div></section><section class="card"><div class="card-heading"><h2>What they carry</h2><span>EQUIPMENT & KEEPSAKES</span></div>${field('inventory',true)}</section></div><section class="section-block"><div class="section-top"><span class="section-number">01</span><h2>Skills & abilities</h2></div>${field('skills',true)}</section><section class="section-block"><div class="section-top"><span class="section-number">02</span><h2>The person beneath</h2><span>LORE & STORY</span></div><div class="story-grid"><div class="motivation-card">${field('goals',true)}</div><div>${field('traits',true)}</div><div class="wide">${field('backstory',true)}</div><div class="wide">${field('notes',true)}</div></div></section><section class="section-block"><div class="section-top"><span class="section-number">03</span><h2>Connections at this event</h2><span>RECORDED RELATIONSHIPS</span></div><div class="relationships">${relationshipsMarkup()}</div></section><p class="provenance">Profiles begin with the Greyhaven template. Connections show its original event history. Your character edits stay in this browser.</p>`;
}
function renderTimeline() {
  const chapter=data.chapters.find(c=>c.id===event().chapter_id);
  $('#event-context').textContent=`${chapter?.title || 'Greyhaven'} · ${event().title}`;
  $('#event-position').textContent=`${eventIndex+1} / ${data.events.length}`;
  $('#previous-event').disabled=eventIndex===0; $('#next-event').disabled=eventIndex===data.events.length-1;
  $('#chapter-labels').innerHTML=data.chapters.map((c,i)=>`<span style="grid-column:span ${data.events.filter(e=>e.chapter_id===c.id).length}">${['I','II','III'][i]} · ${esc(c.title)}</span>`).join('');
  $('#timeline-events').innerHTML=data.events.map((e,i)=>`<button data-event="${i}" class="event-step ${records.some(r=>r.character===selected&&r.event===i+1)?'has-record':''}" aria-current="${i===eventIndex?'step':'false'}" aria-label="Event ${i+1}: ${esc(e.title)}" title="${esc(e.title)}"><span class="event-dot">${i+1}</span><span class="event-name">${esc(e.title)}</span></button>`).join('');
}
function updateDirty() { const count=changes().length; $('#save-state').textContent=count?`${count} unsaved ${count===1?'change':'changes'}`:(storagePending?'Session only — browser storage unavailable':'All changes saved'); $('#review-button').disabled=!count; document.querySelectorAll('[data-field]').forEach(el=>el.classList.toggle('dirty',draft[el.dataset.field]!==saved[el.dataset.field])); }
function render() { saved=resolveProfile(base(),records,eventIndex+1); draft={...saved}; renderCast(); renderSheet(); renderTimeline(); updateDirty(); }
function navigate(action) { if(changes().length) {pending=action; $('#leave-dialog').showModal();} else action(); }
function chooseCharacter(id) { if(id!==selected) navigate(()=>{selected=id;render();$('#sheet-scroll').scrollTop=0;}); }
function chooseEvent(index) { if(index>=0&&index<data.events.length&&index!==eventIndex) navigate(()=>{eventIndex=index;render();}); }
function openReview() {
  if(!changes().length) return;
  if(!draft.name.trim()) {tell('Give this character a name before saving.');pending=null;$('[data-field="name"]').focus();return;}
  $('#review-context').textContent=`${draft.name} · Event ${eventIndex+1}: ${event().title}`;
  $('#review-count').textContent=`${changes().length} changes to review`;
  $('#change-list').innerHTML=changes().map(c=>`<div class="change-row"><div class="change-heading"><strong class=cast-name>${FIELDS[c.field]}</strong><label class="carry-toggle"><input type="checkbox" name="carry" value="${c.field}" checked> Carry forward</label></div><div class="change-values"><div><span>BEFORE</span><p>${esc(c.before)||'Not set'}</p></div><div><span>AFTER</span><p>${esc(c.after)||'Not set'}</p></div></div></div>`).join('');
  $('#review-dialog').showModal();
}
function saveRecords(next) { records=next;try{localStorage.setItem(STORAGE,JSON.stringify({version:1,records}));storageAvailable=true;storagePending=false;}catch{storageAvailable=false;storagePending=true;} }
async function boot() {
  const response=await fetch('./greyhaven.json');if(!response.ok)throw new Error('Template unavailable');data=await response.json();data.events.sort((a,b)=>a.sequence-b.sequence);selected=data.characters.find(c=>c.name==='Mira Vale')?.id || data.characters[0].id;
  try{const stored=JSON.parse(localStorage.getItem(STORAGE)||'null');if(stored?.version===1)records=validRecords(stored.records,data.characters,data.events.length);}catch{storageAvailable=false;}
  render();
  $('#cast-search').addEventListener('input',renderCast);
  document.addEventListener('click',e=>{const c=e.target.closest('[data-character]'),t=e.target.closest('[data-event]'),close=e.target.closest('[data-close]');if(c)chooseCharacter(Number(c.dataset.character));if(t)chooseEvent(Number(t.dataset.event));if(close)$('#'+close.dataset.close).close();});
  $('#sheet').addEventListener('input',e=>{if(e.target.dataset.field){draft[e.target.dataset.field]=e.target.value;updateDirty();}});
  $('#review-button').onclick=()=>{pending=null;openReview();};
  $('#cancel-review').onclick=()=>{$('#review-dialog').close();pending=null;};$('#review-dialog').oncancel=()=>{pending=null;};
  for(const [id,value] of [['select-all',true],['deselect-all',false]])$('#'+id).onclick=()=>document.querySelectorAll('[name="carry"]').forEach(c=>c.checked=value);
  $('#review-form').onsubmit=e=>{e.preventDefault();const list=changes(),carry=new Set([...document.querySelectorAll('[name="carry"]:checked')].map(c=>c.value));saveRecords(commitChanges(records,selected,eventIndex+1,list,carry));$('#review-dialog').close();const next=pending;pending=null;render();if(next)next();tell(storageAvailable?`${list.length} changes saved · ${carry.size} carry forward`:'Saved for this session only: browser storage is unavailable.');};
  $('#stay').onclick=()=>{pending=null;$('#leave-dialog').close();};$('#leave-dialog').oncancel=()=>{pending=null;};
  $('#discard').onclick=()=>{$('#leave-dialog').close();const next=pending;pending=null;if(next)next();};
  $('#leave-review').onclick=()=>{$('#leave-dialog').close();openReview();};
  $('#previous-event').onclick=()=>chooseEvent(eventIndex-1);$('#next-event').onclick=()=>chooseEvent(eventIndex+1);
  $('#context-button').onclick=()=>{$('#context-chapter').textContent=data.chapters.find(c=>c.id===event().chapter_id)?.title || 'Greyhaven';$('#context-title').textContent=event().title;$('#context-description').textContent=event().summary || event().description || '';$('#context-dialog').showModal();};
  for(const id of ['about-button','about-brand'])$('#'+id).onclick=e=>{e.preventDefault();$('#about-dialog').showModal();};
  $('#reset-button').onclick=()=>{$('#about-dialog').close();$('#reset-dialog').showModal();};
  $('#confirm-reset').onclick=()=>{saveRecords([]);pending=null;$('#reset-dialog').close();render();tell(storagePending?'Reset for this session only. Browser storage could not be cleared.':'Original Greyhaven template restored.');};
  document.addEventListener('keydown',e=>{if(document.querySelector('dialog[open]'))return;if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();pending=null;openReview();}if(e.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('#cast-search').focus();}});
  window.addEventListener('beforeunload',e=>{if(changes().length||storagePending){e.preventDefault();e.returnValue='';}});
}
boot().catch(error=>{$('#sheet').textContent='Greyhaven could not open. Start the local prototype server, then reload this page.';console.error(error);});
