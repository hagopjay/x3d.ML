/* 20-sim.js — the run clock, modes and generators (SPEC S1 clock, S6, §7.1, §7.5). Globals: SIM, MODES, S, VALS, judge, vStep, finish, genLive, genReal, genRun24,
   fresh, seekTo, setRate, pickScene, logEv, lastRef, WIN.
   Ported from v3: fresh (349–357), VALS (339), judge/vStep (369–385: recorded branches only; the synthetic branch moves to 58-drawer), finish (387–392), lastRef (393),
   genReal (427–448), genLive (449–467), step (871–878: dt-based, one clock, no carry), logEv (472), setRate/pickScene (892–894).
   Changes: every mode has order[] with T per entry and releases scenes whose T <= S.clk (replay11 spaces scenes 2 s apart: no clock was recorded on 11 Oct);
   seekTo rebuilds with rendering suppressed (S.ff); the scrubber verifies ≤ 4 chains per frame on the main thread and bulk through HASH.batch; S.sealOn is HASH.sealOn.
   Test hooks: window.S, S.scenes, S.byId, S.clk, S.done, SIM.seekTo, __panels (none here). */
(function(){
"use strict";
const WIN=360;
const VALS=[{id:"svc",ref:"svc@11Oct",name:"x3d-mcp-svc",strict:0},{id:"f1",ref:"fork@8c0a457",name:"fork",strict:1},{id:"f2",ref:"fork@eb4b4b4",name:"fork",strict:2},{id:"f3",ref:"fork@8dd0d3e",name:"fork",strict:3},{id:"port",ref:"js-port-of-8dd0d3e",name:"js-port",strict:3}];
let S=null;const fns=new Map(),modes=new Map();let cur=null;
const emit=(ev,a)=>{(fns.get(ev)||[]).forEach(f=>{try{f(a)}catch(e){console.error("SIM."+ev,e)}})};
const SIM={on(ev,f){if(!fns.has(ev))fns.set(ev,[]);fns.get(ev).push(f)},off(ev,f){const l=fns.get(ev)||[];const i=l.indexOf(f);if(i>=0)l.splice(i,1)},
  mode:()=>S?S.mode:null,modes:()=>[...modes.keys()],tmax:()=>cur&&cur.tmax?cur.tmax():0,emit};
const MODES={register(name,m){modes.set(name,Object.assign({name,label:name,tmax:()=>0,order:()=>[],ready:()=>true,lanes:()=>[],meta:()=>null,honesty:""},m))},get:n=>modes.get(n),
  set(name){fresh(name);emit("mode",name);if(self.LOOP)LOOP.dirty(LOOP.bits.MODE|LOOP.bits.SCENE|LOOP.bits.CLOCK)},get current(){return cur}};
function fresh(mode){
  const prev=S,m0=mode||(prev?prev.mode:"live17");cur=modes.get(m0)||modes.get("live17");
  S={mode:m0,seq:0,scenes:[],byId:new Map(),order:[],ri:0,clk:0,rate:prev?prev.rate:30,paused:prev?prev.paused&&!prev.done:false,done:false,vi:m0==="replay11"?0:2,sel:null,hover:null,seed:prev?prev.seed:1,
    flags:Object.assign({failed:true,filter:null,includeMine:false},prev?prev.flags:{}),ff:false,liveIds:new Map(),mod:{},stage:{gen:0,v1p:0,v1f:0,rep:0,v2p:0,v2f:0,ren:0,ok:0,drop:0},cost:0,provBytes:0,
    alerts:[],det:[],inj:0,detected:0,ttd:[],scr:0,flips:0,revals:0,tick:0,sec:{v:0,i:0,d:0},series:[],events:[],viewer:[],pendingVerify:new Set()};
  if(cur){S.order=cur.order();(cur.lanes()||[]).forEach(id=>S.mod[id]={n:0,first:0,rep:0,repOk:0,cost:0,valid:0})}
  self.S=S;emit("reset",S);if(self.LOOP)LOOP.dirtyAll();return S}
/* ---------- verdicts (recorded only) ---------- */
function judge(sc,V){
  if(sc.src==="live"){const it=sc.item;if(V.id==="f2"||V.id==="svc"||V.id==="f1"){const a=it.A[it.A.length-1];return{verdict:a.ok?"valid":"invalid",codes:codesOf(a),ms:a.vms,ms_src:"measured"}}
    if(V.id==="f3"&&self.DRIFT){const v=DRIFT.v8dd0d3e.verdicts["live-2026-10-17/x3d/"+keyOf(it.m,it.p,it.A.length)];if(v)return{verdict:v.valid?"valid":"invalid",codes:(v.xsd?[]:["xsd"]).concat(v.sem||[]),ms:0,ms_src:"recorded"}}
    if(V.id==="port"&&sc.port)return{verdict:sc.port.valid?"valid":"invalid",codes:codesOfRes(sc.port),ms:sc.port.ms,ms_src:"measured"};
    const a=it.A[it.A.length-1];return{verdict:a.ok?"valid":"invalid",codes:codesOf(a),ms:a.vms,ms_src:"measured",note:"no verdict recorded for "+V.ref+"; eb4b4b4 shown"}}
  if(sc.src==="real"){const it=sc.item;
    if(V.id==="svc"){const ok=it.x&&it.s;return{verdict:ok?"valid":"invalid",codes:ok?[]:[it.x?"recorded:semantic":"recorded:xsd"],ms:0,ms_src:"not recorded"}}
    if(V.id==="f1"||V.id==="f2"){const f=V.id==="f1"?it.f1:it.f2;return{verdict:f[0]?"valid":"invalid",codes:f[1],ms:0,ms_src:"recorded"}}
    if(V.id==="f3"&&self.DRIFT){const v=DRIFT.v8dd0d3e.verdicts["replay/"+it.k];if(v)return{verdict:v.valid?"valid":"invalid",codes:(v.xsd?[]:["xsd"]).concat(v.sem||[]),ms:0,ms_src:"recorded"}}
    if(V.id==="port"&&sc.port)return{verdict:sc.port.valid?"valid":"invalid",codes:codesOfRes(sc.port),ms:sc.port.ms,ms_src:"measured"};
    return{verdict:it.f2[0]?"valid":"invalid",codes:it.f2[1],ms:0,ms_src:"recorded",note:"no verdict recorded for "+V.ref+"; eb4b4b4 shown"}}
  if(sc.port)return{verdict:sc.port.valid?"valid":"invalid",codes:codesOfRes(sc.port),ms:sc.port.ms,ms_src:"measured"};
  return{verdict:sc.verdict||"invalid",codes:[],ms:0,ms_src:"none"}}
function vStep(sc,V){const r=judge(sc,V);const rec={op:"validate",validator:V.name,validator_ref:V.ref,verdict:r.verdict,codes:r.codes,ms:r.ms||0,ms_src:r.ms_src||"recorded"};
  if(sc.src==="real"&&V.id==="svc"){rec.recorded=true;rec.xsd_valid=!!sc.item.x;rec.semantic_valid=!!sc.item.s;rec.constraints_ok=!!sc.item.cn}return{rec,verdict:r.verdict}}
const curV=()=>VALS[S.vi];
/* ---------- finish: a scene enters the world (v3 387) ---------- */
function finish(sc,x,v){
  if(x!==undefined)sc.xml=x;if(v!==undefined)sc.verdict=v;sc.nsteps=readSteps(sc.xml).length;if(!sc.vref)sc.vref=lastRef(sc.xml);sc.status="?";S.pendingVerify.add(sc.id);S.provBytes+=sc.xml.length-stripProv(sc.xml).length;
  S.scenes.push(sc);S.byId.set(sc.id,sc);S.sec[sc.verdict==="valid"?"v":"i"]++;
  if(S.scenes.length>WIN){let k=0;while(k<S.scenes.length-1&&S.scenes[k].injured&&!S.scenes[k].detected&&!verify(S.scenes[k].xml).ok)k++;  /* a detectable tamper stays until the scrubber names it */
    const o=S.scenes.splice(k,1)[0];S.byId.delete(o.id);S.pendingVerify.delete(o.id);if(S.sel===o.id)S.sel=null}
  if(!S.ff){emit("scene",sc);if(self.LOOP)LOOP.dirty(LOOP.bits.SCENE)}return sc}
function lastRef(x){const st=readSteps(x);for(let i=st.length-1;i>=0;i--){const j=JSON.parse(st[i][1]);if(j.op==="validate")return j.validator_ref}return"?"}
function logEv(kind,msg){S.alerts.unshift({t:S.clk,kind,msg});if(S.alerts.length>60)S.alerts.pop();if(!S.ff&&self.LOOP)LOOP.dirty(LOOP.bits.VERIFY)}
/* ---------- generators ---------- */
/* Live scene (v3 449): the chain is built from what was recorded, step by step. generate → validate → [repair (the model was shown its report) → validate]… → render.
   Every attempt body is hashed into the chain, so the repaired scene's record names each earlier attempt's content hash. */
function genLive(){
  const idx=S.order[S.ri];if(idx===undefined)return null;const it=LIVE[idx];if(!it||it.T>S.clk)return null;if(!it.B||it.B.length<it.A.length)return null;S.ri++;
  const id="L-"+String(S.ri).padStart(3,"0"),sealed=HASH.sealOn,mm=(LM.models||[]).find(q=>q.id===it.m)||{prov:"api"},f=it.A[it.A.length-1];S.seq=S.ri;
  const sc={id,src:"live",item:it,model:it.m,mode:it.A.length>1?"repair x"+(it.A.length-1):"oneshot",born:S.clk,sealed,status:"?",nsteps:0,vref:"",verdict:"",xml:"",nb:null,blank:false,T:it.T};
  const M=S.mod[it.m]||(S.mod[it.m]={n:0,first:0,rep:0,repOk:0,cost:0,valid:0}),usd=it.A.reduce((a,b)=>a+b.u,0);M.n++;M.cost+=usd;S.cost+=usd;S.stage.gen++;S.liveIds.set(idx,id);
  let x=it.B[0];
  it.A.forEach((a,k)=>{
    const base={model:it.m,provider:mm.prov,prompt_id:it.p,prompt_sha256:it.psha.slice(0,16),tokens_in:a.ti,tokens_out:a.to,latency_ms:a.ms,cost_usd_est:a.u,max_tokens:mm.max_out,finish:a.fin,run_s:a.t0,ms:a.ms,ms_src:"recorded"};
    if(mm.temp!=null)base.temperature=mm.temp;
    if(k===0)x=addStep(it.B[0],{op:"generate",condition:"oneshot",...base,input_sha256:"none"},it.B[0],sealed);
    else{x=addStep(x,{op:"repair",kind:"model",round:k,report_shown:true,report_sha256:it.A[k-1].rsha,fixes:codesOf(it.A[k-1]),...base},it.B[k],sealed);S.stage.rep++;M.rep++}
    x=addStep(x,{op:"validate",validator:"fork",validator_ref:LM.validator,verdict:a.ok?"valid":"invalid",codes:codesOf(a),...(a.ok?{}:{finding:findingOf(a)}),xsd_valid:!!a.x,n_errors:(a.xe||[]).length+(a.se||[]).length,ms:a.vms,ms_src:"measured"},x,sealed)});
  if(it.A[0].ok){M.first++;S.stage.v1p++}else S.stage.v1f++;
  if(!it.A[0].ok&&f.ok){S.stage.v2p++;M.repOk++}
  const nb=f.r.nb??0;sc.nb=nb;sc.blank=nb<.005;sc.drawKind=kindOf(it);
  x=addStep(x,{op:"render",renderer:"x_ite@16.5.0 headless swiftshader (offline, after the run)",load_ok:!f.r.err,nodes:f.r.nodes??0,nonblank_ratio:nb,frames_watched:f.r.frames||0,no_frame:f.r.nf?1:0,parser_msgs:f.r.nmsg||0,unknown_nodes:f.r.unknown||0,ms:f.r.ms||0,ms_src:"measured"},x,sealed);
  if(!sc.blank)S.stage.ren++;if(f.ok){M.valid++;S.stage.ok++}else S.stage.drop++;
  sc.vref=LM.validator;finish(sc,x,f.ok?"valid":"invalid");return sc}
/* Replay scene (v3 427): recorded 11 Oct verdicts; replay always starts at the service that was live on 11 Oct; a later fork is applied by re-validation (38-ladder) */
function genReal(){
  const idx=S.order[S.ri];if(idx===undefined)return null;const it=REAL[idx];if(!it)return null;if(S.ri*2>S.clk)return null;S.ri++;
  const id="R-"+String(S.ri).padStart(3,"0"),sealed=HASH.sealOn;S.seq=S.ri;
  const sc={id,src:"real",item:it,model:it.m,mode:it.mo,born:S.clk,sealed,status:"?",nsteps:0,vref:"",verdict:"",xml:"",nb:null,blank:false,T:(S.ri-1)*2};
  const M=S.mod[it.m]||(S.mod[it.m]={n:0,first:0,rep:0,repOk:0,cost:0,valid:0}),costEst=+(it.rc/it.nrun).toFixed(5);M.n++;M.cost+=costEst;S.cost+=costEst;S.stage.gen++;
  let x=it.b;
  x=addStep(x,{op:"generate",model:it.m,provider:"vllm_l4",run:it.rid,hardware:it.hw,condition:it.mo==="grounded"?"report_repair":"oneshot",temperature:.4,max_tokens:8000,prompt_id:it.p,prompt_sha256:it.psha.slice(0,16),
    attempts_total:it.at,earlier_attempts:it.earlier.map((e,i)=>({attempt:i+1,xsd_valid:!!e[0],semantic_valid:!!e[1]})),tokens_in:it.ti,tokens_out:it.to,latency_ms:it.lat,cost_apportioned_usd:costEst,ms:it.lat,ms_src:"recorded",input_sha256:"none"},x,sealed);
  const svcOk=it.x&&it.s;if(it.at===1&&svcOk){M.first++;S.stage.v1p++}else S.stage.v1f++;
  if(it.at>1){S.stage.rep+=it.at-1;M.rep+=it.at-1;if(svcOk){S.stage.v2p++;M.repOk++}}
  const v0=vStep(sc,VALS[0]);x=addStep(x,v0.rec,x,sealed);
  {const nb=it.r.nb??0;sc.nb=nb;sc.blank=nb<.005;sc.drawKind=kindOf(it);
    x=addStep(x,{op:"render",renderer:"x_ite@16.5.0 headless swiftshader (offline)",load_ok:!it.r.err,nodes:it.r.nodes??0,nonblank_ratio:nb,frames_watched:it.r.frames||0,no_frame:it.r.nf?1:0,parser_msgs:it.r.nmsg||0,unknown_nodes:it.r.unknown||0,ms:it.r.ms||0,ms_src:"measured"},x,sealed);
    if(!sc.blank)S.stage.ren++}
  if(svcOk){M.valid++;S.stage.ok++}else S.stage.drop++;
  sc.vref=VALS[0].ref;finish(sc,x,v0.verdict);
  if(S.vi>0)revalidateOne(sc,curV());
  return sc}
/* 24 Oct run (SPEC §12.3): documented stub; reads RUN24 when present. Lanes per model|arm, autofix rows as repair {kind:"deterministic"}. Registered only when BUILD.has_run24. */
function genRun24(){if(!self.RUN24||!RUN24.items)return null;const idx=S.order[S.ri];if(idx===undefined)return null;const it=RUN24.items[idx];if(!it||it.T>S.clk)return null;S.ri++;
  const id="N-"+String(S.ri).padStart(3,"0"),sealed=HASH.sealOn;S.seq=S.ri;const f=it.A[it.A.length-1];
  const sc={id,src:"live",run:"24oct",item:it,model:it.m+(it.arm?" · "+it.arm:""),mode:it.A.length>1?"repair x"+(it.A.length-1):"oneshot",born:S.clk,sealed,status:"?",nsteps:0,vref:"",verdict:"",xml:"",nb:null,blank:false,T:it.T};
  let x=it.B&&it.B[0]||"<X3D version='4.0' profile='Interchange'><Scene/></X3D>";
  it.A.forEach((a,k)=>{const base={model:it.m,arm:it.arm||"A",prompt_id:it.p,tokens_in:a.ti,tokens_out:a.to,latency_ms:a.ms,tft_ms:a.tft_ms,finish:a.fin,run_s:a.t0,ms:a.ms,ms_src:"recorded"};
    if(k===0)x=addStep(x,{op:"generate",condition:"oneshot",...base,input_sha256:"none"},x,sealed);
    else if(a.agent==="autofix")x=addStep(x,{op:"repair",kind:"deterministic",agent:"autofix:fork@8dd0d3e",round:k,report_shown:false,fixes:a.fix_kinds||[],...base},it.B[k]||x,sealed);
    else x=addStep(x,{op:"repair",kind:"model",round:k,report_shown:true,fixes:codesOf(it.A[k-1]),...base},it.B[k]||x,sealed);
    x=addStep(x,{op:"validate",validator:"fork",validator_ref:(RUN24.meta&&RUN24.meta.validator)||"fork@8dd0d3e",verdict:a.ok?"valid":"invalid",codes:codesOf(a),ms:a.vms||0,ms_src:"measured"},x,sealed)});
  sc.vref=(RUN24.meta&&RUN24.meta.validator)||"fork@8dd0d3e";finish(sc,x,f.ok?"valid":"invalid");return sc}
/* ---------- modes ---------- */
MODES.register("live17",{label:"17 OCT",gen:genLive,tmax:()=>Math.max((self.LM&&LM.t_total)||0,...(self.LIVE||[]).map(i=>i.T||0)),order:()=>(self.LIVE||[]).map((_,i)=>i).sort((a,b)=>LIVE[a].T-LIVE[b].T),
  ready:()=>!!(self.LIVE&&LIVE.length&&LIVE[0].B&&LIVE[0].B.length),lanes:()=>((self.LM&&LM.models)||[]).map(m=>m.id),meta:()=>self.LM,honesty:"RECORDED 17 Oct · replayed on the run's own clock · 1109 s idle collapsed"});
MODES.register("replay11",{label:"11 OCT",gen:genReal,tmax:()=>(self.REAL?REAL.length:174)*2,order:()=>{const rnd=mulberry32(1017),o=(self.REAL||[]).map((_,i)=>i);for(let i=o.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[o[i],o[j]]=[o[j],o[i]]}return o},
  ready:()=>!!(self.REAL&&REAL.length),lanes:()=>[...new Set((self.REAL||[]).map(i=>i.m))],meta:()=>null,honesty:"RECORDED 11 Oct · no run clock was recorded, scenes spaced 2 s apart on the page clock"});
if(typeof BUILD!=="undefined"&&BUILD&&BUILD.has_run24)MODES.register("run24",{label:"24 OCT",gen:genRun24,tmax:()=>(self.RUN24&&RUN24.meta&&RUN24.meta.t_total)||0,order:()=>((self.RUN24&&RUN24.items)||[]).map((_,i)=>i).sort((a,b)=>RUN24.items[a].T-RUN24.items[b].T),ready:()=>!!(self.RUN24&&RUN24.items),lanes:()=>[...new Set(((self.RUN24&&RUN24.items)||[]).map(i=>i.m+(i.arm?" · "+i.arm:"")))],honesty:"RECORDED 24 Oct · fork@8dd0d3e"});
/* ---------- the clock (v3 871, dt-based) ---------- */
let lastClockEmit=0,pendingBatch=false;
function step(dt){
  if(!S||!cur)return;if(!cur.ready())return;if(!S.order.length)S.order=cur.order();
  if(!S.paused&&!S.done){S.clk=Math.min(SIM.tmax(),S.clk+S.rate*dt/1000);S.tick++;const t0=performance.now();
    for(let i=0;i<8;i++){const sc=cur.gen();if(!sc)break;if(performance.now()-t0>6)break}
    if(S.ri>=S.order.length&&S.order.length){S.done=true;S.paused=true;logEv("sys",`${cur.label}: run complete, ${S.scenes.length} scenes${S.mode==="live17"&&self.LIVESTATS?" from "+LIVESTATS.calls+" real calls":""}. Press Restart to run it again.`);emit("done",S);if(self.LOOP)LOOP.dirty(LOOP.bits.SCENE|LOOP.bits.CLOCK)}
    if(self.LOOP)LOOP.dirty(LOOP.bits.CLOCK)}
  scrub(4);
  if(performance.now()-lastClockEmit>100){lastClockEmit=performance.now();emit("clock",S.clk)}}
/* scrubber: verify pending chains first (≤ 4 per frame; bulk through the worker), then sweep the window as v3 did */
function scrub(n){
  if(S.pendingVerify.size>24&&!pendingBatch&&self.HASH){pendingBatch=true;const ids=[...S.pendingVerify].slice(0,96);S.pendingVerify.clear();const xs=ids.map(id=>S.byId.get(id)).filter(Boolean);
    HASH.batch(xs.map(s=>s.id),xs.map(s=>s.xml)).then(st=>{st.forEach((r,i)=>{const sc=xs[i];if(sc&&sc.status==="?"){sc.status=r.status;sc.__verified=true}});emit("verify",xs);if(self.LOOP)LOOP.dirty(LOOP.bits.VERIFY)}).catch(()=>{xs.forEach(s=>S.pendingVerify.add(s.id))}).finally(()=>{pendingBatch=false});return}
  let k=0;for(const id of S.pendingVerify){if(k++>=n)break;S.pendingVerify.delete(id);const sc=S.byId.get(id);if(!sc)continue;const vr=verify(sc.xml);if(sc.status!==vr.status){sc.status=vr.status;sc.__verified=true;if(!S.ff)emit("verify",[sc])}}
  if(k)return;
  for(let i=0;i<n&&S.scenes.length;i++){
    S.scr=(S.scr+1)%S.scenes.length;const sc=S.scenes[S.scr],vr=verify(sc.xml);
    if(sc.status!==vr.status){sc.status=vr.status;if(!S.ff)emit("verify",[sc]);
      if(!vr.ok&&sc.injured&&!sc.detected){sc.detected=true;S.detected++;const ttd=(performance.now()-sc.injured.t)/1000;S.ttd.push(ttd);S.det.push({t:S.clk});S.sec.d++;
        logEv("det",`${sc.id}: ${vr.status.toUpperCase()} after ${ttd.toFixed(2)}s · ${vr.problems[0]}`)}}}
  if(!S.ff&&self.LOOP)LOOP.dirty(LOOP.bits.VERIFY)}
/* ---------- controls ---------- */
function seekTo(t){if(!S||!cur||!cur.ready())return;const mode=S.mode,rate=S.rate,paused=S.paused;fresh(mode);S.ff=true;S.clk=Math.max(0,Math.min(SIM.tmax(),+t||0));S.rate=rate;
  const t0=performance.now();for(;;){const sc=cur.gen();if(!sc)break;if(performance.now()-t0>4000)break}
  while(S.pendingVerify.size){scrub(64)}S.ff=false;S.paused=paused;if(S.ri>=S.order.length&&S.order.length){S.done=true;S.paused=true}
  emit("seek",S.clk);if(self.LOOP)LOOP.dirtyAll();return S.clk}
function setRate(r){if(!S)return;S.rate=+r||30;emit("rate",S.rate);if(self.LOOP)LOOP.dirty(LOOP.bits.CLOCK)}
function pickScene(f){if(!S)return null;const sc=S.scenes.slice().reverse().find(f);if(sc){S.sel=sc.id;emit("select",sc.id);if(self.LOOP)LOOP.dirty(LOOP.bits.SELECT)}return sc}
SIM.step=step;SIM.seekTo=seekTo;SIM.setRate=setRate;SIM.fresh=fresh;SIM.pickScene=pickScene;SIM.scrub=scrub;
SIM.select=id=>{if(!S)return;S.sel=id;emit("select",id);if(self.LOOP)LOOP.dirty(LOOP.bits.SELECT)};
SIM.pause=()=>{if(!S)return;S.paused=true;emit("pause",true);if(self.LOOP)LOOP.dirty(LOOP.bits.CLOCK)};
SIM.resume=()=>{if(!S)return;if(S.done){fresh(S.mode)}S.paused=false;emit("pause",false);if(self.LOOP)LOOP.dirty(LOOP.bits.CLOCK)};
SIM.toggle=()=>S&&S.paused?SIM.resume():SIM.pause();
SIM.restart=()=>{fresh(S?S.mode:"live17");S.paused=false;logEv("sys","restarted ("+S.mode+")");emit("mode",S.mode)};
SIM.addViewerScene=sc=>{if(!S)return null;const n=S.viewer.length+1;sc.id=sc.id||(sc.src==="bench"?"B-":"V-")+String(n).padStart(3,"0");sc.src=sc.src||"viewer";sc.born=S.clk;sc.sealed=!!sc.sealed;sc.status="?";sc.vref=sc.vref||"js-port-of-8dd0d3e";S.viewer.push(sc);finish(sc,sc.xml,sc.verdict);return sc};
SIM.start=mode=>{fresh(mode||"live17");if(self.LOOP){LOOP.sim=step}return S};
Object.assign(self,{SIM,MODES,VALS,judge,vStep,finish,genLive,genReal,genRun24,fresh,seekTo,setRate,pickScene,logEv,lastRef,WIN});
})();
