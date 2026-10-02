import {label} from './relationships.mjs?v=10';

export function graphMarkup({characters,connections,removed,selected,mode,name,esc,tone,eventTitle,profile}) {
  const entries=Object.entries(connections);
  const neighbors=new Set([selected]);
  entries.forEach(([,r])=>{if(r.source_id===selected)neighbors.add(r.target_id);if(r.target_id===selected)neighbors.add(r.source_id);});
  const cast=characters.filter(c=>mode==='full'||neighbors.has(c.id));
  const visible=new Set(cast.map(c=>c.id));
  const edges=entries.filter(([,r])=>visible.has(r.source_id)&&visible.has(r.target_id)&&(mode==='full'||r.source_id===selected||r.target_id===selected));
  const points=new Map();
  const outer=mode==='direct'?cast.filter(c=>c.id!==selected):cast;
  outer.forEach((c,i)=>{const angle=2*Math.PI*i/Math.max(1,outer.length)-Math.PI/2;points.set(c.id,{x:450+330*Math.cos(angle),y:350+265*Math.sin(angle)});});
  if(mode==='direct')points.set(selected,{x:450,y:350});
  const nearby=entries.filter(([,r])=>r.source_id===selected||r.target_id===selected).sort(([,a],[,b])=>name(a.source_id===selected?a.target_id:a.source_id).localeCompare(name(b.source_id===selected?b.target_id:b.source_id)));
  return `<div class="graph-heading"><div><h1>Relationships</h1><p>Explore the cast during ${esc(eventTitle)}.</p></div></div>
  <div class="graph-toolbar"><div class="graph-selection"><label>Selected character <select id="graph-character">${characters.map(c=>`<option value="${c.id}" ${c.id===selected?'selected':''}>${esc(name(c.id))}</option>`).join('')}</select></label><div class="scope-control"><span>Full cast</span><button id="graph-scope-toggle" role="switch" aria-label="Direct connections" aria-checked="${mode==='direct'}"><span></span></button><span>Direct connections</span></div></div></div>
  <div class="graph-layout"><section class="graph-canvas" aria-label="Relationship graph"><div class="graph-zoom"><button data-graph-zoom="fit" aria-label="Zoom to fit" title="Zoom to fit"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M8 3H3v5M16 3h5v5M21 16v5h-5M8 21H3v-5"/><rect x="8" y="8" width="8" height="8" rx="1"/></svg></button><button data-graph-reset aria-label="Reset layout" title="Reset layout — restore default arrangement"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 10l9-7 9 7M5 9v12h5v-7h4v7h5V9"/></svg></button></div><svg id="relationship-graph" data-layout="${mode==='full'?'full':'direct-'+selected}" viewBox="0 0 900 700" role="group" aria-label="${mode==='full'?'Full cast':'Direct connections'} graph"><defs><marker id="graph-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="context-stroke"/></marker></defs><g id="graph-scene">${edges.map(([key,r])=>{
    const a=points.get(r.source_id),b=points.get(r.target_id),dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1;
    const x1=a.x+dx/len*28,y1=a.y+dy/len*28,x2=b.x-dx/len*31,y2=b.y-dy/len*31;
    return `<g class="graph-edge ${r.source_id===selected||r.target_id===selected?'incident':''}" data-graph-edge="${esc(key)}" data-source="${r.source_id}" data-target="${r.target_id}" tabindex="0" role="button" aria-label="Edit ${esc(name(r.source_id))} to ${esc(name(r.target_id))}: ${esc(r.kind)}" data-tone="${tone(r.kind)}"><title>${esc(name(r.source_id))} ${r.semantics==='mutual'?'↔':'→'} ${esc(name(r.target_id))}: ${esc(r.kind)}</title><line class="edge-hit" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/><line class="edge-line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" ${r.semantics==='directional'?'marker-end="url(#graph-arrow)"':''}/></g>`;
  }).join('')}${cast.map(c=>{const p=points.get(c.id);return `<g class="graph-node ${c.id===selected?'selected':''}" data-graph-node="${c.id}" transform="translate(${p.x} ${p.y})" tabindex="0" role="button" aria-label="Select ${esc(name(c.id))}"><circle r="26"/><text class="node-initials" text-anchor="middle" y="5">${esc(name(c.id).split(/\s+/).slice(0,2).map(s=>s[0]).join(''))}</text><text class="node-name" text-anchor="middle" y="46">${esc(name(c.id))}</text></g>`;}).join('')}</g></svg><div class="graph-caption">${cast.length} characters · ${edges.length} connections <span>Drag nodes to arrange. Drag the background to pan. Scroll to zoom. Arrows show direction.</span></div></section>
  <aside class="graph-inspector"><div class="graph-inspector-heading"><div class="inspector-identity"><div class="inspector-portrait" aria-label="Portrait placeholder">${esc(name(selected).split(/\s+/).slice(0,2).map(s=>s[0]).join(''))}</div><div><h2>${esc(name(selected))}</h2><dl><dt>Age</dt><dd>${esc(profile.age)||'Not set'}</dd><dt>Race</dt><dd>${esc(profile.species)||'Not set'}</dd><dt>Role</dt><dd>${esc(profile.role)||'Not set'}</dd></dl></div></div><p class="inspector-summary">${esc(profile.summary)||'No summary yet.'}</p></div><p class="muted">${nearby.length} connections during ${esc(eventTitle)}</p><div class="graph-connection-list" tabindex="0" aria-label="Connections">${nearby.map(([key,r])=>{const other=r.source_id===selected?r.target_id:r.source_id;return `<article class="graph-connection"><button class="graph-person" data-graph-node="${other}">${esc(name(other))}</button><button class="relationship-kind" data-edit-connection="${esc(key)}" data-tone="${tone(label(r,selected))}">${esc(label(r,selected))} ⌄</button><p>${esc(r.notes)}</p><button class="delete-connection" data-delete-connection="${esc(key)}" aria-label="Delete connection with ${esc(name(other))}" title="Delete connection"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/></svg></button></article>`;}).join('')||'<p class="muted">No connections yet.</p>'}</div>${removed.map(([key,r])=>`<p class="pending-removal">${esc(name(r.source_id===selected?r.target_id:r.source_id))} removed <button class="text-button" data-undo-connection="${esc(key)}">Undo</button></p>`).join('')}<div class="graph-inspector-actions"><button class="secondary" data-open-profile>Open profile</button><button class="secondary" data-add-connection>Add connection</button></div></aside></div>`;
}

// View-only state survives selection and event changes for this browser session.
const layouts=new Map();
export function installGraphZoom(root) {
  const svg=root.querySelector('#relationship-graph'), key=svg.dataset.layout;
  if(!layouts.has(key))layouts.set(key,{positions:new Map(),box:[0,0,900,700]});
  const state=layouts.get(key), nodes=[...svg.querySelectorAll('.graph-node')];
  const position=node=>{const m=node.transform.baseVal.consolidate().matrix;return {x:m.e,y:m.f};};
  const defaults=new Map(nodes.map(node=>[node.dataset.graphNode,node.getAttribute('transform')]));
  for(const node of nodes){const p=state.positions.get(node.dataset.graphNode);if(p)node.setAttribute('transform',`translate(${p.x} ${p.y})`);}
  const redrawEdges=()=>{
    const points=new Map(nodes.map(n=>[n.dataset.graphNode,position(n)]));
    svg.querySelectorAll('.graph-edge').forEach(edge=>{
      const a=points.get(edge.dataset.source),b=points.get(edge.dataset.target),dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1;
      edge.querySelectorAll('line').forEach(line=>{for(const [k,v] of Object.entries({x1:a.x+dx/len*28,y1:a.y+dy/len*28,x2:b.x-dx/len*31,y2:b.y-dy/len*31}))line.setAttribute(k,v);});
    });
  };
  const apply=()=>svg.setAttribute('viewBox',state.box.join(' '));apply();redrawEdges();
  const zoomAt=(factor,point)=>{
    const [x,y,w,h]=state.box,newWidth=Math.max(180,Math.min(4500,w/factor)),ratio=newWidth/w;
    state.box=[point.x-(point.x-x)*ratio,point.y-(point.y-y)*ratio,newWidth,h*ratio];apply();
  };
  const world=(x,y,matrix=svg.getScreenCTM().inverse())=>new DOMPoint(x,y).matrixTransform(matrix);
  root.querySelector('[data-graph-zoom=fit]').onclick=()=>{
      const points=nodes.map(position);const minX=Math.min(...points.map(p=>p.x))-90,maxX=Math.max(...points.map(p=>p.x))+90,minY=Math.min(...points.map(p=>p.y))-65,maxY=Math.max(...points.map(p=>p.y))+85;
      const width=Math.max(300,maxX-minX),height=Math.max(240,maxY-minY);state.box=[minX,minY,width,height];apply();
  };
  root.querySelector('[data-graph-reset]').onclick=()=>{
    state.positions.clear();
    for(const node of nodes){node.setAttribute('transform',defaults.get(node.dataset.graphNode));}
    state.box=[0,0,900,700];apply();redrawEdges();
  };
  let drag=null,suppressClick=false;
  svg.addEventListener('pointerdown',e=>{
    if(e.button!==0||!e.isPrimary)return;
    suppressClick=false;
    const node=e.target.closest('.graph-node');
    drag={id:e.pointerId,node,startX:e.clientX,startY:e.clientY,matrix:svg.getScreenCTM().inverse(),box:[...state.box],origin:node?position(node):null,moved:false};
  });
  svg.addEventListener('pointermove',e=>{
    if(!drag||e.pointerId!==drag.id)return;
    if(Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)>4)drag.moved=true;
    if(!drag.moved)return;
    if(!svg.hasPointerCapture(e.pointerId))svg.setPointerCapture(e.pointerId);
    e.preventDefault();svg.classList.add('is-dragging');
    const start=world(drag.startX,drag.startY,drag.matrix),now=world(e.clientX,e.clientY,drag.matrix),dx=now.x-start.x,dy=now.y-start.y;
    if(drag.node){const p={x:drag.origin.x+dx,y:drag.origin.y+dy};drag.node.setAttribute('transform',`translate(${p.x} ${p.y})`);state.positions.set(drag.node.dataset.graphNode,p);redrawEdges();}
    else{state.box=[drag.box[0]-dx,drag.box[1]-dy,drag.box[2],drag.box[3]];apply();}
  });
  const finish=e=>{if(drag&&e.pointerId===drag.id){suppressClick=drag.moved;drag=null;svg.classList.remove('is-dragging');if(svg.hasPointerCapture(e.pointerId))svg.releasePointerCapture(e.pointerId);}};
  svg.addEventListener('pointerup',finish);svg.addEventListener('pointercancel',finish);
  svg.addEventListener('click',e=>{if(suppressClick){e.preventDefault();e.stopImmediatePropagation();suppressClick=false;}},true);
  svg.addEventListener('wheel',e=>{e.preventDefault();zoomAt(Math.exp(-Math.max(-150,Math.min(150,e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?500:1)))*.002),world(e.clientX,e.clientY));},{passive:false});
  svg.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.closest('[role=button]')){e.preventDefault();e.target.closest('[role=button]').dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
}
