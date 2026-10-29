/* 03-data.js — part loading (SPEC §8): fetch parts/<name>.txt → base64 → gunzip → sha256 vs MANIFEST → globals. Globals: DATA, LIVE, REAL, EVENTS, R150, R151,
   DRIFT, SUITE, RUN24, LIVESTATS, REALSTATS, keyOf, ledgerKey, renderOf, kindOf, DRAWS, codesOf, findingOf.
   Ported from v3 lines 225–263 (LIVE post-processing, codesOf, findingOf, DRAWS, DROP_RE, kindOf, REALSTATS, LIVESTATS).
   Test hooks: DATA.status[name], DATA.loaded(name), the globals. A refused part prints `part <name> refused: hash mismatch` through DATA.messages (46-footer shows it in #under). */
(function(){
"use strict";
const ORDER=["live.core","events","live.bodies","replay","renders.series","renders.151","drift","suite","run24","live.jpg"];  /* run24 only when the manifest has it */
const status={},memo=new Map(),waiters=new Map(),listeners=new Map(),texts=new Map(),messages=[];
const LIVE=[],REAL=[];let EVENTS=null,R150=null,R151=null,DRIFT=null,SUITE=null,RUN24=null;
Object.keys((self.MANIFEST&&MANIFEST.parts)||{}).forEach(n=>{status[n]={state:"idle",bytes:(MANIFEST.parts[n].bytes_b64||0),got:0,sha:null,ms:0,err:null}});
const DATA={status,messages,phone:innerWidth<600,order:ORDER,
  loaded:n=>!!(status[n]&&status[n].state==="loaded"),
  on(n,fn){if(!listeners.has(n))listeners.set(n,[]);listeners.get(n).push(fn);if(n!=="*"&&DATA.loaded(n))try{fn(memo.get(n),n)}catch(e){console.error("DATA.on",n,e)}else if(n==="*")Object.keys(status).forEach(k=>{if(DATA.loaded(k))try{fn(k,memo.get(k))}catch(e){console.error("DATA.on *",k,e)}})},
  ready(n){if(!waiters.has(n))waiters.set(n,{});const w=waiters.get(n);if(!w.p)w.p=new Promise((res,rej)=>{w.res=res;w.rej=rej});return w.p},
  text:n=>texts.get(n)||null,
  get:n=>memo.get(n)};
function emit(n,obj){(listeners.get(n)||[]).forEach(f=>{try{f(obj,n)}catch(e){console.error("DATA listener",n,e)}});(listeners.get("*")||[]).forEach(f=>{try{f(n,obj)}catch(e){console.error("DATA listener *",n,e)}});if(self.LOOP)LOOP.dirty(LOOP.bits.DATA)}
function say(m){messages.push(m);console.warn(m)}
async function load(n){
  if(memo.has(n))return memo.get(n);const st=status[n]||(status[n]={state:"idle",bytes:0,got:0});if(st.p)return st.p;
  const w=DATA.ready(n);st.state="loading";const t0=performance.now();
  st.p=(async()=>{try{
    let bytes;st.phase="fetch";
    const get=()=>self.__PARTS&&__PARTS[n]?gzReadBytesInline(__PARTS[n]):gzReadBytes("parts/"+n+".txt",{onProgress:(got,total)=>{st.got=got;if(total)st.bytes=total}});
    try{bytes=await get()}catch(e){if(!/^stalled/.test(String(e&&e.message)))throw e;st.retries=(st.retries||0)+1;say(`part ${n}: ${e.message}; retrying once`);st.got=0;bytes=await get()}
    st.phase="hash";const want=self.MANIFEST&&MANIFEST.parts[n]&&MANIFEST.parts[n].sha256;const hex=await HASH.sha256hex(bytes);st.sha=hex;
    if(want&&hex!==want){st.state="refused";st.err="hash mismatch";say(`part ${n} refused: hash mismatch (${hex.slice(0,8)} vs manifest ${want.slice(0,8)})`);throw new Error("part "+n+" refused")}
    st.phase="parse";const text=new TextDecoder().decode(bytes);let obj;
    if(n.startsWith("xsd")){texts.set(n,text);obj=text}else obj=JSON.parse(text);
    st.phase="fill";st.ms=performance.now()-t0;st.got=st.bytes=st.bytes||bytes.length;fill(n,obj);memo.set(n,obj);st.phase="done";st.state="loaded";emit(n,obj);waiters.get(n).res(obj);return obj}
  catch(e){if(st.state!=="refused"){st.state=/HTTP 404/.test(String(e))?"missing":"refused";st.err=String(e&&e.message||e);say(`part ${n} ${st.state}: ${st.err}`)}st.ms=performance.now()-t0;if(self.LOOP)LOOP.dirty(LOOP.bits.DATA);waiters.get(n).rej(e);throw e}})();
  return st.p}
async function gzReadBytesInline(b64){const bytes=UTIL.b64ToBytes(b64);if(typeof DecompressionStream!=="undefined"){const ds=new DecompressionStream("gzip"),wr=ds.writable.getWriter();wr.write(bytes);wr.close();return new Uint8Array(await new Response(ds.readable).arrayBuffer())}throw new Error("no DecompressionStream for inline parts")}
DATA.load=load;
DATA.start=function(){const have=self.MANIFEST&&MANIFEST.parts;const order=ORDER.filter(n=>!(DATA.phone&&n==="live.jpg")&&(!have||have[n]));  /* a name absent from the manifest (run24 on a build without it) is never fetched */(async()=>{for(const n of order){try{await load(n)}catch(e){}}})();return DATA.ready("live.core")};
/* ---------- fill rules ---------- */
const codesOf=a=>{const c=[];if(!a.x)c.push("xsd");(a.se||[]).forEach(l=>{const m=/\*\*\[([\w-]+)\]\*\*/.exec(l);if(m&&!c.includes(m[1]))c.push(m[1])});return c};
const findingOf=a=>{const l=(a.xe&&a.xe[0])||(a.se&&a.se[0])||"";return l.replace(/^-\s*/,"").replace(/\*\*/g,"").replace(/^Line \d+:\s*/,"").replace(/\{[^}]*\}/g,"").replace(/\s+/g," ").trim().slice(0,150)};
const DRAWS=i=>!!i.r&&!i.r.err&&(i.r.nb||0)>=.005;
const DROP_RE=/Unknown node type|Unknown named or imported node|Container field|insufficient component/,dropped=i=>(i.r.unknown||0)>0||(i.r.msgs||[]).some(m=>DROP_RE.test(m)),
  kindOf=i=>!i.r?"unknown":i.r.err?"unparseable":(i.r.nb||0)>=.005?"draws":(i.r.nf||dropped(i))?"nothing drawable":"blank frame";
const keyOf=(m,p,k)=>`${String(m).replace("/","_")}/${p}_a${k}.x3d`;
/* ledgerKey(item): the key the Cycles ledger (demo/v4/data/staged.json turntables/stills) and renders.151 use for an item — LIVE items
   `${m}/${p}_a${attempts}.x3d` (= keyOf), REAL items their recorded `it.k` = `${m}/${mo}/${p}.x3d`. Scene records: ledgerKey(sc.item). */
const ledgerKey=it=>!it?null:Array.isArray(it.A)?keyOf(it.m,it.p,it.A.length||1):(it.k||null);  /* LIVE items carry k = prompt kind, so the A[] shape is tested first */
const renderOf=(it,k)=>{k=k||it.A.length;const key=keyOf(it.m,it.p,k);return{key,r150:R150&&R150.live[key]||null,r151:R151&&R151.live[key]||null}};
function fill(n,obj){
  if(n==="live.core"){LIVE.length=0;obj.items.forEach((it,i)=>{it.i=i;const f=it.A[it.A.length-1];it.r=f.r;it.ok=f.ok;it.B=it.B||[];LIVE.push(it)});LIVE.meta=obj.meta;self.LM=obj.meta;recompute()}
  else if(n==="live.bodies"){obj.forEach((B,i)=>{if(LIVE[i])LIVE[i].B=B});if(!LIVE.length)pendingBodies=obj}
  else if(n==="live.jpg"){obj.forEach((J,i)=>{if(LIVE[i])J.forEach((j,k)=>{if(j&&LIVE[i].A[k]&&LIVE[i].A[k].r)LIVE[i].A[k].r.jpg=j})})}
  else if(n==="replay"){REAL.length=0;obj.forEach((it,i)=>{it.i=i;REAL.push(it)});if(R151)REAL.forEach(it=>{const r=R151.replay[it.k];if(r){it.r.nb151=r.nb;it.r.err151=r.err;it.r.frames151=r.frames}});recompute()}
  else if(n==="events")EVENTS=obj;
  else if(n==="renders.series")R150=obj;
  else if(n==="renders.151"){R151=obj;REAL.forEach(it=>{const r=R151.replay[it.k];if(r){it.r.nb151=r.nb;it.r.err151=r.err;it.r.frames151=r.frames}})}
  else if(n==="drift")DRIFT=obj;else if(n==="suite")SUITE=obj;else if(n==="run24")RUN24=obj;
  Object.assign(self,{EVENTS,R150,R151,DRIFT,SUITE,RUN24})}
let pendingBodies=null;
/* ---------- stats, the v3 formulas (LIVESTATS lines 248–262, REALSTATS 236–246); inline STATS first, recomputed when the parts land ---------- */
function recompute(){
  const med=a=>UTIL.median(a),sum=(a,f)=>a.reduce((x,y)=>x+f(y),0);
  if(REAL.length){const f=[["svc@11Oct",i=>i.x&&i.s],["fork@8c0a457",i=>i.f1[0]],["fork@eb4b4b4",i=>i.f2[0]]].map(([nm,fn])=>{const v=REAL.filter(fn),d=v.filter(DRAWS).length;return{n:nm,valid:v.length,draws:d,nodraw:v.length-d}});
    const kinds={draws:0,"blank frame":0,"nothing drawable":0,unparseable:0};REAL.forEach(i=>{kinds[kindOf(i)]++});
    const flip=REAL.filter(i=>i.x&&i.s&&!i.f1[0]),both=REAL.filter(i=>!i.r.err&&i.r.cb!=null&&i.r.shot!=null),agree=both.filter(i=>(i.r.cb<.005)===(i.r.shot<.005)).length,
      blankMax=Math.max(0,...REAL.filter(i=>!i.r.err&&(i.r.nb||0)<.005).map(i=>i.r.nb||0)),bl=REAL.filter(i=>!i.r.err&&(i.r.nb||0)<.005),dr=REAL.filter(DRAWS);
    self.REALSTATS={blankMax,n:REAL.length,f,kinds,draws:dr.length,flip:flip.length,flipNoDraw:flip.filter(i=>!DRAWS(i)).length,wf:REAL.filter(i=>i.wf).length,agree,both:both.length,
      blankFrames:med(bl.map(i=>i.r.frames)),blankLast:med(bl.map(i=>i.r.last)),drawFrames:med(dr.map(i=>i.r.frames)),drawLast:med(dr.map(i=>i.r.last)),dropDraw:dr.filter(dropped).length,
      extN:REAL.filter(i=>i.r.ext!==undefined).length,extBlank:REAL.filter(i=>i.r.ext!==undefined&&i.r.ext<.005).length,
      v164n:REAL.filter(i=>i.r.nb164!==undefined).length,v164a:REAL.filter(i=>i.r.nb164!==undefined&&(i.r.err164?"u":i.r.nb164<.005?"b":"d")===(i.r.err?"u":(i.r.nb||0)<.005?"b":"d")).length,
      v151n:REAL.filter(i=>i.r.nb151!==undefined).length,v151a:REAL.filter(i=>i.r.nb151!==undefined&&(i.r.err151?"u":i.r.nb151<.005?"b":"d")===(i.r.err?"u":(i.r.nb||0)<.005?"b":"d")).length}}
  if(LIVE.length){const LMm=LIVE.meta,fin=i=>i.A[i.A.length-1],drew=r=>!!r&&!r.err&&(r.nb||0)>=.005;
    const r6=x=>Math.round(x*1e6)/1e6;  /* claims.py rounds money to 6 decimals; field order below matches it so JSON.stringify compares equal */
    const per=LMm.models.map(m=>{const s=LIVE.filter(i=>i.m===m.id),bad1=s.filter(i=>!i.A[0].ok);
      return{id:m.id,prov:m.prov,kind:m.kind,n:s.length,calls:sum(s,i=>i.A.length),first:s.filter(i=>i.A[0].ok).length,valid:s.filter(i=>fin(i).ok).length,bad1:bad1.length,rep:bad1.filter(i=>fin(i).ok).length,
        blankValid:s.filter(i=>fin(i).ok&&!DRAWS(i)).length,usd:r6(sum(s,i=>sum(i.A,a=>a.u))),tin:sum(s,i=>sum(i.A,a=>a.ti)),tout:sum(s,i=>sum(i.A,a=>a.to)),lat:med(s.flatMap(i=>i.A.map(a=>a.ms))),vmed:med(s.flatMap(i=>i.A.map(a=>a.vms))),
        truncated:s.reduce((n,i)=>n+i.A.filter(a=>/length|max_tokens/i.test(a.fin||"")).length,0),failed:EVENTS?EVENTS.failed.filter(f=>f.m===m.id).length:0,cut:EVENTS?EVENTS.cut.filter(c=>c.m===m.id).length:0,stopped:(LMm.lanes||{})[m.id]||null}});
    const valid=LIVE.filter(i=>fin(i).ok),kinds={draws:0,"blank frame":0,"nothing drawable":0,unparseable:0};LIVE.forEach(i=>{kinds[kindOf(i)]++});const firstValid=LIVE.filter(i=>i.A[0].ok);
    self.LIVESTATS={n:LIVE.length,calls:sum(LIVE,i=>i.A.length),valid:valid.length,validNoDraw:valid.filter(i=>!DRAWS(i)).length,first:firstValid.length,firstNoDraw:firstValid.filter(i=>!drew(i.A[0].r)).length,
      bad1:LIVE.length-firstValid.length,rep:LIVE.filter(i=>!i.A[0].ok&&fin(i).ok).length,invDraw:LIVE.filter(i=>!fin(i).ok&&DRAWS(i)).length,draws:LIVE.filter(DRAWS).length,kinds,per,
      usd:r6(sum(per,p=>p.usd)),tin:sum(per,p=>p.tin),tout:sum(per,p=>p.tout),blankMax:Math.max(0,...LIVE.filter(i=>!i.r.err&&!DRAWS(i)).map(i=>i.r.nb||0)),vmed:med(LIVE.flatMap(i=>i.A.map(a=>a.vms))),mmed:med(LIVE.flatMap(i=>i.A.map(a=>a.ms))),
      blankCat:valid.filter(i=>!DRAWS(i)).reduce((o,i)=>(o[i.c]=(o[i.c]||0)+1,o),{}),repCalls:sum(LIVE,i=>i.A.length-1),multi:LIVE.filter(i=>i.A.length>1).length,giveUp:LIVE.filter(i=>!fin(i).ok).length,truncated:LIVE.reduce((n,i)=>n+i.A.filter(a=>/length|max_tokens/i.test(a.fin||"")).length,0)};
    if(pendingBodies){pendingBodies.forEach((B,i)=>{if(LIVE[i])LIVE[i].B=B});pendingBodies=null}}}
DATA.recompute=recompute;
const S0=self.STATS||{};
Object.assign(self,{DATA,LIVE,REAL,EVENTS,R150,R151,DRIFT,SUITE,RUN24,LIVESTATS:S0.LIVESTATS||null,REALSTATS:S0.REALSTATS||null,keyOf,ledgerKey,renderOf,kindOf,DRAWS,codesOf,findingOf});
if(!self.LM)self.LM=S0.meta||null;
})();
