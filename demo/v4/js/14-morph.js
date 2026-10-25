/* 14-morph.js — S3 THE REPAIR MORPH (SPEC-v4 S3; WORKPLAN 14-morph). Section #morph, part live.bodies.
   Owns: the 2-up stage (attempt 1 over the final: WIPE with a draggable divider, or CROSSFADE), the scrub, the finding head that crossfades to the verdict past 0.5,
   the diff pane (DIFF.diffRows; workers/diff.worker.js for > 400 lines, the same code on the main thread otherwise or when the worker is refused), the two
   pinned measured frames (16.5.0 · 16.5.1, nb and verdicts: the morph is never the evidence), the node pulse (render-time SAI emissiveColor on the final
   canvas, two 600 ms pulses, never written; skipped at fx 0 where the stage is a static frame), the chain ribbon (RIBBON: a 2D strip always; the same tiles
   projected onto the stage floor through the instance's projectPoint at fx ≥ 1), the picker of the repaired-and-valid scenes sorted by diff size (worker
   repairStats), R = replay 0 → 1 over 4 s.
   Canvases: lazily created STAGE.show2 instances on reveal (IO), disposed 2.5 s after leave. fx ≥ 1 and ≥ 600 px: two instances (attempt 1 on top, cameras
   locked by copying the active pose each frame), both staged (§5 rig, no orbit). fx 0 / phone: ONE instance (the final) and a snapshot <img> of attempt 1
   taken from the same instance (the measured 192×144 frame scaled, labelled, while that snapshot renders).
   Globals: MORPH {open(ref), scrub(t), mode(m), replay(), pulse(i), lock(on), cur(), items(), state}, DIFF {tagLines, LCSdiff, diffRows, diffHtml, repairStats,
   diffAsync, repairStatsAsync, status()}, RIBBON {make(host, opts) → {el, set(steps), stamp(i), setT(t), steps, tiles}}, OPCOL.
   Claims: morph.repaired (expected STATS.LIVESTATS.rep), morph.repairStats (no baked value: pending → earned; median changed tag lines, scenes rewritten > ½).
   v3 port (WORKPLAN §A): tagLines, LCSdiff, diffHtml (demo/tether-firehose-v3.template.html 600–615), repairStats (616–620, now over explicit pairs and in the
   worker), OPCOL (574). Test hooks: __morph {cur, t, mode, lock, items, order, diff, steps, inst:{top,bot}, snapshot, pulses, loads, stats, replay, visible},
   MORPH.open("L-003" | LIVE index | "model/prompt_aK.x3d" | {m,p}). Keys: R replays while the section is on screen (never inside an input). */
(function(){
"use strict";
const OPCOL={generate:"p-info",validate:"p-ok",repair:"p-warn",render:"p-mute",transform:"p-info",ingest:"p-mute",measure:"p-acc",judge:"p-ok",summary:"p-mute"};
const OPTOK={"p-info":"--info","p-ok":"--ok","p-warn":"--warn","p-mute":"--mute","p-acc":"--acc"};
/* ---------- DIFF: one tag per line (the unit a reader compares), LCS over lines, two lines of context (v3 600–620) ---------- */
const tagLines=x=>String(x).replace(/\r/g,"").replace(/>\s*</g,">\n<").split("\n");
function LCSdiff(a,b){const n=a.length,m=b.length,w=m+1,t=new Uint16Array((n+1)*w);
  for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)t[i*w+j]=a[i]===b[j]?t[(i+1)*w+j+1]+1:Math.max(t[(i+1)*w+j],t[i*w+j+1]);
  const o=[];let i=0,j=0;while(i<n&&j<m){if(a[i]===b[j]){o.push([" ",a[i]]);i++;j++}else if(t[(i+1)*w+j]>=t[i*w+j+1])o.push(["-",a[i++]]);else o.push(["+",b[j++]])}
  while(i<n)o.push(["-",a[i++]]);while(j<m)o.push(["+",b[j++]]);return o}
/* rows: [sign, text, i] with sign " " | "+" | "-" | "…" (a gap) | "~" (the "N more" line); i = index in the full diff */
function diffRows(a,b,maxShown){const d=LCSdiff(tagLines(a),tagLines(b)),keep=new Array(d.length).fill(false),add=d.filter(r=>r[0]==="+").length,del=d.filter(r=>r[0]==="-").length;
  d.forEach((r,i)=>{if(r[0]!==" ")for(let k=Math.max(0,i-2);k<=Math.min(d.length-1,i+2);k++)keep[k]=true});
  const rows=[];let gap=false,shown=0,seen=0;maxShown=maxShown||100;
  for(let i=0;i<d.length;i++){if(!keep[i]){gap=true;continue}
    if(shown>=maxShown){rows.push(["~",String(add+del-seen),i]);break}
    if(gap&&rows.length)rows.push(["…","",i]);gap=false;shown++;if(d[i][0]!==" ")seen++;rows.push([d[i][0],d[i][1].slice(0,220),i])}
  return{add,del,base:tagLines(a).length,rows,total:d.length}}
function diffHtml(a,b){const r=diffRows(a,b,100);const html=r.rows.map(([s,t])=>s==="~"?`<span class="g">… ${esc(t)} more changed lines not shown</span>`:s==="…"?'<span class="g">  …</span>':`<span class="${s==="+"?"a":s==="-"?"d":"c"}">${s} ${esc(t)}</span>`).join("\n");return{html,add:r.add,del:r.del,base:r.base}}
function repairStats(pairs){const per=[],ch=[],fr=[],med=x=>{x=x.slice().sort((p,q)=>p-q);return x.length?x[x.length>>1]:0};
  for(const p of pairs){const a=tagLines(p.a),d=LCSdiff(a,tagLines(p.b)),changed=d.filter(r=>r[0]!==" ").length,add=d.filter(r=>r[0]==="+").length,del=d.filter(r=>r[0]==="-").length,frac=changed/Math.max(1,a.length);
    per.push({id:p.id,changed,base:a.length,frac,add,del});ch.push(changed);fr.push(frac)}
  return{stats:{n:ch.length,med:med(ch),frac:med(fr),big:fr.filter(f=>f>.5).length},per}}
/* the worker client: one own-file worker, created on first need; refused (CSP worker-src 'none') → the same functions on the main thread */
let W=null,wFail=false,wid=0;const pend=new Map();
function worker(){if(W||wFail)return W;try{W=new Worker("workers/diff.worker.js");
    W.onmessage=e=>{const d=e.data||{},p=pend.get(d.id);if(!p)return;pend.delete(d.id);if(d.error)p.rej(new Error(d.error));else p.res(d)};
    W.onerror=e=>{wFail=true;const err=new Error("diff worker: "+String(e&&e.message||"error").slice(0,120));pend.forEach(p=>p.rej(err));pend.clear();try{W.terminate()}catch(x){}W=null}}
  catch(e){wFail=true;W=null}return W}
function call(msg,timeoutMs){const w=worker();if(!w)return Promise.reject(new Error("no diff worker"));
  return new Promise((res,rej)=>{const id=++wid;pend.set(id,{res,rej});w.postMessage(Object.assign({id},msg));later(()=>{if(pend.has(id)){pend.delete(id);rej(new Error("diff worker timeout"))}},timeoutMs||20000)})}
async function diffAsync(a,b,maxShown){a=String(a||"");b=String(b||"");const n=tagLines(a).length+tagLines(b).length;
  if(n>400&&!wFail){try{const r=await call({type:"diff",a,b,maxShown});return{rows:r.rows,add:r.add,del:r.del,base:r.base,total:r.total,via:"worker"}}catch(e){}}
  return Object.assign(diffRows(a,b,maxShown),{via:"main"})}
async function repairStatsAsync(pairs){if(!wFail){try{const r=await call({type:"repairStats",pairs},40000);return{stats:r.stats,per:r.per,via:"worker"}}catch(e){}}
  const per=[],q=pairs.slice();await new Promise(res=>{const step=()=>{const t0=performance.now();while(q.length&&performance.now()-t0<8)per.push(repairStats([q.shift()]).per[0]);if(q.length)later(step,0);else res()};later(step,0)});
  const ch=per.map(p=>p.changed),fr=per.map(p=>p.frac),med=x=>{x=x.slice().sort((p,q)=>p-q);return x.length?x[x.length>>1]:0};
  return{stats:{n:ch.length,med:med(ch),frac:med(fr),big:fr.filter(f=>f>.5).length},per,via:"main"}}
const DIFF={tagLines,LCSdiff,diffRows,diffHtml,repairStats,diffAsync,repairStatsAsync,status:()=>wFail?"main thread (worker refused)":W?"worker":"idle"};
/* ---------- RIBBON: the chain as tiles, colour by op; stamp in as the slider crosses each step; prev-hash links (dashed until the chain is built) ---------- */
const RIBBON={make(host,opts){opts=opts||{};const root=el("div",{class:"ribbon"});host.appendChild(root);
  const R={el:root,steps:[],tiles:[],links:[],t:1,cur:-1,
    set(steps){R.steps=steps||[];root.textContent="";R.tiles=[];R.links=[];
      R.steps.forEach((s,i)=>{if(i){const l=el("i",{class:"rlink"+(s.chain?"":" dash")});R.links.push(l);root.appendChild(l)}
        const tl=el("span",{class:"rtile pill "+(OPCOL[s.op]||"p-mute"),text:`${i+1} ${String(s.op||"?").toUpperCase()}`,data:{i:String(i)},title:s.chain?"a step of the verified chain":"recorded facts: the chain builds when the run clock reaches this scene",
          onmouseenter:()=>{if(opts.onHover)opts.onHover(s,i)},onmouseleave:()=>{if(opts.onHover)opts.onHover(null,-1)},onclick:()=>{if(opts.onClick)opts.onClick(s,i)}});R.tiles.push(tl);root.appendChild(tl)});
      if(opts.note){const n=opts.note(R.steps);if(n)root.appendChild(el("span",{class:"rnote",text:n}))}R.setT(R.t)},
    setT(t){R.t=t;const n=R.steps.length;R.tiles.forEach((tl,i)=>tl.classList.toggle("on",n<=1||i/(n-1)<=t+1e-9));R.links.forEach((l,i)=>l.classList.toggle("on",n<=1||(i+1)/(n-1)<=t+1e-9))},
    stamp(i){R.cur=i;R.tiles.forEach((tl,k)=>{tl.classList.toggle("cur",k===i);if(k<=i)tl.classList.add("on")})}};
  return R}};
/* ---------- the section ---------- */
const E={},ST={cur:null,t:0,mode:"wipe",lock:true,top:null,bot:null,gen:0,loads:0,snapshot:null,diff:null,steps:[],sc:null,replay:null,pulses:0,visible:false,leave:null,items:[],order:[],stats:null,per:null,bbox:null,pulsed:false,shapes:null,active:"top",drag:false,port:null};
const __morph={cur:null,t:0,mode:"wipe",lock:true,items:0,order:[],diff:null,steps:[],inst:{top:null,bot:null},snapshot:null,pulses:0,loads:0,stats:null,replay:null,visible:false,via:null};
let RIB=null,sec=null;
const short=m=>String(m).replace(/^.*\//,"");
const laneName=m=>{if(!(self.BUILD&&BUILD.share))return short(m);const paid=((self.LM||STATS.meta||{}).models||[]).filter(x=>x.prov!=="nvidia").map(x=>x.id);const i=paid.indexOf(m);return i>=0?"closed-"+"ABCDEF"[i]:"open-"+(((self.LM||STATS.meta||{}).models||[]).findIndex(x=>x.id===m)+1)};
const twoUp=()=>!!(self.FX&&FX.level>0&&innerWidth>=600);
const fin=it=>it.A[it.A.length-1];
const items=()=>(self.LIVE||[]).filter(i=>i.A.length>1&&fin(i).ok);
const finding=a=>{const l=(a&&((a.xe&&a.xe[0])||(a.se&&a.se[0])))||"";return l.replace(/^-\s*/,"").replace(/\*\*/g,"").replace(/\s+/g," ").trim()};
function hexRgb(h){const m=/^#?([0-9a-f]{6})$/i.exec(String(h||"").trim());if(!m)return[.22,.78,.83];const n=parseInt(m[1],16);return[(n>>16&255)/255,(n>>8&255)/255,(n&255)/255]}
function resolve(ref){if(ref==null)return null;if(typeof ref==="object"&&ref.A)return ref;if(typeof ref==="number")return(self.LIVE||[])[ref]||null;
  if(typeof ref==="object")return(self.LIVE||[]).find(i=>i.m===ref.m&&i.p===ref.p)||null;
  const s=String(ref);if(/^L-\d+$/.test(s)){const sc=self.S&&S.byId.get(s);return sc&&sc.item||null}
  const m=/^(.+)\/([\w-]+?)(?:_a\d+)?(?:\.x3d)?$/.exec(s);if(m)return(self.LIVE||[]).find(i=>String(i.m).replace("/","_")===m[1]&&i.p===m[2])||null;return null}
function headerSpec(){const gl=self.ENV&&ENV.gl;const rend=gl==="gpu"?"X_ITE 16.5.0 in this browser · gpu":gl==="software"?"X_ITE 16.5.0 in this browser · software":"none";
  const rep=(self.LIVESTATS&&LIVESTATS.rep)||(self.STATS&&STATS.LIVESTATS&&STATS.LIVESTATS.rep);
  return{title:"The repair morph",unit:`attempt 1 → final · ${rep!=null?fmt.int(rep)+" repaired-and-valid scenes":"the repaired-and-valid scenes"} · the diff computed here`,stamps:{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:rend},grade:"C",
    honesty:"attempt bodies as recorded · verdicts fork@eb4b4b4 recorded and js-port-of-8dd0d3e re-run here (shown when it differs) · diff computed in this page · staged renders · counted frames pinned right · Confirmed for this scene"}}
/* ---- the stage instances ---- */
function ensureInst(){if(!self.STAGE||!STAGE.show2||!self.X3D)return false;let made=false;
  if(!ST.bot){ST.bot=STAGE.show2(E.bot,{name:"morph-final"});__morph.inst.bot=ST.bot;made=true}
  if(twoUp()&&!ST.top){ST.top=STAGE.show2(E.top,{name:"morph-a1"});__morph.inst.top=ST.top;E.top.hidden=false;made=true}
  if(made&&ST.cur)loadCur();return made}
function disposeInst(){[ST.top,ST.bot].forEach(i=>{if(i)try{i.dispose()}catch(e){}});ST.top=ST.bot=null;__morph.inst.top=__morph.inst.bot=null;ST.shapes=null;ST.bbox=null;E.top.hidden=true;E.snap.hidden=true;ST.snapshot=null;__morph.snapshot=null;txt(E.tagC,"stage disposed off screen")}
const bodies=it=>it&&it.B&&it.B.length>=it.A.length?{a:it.B[0],b:it.B[it.B.length-1]}:null;
async function loadCur(){const it=ST.cur,bb=bodies(it);if(!it||!bb||!ST.bot)return;const gen=++ST.gen;ST.bbox=null;ST.shapes=null;txt(E.note,"");
  if(ST.top){const [r1,r0]=await Promise.all([ST.bot.load(bb.b,{staged:true,orbit:false,scene:"morph-final"}),ST.top.load(bb.a,{staged:true,orbit:false,scene:"morph-a1"})]);if(gen!==ST.gen)return;
    ST.loads++;__morph.loads=ST.loads;txt(E.tagC,ST.bot.label());if(!r1.ok||!r0.ok)txt(E.note,(r0.err||r1.err||"")+"");ST.bbox=ST.bot.bbox();hookActive();return}
  /* one instance: the final stays loaded; attempt 1 is a snapshot of the same instance (the measured frame, scaled, until it renders) */
  const a0=it.A[0],jpg=a0.r&&a0.r.jpg;E.snap.hidden=false;ST.snapshot=jpg?"measured":null;__morph.snapshot=ST.snapshot;
  if(jpg)E.snap.src="data:image/jpeg;base64,"+jpg;else E.snap.removeAttribute("src");
  txt(E.note,"attempt 1 shown as its measured 192×144 frame (scaled) while the live snapshot renders · one X_ITE instance at fx 0");
  const r0=await ST.bot.load(bb.a,{staged:false,scene:"morph-a1"});if(gen!==ST.gen)return;
  if(r0.ok){await later(700);if(gen!==ST.gen)return;const url=await ST.bot.snapshot("image/jpeg");if(gen!==ST.gen)return;if(url){E.snap.src=url;ST.snapshot="live";__morph.snapshot="live";txt(E.note,"attempt 1: a live snapshot of this instance (raw bytes, no rig) · final: live · one X_ITE instance at fx 0")}}
  const r1=await ST.bot.load(bb.b,{staged:false,scene:"morph-final"});if(gen!==ST.gen)return;ST.loads++;__morph.loads=ST.loads;txt(E.tagC,ST.bot.label());if(!r1.ok)txt(E.note,r1.err||"");ST.bbox=ST.bot.bbox()}
function hookActive(){[["top",E.top],["bot",E.bot]].forEach(([k,host])=>{if(host.dataset.hooked)return;host.dataset.hooked="1";host.addEventListener("pointerdown",()=>{ST.active=k},{passive:true})})}
/* ---- the wipe / crossfade ---- */
function applyT(){const t=ST.t;__morph.t=t;txt(E.tv,Math.round(t*100)+"%");if(+E.range.value!==t)E.range.value=String(t);
  const top=ST.top?E.top:E.snap;const other=ST.top?E.snap:E.top;other.style.clipPath="";
  if(ST.mode==="wipe"){top.style.clipPath=`inset(0 ${(t*100).toFixed(2)}% 0 0)`;top.style.opacity="";E.div.hidden=false;E.div.style.left=((1-t)*100).toFixed(2)+"%"}
  else{top.style.clipPath="";top.style.opacity=String(1-t);E.div.hidden=true}
  renderHead();if(RIB)RIB.setT(t);if(t>=.5&&!ST.pulsed){ST.pulsed=true;if(twoUp())pulseChanged()}}
function renderHead(){const it=ST.cur;if(!it){txt(E.h3,"pick a repaired scene from the strip below");E.vl.textContent="";return}
  const a0=it.A[0],f=fin(it),past=ST.t>=.5,d=ST.diff;E.h3.classList.toggle("ok",past);
  if(!past){txt(E.h3,finding(a0)||"invalid on fork@eb4b4b4 (no finding line recorded)");E.vl.textContent="";codesOf(a0).forEach(c=>E.vl.appendChild(el("span",{class:"pill p-bad",text:c})));
    E.vl.appendChild(el("span",{text:`INVALID on fork@eb4b4b4 in ${fmt.int(a0.vms)} ms · attempt 1 of ${it.A.length} · ${it.p} · ${laneName(it.m)}`}))}
  else{txt(E.h3,`VALID on fork@eb4b4b4 in ${fmt.int(f.vms)} ms`);E.vl.textContent="";
    E.vl.appendChild(el("span",{text:d?`+${d.add} −${d.del} tag lines of ${d.base} · ${fmt.pct((d.add+d.del)/Math.max(1,d.base),0)} of the scene`:bodies(it)?"diff: computing…":"diff arrives with part live.bodies"}));
    E.vl.appendChild(el("span",{text:`· after ${it.A.length-1} repair${it.A.length>2?"s":""} · the model was sent its own report (${fmt.int(a0.rl)} characters)`}));
    if(ST.port)E.vl.appendChild(el("span",{class:"pill "+(ST.port.cmp==="agrees"?"p-ok":"p-warn"),text:`js-port-of-8dd0d3e re-run here: ${ST.port.cmp}`,title:ST.port.detail||""}))}}
/* ---- diff pane and node pulse ---- */
function renderDiff(r){E.df.textContent="";r.rows.forEach(([s,t,i])=>{const cls=s==="+"?"a":s==="-"?"d":s===" "?"c":"g";const text=s==="~"?`… ${t} more changed lines not shown`:s==="…"?"  …":`${s} ${t}`;
    const sp=el("span",{class:cls,text,data:{i:String(i),s}});if(cls==="a"||cls==="d"){sp.title="click: pulse this node on the final canvas (render-time, never written)";sp.addEventListener("click",()=>MORPH.pulse(i))}E.df.appendChild(sp)});
  txt(E.dsum,`+${r.add} −${r.del} tag lines of ${r.base} · ${fmt.pct((r.add+r.del)/Math.max(1,r.base),0)} of the scene · diff ${r.via==="worker"?"in workers/diff.worker.js":"on the main thread"} · one tag per line, two lines of context`)}
function shapeList(inst){if(ST.shapes)return ST.shapes;const out=[];try{const sc=inst.browser.currentScene,C=self.X3D.X3DConstants,seen=new Set();
    const walk=(n,d)=>{if(!n||d>14||seen.has(n))return;seen.add(n);let t="";try{t=n.getNodeTypeName()}catch(e){return}if(t==="Shape"){out.push(n);return}
      if(t==="Appearance"||t==="Material"||/Interpolator$|Sensor$|^Metadata|Viewpoint$|Light$/.test(t))return;
      for(const f of n.getFieldDefinitions()){if(f.name==="appearance"||f.name==="geometry")continue;if(f.dataType===C.SFNode){try{const c=n[f.name];if(c)walk(c,d+1)}catch(e){}}else if(f.dataType===C.MFNode){try{for(const c of n[f.name])walk(c,d+1)}catch(e){}}}};
    for(const n of sc.rootNodes)walk(n,0)}catch(e){}ST.shapes=out;return out}
function materialsOf(node,out){try{const t=node.getNodeTypeName();if(/Material$/.test(t)){out.push(node);return}if(t==="Shape"){const ap=node.appearance,m=ap&&ap.material;if(m)out.push(m);return}
    const C=self.X3D.X3DConstants;for(const f of node.getFieldDefinitions()){if(out.length>8)break;if(f.dataType===C.SFNode){const c=node[f.name];if(c)materialsOf(c,out)}else if(f.dataType===C.MFNode){for(const c of node[f.name]){if(out.length>8)break;materialsOf(c,out)}}}}catch(e){}return out}
/* a changed tag line → the Material(s) to pulse: by DEF name through getNamedNode, else by Shape order in the final body */
function targetsOf(lineText,sign){const inst=ST.bot;if(!inst||!inst.ok||!ST.cur)return[];const bb=bodies(ST.cur);if(!bb)return[];const out=[];
  const def=/\bDEF=['"]([^'"]+)['"]/.exec(lineText||"");if(def){try{const n=inst.browser.currentScene.getNamedNode(def[1]);if(n)materialsOf(n,out)}catch(e){}if(out.length)return out}
  const lines=tagLines(sign==="-"?bb.a:bb.b);let idx=lines.indexOf(lineText);if(idx<0)idx=lines.findIndex(l=>l.startsWith(lineText.slice(0,40)));if(idx<0)return out;
  let k=-1;for(let i=0;i<=idx;i++)if(/^<Shape\b/.test(lines[i]))k++;if(k<0){for(let i=idx+1;i<lines.length;i++)if(/^<Shape\b/.test(lines[i])){k=0;break}}
  const shapes=shapeList(inst);const sh=k>=0?shapes[Math.min(k,shapes.length-1)]:null;if(sh)materialsOf(sh,out);return out}
function pulseMats(mats){if(!mats.length||!self.X3D)return 0;const inst=ST.bot;if(!inst||!inst.ok)return 0;if(inst.frozen)inst.resume();const c=hexRgb(cssv("--acc"));
  const orig=mats.map(m=>{try{const e=m.emissiveColor;return[+e.r||0,+e.g||0,+e.b||0]}catch(e){return[0,0,0]}});
  const on=()=>mats.forEach(m=>{try{m.emissiveColor=new X3D.SFColor(c[0],c[1],c[2])}catch(e){}}),off=()=>mats.forEach((m,i)=>{try{m.emissiveColor=new X3D.SFColor(orig[i][0],orig[i][1],orig[i][2])}catch(e){}});
  on();later(off,600);later(on,1200);later(()=>{off();if(self.FX&&FX.level===0)inst.freezeSoon(inst.token)},1800);ST.pulses++;__morph.pulses=ST.pulses;return mats.length}
function pulseChanged(){const d=ST.diff;if(!d)return 0;const mats=[];const seen=new Set();d.rows.forEach(([s,t])=>{if(s!=="+"&&s!=="-")return;targetsOf(t,s).forEach(m=>{if(!seen.has(m)){seen.add(m);mats.push(m)}})});
  const n=pulseMats(mats.slice(0,12));txt(E.note,n?`${n} node${n>1?"s":""} pulsed on the final canvas: emissiveColor at render time, nothing written`:(self.FX&&FX.level===0?"node pulse skipped at fx 0 (static frame)":"no node matched the changed lines"));return n}
/* ---- ribbon steps: the verified chain when the clock has built it, else the recorded facts ---- */
function stepsOf(it){const id=self.S&&S.liveIds&&S.liveIds.get(it.i),sc=id&&S.byId.get(id);ST.sc=sc||null;
  if(sc){const st=readSteps(sc.xml);if(st.length)return st.map(([n,c])=>{let op="?";try{op=JSON.parse(c).op}catch(e){}return{n,op,json:c,chain:true,id:sc.id}})}
  const out=[];it.A.forEach((a,k)=>{out.push({n:out.length+1,op:k?"repair":"generate",chain:false,facts:{model:it.m,prompt_id:it.p,tokens_in:a.ti,tokens_out:a.to,latency_ms:a.ms,cost_usd_est:a.u,finish:a.fin,round:k||undefined,report_shown:k?true:undefined}});
    out.push({n:out.length+1,op:"validate",chain:false,facts:{validator_ref:"fork@eb4b4b4",verdict:a.ok?"valid":"invalid",codes:codesOf(a),ms:a.vms,ms_src:"measured"}})});
  const f=fin(it);out.push({n:out.length+1,op:"render",chain:false,facts:{renderer:"x_ite@16.5.0 headless swiftshader (offline)",nonblank_ratio:f.r&&f.r.nb,frames_watched:f.r&&f.r.frames,nodes:f.r&&f.r.nodes}});return out}
function ribbonNote(steps){if(!steps.length)return"";if(steps[0].chain)return`chain ${steps[0].id} · ${steps.length} steps · hover a tile for its JSON`;const it=ST.cur;return`recorded facts · the hash chain builds when the run clock reaches ${it?fmt.clock(it.T):"this scene"}`}
function onRibbonHover(s){if(!s){E.rjson.textContent="";return}let o;if(s.json){try{o=JSON.parse(s.json)}catch(e){o={raw:s.json}}}else o=Object.assign({op:s.op,note:"recorded facts; the chain step is written when the run clock reaches this scene"},s.facts);
  txt(E.rjson,`step ${s.n} ${String(s.op).toUpperCase()}\n`+JSON.stringify(o,null,1))}
/* projected floor ribbon (fx ≥ 1): the same tiles drawn on the overlay canvas through the final instance's projectPoint; cleared when a point is behind the camera */
function drawFloor(){const cv=E.cv;const inst=ST.bot;const n=ST.steps.length;
  if(!twoUp()||!inst||!inst.ok||!n||!ST.bbox||ST.bbox.empty){if(cv.dataset.on==="1"){cv.dataset.on="0";const w=E.stage.clientWidth,h=E.stage.clientHeight;fitCanvas(cv,w,h).ctx.clearRect(0,0,w,h)}return}
  const w=E.stage.clientWidth,h=E.stage.clientHeight;   /* layout is read only when the overlay is live (fx ≥ 1, two instances) */
  const bb=ST.bbox,ext=Math.max(...bb.size)||1,sp=ext*.32,pts=[],y=bb.min[1],z=bb.max[2]+ext*.18;
  for(let i=0;i<n;i++){const p=inst.project([bb.center[0]+(i-(n-1)/2)*sp,y,z]);if(!p||p.behind||!Number.isFinite(p.x)||!Number.isFinite(p.y)){if(cv.dataset.on==="1"){cv.dataset.on="0";fitCanvas(cv,w,h).ctx.clearRect(0,0,w,h)}return}pts.push(p)}
  const key=pts.map(p=>(p.x|0)+","+(p.y|0)).join(";")+"|"+ST.t.toFixed(3)+"|"+w+"x"+h;if(cv.dataset.key===key)return;cv.dataset.key=key;cv.dataset.on="1";
  const{ctx}=fitCanvas(cv,w,h);ctx.clearRect(0,0,w,h);ctx.strokeStyle=cssv("--acc");ctx.lineWidth=1;ctx.globalAlpha=.7;ctx.beginPath();pts.forEach((p,i)=>{if(i)ctx.lineTo(p.x,p.y);else ctx.moveTo(p.x,p.y)});ctx.stroke();
  ctx.font="600 10px "+cssv("--mono");ctx.textAlign="center";ctx.textBaseline="middle";
  pts.forEach((p,i)=>{const s=ST.steps[i],on=n<=1||i/(n-1)<=ST.t+1e-9,tok=OPTOK[OPCOL[s.op]||"p-mute"]||"--mute";ctx.globalAlpha=on?.95:.3;ctx.fillStyle=cssv("--p1");ctx.fillRect(p.x-24,p.y-8,48,16);ctx.strokeStyle=cssv(tok);ctx.strokeRect(p.x-24+.5,p.y-8+.5,47,15);ctx.fillStyle=cssv(tok);ctx.fillText(`${i+1} ${String(s.op).toUpperCase().slice(0,8)}`,p.x,p.y+.5)});ctx.globalAlpha=1}
/* ---- pins, picker ---- */
function pin(it,k){const a=it.A[k],key=keyOf(it.m,it.p,k+1),r1=self.R151&&R151.live&&R151.live[key]||null,jpg=a.r&&a.r.jpg;
  return el("div",{class:"pin m"},[el("span",{class:"fr "+(a.ok?"v":"i")},jpg?el("img",{src:"data:image/jpeg;base64,"+jpg,alt:`measured frame, attempt ${k+1}`,width:"96",height:"72"}):el("span",{class:"nf",text:a.r&&a.r.err?"X_ITE could not parse this attempt":"frame arrives with part live.jpg"})),
    el("div",null,[el("b",{text:`${k===0?"attempt 1":"final · attempt "+(k+1)} · ${a.ok?"VALID":"INVALID"}`}),` on fork@eb4b4b4 · ${fmt.int(a.vms)} ms`]),
    el("div",{text:`16.5.0 offline: ${a.r&&!a.r.err&&a.r.nb!=null?fmt.pct(a.r.nb,1):"—"} · 16.5.1 offline: ${r1?(r1.err?"could not parse":fmt.pct(r1.nb,1)):"no record"}`}),
    el("div",{text:"192×144 counted frame · the morph is never the evidence"})])}
function renderPins(){E.pins.textContent="";const it=ST.cur;if(!it)return;E.pins.appendChild(pin(it,0));E.pins.appendChild(pin(it,it.A.length-1))}
function buildPicker(){const list=items();ST.items=list;__morph.items=list.length;const stat=it=>ST.per&&ST.per.has(it.i)?ST.per.get(it.i).changed:-1;
  const order=list.slice().sort((x,y)=>ST.per?(stat(y)-stat(x)||x.i-y.i):(y.A.length-x.A.length||x.i-y.i));ST.order=order;__morph.order=order.map(i=>i.i);
  E.strip.textContent="";order.forEach(it=>{const f=fin(it),jpg=f.r&&f.r.jpg;const b=el("button",{class:"th "+(f.ok?"v":"i")+(ST.cur===it?" sel":""),type:"button",title:`${it.p} · ${laneName(it.m)} · ${it.A.length} calls${ST.per&&ST.per.has(it.i)?" · "+ST.per.get(it.i).changed+" tag lines changed":""}`,data:{i:String(it.i)},onclick:()=>MORPH.open(it.i)},
      [jpg?el("img",{src:"data:image/jpeg;base64,"+jpg,alt:"",loading:"lazy",width:"96",height:"72"}):el("span",{class:"nj",text:f.r&&f.r.err?"no frame":"jpg pending"}),el("span",{class:"lbl",text:`${it.p} · ${laneName(it.m)}${ST.per&&ST.per.has(it.i)?" · "+ST.per.get(it.i).changed:""}`})]);E.strip.appendChild(b)});
  E.ph.textContent="";E.ph.appendChild(claimChip("morph.repaired",{size:"s",label:"repaired-and-valid scenes"}));E.ph.appendChild(el("span",{text:ST.stats?`· sorted by changed tag lines (first attempt vs final) ·`:"· sorted by calls until the diff worker sorts by diff size ·"}));E.ph.appendChild(claimChip("morph.repairStats",{size:"s",label:"median changed · rewrote more than half"}))}
async function computeStats(){const list=items().filter(it=>bodies(it));if(!list.length||ST.statsP)return;ST.statsP=true;
  const r=await repairStatsAsync(list.map(it=>({id:it.i,a:it.B[0],b:it.B[it.B.length-1]})));ST.stats=r.stats;ST.per=new Map(r.per.map(p=>[p.id,p]));__morph.stats=r.stats;__morph.via=r.via;buildPicker();CLAIMS.run("morph.repairStats");CLAIMS.run("morph.repaired")}
/* ---- the port verdict (shown when it differs): only when the js-port is already loaded, never pulls it in ---- */
function portCheck(it){ST.port=null;if(!(self.VAL&&VAL.mode==="full")||!bodies(it))return;const f=fin(it);VAL.validate(it.B[it.B.length-1]).then(res=>{if(ST.cur!==it)return;const cmp=VAL.compare(res,!!f.ok,codesOf(f));ST.port={cmp,detail:cmp==="agrees"?"valid on both":`port says ${res.valid?"valid":"invalid"} · codes ${codesOfRes(res).join(",")||"none"}`};renderHead()}).catch(()=>{})}
/* ---- open ---- */
function open(ref){const it=resolve(ref);if(!it)return null;ST.cur=it;__morph.cur=it;ST.gen++;ST.t=0;ST.pulsed=false;ST.diff=null;__morph.diff=null;ST.replay=null;ST.bbox=null;ST.shapes=null;E.df.textContent="";
  txt(E.tagL,`ATTEMPT 1 · ${fin(it)===it.A[0]?"":"INVALID"}`);txt(E.tagR,`FINAL · attempt ${it.A.length} · VALID`);renderPins();
  const bb=bodies(it);if(bb){txt(E.dsum,"diff: computing…");diffAsync(bb.a,bb.b,120).then(r=>{if(ST.cur!==it)return;ST.diff=r;__morph.diff=r;renderDiff(r);renderHead()})}else txt(E.dsum,"diff arrives with part live.bodies");
  ST.steps=stepsOf(it);__morph.steps=ST.steps;if(RIB)RIB.set(ST.steps);E.rjson.textContent="";portCheck(it);applyT();
  E.strip.querySelectorAll("button.th").forEach(b=>b.classList.toggle("sel",+b.dataset.i===it.i));
  if(ST.visible)ensureInst();if(ST.bot)loadCur();return it}
const MORPH={open,cur:()=>ST.cur,items,state:ST,
  scrub(t){ST.t=UTIL.clamp(+t||0,0,1);applyT();return ST.t},
  mode(m){ST.mode=m==="crossfade"?"crossfade":"wipe";__morph.mode=ST.mode;E.seg.querySelectorAll("button").forEach(b=>b.classList.toggle("on",b.dataset.m===ST.mode));applyT();return ST.mode},
  replay(){ST.replay={t0:performance.now(),ms:4000};__morph.replay=ST.replay;ST.pulsed=false;return true},
  pulse(i){const d=ST.diff;if(!d)return 0;const row=d.rows.find(r=>r[2]===i)||d.rows[i];if(!row||(row[0]!=="+"&&row[0]!=="-"))return 0;const n=pulseMats(targetsOf(row[1],row[0]).slice(0,8));txt(E.note,n?`${n} node${n>1?"s":""} pulsed for the clicked line`:(self.FX&&FX.level===0?"node pulse skipped at fx 0 (static frame)":"no node matched that line"));return n},
  lock(on){ST.lock=!!on;__morph.lock=ST.lock;E.bLock.classList.toggle("on",ST.lock);return ST.lock},
  close(){disposeInst()}};
function mount(s){sec=s;sectionHeader(sec,headerSpec());const sb=sec.querySelector(".sb");if(!sb)return;sb.textContent="";
  E.h3=el("h3",{text:"pick a repaired scene from the strip below"});E.vl=el("div",{class:"vl"});E.head=el("div",{class:"mhead"},[E.h3,E.vl]);
  E.bot=el("div",{class:"mlayer bot"});E.top=el("div",{class:"mlayer top",hidden:""});E.snap=el("img",{class:"msnap",alt:"attempt 1",hidden:""});E.div=el("div",{class:"mdiv",role:"separator","aria-label":"wipe divider",title:"drag"});
  E.cv=el("canvas",{class:"mribbonCv"});E.tagL=el("div",{class:"mtag l m",text:"ATTEMPT 1"});E.tagR=el("div",{class:"mtag r m",text:"FINAL"});E.tagC=el("div",{class:"mtag c m",text:"stage created when this section scrolls into view"});E.note=el("div",{class:"mnote m"});
  E.stage=el("div",{class:"mstage"},[E.bot,E.top,E.snap,E.div,E.cv,E.tagL,E.tagR,E.tagC,E.note]);
  E.seg=el("span",{class:"seg"},[el("button",{text:"WIPE",data:{m:"wipe"},class:"on",onclick:()=>MORPH.mode("wipe")}),el("button",{text:"CROSSFADE",data:{m:"crossfade"},onclick:()=>MORPH.mode("crossfade")})]);
  E.range=el("input",{type:"range",min:"0",max:"1",step:"0.005",value:"0","aria-label":"repair scrub: attempt 1 to final",oninput:e=>MORPH.scrub(+e.target.value)});E.tv=el("span",{class:"t m",text:"0%"});
  E.bReplay=el("button",{text:"Replay (R)",onclick:()=>MORPH.replay()});E.bLock=el("button",{class:"on",text:"Camera lock",title:"copy the active canvas' pose to the other each frame (fx ≥ 1)",onclick:()=>MORPH.lock(!ST.lock)});E.bPulse=el("button",{text:"Pulse changed nodes",onclick:()=>pulseChanged()});
  E.ctl=el("div",{class:"mctl"},[E.seg,E.range,E.tv,E.bReplay,E.bLock,E.bPulse]);
  E.ribbonHost=el("div");E.rjson=el("div",{class:"rjson m"});
  E.pins=el("div",{class:"pins"});E.dsum=el("div",{class:"dsum"});E.df=el("div",{class:"df m","aria-label":"tag-line diff"});E.side=el("div",{class:"mside"},[E.pins,E.dsum,E.df]);
  E.ph=el("div",{class:"ph"});E.strip=el("div",{class:"strip"});E.picker=el("div",{class:"mpicker"},[E.ph,E.strip]);
  sb.append(E.head,el("div",{class:"mwrap"},[el("div",{class:"mleft"},[E.stage,E.ctl,E.ribbonHost,E.rjson]),E.side]),E.picker);
  RIB=RIBBON.make(E.ribbonHost,{onHover:onRibbonHover,note:ribbonNote,onClick:(s,i)=>{RIB.stamp(i);onRibbonHover(s)}});
  /* divider drag */
  E.div.addEventListener("pointerdown",e=>{ST.drag=true;try{E.div.setPointerCapture(e.pointerId)}catch(x){}e.preventDefault()});
  E.div.addEventListener("pointermove",e=>{if(!ST.drag)return;const r=E.stage.getBoundingClientRect();MORPH.scrub(1-(e.clientX-r.left)/Math.max(1,r.width))});
  const up=()=>{ST.drag=false};E.div.addEventListener("pointerup",up);E.div.addEventListener("pointercancel",up);
  /* observed on the stage box, not the section: IO keeps one callback per element and the LOOP panel below observes the section */
  IO.observe(E.stage,v=>{ST.visible=v;__morph.visible=v;if(v){if(ST.leave){ST.leave();ST.leave=null}ensureInst()}else{if(ST.leave)ST.leave();ST.leave=later(()=>{ST.leave=null;if(!ST.visible)disposeInst()},2500)}},{rootMargin:"64px"});
  document.addEventListener("keydown",e=>{if(e.target&&/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))return;if((e.key==="r"||e.key==="R")&&ST.visible&&ST.cur)MORPH.replay()});
  if(self.FX)FX.onChange(()=>{if(ST.visible&&ST.bot){disposeInst();ensureInst()}});
  LOOP.register({name:"morph",bit:LOOP.bits.CLOCK,always:true,rateHz:30,budgetMs:3,el:sec,draw(now){
    if(ST.visible&&!ST.bot&&self.X3D)ensureInst();
    if(ST.replay){const t=Math.min(1,(now-ST.replay.t0)/ST.replay.ms);ST.t=t;applyT();if(t>=1){ST.replay=null;__morph.replay=null}}
    if(ST.lock&&ST.top&&ST.bot&&ST.top.ok&&ST.bot.ok){const act=ST.active==="top"?ST.top:ST.bot,oth=act===ST.top?ST.bot:ST.top;const p=act.pose();if(p)oth.setPose(p.position,p.q)}
    if(ST.cur&&!ST.sc&&self.S&&S.liveIds&&S.liveIds.get(ST.cur.i)){ST.steps=stepsOf(ST.cur);__morph.steps=ST.steps;RIB.set(ST.steps)}
    drawFloor()}});
  CLAIMS.define("morph.repaired",{label:"repaired-and-valid scenes",unit:"A.length > 1 and the final valid on fork@eb4b4b4",needs:["live.core"],expected:self.STATS&&STATS.LIVESTATS?STATS.LIVESTATS.rep:undefined,grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none",compute(){return items().length}});
  CLAIMS.define("morph.repairStats",{label:"how much a repair rewrites",unit:"median changed tag lines · scenes rewritten more than half",needs:["live.bodies"],grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none",text:v=>v?`${fmt.int(v.med)} · ${fmt.int(v.big)}`:"—",
    async compute(){if(ST.stats)return ST.stats;const list=items().filter(it=>bodies(it));const r=await repairStatsAsync(list.map(it=>({id:it.i,a:it.B[0],b:it.B[it.B.length-1]})));return r.stats}});
  buildPicker()}
function onData(name){if(name==="live.core"||name==="live.bodies"||name==="live.jpg"||name==="renders.151"){buildPicker();if(ST.cur){renderPins();if(!ST.diff&&bodies(ST.cur))open(ST.cur)}if(name==="live.bodies"||name==="live.core")computeStats()}
  if(name==="live.core"&&sec)sectionHeader(sec,headerSpec())}
SECTIONS.register({id:"morph",part:"live.bodies",mount(s){try{mount(s)}catch(e){console.error("morph mount",e);if(self.BOOT)BOOT.error(e,"morph mount")}},onData});
Object.assign(self,{MORPH,DIFF,RIBBON,OPCOL,__morph});
})();
