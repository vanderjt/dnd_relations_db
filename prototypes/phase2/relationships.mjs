export const TYPES = [
  ['friend','Friend','Friend','mutual'],['ally','Ally','Ally','mutual'],
  ['family','Family','Family','mutual'],['rival','Rival','Rival','mutual'],
  ['enemy','Enemy','Enemy','mutual'],['colleague','Colleague','Colleague','mutual'],
  ['mentor','Mentor','Student','directional'],['employer','Employer','Employee','directional'],
  ['distrust','Distrusts','Distrusted by','directional'],
  ['hostile','Hostile toward','Target of hostility','directional'],
];
export const pair = (a,b) => [a,b].sort((x,y)=>x-y).join(':');
export const equal = (a,b) => JSON.stringify(a??null)===JSON.stringify(b??null);
export function clean(r) {
  return {source_id:r.source_id,target_id:r.target_id,kind:r.kind,
    inverse_label:r.inverse_label||'',semantics:r.semantics,notes:r.notes||''};
}
export function label(r, character) {
  if(r.semantics==='mutual'||r.source_id===character)return r.kind;
  return r.inverse_label||`Receives ${r.kind.toLowerCase()}`;
}
export function typed(type, reverse, character, other, notes='') {
  const t=TYPES.find(t=>t[0]===type);
  if(!t)throw new Error('Unknown relationship type');
  return {source_id:reverse?other:character,target_id:reverse?character:other,
    kind:t[1],inverse_label:t[3]==='mutual'?'':t[2],semantics:t[3],notes};
}
// Derive explicit transitions from the original event snapshots. Unchanged
// snapshots are not new decisions and do not interrupt a continuing edit.
export function seedHistory(data) {
  const history=[];let previous={};
  data.events.forEach((event,index)=>{
    const next=Object.fromEntries((data.relationships[String(event.id)]||[]).map(r=>['legacy-'+r.id,clean(r)]));
    for(const key of new Set([...Object.keys(previous),...Object.keys(next)])) {
      if(!equal(previous[key],next[key]))history.push({key,event:index+1,value:next[key]||null,persist:true});
    }
    previous=next;
  });
  return history;
}
export function resolveConnections(seed, edits, event) {
  const keys=new Set([...seed,...edits].map(r=>r.key)), result={};
  for(const key of keys) {
    const original=seed.filter(r=>r.key===key&&r.event<=event);
    const custom=edits.filter(r=>r.key===key&&r.event<=event);
    const exact=custom.find(r=>r.event===event);
    const continuing=[...original,...custom.filter(r=>r.persist)].sort((a,b)=>b.event-a.event||(custom.includes(b)?1:0)-(custom.includes(a)?1:0))[0];
    const value=(exact||continuing)?.value;
    if(value)result[key]=value;
  }
  return result;
}
export function commitConnections(records,event,changes,carry) {
  const keys=new Set(changes.map(c=>c.key));
  return [...records.filter(r=>!(r.event===event&&keys.has(r.key))),
    ...changes.map(c=>({key:c.key,event,value:c.value,persist:carry.has(c.field)}))];
}
export function validConnectionRecords(raw,data) {
  if(!Array.isArray(raw))return [];
  const ids=new Set(data.characters.map(c=>c.id));
  const legacy=new Map(seedHistory(data).filter(r=>r.value).map(r=>[r.key,pair(r.value.source_id,r.value.target_id)]));
  const result=new Map();
  for(const r of raw) {
    if(!r||typeof r.key!=='string'||!Number.isInteger(r.event)||r.event<1||r.event>data.events.length||typeof r.persist!=='boolean')continue;
    const v=r.value;
    const newPair=r.key.startsWith('pair-')?r.key.slice(5):null;
    const endpoints=newPair?.split(':').map(Number);
    if(!legacy.has(r.key)&&!(endpoints?.length===2&&endpoints.every(id=>ids.has(id))&&endpoints[0]<endpoints[1]))continue;
    if(v!==null&&(!v||!ids.has(v.source_id)||!ids.has(v.target_id)||v.source_id===v.target_id||!['mutual','directional'].includes(v.semantics)||!['kind','inverse_label','notes'].every(k=>typeof v[k]==='string')||!v.kind.trim()||pair(v.source_id,v.target_id)!==(legacy.get(r.key)||newPair)))continue;
    result.set(r.key+'@'+r.event,{key:r.key,event:r.event,value:v?clean(v):null,persist:r.persist});
  }
  return [...result.values()];
}
