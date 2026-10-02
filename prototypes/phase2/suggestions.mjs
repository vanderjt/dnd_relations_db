export const SUGGESTED_FIELDS = new Set(['species', 'role', 'status', 'location', 'faction']);
export function uniqueOptions(values) {
  const items=new Map();
  for(const value of values) {
    if(typeof value!=='string') continue;
    const clean=value.trim();
    if(clean&&!items.has(clean.toLocaleLowerCase())) items.set(clean.toLocaleLowerCase(),clean);
  }
  return [...items.values()].sort((a,b)=>a.localeCompare(b));
}

// One floating list avoids clipping inside the independently scrolling sheet.
export function installSuggestions(root, getOptions) {
  const panel=document.createElement('div');
  panel.className='suggestion-panel';panel.hidden=true;
  const list=document.createElement('div');list.id='field-options';list.role='listbox';
  const hint=document.createElement('div');hint.className='suggestion-hint';
  hint.textContent='Type to filter. New values join the list when you save.';
  panel.append(list,hint);document.body.append(panel);
  let input=null, options=[], active=-1;
  function close() {
    if(input){input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');}
    panel.hidden=true;input=null;active=-1;
  }
  function highlight(index) {
    active=index;
    [...list.children].forEach((el,i)=>el.setAttribute('aria-selected',String(i===index)));
    if(index>=0){input.setAttribute('aria-activedescendant',list.children[index].id);list.children[index].scrollIntoView({block:'nearest'});}
    else input.removeAttribute('aria-activedescendant');
  }
  function open(el, filter=false) {
    if(input&&input!==el) close();
    input=el;
    const values=uniqueOptions(getOptions(el.dataset.field));
    const query=filter?el.value.trim().toLocaleLowerCase():'';
    options=values.filter(v=>v.toLocaleLowerCase().includes(query)).map(value=>({value,custom:false}));
    const typed=el.value.trim();
    if(filter&&typed&&!values.some(v=>v.toLocaleLowerCase()===typed.toLocaleLowerCase())) options.push({value:typed,custom:true});
    list.replaceChildren();list.setAttribute('aria-label',el.getAttribute('aria-label')+' options');
    options.forEach((option,i)=>{
      const row=document.createElement('div');row.id=`field-option-${i}`;row.role='option';row.dataset.index=i;
      row.textContent=option.custom?`Use “${option.value}” (new)`:option.value;
      list.append(row);
    });
    if(!options.length){const empty=document.createElement('p');empty.className='suggestion-empty';empty.textContent='No options yet. Type a new value.';list.append(empty);}
    panel.hidden=false;el.setAttribute('aria-expanded','true');highlight(-1);
    const rect=el.getBoundingClientRect(), width=Math.min(Math.max(rect.width,250),innerWidth-24);
    panel.style.width=width+'px';panel.style.left=Math.min(Math.max(12,rect.left),innerWidth-width-12)+'px';
    const below=innerHeight-rect.bottom-12, above=rect.top-12;
    const upward=below<210&&above>below;
    list.style.maxHeight=Math.max(60,Math.min(220,(upward?above:below)-60))+'px';
    panel.style.top=(upward?Math.max(8,rect.top-panel.offsetHeight-4):rect.bottom+4)+'px';
  }
  function choose(index) {
    if(!options[index])return;
    const el=input;el.value=options[index].value;
    el.dispatchEvent(new Event('input',{bubbles:true}));close();el.focus();
  }
  root.addEventListener('pointerdown',e=>{if(e.target.closest('[data-options-for]'))e.preventDefault();});
  root.addEventListener('click',e=>{
    const toggle=e.target.closest('[data-options-for]');
    if(toggle){const el=root.querySelector(`[data-field="${toggle.dataset.optionsFor}"]`);const wasOpen=input===el;el.focus();if(wasOpen)close();else open(el);return;}
    if(e.target.matches('[role=combobox]'))open(e.target);
  });
  root.addEventListener('focusin',e=>{if(e.target.matches('[role=combobox]'))open(e.target);});
  root.addEventListener('input',e=>{if(e.target.matches('[role=combobox]')&&!e.isComposing)open(e.target,true);});
  root.addEventListener('compositionend',e=>{if(e.target.matches('[role=combobox]'))open(e.target,true);});
  root.addEventListener('keydown',e=>{
    if(!e.target.matches('[role=combobox]')||e.isComposing)return;
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){
      e.preventDefault();if(input!==e.target)open(e.target);
      if(options.length)highlight((active+(e.key==='ArrowDown'?1:active<0?0:-1)+options.length)%options.length);
    }else if(e.key==='Enter'&&input===e.target){e.preventDefault();if(active>=0)choose(active);else close();}
    else if(e.key==='Escape'&&input){e.preventDefault();e.stopPropagation();close();}
    else if(e.key==='Tab')close();
  });
  panel.addEventListener('pointerdown',e=>e.preventDefault());
  panel.addEventListener('click',e=>{const row=e.target.closest('[data-index]');if(row)choose(Number(row.dataset.index));});
  document.addEventListener('pointerdown',e=>{if(input&&!panel.contains(e.target)&&e.target!==input&&!e.target.closest('[data-options-for]'))close();});
  document.addEventListener('focusin',e=>{if(input&&e.target!==input&&!panel.contains(e.target))close();});
  window.addEventListener('resize',close);
  document.addEventListener('scroll',e=>{if(!panel.contains(e.target))close();},true);
  return close;
}
