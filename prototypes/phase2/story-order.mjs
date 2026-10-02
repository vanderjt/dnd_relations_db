import {FIELDS,resolveProfile} from './model.mjs';
import {seedHistory,resolveConnections,equal} from './relationships.mjs';

// Records use sequence positions in this prototype. Remap through event IDs so
// moving a scene never attaches an authored decision to a different scene.
export function planEventMove(data,records,connections,id,chapter,before=null){
  const source=data.events.find(e=>e.id===id);
  if(!source||!data.chapters.some(c=>c.id===chapter))throw new Error('Unknown event or chapter');
  const events=data.events.filter(e=>e.id!==id).map(e=>({...e}));
  let index;
  if(before!==null){index=events.findIndex(e=>e.id===before&&e.chapter_id===chapter);if(index<0)throw new Error('Invalid destination');}
  else {const rank=data.chapters.findIndex(c=>c.id===chapter);index=events.findIndex(e=>data.chapters.findIndex(c=>c.id===e.chapter_id)>rank);if(index<0)index=events.length;}
  events.splice(index,0,{...source,chapter_id:chapter});events.forEach((e,i)=>e.sequence=i+1);
  return {...assessOrder(data,records,connections,events),changed:events.some((e,i)=>e.id!==data.events[i].id||e.chapter_id!==data.events[i].chapter_id),from:data.events.indexOf(source)+1,to:index+1};
}
export function planChapterMove(data,records,connections,id,before=null){
  const source=data.chapters.find(c=>c.id===id);if(!source)throw new Error('Unknown chapter');
  const chapters=data.chapters.filter(c=>c.id!==id).map(c=>({...c}));
  const index=before===null?chapters.length:chapters.findIndex(c=>c.id===before);if(index<0)throw new Error('Invalid destination');
  chapters.splice(index,0,{...source});chapters.forEach((c,i)=>c.sequence=i+1);
  const events=chapters.flatMap(c=>data.events.filter(e=>e.chapter_id===c.id).map(e=>({...e})));events.forEach((e,i)=>e.sequence=i+1);
  return {...assessOrder(data,records,connections,events),chapters,changed:chapters.some((c,i)=>c.id!==data.chapters[i].id),from:data.chapters.indexOf(source)+1,to:index+1,eventCount:data.events.filter(e=>e.chapter_id===id).length};
}
export function planStoryDeletion(data,records,connections,kind,id,destination=null){
  const isChapter=kind==='chapter',source=(isChapter?data.chapters:data.events).find(x=>x.id===id);
  if(!source)throw new Error('This item no longer exists.');
  if(isChapter&&data.chapters.length===1)throw new Error('Keep at least one chapter. Create another chapter before removing this one.');
  if(destination!==null&&(!isChapter||destination===id||!data.chapters.some(c=>c.id===destination)))throw new Error('Choose another chapter for these events.');
  const removedEvents=data.events.filter(e=>isChapter?e.chapter_id===id&&destination===null:e.id===id);
  // Keeping a chapter’s events never removes individual event records.
  const deleted=new Set(isChapter&&destination!==null?[]:removedEvents.map(e=>e.id));
  const chapters=data.chapters.filter(c=>!isChapter||c.id!==id).map((c,i)=>({...c,sequence:i+1}));
  let events=data.events.filter(e=>!deleted.has(e.id)).map(e=>({...e}));
  if(isChapter&&destination!==null){const moved=events.filter(e=>e.chapter_id===id).map(e=>({...e,chapter_id:destination}));events=chapters.flatMap(c=>[...events.filter(e=>e.chapter_id===c.id),...(c.id===destination?moved:[])]);}
  if(!events.length)throw new Error('Keep at least one event. Create a replacement event before deleting the last one.');
  events.forEach((e,i)=>e.sequence=i+1);
  const removedProfiles=records.filter(r=>deleted.has(data.events[r.event-1].id));
  const removedConnections=connections.filter(r=>deleted.has(data.events[r.event-1].id));
  const profileEdits=removedProfiles.map(r=>{const c=data.characters.find(c=>c.id===r.character);return `${c?resolveProfile(c,records,r.event).name:'Removed character'} — ${FIELDS[r.field]}: ${r.value||'not set'} (${data.events[r.event-1].title})`;});
  const connectionEdits=removedConnections.map(r=>{const original=r.value||[...connections,...seedHistory(data)].find(x=>x.key===r.key&&x.value)?.value;const names=original?[original.source_id,original.target_id].map(id=>data.characters.find(c=>c.id===id)?.name||'Removed character').join(' / '):r.key;return `${names} — ${r.value?r.value.kind:'connection removal'} (${data.events[r.event-1].title})`;});
  return {...assessOrder(data,records,connections,events),chapters,deletedEvents:[...deleted].map(id=>data.events.find(e=>e.id===id)),profileEdits,connectionEdits,movedEvents:isChapter&&destination!==null?data.events.filter(e=>e.chapter_id===id).length:0};
}
function assessOrder(data,records,connections,events){
  const positions=new Map(events.map((e,i)=>[e.id,i+1]));
  const remap=list=>list.filter(r=>positions.has(data.events[r.event-1].id)).map(r=>({...r,event:positions.get(data.events[r.event-1].id)}));
  const nextRecords=remap(records),nextConnections=remap(connections),oldSeed=seedHistory(data),newSeed=seedHistory({...data,events});
  const effects=[];
  for(const [i,e] of data.events.entries()){
    const next=positions.get(e.id);if(next===undefined)continue;
    const details=[];let profiles=0;
    const value=v=>v?`“${v}”`:'not set';
    for(const c of data.characters){
      const oldProfile=resolveProfile(c,records,i+1),newProfile=resolveProfile(c,nextRecords,next);
      const fields=Object.keys(FIELDS).filter(k=>oldProfile[k]!==newProfile[k]);
      if(fields.length)profiles++;
      for(const key of fields)details.push(`${oldProfile.name}’s ${FIELDS[key].toLowerCase()} changes from ${value(oldProfile[key])} to ${value(newProfile[key])}.`);
    }
    const oldState=resolveConnections(oldSeed,connections,i+1),newState=resolveConnections(newSeed,nextConnections,next);
    const relationships=[...new Set([...Object.keys(oldState),...Object.keys(newState)])].filter(k=>!equal(oldState[k],newState[k])).length;
    const person=(id,edits,position)=>{const c=data.characters.find(c=>c.id===id);return c?resolveProfile(c,edits,position).name:'Removed character';};
    const describe=(r,edits,position)=>`${person(r.source_id,edits,position)} ${r.semantics==='mutual'?'↔':'→'} ${person(r.target_id,edits,position)}: ${r.kind}`;
    for(const key of new Set([...Object.keys(oldState),...Object.keys(newState)])){
      const old=oldState[key],now=newState[key];if(equal(old,now))continue;
      if(!old)details.push(`${describe(now,nextRecords,next)} becomes present at this event.${now.notes?` Notes: ${value(now.notes)}.`:''}`);
      else if(!now)details.push(`${describe(old,records,i+1)} is no longer present at this event.`);
      else {
        const a=describe(old,records,i+1),b=describe(now,nextRecords,next);
        if(a!==b)details.push(`Connection changes from ${a} to ${b}.`);
        if(old.notes!==now.notes)details.push(`${b} — notes change from ${value(old.notes)} to ${value(now.notes)}.`);
        if(a===b&&old.notes===now.notes)details.push(`${b} — the reverse relationship label changes from ${value(old.inverse_label)} to ${value(now.inverse_label)}.`);
      }
    }
    if(profiles||relationships)effects.push({id:e.id,title:e.title,profiles,relationships,details});
  }
  return {events,records:nextRecords,connections:nextConnections,effects};
}
