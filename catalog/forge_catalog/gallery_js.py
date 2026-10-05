"""Vanilla JS for gallery.html (kept as a raw string; no external deps)."""

JS = r"""
(function(){
const D=JSON.parse(document.getElementById('catalog-data').textContent);
const A=D.assets, byId=new Map(A.map(a=>[a.id,a]));
const byHash=new Map(), kids=new Map();
for(const a of A){
  if(a.content_hash){if(!byHash.has(a.content_hash))byHash.set(a.content_hash,[]);byHash.get(a.content_hash).push(a.id);}
  if(a.derived_from){for(const p of JSON.parse(a.derived_from)){if(!kids.has(p))kids.set(p,[]);kids.get(p).push(a.id);}}
}
const FACETS=['project','kind','source_tool','model','license','batch'];
const sel={};FACETS.forEach(f=>sel[f]=new Set());
let tab='assets',q='',from='',to='',shown=0;const PAGE=240;
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const val=(a,f)=>a[f]==null||a[f]===''?'(空)':String(a[f]);
const hasLic=a=>a.license&&a.license.toLowerCase()!=='unknown';

function stats(){
  const n=A.length,lic=A.filter(hasLic).length;
  $('#stats').innerHTML=[['资产',n],['license 覆盖',(n?(100*lic/n).toFixed(1):0)+'%  ('+lic+')'],
    ['重复组',D.dup_groups],['孤儿图',D.orphans_total],['台账行',D.ledger_rows],
    ['对比图',A.filter(a=>a.kind==='compare').length]]
    .map(([k,v])=>`<span class="stat">${k} <b>${esc(v)}</b></span>`).join(' ');
  $('#stats').style.display='flex';$('#stats').style.gap='1.2em';
}
function base(){return A.filter(a=>tab==='compare'?a.kind==='compare':a.kind!=='compare');}
function match(a,skip){
  for(const f of FACETS){if(f!==skip&&sel[f].size&&!sel[f].has(val(a,f)))return false;}
  if(q){const t=((a.prompt||'')+' '+a.rel_path+' '+(a.tags_json||'')).toLowerCase();if(!t.includes(q))return false;}
  const d=(a.created_at||'').slice(0,10);
  if(from&&(!d||d<from))return false;if(to&&(!d||d>to))return false;
  return true;
}
function buildFilters(){
  const B=base();
  let h=`<h3>搜索 prompt / 路径</h3><input type="text" id="q" value="${esc(q)}" placeholder="关键词">
  <h3>日期</h3><input type="date" id="from" value="${from}"><input type="date" id="to" value="${to}" style="margin-top:.3em">
  <button class="btn" id="reset" style="margin-top:.6em;width:100%">清空筛选</button>`;
  for(const f of FACETS){
    const c=new Map();for(const a of B){if(match(a,f)){const v=val(a,f);c.set(v,(c.get(v)||0)+1);}}
    for(const v of sel[f])if(!c.has(v))c.set(v,0);
    const items=[...c.entries()].sort((x,y)=>y[1]-x[1]||x[0].localeCompare(y[0]));
    h+=`<h3>${f} (${items.length})</h3><div class="opts" data-f="${f}">`+
      (items.length>12?`<input type="text" class="of" placeholder="过滤选项">`:'')+
      items.map(([v,n])=>`<label data-v="${esc(v.toLowerCase())}"><input type="checkbox" value="${esc(v)}" ${sel[f].has(v)?'checked':''}>`+
        `<span>${esc(v)}</span><span class="n">${n}</span></label>`).join('')+`</div>`;
  }
  $('#filters').innerHTML=h;
  $('#q').oninput=e=>{q=e.target.value.trim().toLowerCase();refresh(false);};
  $('#from').onchange=e=>{from=e.target.value;refresh();};
  $('#to').onchange=e=>{to=e.target.value;refresh();};
  $('#reset').onclick=()=>{FACETS.forEach(f=>sel[f].clear());q=from=to='';refresh();};
  document.querySelectorAll('.opts').forEach(box=>{
    const f=box.dataset.f;
    box.addEventListener('change',e=>{if(e.target.type!=='checkbox')return;
      e.target.checked?sel[f].add(e.target.value):sel[f].delete(e.target.value);refresh();});
    const of=box.querySelector('.of');
    if(of)of.oninput=()=>{const t=of.value.toLowerCase();
      box.querySelectorAll('label').forEach(l=>l.style.display=l.dataset.v.includes(t)?'':'none');};
  });
}
let list=[];
function placeholder(a){return {model3d:'3D',audio:'♪','ledger-entry':'台账','manifest-entry':'清单'}[a.kind]||a.kind;}
function card(a){
  const th=a.thumb?`<img loading="lazy" src="thumbs/${a.id}.jpg" alt="">`:esc(placeholder(a));
  return `<div class="card${a.file_exists?'':' missing'}" data-id="${a.id}"><div class="thumb">${th}</div>
  <div class="meta"><div title="${esc(a.license||'unknown')}"><span class="lic ${a.lc}"></span>${esc(a.project)}</div>
  <div class="mute">${esc(a.model||a.source_tool||'')}</div><div class="mute">${esc(a.batch||'')}</div></div></div>`;
}
function more(){
  const chunk=list.slice(shown,shown+PAGE);shown+=chunk.length;
  $('#grid').insertAdjacentHTML('beforeend',chunk.map(card).join(''));
  $('#more').style.display=shown<list.length?'block':'none';
  $('#count').textContent=`显示 ${shown} / 筛选后 ${list.length} / 本页签 ${base().length}`;
}
function refresh(rebuild=true){
  list=base().filter(a=>match(a,null));
  list.sort((x,y)=>(y.created_at||'').localeCompare(x.created_at||''));
  shown=0;$('#grid').innerHTML='';more();
  if(rebuild)buildFilters();
}
const jump=id=>{const a=byId.get(id);return a?`<a class="jump" data-id="${id}">${esc(a.project)} · ${esc(a.rel_path)}</a>`:esc(id);};
function pretty(s){try{return JSON.stringify(JSON.parse(s),null,2);}catch(e){return s;}}
function open(id){
  const a=byId.get(id);if(!a)return;
  const skip=new Set(['prompt','params_json','lc','thumb','input_refs_json','derived_from']);
  let h=`<button class="btn" id="close" style="float:right">关闭 (Esc)</button><h2 style="margin-top:0;font-size:1.1em">${esc(a.rel_path.split('/').pop())}</h2>`;
  if(a.thumb)h+=`<img src="thumbs/${a.id}.jpg" alt="">`;
  h+='<table>'+Object.keys(a).filter(k=>!skip.has(k)).map(k=>
    `<tr><td>${esc(k)}</td><td>${k==='license'?`<span class="lic ${a.lc}"></span>`:''}${esc(a[k])}</td></tr>`).join('')+'</table>';
  if(a.prompt)h+=`<h3>prompt</h3><pre>${esc(a.prompt)}</pre>`;
  if(a.input_refs_json)h+=`<h3>input refs</h3><pre>${esc(pretty(a.input_refs_json))}</pre>`;
  if(a.derived_from)h+=`<h3>派生自 derived_from</h3>`+JSON.parse(a.derived_from).map(i=>`<div>${jump(i)}</div>`).join('');
  if(kids.has(a.id))h+=`<h3>被派生 (${kids.get(a.id).length})</h3>`+kids.get(a.id).map(i=>`<div>${jump(i)}</div>`).join('');
  const same=(byHash.get(a.content_hash)||[]).filter(i=>i!==a.id);
  if(same.length)h+=`<h3>同 hash 重复 (${same.length})</h3>`+same.map(i=>`<div>${jump(i)}</div>`).join('');
  if(a.params_json)h+=`<h3>params</h3><pre>${esc(pretty(a.params_json))}</pre>`;
  const dr=$('#drawer');dr.innerHTML=h;dr.classList.add('on');dr.scrollTop=0;
  $('#close').onclick=()=>dr.classList.remove('on');
}
document.addEventListener('click',e=>{
  const j=e.target.closest('a.jump');if(j){open(j.dataset.id);return;}
  const c=e.target.closest('.card');if(c)open(c.dataset.id);
});
document.addEventListener('keydown',e=>{if(e.key==='Escape')$('#drawer').classList.remove('on');});
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('on',x===b));
  tab=b.dataset.tab;FACETS.forEach(f=>sel[f].clear());refresh();});
$('#more').onclick=more;
const gw=$('#gridwrap');gw.addEventListener('scroll',()=>{
  if(gw.scrollTop+gw.clientHeight>gw.scrollHeight-600&&shown<list.length)more();});
stats();refresh();
})();
"""
