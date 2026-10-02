import {TYPES,pair,equal,label,typed,seedHistory,resolveConnections,commitConnections,validConnectionRecords} from './relationships.mjs?v=6';

export function createConnectionEditor({data,context,name,esc,tone,changed}) {
  const seed=seedHistory(data);
  let records=[], saved={}, draft={}, removed=new Map(), editing=null;
  const dialog=document.createElement('dialog');dialog.id='connection-dialog';
  dialog.innerHTML=`<form id="connection-form"><div class="dialog-header"><h2 id="connection-title">Add connection</h2><p id="connection-context"></p></div><div class="connection-form-fields"><label class="field">Character<select id="connection-person" required></select></label><label class="field">Relationship<select id="connection-type" required></select></label><p id="connection-preview" aria-live="polite"></p><label class="field">Notes<textarea id="connection-notes" rows="3"></textarea></label><p class="muted">This stages a change. Review changes to save it and choose whether it carries forward.</p></div><div class="dialog-actions"><button type="button" class="secondary" id="connection-cancel">Cancel</button><button class="primary" type="submit">Apply change</button></div></form>`;
  dialog.setAttribute('aria-labelledby','connection-title');document.body.append(dialog);
  const $=s=>dialog.querySelector(s);
  function relevant(r){const c=context().character;return r&&(r.source_id===c||r.target_id===c);}
  function other(r){return r.source_id===context().character?r.target_id:r.source_id;}
  function description(r){return r?`${label(r,context().character)}${r.notes?' — '+r.notes:''}`:'No connection';}
  function changes(){return [...new Set([...Object.keys(saved),...Object.keys(draft)])].filter(k=>!equal(saved[k],draft[k])).map(key=>({key,field:'connection:'+key,label:`Connection with ${name(other(draft[key]||saved[key]))}`,before:description(saved[key]),after:description(draft[key]),value:draft[key]||null}));}
  function markup() {
    const rows=Object.entries(draft).filter(([,r])=>relevant(r)).sort(([,a],[,b])=>name(other(a)).localeCompare(name(other(b))));
    const table=rows.length?`<table class="connections-table"><caption class="sr-only">Connections at this event, sorted by character name</caption><thead><tr><th scope="col">Character</th><th scope="col">Relationship</th><th scope="col">Details</th><th scope="col"><span class="sr-only">Actions</span></th></tr></thead><tbody>${rows.map(([key,r])=>`<tr><th scope="row"><button class="connection-person" data-character="${other(r)}">${esc(name(other(r)))}</button></th><td><button class="relationship-kind" data-edit-connection="${esc(key)}" data-tone="${tone(label(r,context().character))}" aria-label="Change relationship with ${esc(name(other(r)))}">${esc(label(r,context().character))} <span aria-hidden="true">⌄</span></button>${!equal(saved[key],r)?'<span class="connection-unsaved">Unsaved</span>':''}</td><td class="connection-details">${esc(r.notes)||'<span class="muted">No details recorded</span>'}</td><td><button class="delete-connection" data-delete-connection="${esc(key)}" aria-label="Delete connection with ${esc(name(other(r)))}" title="Delete connection with ${esc(name(other(r)))}"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/></svg></button></td></tr>`).join('')}</tbody></table>`:'<p class="muted">No connections at this event.</p>';
    return table+`<div class="connection-footer">${[...removed].map(([key,r])=>`<div class="pending-removal">${esc(name(other(r)))} removed · not saved <button class="text-button" data-undo-connection="${esc(key)}">Undo</button></div>`).join('')}<button class="secondary" data-add-connection>Add connection</button></div>`;
  }
  function refresh(){const host=document.querySelector('.connections');if(host)host.innerHTML=markup();changed();}
  function value() {
    const choice=$('#connection-type').value;
    if(choice==='original')return {...draft[editing],notes:$('#connection-notes').value};
    const [type,reverse]=choice.split(':');
    return typed(type,reverse==='reverse',context().character,Number($('#connection-person').value),$('#connection-notes').value);
  }
  function preview(){
    if(!$('#connection-person').value){$('#connection-preview').textContent='Every other cast member is already connected.';return;}
    const r=value();
    const verbs={Mentor:'mentors',Employer:'employs',Distrusts:'distrusts','Hostile toward':'is hostile toward'};
    $('#connection-preview').textContent=r.semantics==='mutual'?`${name(r.source_id)} and ${name(r.target_id)}: ${r.kind} (mutual).`:verbs[r.kind]?`${name(r.source_id)} ${verbs[r.kind]} ${name(r.target_id)}. ${name(r.target_id)} sees “${label(r,r.target_id)}”.`:`${name(r.source_id)} → ${name(r.target_id)}: ${r.kind} (one-way).`;
  }
  function open(key=null){
    editing=key;const current=key?draft[key]:null;
    $('#connection-title').textContent=current?'Edit connection':'Add connection';
    $('#connection-context').textContent=`${name(context().character)} · Event ${context().event}`;
    const connected=new Set(Object.values(draft).filter(relevant).map(other));
    const choices=data.characters.filter(c=>c.id!==context().character&&(current?c.id===other(current):!connected.has(c.id))).sort((a,b)=>name(a.id).localeCompare(name(b.id)));
    $('#connection-person').innerHTML=choices.map(c=>`<option value="${c.id}">${esc(name(c.id))}</option>`).join('');
    $('#connection-person').disabled=!!current;
    $('#connection-type').innerHTML=(current?`<option value="original">${esc(label(current,context().character))} — current</option>`:'')+TYPES.map(([id,forward,reverse,semantics])=>`<option value="${id}:forward">${esc(forward)}${semantics==='mutual'?' (mutual)':''}</option>${semantics==='directional'?`<option value="${id}:reverse">${esc(reverse)}</option>`:''}`).join('');
    $('#connection-notes').value=current?.notes||'';
    $('button[type=submit]').disabled=!choices.length;preview();dialog.showModal();
    (current?$('#connection-type'):$('#connection-person')).focus();
  }
  $('#connection-person').onchange=preview;$('#connection-type').onchange=preview;
  $('#connection-cancel').onclick=()=>dialog.close();
  $('#connection-form').onsubmit=e=>{
    e.preventDefault();if(!$('#connection-person').value)return;
    const r=value();
    // Reconnect a deleted legacy record under the same identity, avoiding duplicates.
    const key=editing||Object.keys(saved).find(k=>pair(saved[k].source_id,saved[k].target_id)===pair(r.source_id,r.target_id))||Object.keys(resolveConnections(seed,[],context().event)).find(k=>{const original=resolveConnections(seed,[],context().event)[k];return pair(original.source_id,original.target_id)===pair(r.source_id,r.target_id);})||'pair-'+pair(r.source_id,r.target_id);
    draft[key]=r;removed.delete(key);dialog.close();refresh();
    document.querySelector(`[data-edit-connection="${key}"]`)?.focus();
  };
  document.querySelector('#sheet').addEventListener('click',e=>{
    const edit=e.target.closest('[data-edit-connection]'),del=e.target.closest('[data-delete-connection]'),undo=e.target.closest('[data-undo-connection]');
    if(edit)open(edit.dataset.editConnection);
    if(e.target.closest('[data-add-connection]'))open();
    if(del){const key=del.dataset.deleteConnection;removed.set(key,draft[key]);delete draft[key];refresh();document.querySelector(`[data-undo-connection="${key}"]`)?.focus();}
    if(undo){const key=undo.dataset.undoConnection;draft[key]=removed.get(key);removed.delete(key);refresh();document.querySelector(`[data-edit-connection="${key}"]`)?.focus();}
  });
  return {
    markup,changes,open,state:()=>draft,removed:()=>[...removed],
    reset(){const ids=new Set(data.characters.map(c=>c.id));saved=Object.fromEntries(Object.entries(resolveConnections(seed,records,context().event)).filter(([,r])=>ids.has(r.source_id)&&ids.has(r.target_id)));draft=structuredClone(saved);removed.clear();},
    load(raw){records=validConnectionRecords(raw,data);},
    records:()=>records,
    commit(carry){records=commitConnections(records,context().event,changes(),carry);},
    removeCharacter(id){
      const keys=new Set([...seed,...records].filter(r=>r.value&&(r.value.source_id===id||r.value.target_id===id)).map(r=>r.key));
      records=records.filter(r=>!keys.has(r.key));
    },
    clear(){records=[];},
    hasRecord(character,event){return records.some(r=>r.event===event&&(r.value? r.value.source_id===character||r.value.target_id===character : [...seed,...records].some(s=>s.key===r.key&&s.value&&(s.value.source_id===character||s.value.target_id===character))));},
  };
}
