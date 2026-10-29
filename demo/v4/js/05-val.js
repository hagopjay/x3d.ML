/* 05-val.js — VAL facade over the js-port (SPEC §6, ARCHITECTURE §4 / 05). Replaces the wave-1 stub; the documented surface is unchanged.
   Globals: VAL, reportHtml, repairText, codesOfRes. Test hooks: VAL.mode, VAL.reason, VAL.ready, VAL.status (= __val: phase, pct, transport, compileMs,
   loadMs, selfTest, n, totalMs), VAL.need(), VAL.canary(), VAL.lastCanary, #portChip[data-mode].
   Wiring: workers/val.worker.js (classic own file → a blob: copy of the same source → the main thread as a last resort) importScripts jsval/x3dval.js, which
   dynamic-import()s jsval/vendor/libxml2-wasm.bundle.mjs ('wasm-unsafe-eval'). The two big XSDs are the parts xsd40/xsd41 (DATA.load: gzip+base64, sha256
   against the manifest) handed to the worker as bytes; the five small XSDs and the json tables are fetched from jsval/data/ (copied there by the build).
   Modes: unloaded → full (after a self-test on known bodies) | none (reason: wasm blocked, every transport refused, a schema part refused, the self-test
   failed, the worker died). 'semantic-only' stays in the vocabulary for the DOMParser path jsval has not shipped. Loading: eager at fx ≥ 1; at fx 0 once the
   data parts are in (phone / saveData: on first need); VAL.need() pulls it at once (Bench, ladder, lane, Report). A main-thread compile (≈ 3 s stall) only on need.
   Label everywhere: js-port-of-8dd0d3e, never fork@. v3: nothing ported (new in v4); reportHtml follows the v3 inspector report lines 628–634. */
(function(){
"use strict";
const fns=[],BOOT_MS=20000,ENV_MS=15000,DEFER_MS=90000,MEMO_MAX=2000;
const status={phase:"idle",pct:0,ms:0,transport:null,compileMs:null,loadMs:null,selfTest:null,n:0,totalMs:0,lastMs:null,started:0,note:"",err:null};
let needRes=null;const needP=new Promise(r=>{needRes=r});let client=null,rpc=null;
const msg=e=>String(e&&e.message||e).slice(0,160);
const VAL={label:"js-port-of-8dd0d3e",recorded:"fork@8dd0d3e",vendor:"libxml2-wasm 0.7.2",mode:"unloaded",reason:"validator not loaded yet",ready:null,memo:new Map(),worker:null,info:null,status,opts:null,transport:null,lastCanary:null,
  on(f){fns.push(f)},
  _set(mode,reason){VAL.mode=mode;VAL.reason=reason||"";status.reason=VAL.reason;if(mode==="none"){status.phase="failed";status.err=VAL.reason}fns.forEach(f=>{try{f(mode)}catch(e){}});if(self.LOOP)LOOP.dirty(LOOP.bits.VAL)},
  /* init({eager}): the boot calls it once; the decision to load is taken here, the load itself in _load. */
  init(opts){if(VAL.ready)return VAL.ready;VAL.opts=opts||{};
    VAL.ready=(async()=>{try{
      status.phase="env";await envSettled();
      if(self.ENV&&ENV.wasmInstantiate===false){VAL._set("none","WebAssembly is blocked by this viewer's policy (no 'wasm-unsafe-eval'): the exact validator runs on libxml2-wasm and cannot start here; recorded verdicts only");return"none"}
      const eager=!!VAL.opts.eager,lazy=(self.DATA&&DATA.phone)||(self.ENV&&ENV.saveData);
      if(!eager){status.phase="deferred";status.note=lazy?"loads on first need (phone / saveData)":"loads once the data parts are in, or on first need";
        await Promise.race([needP,lazy?new Promise(()=>{}):(self.DATA?DATA.ready("suite").catch(()=>{}).then(()=>later(800)):later(0)),later(DEFER_MS)])}
      return await VAL._load()}
    catch(e){VAL._set("none","validator failed to load: "+msg(e));return"none"}})();
    return VAL.ready},
  need(){if(needRes){needRes();needRes=null}return VAL.init()},
  async validate(xml){await VAL.need();if(VAL.mode!=="full"&&VAL.mode!=="semantic-only")throw new Error("VAL unavailable: "+VAL.reason);return VAL._validate(xml)},
  _validate:async function(xml){xml=String(xml);const k=sha(xml);const m=VAL.memo.get(k);if(m)return m;const t0=performance.now();const r=await rpc("validate",[xml,{}]);
    r.label=VAL.label;r.transport=VAL.transport;r.wall=Math.round((performance.now()-t0)*10)/10;if(VAL.memo.size>=MEMO_MAX)VAL.memo.delete(VAL.memo.keys().next().value);VAL.memo.set(k,r);
    status.n++;status.totalMs+=r.ms||0;status.lastMs=r.ms;return r},
  /* items [{id, xml}] → Map id → res; up to 8 in flight through the worker (it serialises them), one at a time with a yield on the main thread */
  async validateMany(items,onProgress){await VAL.need();if(VAL.mode!=="full"&&VAL.mode!=="semantic-only")throw new Error("VAL unavailable: "+VAL.reason);
    const out=new Map(),q=items.slice(),conc=VAL.transport==="main"?1:8;let done=0;
    await Promise.all(Array.from({length:Math.min(conc,q.length)},async()=>{while(q.length){const it=q.shift();let r;try{r=await VAL._validate(it.xml)}catch(e){r={valid:null,error:msg(e),label:VAL.label}}
      out.set(it.id,r);done++;if(onProgress)try{onProgress(done,items.length,r,it.id)}catch(e){}if(VAL.transport==="main")await later(0)}}));
    return out},
  /* canary: every body with a recorded fork@8dd0d3e verdict (DRIFT.v8dd0d3e.verdicts: 383 live attempts, 174 replay bodies, the physics ledger) validated here;
     a flip = a changed valid flag, XSD flag, XSD error count or sorted set of semantic error codes (the rule drift/canary.py used). */
  async canary(onProgress){await VAL.need();if(VAL.mode!=="full")return{bodies:0,flips:[],groups:{live:0,replay:0,ledger:0},reason:VAL.reason,agree:0,label:VAL.label,recorded:VAL.recorded};
    await Promise.all(["drift","live.bodies","replay"].map(n=>DATA.ready(n).catch(()=>{})));
    if(!self.DRIFT)throw new Error("drift part not loaded: no recorded verdicts to compare with");
    const V=DRIFT.v8dd0d3e.verdicts,items=[],skipped=[];let ledger=null;
    for(const k in V){if(/\.ledger\.x3d$/.test(k)){if(ledger===null)ledger=await fetch("data/physics-ledger.x3d").then(r=>r.ok?r.text():null).catch(()=>null);if(ledger)items.push({id:k,xml:ledger,group:"ledger"});else skipped.push(k);continue}
      const b=bodyFor(k);if(b==null)skipped.push(k);else items.push({id:k,xml:b.xml,group:b.group})}
    const t0=performance.now(),res=await VAL.validateMany(items,onProgress),flips=[],groups={live:0,replay:0,ledger:0},ms=[];let warnDiff=0;
    items.forEach((it,i)=>{const r=res.get(it.id),rec=V[it.id];groups[it.group]++;if(!r||r.error){flips.push({id:it.id,recorded:rec,port:{error:r&&r.error||"no result"}});return}if(i>=10)ms.push(r.ms);
      const port={valid:!!r.valid,xsd:!!(r.xsd&&r.xsd.valid)&&r.xsd.status!=="exception",nxsd:((r.xsd&&r.xsd.errors)||[]).length,sem:uniq(((r.semantic&&r.semantic.errors)||[]).map(e=>e.id)),warn:uniq(((r.semantic&&r.semantic.warnings)||[]).map(e=>e.id))};
      const recN={valid:!!rec.valid,xsd:!!rec.xsd,nxsd:rec.nxsd|0,sem:(rec.sem||[]).slice().sort(),warn:(rec.warn||[]).slice().sort()};
      if(port.valid!==recN.valid||port.xsd!==recN.xsd||port.nxsd!==recN.nxsd||port.sem.join(",")!==recN.sem.join(","))flips.push({id:it.id,recorded:recN,port});else if(port.warn.join(",")!==recN.warn.join(","))warnDiff++});
    const s=ms.slice().sort((a,b)=>a-b),pct=q=>s.length?s[Math.min(s.length-1,Math.floor(s.length*q))]:null;
    const out={bodies:items.length,flips,groups,skipped,agree:items.length-flips.length,warnDiff,ms:Math.round(performance.now()-t0),perBody:{median:pct(.5),p90:pct(.9),p95:pct(.95),max:s.length?s[s.length-1]:null,n:s.length,note:"X3DVAL.validate ms per body after the first 10"},label:VAL.label,recorded:VAL.recorded,transport:VAL.transport};
    VAL.lastCanary=out;if(self.LOOP)LOOP.dirty(LOOP.bits.VAL);return out},
  compare(res,recordedOk,recordedCodes){if(!res||res.valid==null)return"differs";if(!!res.valid!==!!recordedOk)return"differs";const a=codesOfRes(res).slice().sort().join(","),b=(recordedCodes||[]).slice().sort().join(",");return a===b?"agrees":"differs"}};
const uniq=a=>[...new Set(a)].sort();
/* the body behind a recorded-verdict key: live-2026-10-17/x3d/<model_>/<p>_a<k>.x3d → LIVE[].B[k-1]; replay/<k> → REAL[].b */
function bodyFor(k){let m=/^live-[\d-]+\/x3d\/(.+?)\/([\w-]+)_a(\d+)\.x3d$/.exec(k);
  if(m){const it=(self.LIVE||[]).find(i=>i.m.replace("/","_")===m[1]&&i.p===m[2]);const b=it&&it.B&&it.B[+m[3]-1];if(typeof b==="string")return{xml:b,group:"live"}   /* "" = a recorded empty answer (fin length, 0 chars): validated too */
    const key=m[1]+"/"+m[2]+"_a"+m[3]+".x3d";for(const c of (self.EVENTS&&EVENTS.cut)||[])for(const cb of c.bodies||[])if(cb&&cb.k===key&&typeof cb.xml==="string")return{xml:cb.xml,group:"live"};   /* the 25 cut-chain bodies ride in EVENTS.cut[].bodies */
    return null}
  m=/^replay\/(.+)$/.exec(k);if(m){const it=(self.REAL||[]).find(i=>i.k===m[1]);return it&&it.b?{xml:it.b,group:"replay"}:null}return null}
/* ENV settles the wasm question within a second; the worker probes may take 12 s, so poll the field rather than wait for ENV.ready */
async function envSettled(){if(!self.ENV)return false;const t0=performance.now();while(ENV.wasmInstantiate===null&&!ENV.done&&performance.now()-t0<ENV_MS)await later(100);return true}
function progress(p){if(!p)return;const st={lib:.5,data:.6,compile:.9,ready:.95}[p.stage];if(st!=null)status.pct=Math.max(status.pct,st);status.stage=p.stage;if(p.stage==="compile")status.compileMs=Object.assign(status.compileMs||{},{[p.version]:p.ms});if(self.LOOP)LOOP.dirty(LOOP.bits.VAL)}
/* ---------- transports ---------- */
function mkClient(w,kind){const pend=new Map();let id=0;const c={w,kind,alive:true,
  call(op,args,onProgress){return new Promise((res,rej)=>{if(!c.alive)return rej(new Error("validator worker is gone"));const i=++id;pend.set(i,{res,rej,onProgress});w.postMessage({id:i,op,args:args||[]})})},
  terminate(){c.alive=false;try{w.terminate()}catch(e){}pend.forEach(p=>p.rej(new Error("terminated")));pend.clear()}};
  w.onmessage=ev=>{const m=ev.data||{},p=pend.get(m.id);if(!p)return;if(m.progress){if(p.onProgress)p.onProgress(m.progress);return}pend.delete(m.id);
    if(m.ok)p.res(m.result);else{const e=new Error(m.error&&m.error.message||"worker error");e.name=(m.error&&m.error.name)||"Error";p.rej(e)}};
  w.onerror=e=>{const err=new Error(kind+" error: "+msg(e&&(e.message||e.type)||e));c.alive=false;pend.forEach(p=>p.rej(err));pend.clear();if(VAL.mode==="full")VAL._set("none","validator worker died: "+err.message)};
  return c}
async function bootWorker(make,kind,jsval){let w;try{w=make()}catch(e){throw new Error(kind+" refused: "+msg(e))}const c=mkClient(w,kind);
  try{await Promise.race([c.call("boot",[{jsval}]),later(BOOT_MS).then(()=>{throw new Error(kind+" did not boot in "+BOOT_MS/1000+" s")})])}catch(e){c.terminate();throw e}return c}
function loadMainScript(){return new Promise((res,rej)=>{if(self.X3DVAL&&typeof X3DVAL.load==="function")return res();const s=document.createElement("script");s.src="jsval/x3dval.js";
  s.onload=()=>self.X3DVAL?res():rej(new Error("jsval/x3dval.js did not define X3DVAL"));s.onerror=()=>rej(new Error("jsval/x3dval.js refused (script-src)"));document.head.appendChild(s)})}
/* ---------- the load ---------- */
VAL._load=async function(){
  status.started=performance.now();status.phase="parts";const notes=[];
  const want=["xsd40","xsd41"];let texts;
  try{texts=await Promise.all(want.map(n=>DATA.load(n)))}catch(e){const bad=want.filter(n=>DATA.status[n]&&DATA.status[n].state!=="loaded");VAL._set("none",`schema part ${bad.join(", ")||"xsd"} ${bad.map(n=>DATA.status[n].state+(DATA.status[n].err?" ("+DATA.status[n].err+")":"")).join("; ")||msg(e)}: the schema would not be the one the fork used, so the validator does not run`);return"none"}
  status.pct=.4;const enc=new TextEncoder(),bytes={"x3d-4.0.xsd":enc.encode(texts[0]),"x3d-4.1.xsd":enc.encode(texts[1])};
  const jsval=new URL("jsval/",location.href).href;
  status.phase="worker";client=null;
  if(typeof Worker!=="undefined"&&!(self.ENV&&ENV.worker===false&&ENV.workerBlob===false)){
    if(!(self.ENV&&ENV.worker===false))try{client=await bootWorker(()=>new Worker("workers/val.worker.js"),"worker",jsval)}catch(e){notes.push(msg(e))}
    if(!client&&!(self.ENV&&ENV.workerBlob===false))try{const src=await fetch("workers/val.worker.js").then(r=>{if(!r.ok)throw new Error("HTTP "+r.status);return r.text()});
      client=await bootWorker(()=>new Worker(URL.createObjectURL(new Blob([src],{type:"text/javascript"}))),"blob worker",jsval)}catch(e){notes.push(msg(e))}}
  else notes.push("workers unavailable in this viewer");
  if(client){VAL.transport=status.transport=client.kind==="worker"?"worker":"blob";VAL.worker=client.w;rpc=(op,args)=>client.call(op,args)}
  else{/* main thread: only on an explicit need (a 3 s compile stall), never because the parts landed */
    if(!VAL.opts.eager&&needRes){status.phase="deferred";status.note="no worker: the main-thread compile (≈ 3 s stall) waits for the first need";await needP}
    status.phase="script";await loadMainScript();VAL.transport=status.transport="main";
    const read=url=>{const n=String(url).replace(/^.*\//,"");if(bytes[n])return Promise.resolve(bytes[n]);return fetch(url).then(r=>{if(!r.ok)throw new Error("fetch "+url+" -> HTTP "+r.status);return r.arrayBuffer()}).then(ab=>new Uint8Array(ab))};
    rpc=async(op,args)=>X3DVAL[op](...args);rpc.load=o=>X3DVAL.load({base:o.base,precompile:o.precompile,read,onProgress:progress}).then(()=>X3DVAL.info())}
  status.notes=notes;status.phase="lib";
  const info=client?await client.call("load",[{base:jsval,precompile:["4.0"],bytes}],progress):await rpc.load({base:jsval,precompile:["4.0"]});
  VAL.info=info;status.loadMs=info&&info.loadMs;status.compileMs=(info&&info.compileMs)||status.compileMs;status.vendor=info&&info.vendor;
  status.phase="selftest";const st=await selfTest();status.selfTest=st;
  if(!st.ok){VAL._set("none","self-test failed on a known body ("+st.detail+"): the port's answer here is not the fork's, so it is not shown");return"none"}
  status.phase="ready";status.pct=1;status.ms=Math.round(performance.now()-status.started);VAL._set("full","");return"full"};
/* three bodies whose fork@8dd0d3e verdict is known: a minimal valid scene, a duplicate DEF, a malformed document, plus the hero's recorded-valid final body */
async function selfTest(){const t0=performance.now();const cases=[
  ["minimal valid","<X3D profile='Interchange' version='4.0'><Scene><Viewpoint position='0 0 5'/><Shape><Appearance><Material/></Appearance><Box/></Shape></Scene></X3D>",r=>r.valid===true&&r.xsd&&r.xsd.valid===true&&r.semantic&&r.semantic.errors.length===0],
  ["duplicate DEF","<X3D profile='Interchange' version='4.0'><Scene><Shape DEF='a'><Box/></Shape><Shape DEF='a'><Box/></Shape></Scene></X3D>",r=>r.valid===false&&codesOfRes(r).includes("duplicate-def")],
  ["malformed","<X3D profile='Interchange' version='4.0'><Scene><Shape></Scene>",r=>r.valid===false&&r.xsd&&/^XML parse error/.test((r.xsd.errors||[])[0]||"")]];
  if(self.HERO&&HERO.items&&HERO.items[0]&&HERO.items[0].ok)cases.push(["hero final body (recorded valid)",HERO.items[0].body,r=>r.valid===true]);
  for(const[name,xml,ok]of cases){let r;try{r=await rpc("validate",[xml,{}])}catch(e){return{ok:false,detail:name+": "+msg(e),ms:Math.round(performance.now()-t0)}}
    if(!ok(r))return{ok:false,detail:name+" → valid "+r.valid+" "+JSON.stringify(codesOfRes(r)).slice(0,80),ms:Math.round(performance.now()-t0)}}
  return{ok:true,detail:cases.length+" known bodies agree",n:cases.length,ms:Math.round(performance.now()-t0)}}
/* ---------- shared renderers ---------- */
function codesOfRes(res){const c=[];if(!res)return c;if(res.xsd&&((res.xsd.errors&&res.xsd.errors.length)||res.xsd.status==="exception"))c.push("xsd");((res.semantic&&res.semantic.errors)||[]).forEach(e=>{const id=e&&(e.id||e.code);if(id&&!c.includes(id))c.push(id)});return c}
const fmtMs=ms=>ms==null?"—":ms<10?(+ms).toFixed(1)+" ms":fmt.ms(ms);
const isParse=res=>!!(res&&res.xsd&&res.xsd.errors&&res.xsd.errors.length===1&&/^XML parse error/.test(res.xsd.errors[0]));
/* reportHtml(res, {fixes: Map cardKey → {label}}) → safe HTML (every data string escaped). Card keys: xsd:<i>, sem:<i>, fix:<i>; a card with a fix gets an
   APPLY button (class repApply, data-fix=key) the Bench listens for; data-line on cards that name a line. Used by the Bench, the Report tab, the lane, Receipt. */
function reportHtml(res,opts){opts=opts||{};if(!res)return'<div class="rep"><span class="pill p-mute">NO REPORT</span></div>';
  const fixes=opts.fixes||null,label=res.label||VAL.label,xe=(res.xsd&&res.xsd.errors)||[],notes=(res.xsd&&res.xsd.notes)||[],S=res.semantic||{},se=S.errors||[],sw=S.warnings||[],si=S.info||[],fx=S.fixes||[],parse=isParse(res);
  const card=(key,code,tone,line,text)=>{const f=fixes&&fixes.get(key);return`<div class="repCard ${tone}" data-key="${esc(key)}" data-code="${esc(code)}"${line?` data-line="${line}"`:""}><span class="pill p-${tone}">${esc(code)}</span>${line?`<button type="button" class="repLine" data-line="${line}">line ${line}</button>`:""}<span class="repMsg">${esc(text)}</span>${f?`<span class="repFix"><i>fix:</i> ${esc(f.label)} <button type="button" class="repApply" data-fix="${esc(key)}">APPLY</button></span>`:""}</div>`};
  const pill=parse?'<span class="pill p-bad">NOT WELL-FORMED</span>':res.valid==null?'<span class="pill p-mute">NO VERDICT</span>':res.valid?'<span class="pill p-ok">VALID</span>':'<span class="pill p-bad">INVALID</span>';
  let h=`<div class="rep" data-valid="${res.valid?1:0}">${pill} <span class="repHead">${esc(label)}${res.recorded?"":" here"}${res.ms!=null?` · ${fmtMs(res.ms)}`:""}${res.xsd&&res.xsd.schema_version?` · XSD x3d-${esc(res.xsd.schema_version)}.xsd via ${esc(VAL.vendor)}`:""}</span>`;
  if(res.error)h+=card("err","error","bad",null,String(res.error));
  xe.forEach((l,i)=>{const m=/^Line (\d+):\s*/.exec(l);h+=card("xsd:"+i,parse?"xml":"xsd","bad",m?+m[1]:null,m?l.slice(m[0].length):l)});
  if(res.xsd&&res.xsd.status==="exception")h+=card("xsdx","xsd","bad",null,"the XSD engine raised here, as the fork's lxml does on this body: "+(res.xsd.error||""));
  notes.forEach((n,i)=>h+=card("note:"+i,"note","info",null,n));
  se.forEach((e,i)=>h+=card("sem:"+i,e.id||"semantic","bad",null,e.msg||e.message||String(e)));
  if(S.status==="exception")h+=card("semx","semantic","bad",null,"the semantic pass raised here, as the fork does on this body: "+(S.error||""));
  sw.forEach((e,i)=>h+=card("warn:"+i,e.id||"warning","warn",null,e.msg||e.message||String(e)));
  fx.forEach((e,i)=>h+=card("fix:"+i,e.id||"fix","ok",null,e.msg||e.message||String(e)));
  si.filter(e=>!/-fix$/.test(e.id||"")).forEach((e,i)=>h+=card("info:"+i,e.id||"info","mute",null,e.msg||e.message||String(e)));
  if(res.valid&&!xe.length&&!se.length)h+=`<div class="repCard ok"><span class="pill p-ok">all clear</span><span class="repMsg">no XSD errors, no semantic errors${sw.length?`; ${sw.length} warning${sw.length===1?"":"s"}`:""}${si.length?`; ${si.length} info`:""}</span></div>`;
  h+=`<div class="repFoot">${res.recorded?`recorded report · ${esc(label)}`:`validated in ${fmtMs(res.ms)} · ${esc(label)} · ${res.transport==="main"?"main thread":"worker"} · XSD ${res.xsd&&res.xsd.schema_version?"x3d-"+esc(res.xsd.schema_version)+".xsd":"—"} via ${esc(VAL.vendor)}`}</div></div>`;
  return h}
/* repairText(res) = SYS.REPAIR filled verbatim (demo/live/validate_fork.py repair_text: XSD errors; semantic error lines plus the exact-fix lines) */
function repairText(res){const T=(typeof SYS!=="undefined"&&SYS&&SYS.REPAIR)||"The validator rejected the scene. Fix every error and return the whole corrected X3D document.\nXSD errors:\n{xsd}\nSemantic errors:\n{sem}\n";
  const line=e=>`- **[${e.id||e.code||"semantic"}]** ${e.msg||e.message||String(e)}`;const S=(res&&res.semantic)||{};
  const xsd=((res&&res.xsd&&res.xsd.errors)||[]).join("\n")||"none",sem=(S.errors||[]).map(line).concat((S.fixes||[]).map(line)).join("\n")||"none";
  return T.split("{xsd}").join(xsd).split("{sem}").join(sem)}
/* the mast chip: the port's own state, never a number about the runs */
if(self.LOOP)LOOP.register({name:"valchip",bit:LOOP.bits.VAL|LOOP.bits.DATA,rateHz:4,draw(){const c=$("portChip");if(!c)return;let t=VAL.label;
  if(VAL.mode==="full")t+=` · ready${status.compileMs&&status.compileMs["4.0"]!=null?" · xsd 4.0 compiled in "+fmtMs(status.compileMs["4.0"]):""}`;
  else if(VAL.mode==="none")t+=" · not available";
  else if(status.phase==="parts"){const a=self.DATA&&DATA.status.xsd40,b=self.DATA&&DATA.status.xsd41;const f=(x)=>x&&x.bytes?Math.min(1,(x.got||0)/x.bytes):0;t+=` · schemas ${Math.round(50*(f(a)+f(b)))}%`}
  else if(status.phase==="idle"||status.phase==="deferred"||status.phase==="env")t+=" · on demand";
  else t+=` · ${status.phase}${status.stage?" "+status.stage:""}`;
  txt(c,t);c.title=VAL.mode==="none"?VAL.reason:`${VAL.mode}${status.transport?" · "+status.transport:""}${status.loadMs?" · load "+fmtMs(status.loadMs):""}${status.note?" · "+status.note:""}`;
  if(c.dataset.mode!==VAL.mode){c.dataset.mode=VAL.mode;c.classList.toggle("v",VAL.mode==="full");c.classList.toggle("bad",VAL.mode==="none")}}});
Object.assign(self,{VAL,reportHtml,repairText,codesOfRes,__val:status});
})();
