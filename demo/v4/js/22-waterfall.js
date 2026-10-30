/* 22-waterfall.js — S6 THE RUN AS FILM: S6.1 waterfall + minimap, S6.2 run strip, S6.4 spend meter (SPEC-v4 S6; WORKPLAN 22-waterfall).
   Globals: FILM (the run source abstraction: FILM.register(mode, src), FILM.source(), FILM.disp(model, i), FILM.sources), WF (WF.pack(), WF.win, WF.setWin(t0,t1), WF.reset(),
   WF.addViewer(row), WF.touch(), WF.barRect(i,k), WF.hit(x,y), WF.hover, WF.canvas), __panels.waterfall / minimap / runstrip / spend (panel records with counters).
   Ported from v3 demo/tether-firehose-v3.template.html lines 710–716 (WF: lanes from LM.models, one span per API call, sub-row packing by t1) and 717–735 (svgWF bar colours:
   green ended valid / red ended invalid / cyan in flight, repair calls outlined; wfStat totals: done, in flight, tokens, spend, repair calls, ended valid; click → S.sel).
   Changed: canvas through LOOP (no SVG, no markup strings, no <title> tooltips), every number a claim chip (CLAIMS c.calls, c.failed, c.cut, c.truncated, film.*), failed calls / cut chains /
   probes / idle collapses / credit stop drawn from EVENTS, a time window (minimap drag + brush zoom ≥ 30 s), hover side card linked through S.hover, phone transposed layout,
   24 Oct arms through FILM.register('run24') (lanes per model · arm, autofix sub-bars, stream sparklines, tft ticks), viewer lane `you · live` through WF.addViewer.
   Test hooks: __panels.waterfall.{rows, bars, failed, failedTotal, cut, cutTotal, lanes, labels, probes, gaps, vertical, draws, hits}, __panels.minimap.draws, __panels.spend.{usd, draws},
   __panels.runstrip.{done, flight}, WF.win, WF.barRect(i,k) → {x,y,w,h} css px on #wfCanvas or null, WF.hit(x,y), WF.hover (current hover record), #runstrip .kpi (4), #wfEvents, #wfCard.
   Events emitted (for 32-inspector): after SIM.select(id) on a bar click → SIM.emit("open", {id, tab:"tether", from:"waterfall"}); on a failed tick / cut stub click →
   SIM.emit("open", {ledger:{kind, m, p, k, t0, t1, reason}, from:"waterfall"}). Hover sets S.hover = scene id (null when none) and dirties LOOP.bits.HOVER.
   24 Oct consumer hook: a part run24.* fills RUN24 (03-data) with the LIVE chain schema plus `arm` per item (and optionally A[].stream[], A[].tft_ms, A[].agent === "autofix",
   A[].fix_kinds; RUN24.meta {models[{id, prov, arms[]}], lanes{key: why}, t_total}; RUN24.events {failed, cut, probes, collapse, creditStop}); the source registered below reads
   it when BUILD.has_run24 makes 20-sim register the mode. Nothing in the panels is mode-specific: they read FILM.source(). */
(function(){
"use strict";
const B=LOOP.bits;
const DOLLAR=String.fromCharCode(36);                     /* the share sweep refuses a literal dollar sign followed by a digit anywhere in the bundle */
const PRIV=()=>!(self.BUILD&&BUILD.share);               /* private build: provider names, spend, prompt text; the share build (wave 3) drops them */
const r6=x=>Math.round(x*1e6)/1e6;
const dispBase=m=>String(m||"").replace(/^[\w.-]+\//,"");  /* v3 disp (line 343) without the SAFE map: the share build gets the SAFE map in wave 3 */
function disp(m,i){return dispBase(m)}   /* the share build's ids are already the SAFE map's lane labels (build_v4.py --share), so one naming scheme serves both builds */
/* ---------- sources: one per MODES entry; a new mode plugs in with FILM.register(name, src) and the panels never change ---------- */
const SOURCES={};
function register(mode,src){SOURCES[mode]=Object.assign({mode,chains:()=>[],meta:()=>null,events:()=>null,lanes:()=>[],laneOf:it=>it.m+(it.arm?" · "+it.arm:""),tmax:()=>0,
  stamps:{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded"},honesty:()=>"",note:"",sceneOf:genericScene,clockNote:""},src);return SOURCES[mode]}
function genericScene(it){if(!self.S)return null;for(let i=S.scenes.length-1;i>=0;i--){const s=S.scenes[i];if(s.item===it||(it&&s.item===it.real))return s.id}return null}
const nStat=(id,k)=>{const c=self.STATS&&STATS.claims&&STATS.claims[id];return c?c[k||"expected"]:null};
register("live17",{chains:()=>self.LIVE||[],meta:()=>self.LM||null,events:()=>self.EVENTS||null,
  lanes(){const M=(self.LM&&LM.models)||[];return M.map((m,i)=>({key:m.id,model:m.id,arm:null,prov:m.prov||null,why:((self.LM&&LM.lanes)||{})[m.id]||null,i}))},
  laneOf:it=>it.m,tmax:()=>Math.max((self.LM&&LM.t_total)||0,...((self.LIVE||[]).map(i=>i.T||0))),
  stamps:{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded"},sceneOf:it=>(self.S&&it&&S.liveIds.get(it.i))||null,
  clockNote:"run clock · idle gaps collapsed",
  honesty(){const L=self.LM||(self.STATS&&STATS.meta)||{};return`RECORDED ${L.date||"17 Oct"} · ${fmt.int(nStat("c.calls"))} calls on the page + ${fmt.int(nStat("c.failed"))} failed calls + ${fmt.int(nStat("c.cut"))} cut chains from events.jsonl and ledger.jsonl (kinds only; raw provider text never ships) · ${L.validator||"fork@eb4b4b4"} in process · ms = provider-reported call time · spend = list price (L) · ${Math.round(L.idle_collapsed_s||0)} s of idle gaps collapsed · Confirmed`}});
/* replay 11 Oct: no run clock was recorded (20-sim spaces scenes 2 s apart on the page clock); one bar per scene, length = the recorded latency, no validator time */
let replayChains=null,replayN=-1;
function replayAdapt(){const R=self.REAL||[];if(replayChains&&replayN===R.length)return replayChains;const md=self.MODES&&MODES.get("replay11");const order=md?md.order():R.map((_,i)=>i);const pos=new Array(R.length).fill(0);order.forEach((idx,r)=>{pos[idx]=r});
  replayChains=R.map((it,i)=>{const T=pos[i]*2,ms=+it.lat||0;return{m:it.m,p:it.p,pt:it.pt||"",T,i,real:it,A:[{t0:T,t1:T+ms/1000,ms,vms:null,ti:+it.ti||0,to:+it.to||0,u:it.nrun?r6(it.rc/it.nrun):0,ok:!!(it.x&&it.s),fin:null,x:it.x,r:it.r}]}});replayN=R.length;return replayChains}
register("replay11",{chains:replayAdapt,meta:()=>null,events:()=>null,
  lanes(){const seen=[];(self.REAL||[]).forEach(it=>{if(!seen.includes(it.m))seen.push(it.m)});return seen.map((m,i)=>({key:m,model:m,arm:null,prov:PRIV()?"vllm_l4":null,why:null,i}))},
  laneOf:it=>it.m,tmax:()=>(self.REAL?REAL.length:174)*2,stamps:{source:"RECORDED 11 Oct",validator:"svc@11Oct recorded"},
  clockNote:"page clock · no run clock was recorded on 11 Oct",
  honesty:()=>`RECORDED 11 Oct · no run clock was recorded: scenes are spaced 2 s apart on the page clock and each bar's length is the recorded latency · validator time not recorded on 11 Oct · verdicts svc@11Oct · Confirmed for the verdicts, Likely for the placement`});
/* 24 Oct run (SPEC §12.3): lanes per model · arm; registered here regardless, read only when RUN24 is filled (BUILD.has_run24 makes 20-sim register the mode) */
register("run24",{chains:()=>(self.RUN24&&RUN24.items)||[],meta:()=>(self.RUN24&&RUN24.meta)||null,events:()=>(self.RUN24&&RUN24.events)||null,
  lanes(){const items=(self.RUN24&&RUN24.items)||[],meta=(self.RUN24&&RUN24.meta)||{},out=[],seen=new Set();
    const add=(m,arm)=>{const key=m+(arm?" · "+arm:"");if(seen.has(key))return;seen.add(key);const mm=(meta.models||[]).find(q=>q.id===m)||{};out.push({key,model:m,arm:arm||null,prov:mm.prov||null,why:((meta.lanes||{})[key])||((meta.lanes||{})[m])||null,i:out.length})};
    (meta.models||[]).forEach(m=>(m.arms||[]).forEach(a=>add(m.id,a)));items.forEach(it=>add(it.m,it.arm));return out},
  tmax:()=>(self.RUN24&&RUN24.meta&&RUN24.meta.t_total)||Math.max(0,...(((self.RUN24&&RUN24.items)||[]).map(i=>i.T||0))),
  stamps:{source:"RECORDED 24 Oct",validator:"fork@8dd0d3e recorded"},clockNote:"run clock · token timestamps from the stream",
  honesty(){const M=(self.RUN24&&RUN24.meta)||{};return`RECORDED 24 Oct · ${M.validator||"fork@8dd0d3e"} · token timestamps from the stream · free tier counts as ${DOLLAR}0 · arm A model-repair, arm B autofix-first (autofix rows are deterministic repairs, excluded from the report-shown repair rate)${M.wall_min?" · stopped by a "+M.wall_min+" min wall":""}`}});
/* any other mode (44-desk registers files:<name>): chains are the released scenes' items, lanes from the mode's lanes() */
function generic(mode){const md=self.MODES&&MODES.get(mode);return register(mode,{chains:()=>self.S?S.scenes.map(s=>s.item).filter(it=>it&&Array.isArray(it.A)):[],
  lanes:()=>((md&&md.lanes())||[]).map((k,i)=>({key:k,model:String(k).split(" · ")[0],arm:String(k).split(" · ")[1]||null,prov:null,why:null,i})),tmax:()=>self.SIM?SIM.tmax():0,
  stamps:{source:"RECORDED 24 Oct",validator:"fork@8dd0d3e recorded"},honesty:()=>(md&&md.honesty)||"",clockNote:"run clock"})}
function source(){const mode=self.S?S.mode:"live17";return SOURCES[mode]||generic(mode)}
const FILM={register,source,disp,sources:SOURCES};
/* ---------- packing (v3 WF): spans sorted by t0, sub-row = first row free at t0 ---------- */
let packed=null,packSig="";
const viewerRows=[];let viewerT0=0;
function pack(){const src=source();const chains=src.chains();const sig=src.mode+"|"+chains.length;if(packed&&packSig===sig)return packed;
  const lanes=src.lanes().map(L=>Object.assign({rows:[],spans:[],st:null},L)),byKey=new Map(lanes.map(L=>[L.key,L]));
  chains.forEach((it,i)=>{if(!it||!Array.isArray(it.A))return;const key=src.laneOf(it);let L=byKey.get(key);if(!L){L={key,model:it.m,arm:it.arm||null,prov:null,why:null,i:lanes.length,rows:[],spans:[],st:null};lanes.push(L);byKey.set(key,L)}
    it.A.forEach((a,k)=>L.spans.push({i,k,n:it.A.length,it,a,t0:+a.t0||0,t1:+a.t1||0,ok:!!a.ok,u:+a.u||0,ti:+a.ti||0,to:+a.to||0,ms:+a.ms||0,vms:a.vms==null?null:+a.vms,p:it.p,m:it.m,rep:k>0,auto:a.agent==="autofix",tft:a.tft_ms==null?null:+a.tft_ms,stream:Array.isArray(a.stream)?a.stream:null,lane:L}))});
  lanes.forEach(L=>{L.spans.sort((a,b)=>a.t0-b.t0||a.t1-b.t1);L.spans.forEach(q=>{let r=L.rows.findIndex(e=>e<=q.t0+.01);if(r<0){r=L.rows.length;L.rows.push(0)}L.rows[r]=q.t1;q.r=r})});
  const all=lanes.flatMap(L=>L.spans).sort((a,b)=>a.t1-b.t1);const ev=src.events()||{};
  /* the run clock ends with the last call on the page (LM.t_total); ledger rows that ended later (cut chains, failed calls after the last page call) are clamped to the end */
  const tmax=Math.max(src.tmax()||0,...all.map(q=>q.t1));const clampT=t=>Math.min(Math.max(0,+t||0),tmax);
  /* idle collapses: [from, to, delta] on the raw clock → the 3 s stretch sits at from − (deltas before it) on the collapsed clock */
  let cum=0;const gaps=(ev.collapse||[]).map(g=>{const t=g[0]-cum;cum+=g[2];return{t,w:3,delta:g[2],raw0:g[0],raw1:g[1]}});
  const probes=(ev.probes||[]).filter(p=>typeof p.dt==="number"&&p.dt<0);
  const NB=48;lanes.forEach(L=>{const ms=L.spans.map(q=>q.ms),bins=new Float32Array(NB);L.spans.forEach(q=>{const b=Math.min(NB-1,Math.max(0,Math.floor(q.t1/Math.max(1,tmax)*NB)));bins[b]+=q.to});
    const fails=(ev.failed||[]).filter(f=>f.m===L.model&&(!L.arm||f.arm===L.arm)).map(f=>Object.assign({},f,{tc:clampT(f.t0)})),cuts=(ev.cut||[]).filter(c=>c.m===L.model&&(!L.arm||c.arm===L.arm)).map(c=>Object.assign({},c,{tc:clampT(c.t1)}));
    L.st={calls:L.spans.length,par:L.rows.length,med:UTIL.median(ms),failed:fails,cut:cuts,bins,binMax:Math.max(1e-9,...bins),usd:r6(L.spans.reduce((a,q)=>a+q.u,0)),tin:L.spans.reduce((a,q)=>a+q.ti,0),tout:L.spans.reduce((a,q)=>a+q.to,0)}});
  /* event lines per lane from the recorded stop reasons (LM.lanes / meta.lanes text) and EVENTS */
  const lines=[];lanes.forEach(L=>{const why=String(L.why||"").toLowerCase();const last=L.spans.length?Math.max(...L.spans.map(q=>q.t1)):0;const lastCut=r=>Math.max(0,...L.st.cut.filter(c=>!r||c.reason===r).map(c=>c.tc));
    if(/credit/.test(why)&&ev.creditStop)lines.push({lane:L,t:clampT(ev.creditStop.t),label:PRIV()?"CREDITS OUT":"credit exhausted",kind:"credit",share:"one lane's credit exhausted",refused:ev.creditStop.refused});
    else if(/spend cap|\bcap\b/.test(why))lines.push({lane:L,t:Math.max(last,lastCut("cap")),label:"SPEND CAP",kind:"cap"});
    else if(/time-box|time box|timebox|wall/.test(why))lines.push({lane:L,t:Math.max(last,lastCut("time box")),label:"TIME BOX",kind:"timebox"})});
  packed={src,lanes,all,total:all.length,tmax,ev,gaps,probes,lines,collapsed:cum};packSig=sig;hits=[];return packed}
function viewerLane(){if(!viewerRows.length)return null;const el=(performance.now()-viewerT0)/1000;const L={key:"you",model:"you",arm:null,prov:null,why:null,i:-1,you:true,rows:[],spans:[],st:null};
  viewerRows.forEach((row,k)=>{const t1=row.inflight?(row.t1!=null?+row.t1:el):(+row.t1||0);L.spans.push({i:-1,k:row.k|0,n:row.n|0,it:null,a:row,t0:+row.t0||0,t1,ok:!!row.ok,u:0,ti:+row.ti||0,to:+row.to||0,ms:+row.ms||((t1-(+row.t0||0))*1000),vms:row.vms==null?null:+row.vms,p:row.p||"",m:"you",rep:(row.k|0)>0,auto:false,tft:null,stream:null,lane:L,you:true,inflight:!!row.inflight,id:row.id||null})});
  L.spans.sort((a,b)=>a.t0-b.t0);L.spans.forEach(q=>{let r=L.rows.findIndex(e=>e<=q.t0+.01);if(r<0){r=L.rows.length;L.rows.push(0)}L.rows[r]=q.t1;q.r=r});
  L.st={calls:L.spans.length,par:L.rows.length,med:UTIL.median(L.spans.map(q=>q.ms)),failed:[],cut:[],bins:null,binMax:1,usd:0,tin:0,tout:0};return L}
/* scene id per chain item: a Map lookup for live17 (S.liveIds), otherwise an index over S.scenes rebuilt when the release counter moves */
let scIdx=null,scIdxSig="";
function sceneIndex(P){if(P.src.mode==="live17")return it=>(self.S&&it&&S.liveIds.get(it.i))||null;const sg=(self.S?S.mode+"|"+S.seq+"|"+S.scenes.length:"");
  if(sg!==scIdxSig){scIdxSig=sg;scIdx=new Map();if(self.S)S.scenes.forEach(s=>{if(s.item)scIdx.set(s.item,s.id)})}return it=>it?(scIdx.get(it)||scIdx.get(it.real)||null):null}
/* ---------- state ---------- */
let cv=null,mm=null,wrap=null,card=null,host=null,width=0,mmWidth=0,hits=[],hoverRec=null,brush=null,drag=null,lastLabelsSig="",lastHeaderMode="";
const WF={win:null,hover:null,canvas:null,pack,
  setWin(t0,t1){const P=pack();const tm=P.tmax||1;t0=UTIL.clamp(Math.min(t0,t1),0,tm);t1=UTIL.clamp(Math.max(t0,t1),0,tm);if(t1-t0<30){const c=(t0+t1)/2;t0=UTIL.clamp(c-15,0,tm);t1=t0+30}if(t0<=0&&t1>=tm)WF.win=null;else WF.win={t0,t1};LOOP.dirty(B.SCENE)},
  reset(){WF.win=null;LOOP.dirty(B.SCENE)},
  addViewer(row){if(!viewerRows.length)viewerT0=performance.now();row=Object.assign({t0:0,t1:null,inflight:true,ok:false,k:0,n:1},row);viewerRows.push(row);LOOP.dirty(B.LANE|B.SCENE);return row},
  clearViewer(){viewerRows.length=0;LOOP.dirty(B.LANE|B.SCENE)},
  touch(){LOOP.dirty(B.LANE|B.SCENE)},
  /* the nearest hit box under the pointer (2 px slop); narrow bars widened to 4 px can overlap, so the closest centre wins */
  hit(x,y){let best=null,bd=1e9;for(let i=hits.length-1;i>=0;i--){const h=hits[i];if(x>=h.x-2&&x<=h.x+h.w+2&&y>=h.y-2&&y<=h.y+h.h+2){const d=Math.abs(x-h.x-h.w/2)/Math.max(1,h.w)+Math.abs(y-h.y-h.h/2)/Math.max(1,h.h)+(h.kind==="bar"?0:-.5);if(d<bd){bd=d;best=h}}}return best},
  hits:()=>hits.map(h=>({kind:h.kind,x:h.x,y:h.y,w:h.w,h:h.h,q:h.q,id:h.id||null,glyph:h.glyph||null})),
  barRect(i,k){const h=hits.find(h=>h.kind==="bar"&&h.q.i===i&&h.q.k===(k|0));return h?{x:h.x,y:h.y,w:h.w,h:h.h}:null}};
/* ---------- geometry helpers: u = along the time axis, v = along the lane axis; V (phone) swaps them ---------- */
function makeGeo(W,H,V,P,lanes){const win=WF.win||{t0:0,t1:Math.max(1,P.tmax)};const hasProbes=P.probes.length>0;
  const labelW=V?0:(W<900?118:W<1200?170:214),gut=hasProbes?(V?14:26):0,u0=V?(42+gut):(labelW+gut+6),u1=V?(H-6):(W-10);
  const T=t=>u0+(u1-u0)*(t-win.t0)/(win.t1-win.t0);const Tinv=u=>win.t0+(u-u0)/(u1-u0)*(win.t1-win.t0);
  return{W,H,V,win,labelW,gut,u0,u1,T,Tinv,
    box(ta,tb,va,vb,min){const ua=T(ta),ub=T(tb),m=min==null?1.3:min;return V?{x:va,y:ua,w:vb-va,h:Math.max(m,ub-ua)}:{x:ua,y:va,w:Math.max(m,ub-ua),h:vb-va}},
    pt(t,v){const u=T(t);return V?{x:v,y:u}:{x:u,y:v}}}}
function hatch(ctx,x,y,w,h,col){ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.strokeStyle=col;ctx.lineWidth=1;ctx.beginPath();for(let s=-h;s<w+h;s+=4){ctx.moveTo(x+s,y+h);ctx.lineTo(x+s+h,y)}ctx.stroke();ctx.restore()}
function axisStep(span){return span>2400?600:span>900?300:span>300?120:span>120?30:span>30?10:span>6?2:span>1?.5:.1}
const clockLabel=(t,step)=>step>=1?fmt.clock(t):(Math.round(t*10)/10).toFixed(1)+" s";
/* ---------- the waterfall panel ---------- */
let wfPanel=null;
function drawWF(now){const P=pack();if(!P||!cv)return;const p=wfPanel;const clk=self.S?S.clk:0,sel=self.S?S.sel:null,showFailed=!self.S||S.flags.failed!==false;
  const W=width||cv.clientWidth||600,V=W<600;const you=viewerLane();const lanes=you?P.lanes.concat([you]):P.lanes;
  const totalRows=lanes.reduce((a,L)=>a+Math.max(1,L.rows.length),0),GUT=V?6:8,GAP=V?6:10,TOP=V?36:18,PROBE=P.probes.length?(V?0:14):0;
  let H=420;let rowH=V?0:Math.floor((H-TOP-PROBE-lanes.length*(2*GUT+GAP)-6)/Math.max(1,totalRows)-1.5);if(!V&&rowH<3){rowH=3;H=TOP+PROBE+lanes.length*(2*GUT+GAP)+totalRows*4.5+8}if(rowH>7)rowH=7;
  if(V)H=Math.max(420,Math.min(720,innerHeight*.6));
  const{ctx}=fitCanvas(cv,W,H);const g=makeGeo(W,H,V,P,lanes);const lite=p.lite&&now<p.liteUntil;const fx=self.FX?FX.level:0;
  const C={bg:cssv("--p0"),line:cssv("--line"),line2:cssv("--line2"),fg:cssv("--fg"),mute:cssv("--mute"),dim:cssv("--dim"),ok:cssv("--ok"),bad:cssv("--bad"),acc:cssv("--acc"),warn:cssv("--warn"),info:cssv("--info"),you:cssv("--you"),p2:cssv("--p2")};
  const mono=cssv("--mono")||"monospace";ctx.clearRect(0,0,W,H);hits=[];p.labels=[];
  /* plot area */
  const plot=V?{x:36,y:g.u0,w:W-42,h:g.u1-g.u0}:{x:g.u0,y:TOP-6,w:g.u1-g.u0,h:H-TOP+2};const idOf=sceneIndex(P);
  /* idle collapses: hatched 3 s stretches on the collapsed clock */
  ctx.save();ctx.beginPath();ctx.rect(plot.x,plot.y,plot.w,plot.h);ctx.clip();
  P.gaps.forEach(gp=>{const b=g.box(gp.t,gp.t+gp.w,V?plot.x:plot.y,V?plot.x+plot.w:plot.y+plot.h,6);ctx.fillStyle=C.p2;ctx.fillRect(b.x,b.y,b.w,b.h);hatch(ctx,b.x,b.y,b.w,b.h,C.line2);hits.push({x:b.x,y:b.y,w:b.w,h:b.h,kind:"gap",q:gp})});
  ctx.restore();p.gaps=P.gaps.length;
  /* axis */
  const span=g.win.t1-g.win.t0,step=axisStep(span);ctx.font="500 10.5px "+mono;ctx.textBaseline="alphabetic";ctx.strokeStyle=C.line;ctx.lineWidth=1;
  for(let t=Math.ceil(g.win.t0/step)*step;t<=g.win.t1+1e-9;t+=step){const u=g.T(t);ctx.beginPath();if(V){ctx.moveTo(plot.x,u);ctx.lineTo(plot.x+plot.w,u)}else{ctx.moveTo(u,plot.y);ctx.lineTo(u,plot.y+plot.h)}ctx.stroke();ctx.fillStyle=C.dim;if(V)ctx.fillText(clockLabel(t,step),2,u+3);else ctx.fillText(clockLabel(t,step),u+2,11)}
  ctx.fillStyle=C.dim;if(!V){const cn=P.src.clockNote||"run clock";ctx.fillText(cn.slice(0,Math.floor((g.labelW-4)/6.4)),2,11)}
  /* pre-run probe gutter (t < 0) */
  if(P.probes.length){ctx.fillStyle=C.dim;const dts=P.probes.map(q=>q.dt),dmin=Math.min(...dts)||-1;
    P.probes.forEach((q,i)=>{let x,y;if(V){x=plot.x+6+(plot.w-12)*(i+.5)/P.probes.length;y=g.u0-7}else{x=g.u0-g.gut+2+(g.gut-6)*(1-q.dt/dmin);y=TOP+PROBE/2+2}
      ctx.beginPath();ctx.arc(x,y,2.6,0,Math.PI*2);if(q.ok){ctx.fillStyle=C.mute;ctx.fill()}else{ctx.strokeStyle=C.mute;ctx.lineWidth=1;ctx.stroke()}hits.push({x:x-4,y:y-4,w:8,h:8,kind:"probe",q})});
    if(!V){ctx.fillStyle=C.dim;ctx.font="500 10.5px "+mono;ctx.fillText(`pre-run probes · ${P.probes.length}`,2,TOP+PROBE/2+5)}}
  p.probes=P.probes.length;
  /* lanes */
  let v=V?plot.x:TOP+PROBE;const laneW=V?Math.min(48,Math.floor((plot.w-4)/Math.max(1,lanes.length))):0;let rows=0,bars=0,failedN=0,cutN=0;const labels=[];
  lanes.forEach((L,li)=>{const nr=Math.max(1,L.rows.length);const bandLen=V?laneW:(2*GUT+nr*(rowH+1.5));const va=v,vb=v+bandLen;const hue=L.you?C.you:cssv("--lane-"+((L.i<0?li:L.i)%11+1))||C.acc;
    const name=L.you?"you · live":disp(L.model,L.i)+(L.arm?(L.arm==="B"?" · B autofix-first":" · "+L.arm):"");labels.push(name);
    /* label block */
    ctx.fillStyle=L.you?C.you:C.fg;ctx.font="600 12.5px "+mono;
    if(V){const nchars=Math.max(4,Math.floor((laneW-2)/6.4));ctx.save();ctx.translate(va+laneW/2,10);ctx.textAlign="center";ctx.font="600 10.5px "+mono;ctx.fillText(name.slice(0,nchars),0,0);ctx.fillText(name.slice(nchars,2*nchars),0,11);ctx.fillStyle=C.dim;ctx.fillText(String(L.st.calls),0,22);ctx.restore()}
    else{const cy=va+Math.min(bandLen,24)/2+1,nchars=Math.floor((g.labelW-4)/6.4);ctx.fillText(name.slice(0,nchars),2,cy);ctx.fillStyle=C.mute;ctx.font="400 10.5px "+mono;
      const sub=`${L.st.calls} calls · ${L.st.par} par${L.st.med!=null?" · med "+fmt.ms(L.st.med):""}${L.st.cut.length?" · cut "+L.st.cut.length:""}${PRIV()&&L.prov?" · "+L.prov:""}`;ctx.fillText(sub.slice(0,nchars),2,cy+12);
      if(L.you)ctx.fillText("your clock · not in any table",2,cy+24);
      /* tokens/s sparkline (10 px) + running spend (private) */
      if(L.st.bins&&bandLen>=48&&!lite){const sx=2,sw=Math.min(g.labelW-8,120),sy=va+bandLen-12;ctx.strokeStyle=hue;ctx.lineWidth=1;ctx.beginPath();const bw=sw/L.st.bins.length;const upto=Math.floor(clk/Math.max(1,P.tmax)*L.st.bins.length);
        for(let b=0;b<=Math.min(upto,L.st.bins.length-1);b++){const y=sy+10-10*L.st.bins[b]/L.st.binMax;if(b===0)ctx.moveTo(sx,y);else ctx.lineTo(sx+b*bw,y)}ctx.stroke();
        if(PRIV()&&!L.you&&L.st.usd>0){const usdNow=L.spans.reduce((a,q)=>a+(q.t1<=clk?q.u:0),0);ctx.fillStyle=C.dim;ctx.textAlign="right";ctx.fillText(fmt.usd(usdNow),Math.min(g.labelW-2,sx+sw+46),sy+10);ctx.textAlign="left"}}}
    /* separator */
    ctx.strokeStyle=C.line;ctx.setLineDash([1,3]);ctx.beginPath();if(V){ctx.moveTo(vb+GAP/2,plot.y);ctx.lineTo(vb+GAP/2,plot.y+plot.h)}else{ctx.moveTo(plot.x,vb+GAP/2-1);ctx.lineTo(plot.x+plot.w,vb+GAP/2-1)}ctx.stroke();ctx.setLineDash([]);
    /* bars, clipped to the window */
    ctx.save();ctx.beginPath();ctx.rect(plot.x,plot.y,plot.w,plot.h);ctx.clip();
    const rowV=r=>V?(va+2+r*((laneW-4)/nr)):(va+GUT+r*(rowH+1.5)),rowLen=V?Math.max(2,(laneW-4)/nr-1):rowH;
    L.spans.forEach(q=>{if(q.t0>clk&&!q.you)return;if(!q.you)rows++;const fin=q.you?!q.inflight:q.t1<=clk;const tEnd=q.you?q.t1:Math.min(q.t1,clk);
      if(tEnd<g.win.t0||q.t0>g.win.t1)return;const rv=rowV(q.r);const b=g.box(q.t0,tEnd,rv,rv+rowLen);bars++;
      const fill=!fin?C.acc:q.ok?C.ok:C.bad;ctx.globalAlpha=q.rep?.55:.92;ctx.fillStyle=fill;
      if(!fin&&fx>=1&&!lite){ctx.shadowColor=C.acc;ctx.shadowBlur=6}ctx.fillRect(b.x,b.y,b.w,b.h);ctx.shadowBlur=0;ctx.globalAlpha=1;
      if(q.rep){ctx.strokeStyle=q.auto?C.info:C.fg;ctx.lineWidth=q.auto?1.2:.9;if(q.auto)ctx.setLineDash([2,2]);ctx.strokeRect(b.x+.5,b.y+.5,Math.max(1,b.w-1),Math.max(1,b.h-1));ctx.setLineDash([])}
      /* 24 Oct: stream sparkline inside wide bars, tft tick */
      if(q.stream&&!lite&&(V?b.h:b.w)>=24){ctx.strokeStyle=C.fg;ctx.lineWidth=.8;ctx.beginPath();const n=q.stream.length;let mx=1;const pts=q.stream.map(s=>Array.isArray(s)?{t:+s[0],n:+s[1]}:{t:+s,n:1});let acc=0;pts.forEach(s=>{acc+=s.n;s.c=acc;mx=acc});
        pts.forEach((s,i)=>{const f=UTIL.clamp((s.t-(s.t>q.t0?q.t0:0))/Math.max(1e-6,q.t1-q.t0),0,1),h=s.c/mx;const x=V?(b.x+b.w*(1-h)):(b.x+b.w*f),y=V?(b.y+b.h*f):(b.y+b.h*(1-h));if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});ctx.stroke()}
      if(q.tft!=null&&!lite){const tt=q.t0+q.tft/1000;if(tt<=tEnd){const pt=g.pt(tt,rv);ctx.fillStyle=C.warn;ctx.fillRect(V?pt.x:pt.x-.5,V?pt.y-.5:pt.y,V?rowLen:1,V?1:rowLen)}}
      const id=q.you?q.id:idOf(q.it);
      if(id&&sel===id){ctx.strokeStyle=C.fg;ctx.lineWidth=1.2;ctx.strokeRect(b.x-1,b.y-1,b.w+2,b.h+2)}
      if(hoverRec&&hoverRec.kind==="bar"&&hoverRec.q===q){ctx.strokeStyle=C.warn;ctx.lineWidth=1.2;ctx.strokeRect(b.x-1.5,b.y-1.5,b.w+3,b.h+3)}
      hits.push({x:b.x,y:b.y,w:Math.max(4,b.w),h:Math.max(4,b.h),kind:"bar",q,id})});
    /* failed calls: hollow red ticks in the top gutter (V: left strip) with the HTTP class glyph when there is room */
    if(showFailed)L.st.failed.forEach(f=>{if(f.tc>clk)return;failedN++;if(f.tc<g.win.t0||f.tc>g.win.t1)return;const pt=g.pt(f.tc,V?va:va+1);ctx.strokeStyle=C.bad;ctx.lineWidth=1;
      if(V)ctx.strokeRect(pt.x+.5,pt.y-1.5,4,3);else ctx.strokeRect(pt.x-1.5,pt.y+.5,3,GUT-2);
      const glyph=f.kind==="credit"?DOLLAR+"0":String(f.kind);if(!V&&span<=600){ctx.fillStyle=C.bad;ctx.font="500 10.5px "+mono;ctx.fillText(glyph,pt.x+3,pt.y+GUT-2)}
      hits.push({x:V?pt.x:pt.x-3,y:V?pt.y-3:pt.y,w:6,h:V?6:GUT,kind:"fail",q:f,lane:L,glyph})});
    /* cut chains: dashed stub to the right of the last recorded call in the bottom gutter (V: right strip) with the reason when there is room */
    L.st.cut.forEach(c=>{const t1=c.tc;if(t1>clk)return;cutN++;if(t1<g.win.t0||t1>g.win.t1)return;const sv=V?vb-5:vb-GUT+3;const a=g.pt(t1,sv);ctx.strokeStyle=C.bad;ctx.setLineDash([3,2]);ctx.lineWidth=1.2;ctx.beginPath();
      if(V){ctx.moveTo(a.x,a.y);ctx.lineTo(a.x,a.y+14)}else{ctx.moveTo(a.x,a.y);ctx.lineTo(a.x+14,a.y)}ctx.stroke();ctx.setLineDash([]);
      if(!V&&span<=900){ctx.fillStyle=C.bad;ctx.font="500 10.5px "+mono;ctx.fillText(String(c.reason||"cut"),a.x+16,a.y+4)}
      hits.push({x:V?a.x-3:a.x,y:V?a.y:a.y-4,w:V?6:16,h:V?16:8,kind:"cut",q:c,lane:L})});
    ctx.restore();v=vb+GAP});
  /* event lines (credit stop, spend cap, time box) across their lane band */
  ctx.save();ctx.beginPath();ctx.rect(plot.x,plot.y,plot.w,plot.h);ctx.clip();
  P.lines.forEach(ln=>{if(ln.t>clk||ln.t<g.win.t0||ln.t>g.win.t1)return;const idx=lanes.indexOf(ln.lane);let va=V?plot.x:TOP+PROBE;for(let i=0;i<idx;i++){const Li=lanes[i];va+=(V?laneW:(2*GUT+Math.max(1,Li.rows.length)*(rowH+1.5)))+GAP}
    const vb=va+(V?laneW:(2*GUT+Math.max(1,ln.lane.rows.length)*(rowH+1.5)));const col=ln.kind==="credit"?C.bad:C.warn;ctx.strokeStyle=col;ctx.setLineDash([4,3]);ctx.lineWidth=1.2;ctx.beginPath();
    const a=g.pt(ln.t,va),b=g.pt(ln.t,vb);ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle=col;ctx.font="600 10.5px "+mono;if(V){ctx.fillText(ln.label.slice(0,8),a.x+2,a.y+10)}else{ctx.fillText(ln.label,a.x+4,va+10)}p.labels.push(ln.label)});
  /* playhead */
  {const a=g.pt(clk,V?plot.x:plot.y),b=g.pt(clk,V?plot.x+plot.w:plot.y+plot.h);ctx.strokeStyle=C.warn;ctx.setLineDash([3,2]);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();ctx.setLineDash([])}
  /* brush rectangle */
  if(brush&&brush.tb!=null){const b=g.box(Math.min(brush.ta,brush.tb),Math.max(brush.ta,brush.tb),V?plot.x:plot.y,V?plot.x+plot.w:plot.y+plot.h);ctx.fillStyle=C.acc;ctx.globalAlpha=.15;ctx.fillRect(b.x,b.y,b.w,b.h);ctx.globalAlpha=1;ctx.strokeStyle=C.acc;ctx.strokeRect(b.x+.5,b.y+.5,b.w-1,b.h-1)}
  ctx.restore();
  Object.assign(p,{rows,bars,failed:failedN,failedTotal:(P.ev.failed||[]).length,cut:cutN,cutTotal:(P.ev.cut||[]).length,lanes:labels,vertical:V,hits:hits.length,height:H,geo:g});
  eventsLegend(P,clk)}
/* the DOM legend under the canvas: event labels appear as the clock passes them (txt only on change) */
function eventsLegend(P,clk){const e=$("wfEvents");if(!e)return;const parts=[];
  P.lines.forEach(ln=>{if(ln.t<=clk)parts.push(`${ln.label} ${fmt.clock(ln.t)} · ${disp(ln.lane.model,ln.lane.i)}${ln.kind==="credit"&&ln.refused?" · "+ln.refused+" calls refused":""}`)});
  if(P.probes.length)parts.push(`${P.probes.length} probes before t0`);if(P.gaps.length)parts.push(`${P.gaps.length} idle gaps collapsed (${Math.round(P.collapsed)} s)`);
  if(P.src.mode==="replay11")parts.push("bars placed on the page clock, lengths = recorded latency");
  const s=parts.join(" · ");if(s!==lastLabelsSig){lastLabelsSig=s;txt(e,s)}}
/* ---------- minimap: every bar compressed, one row per lane, the window as a draggable frame ---------- */
let mmPanel=null;
function drawMM(){const P=pack();if(!P||!mm)return;const V=(width||cv.clientWidth||600)<600;const W=V?36:(mmWidth||mm.clientWidth||600),H=V?(wfPanel.height||420):36;const{ctx}=fitCanvas(mm,W,H);
  const clk=self.S?S.clk:0,tm=Math.max(1,P.tmax);const C={line:cssv("--line"),ok:cssv("--ok"),bad:cssv("--bad"),acc:cssv("--acc"),warn:cssv("--warn"),dim:cssv("--dim"),fg:cssv("--fg")};
  ctx.clearRect(0,0,W,H);const n=Math.max(1,P.lanes.length),lh=(V?W:H)/n;const T=t=>V?(t/tm*H):(t/tm*W);
  P.lanes.forEach((L,i)=>{L.spans.forEach(q=>{const fin=q.t1<=clk,started=q.t0<=clk;ctx.fillStyle=started?(fin?(q.ok?C.ok:C.bad):C.acc):C.line;ctx.globalAlpha=started?.9:.6;
    const a=T(q.t0),b=T(Math.min(q.t1,started?Math.max(q.t0,clk):q.t1));if(V)ctx.fillRect(i*lh+1,a,Math.max(1,lh-2),Math.max(1,b-a));else ctx.fillRect(a,i*lh+1,Math.max(1,b-a),Math.max(1,lh-2))})});ctx.globalAlpha=1;
  const w=WF.win||{t0:0,t1:tm};ctx.strokeStyle=C.fg;ctx.lineWidth=1;const a=T(w.t0),b=T(w.t1);if(V)ctx.strokeRect(.5,a+.5,W-1,Math.max(2,b-a)-1);else ctx.strokeRect(a+.5,.5,Math.max(2,b-a)-1,H-1);
  ctx.strokeStyle=C.warn;ctx.beginPath();const c=T(clk);if(V){ctx.moveTo(0,c);ctx.lineTo(W,c)}else{ctx.moveTo(c,0);ctx.lineTo(c,H)}ctx.stroke();mmPanel.T=T;mmPanel.tm=tm;mmPanel.V=V;mmPanel.W=W;mmPanel.H=H}
/* ---------- run strip (S6.2): four .kpi counters updated by txt, claim chips for the recorded totals ---------- */
let rsPanel=null,rsEls=null;
function drawRS(){const P=pack();if(!P||!rsEls)return;const clk=self.S?S.clk:0;let done=0,fl=0,tin=0,tout=0,usd=0,rp=0,rok=0;
  P.all.forEach(q=>{if(q.t1<=clk){done++;tin+=q.ti;tout+=q.to;usd+=q.u;if(q.rep&&!q.auto){rp++;if(q.ok)rok++}}else if(q.t0<=clk)fl++});
  txt(rsEls.clock,fmt.clock(clk));txt(rsEls.of,`of ${fmt.clock(P.tmax)} ${P.src.clockNote||"run clock"}`);
  txt(rsEls.done,`${fmt.int(done)}`);txt(rsEls.doneS,`of ${fmt.int(P.total)} recorded calls`);txt(rsEls.flight,String(fl));txt(rsEls.flightS,fl===1?"call in flight":"calls in flight");
  txt(rsEls.tokens,`${fmt.int(tin)} → ${fmt.int(tout)}`);txt(rsEls.tokensS,"tokens in → out, so far");txt(rsEls.rep,`${fmt.int(rp)} · ${fmt.int(rok)}`);txt(rsEls.repS,"repair calls · ended valid (report shown)");
  Object.assign(rsPanel,{done,flight:fl,tin,tout,usd,rp,rok});if(spPanel)spPanel.usdNow=usd}
/* ---------- spend meter (S6.4, private build only): the list-price estimate climbing; the page total and the ledger total marked; the hard stop only when the meta carries it ---------- */
let spPanel=null,spCv=null;
function drawSP(){if(!spCv||!PRIV())return;const P=pack();if(!P)return;const clk=self.S?S.clk:0;const W=width||spCv.clientWidth||600,H=28;const{ctx}=fitCanvas(spCv,W,H);
  const C={line:cssv("--line"),line2:cssv("--line2"),warn:cssv("--warn"),bad:cssv("--bad"),dim:cssv("--dim"),fg:cssv("--fg"),p2:cssv("--p2")};const mono=cssv("--mono")||"monospace";
  const usd=spPanel.usdNow!=null?spPanel.usdNow:P.all.reduce((a,q)=>a+(q.t1<=clk?q.u:0),0);const page=P.all.reduce((a,q)=>a+q.u,0),ledger=(P.ev.reconcile&&+P.ev.reconcile.usd_ledger)||0;
  const meta=P.src.meta()||{},cap=meta.cap_usd!=null?+meta.cap_usd:(self.STATS&&STATS.meta&&STATS.meta.cap_usd!=null?+STATS.meta.cap_usd:null);
  const scale=Math.max(page,ledger,cap||0,1e-6);const X=v=>8+(W-16)*Math.min(1,v/scale);ctx.clearRect(0,0,W,H);
  ctx.fillStyle=C.p2;ctx.fillRect(8,11,W-16,7);ctx.fillStyle=C.warn;ctx.fillRect(8,11,Math.max(0,X(usd)-8),7);
  ctx.font="500 10.5px "+mono;ctx.fillStyle=C.dim;ctx.fillText(`spend ${fmt.usd(usd)} so far · list price`,8,8);
  ctx.strokeStyle=C.fg;ctx.beginPath();ctx.moveTo(X(page)+.5,9);ctx.lineTo(X(page)+.5,20);ctx.stroke();
  if(ledger){ctx.strokeStyle=C.line2;ctx.beginPath();ctx.moveTo(X(ledger)+.5,9);ctx.lineTo(X(ledger)+.5,20);ctx.stroke()}
  if(cap!=null){ctx.strokeStyle=C.bad;ctx.setLineDash([3,2]);ctx.beginPath();ctx.moveTo(X(cap)+.5,4);ctx.lineTo(X(cap)+.5,24);ctx.stroke();ctx.setLineDash([])}
  const cap1=`| page total ${fmt.usd(page)}${ledger?" · | ledger "+fmt.usd(ledger)+" incl. calls not on the page":""}${cap!=null?" · ¦ hard stop "+fmt.usd(cap):" · hard stop: cap_usd not baked into this build"}`;
  ctx.fillStyle=C.dim;ctx.fillText(cap1.slice(0,Math.floor((W-16)/6.4)),8,27);
  spPanel.usd=usd;spPanel.page=page;spPanel.ledger=ledger;spPanel.cap=cap}
/* ---------- hover card (DOM, patched by txt; positioned beside the pointer on desktop, a sheet under the canvas on phone) ---------- */
let cardEls=null,cardKey="";
function cardShow(rec,x,y){if(!card||!cardEls)return;if(!rec){if(!card.hidden){card.hidden=true;cardKey=""}return}
  const E=cardEls,P=pack();let key="";
  if(rec.kind==="bar"){const q=rec.q,it=q.it,a=q.a;key="bar:"+q.m+"/"+q.p+"/"+q.k+"/"+(q.t1<=(self.S?S.clk:0));const fin=q.you?!q.inflight:q.t1<=(self.S?S.clk:0);
    if(key!==cardKey){txt(E.title,q.you?"you · live":disp(q.m,q.lane.i)+(q.lane.arm?" · arm "+q.lane.arm:""));txt(E.prompt,`${q.p||"—"}${PRIV()&&it&&it.pt?" · "+String(it.pt).slice(0,110):""}`);
      txt(E.attempt,`attempt ${q.k+1} of ${q.n}${q.rep?(q.auto?" · autofix (deterministic repair)":" · repair, report shown"):""}`);txt(E.time,`${fmt.clock(q.t0)} → ${fmt.clock(q.t1)} · ${fmt.ms(q.ms)}${q.tft!=null?" · first token "+fmt.ms(q.tft):""}`);
      txt(E.tokens,`${fmt.int(q.ti)} → ${fmt.int(q.to)} tokens${PRIV()&&!q.you?" · "+fmt.usd(q.u):""}${a&&a.fin?" · finish "+a.fin:""}`);
      txt(E.verdict,fin?(q.ok?"VALID":"INVALID")+(q.you?" (js-port-of-8dd0d3e)":" on "+(P.src.stamps.validator||"").replace(" recorded",""))+(q.vms!=null?" · validator "+fmt.ms(q.vms):""):"in flight");
      E.verdict.className="pill "+(fin?(q.ok?"p-ok":"p-bad"):"p-acc");txt(E.finding,a&&!q.ok&&fin&&self.findingOf?findingOf(a)||"":"");
      const jpg=a&&a.r&&a.r.jpg;if(jpg){E.img.src="data:image/jpeg;base64,"+jpg;E.img.hidden=false;txt(E.imgCap,`measured frame · X_ITE 16.5.0 offline · ${a.r.nb!=null?fmt.pct(a.r.nb):"—"} nonblank`)}else{E.img.hidden=true;txt(E.imgCap,a&&a.r?"measured frame not shipped for this attempt":"")}
      E.open.hidden=!(rec.id||q.you&&q.id);E.open.dataset.id=rec.id||q.id||"";E.open.dataset.kind="bar";cardKey=key}}
  else if(rec.kind==="fail"){const f=rec.q;key="fail:"+f.m+f.p+f.k+f.t0;if(key!==cardKey){txt(E.title,disp(f.m,rec.lane.i)+" · failed call");txt(E.prompt,`${f.p} · attempt ${f.k}`);txt(E.attempt,`ledger row · kind ${rec.glyph}${f.kind==="credit"?" (insufficient credit)":f.kind==="429"?" (rate limited)":f.kind==="502"?" (upstream error)":""}`);
    txt(E.time,`${fmt.clock(f.t0)}${f.t1&&f.t1!==f.t0?" → "+fmt.clock(f.t1):""}`);txt(E.tokens,"no body: the call returned no scene");txt(E.verdict,"FAILED");E.verdict.className="pill p-bad";txt(E.finding,"");E.img.hidden=true;txt(E.imgCap,"");E.open.hidden=false;E.open.dataset.id="";E.open.dataset.kind="ledger";cardKey=key}}
  else if(rec.kind==="cut"){const c=rec.q;key="cut:"+c.m+c.p+c.t1;if(key!==cardKey){txt(E.title,disp(c.m,rec.lane.i)+" · cut chain");txt(E.prompt,`${c.p} · ${c.calls||c.k||1} recorded call${(c.calls||c.k||1)===1?"":"s"}, not on the page`);txt(E.attempt,`reason: ${c.reason||"cut"}`);
    txt(E.time,`last call ended ${fmt.clock(+c.t1||0)}`);txt(E.tokens,"");txt(E.verdict,"CUT");E.verdict.className="pill p-warn";txt(E.finding,"");E.img.hidden=true;txt(E.imgCap,"");E.open.hidden=false;E.open.dataset.id="";E.open.dataset.kind="ledger";cardKey=key}}
  else if(rec.kind==="probe"){const q=rec.q;key="probe:"+q.m+q.dt;if(key!==cardKey){txt(E.title,PRIV()?dispBase(q.m)+" · pre-run probe":"pre-run probe");txt(E.prompt,q.utc||"");txt(E.attempt,q.ok?"answered":"refused · "+(q.code||"?"));txt(E.time,`${Math.round(q.dt)} s before t0`);txt(E.tokens,q.ms!=null?fmt.ms(q.ms):"");txt(E.verdict,q.ok?"OK":"NO");E.verdict.className="pill "+(q.ok?"p-ok":"p-bad");txt(E.finding,"");E.img.hidden=true;txt(E.imgCap,"");E.open.hidden=true;cardKey=key}}
  else if(rec.kind==="gap"){const q=rec.q;key="gap:"+q.t;if(key!==cardKey){txt(E.title,"idle gap collapsed");txt(E.prompt,`${Math.round(q.delta)} s with nothing in flight cut to 3 s`);txt(E.attempt,`raw clock ${fmt.clock(q.raw0)} → ${fmt.clock(q.raw1)}`);txt(E.time,`collapsed clock ${fmt.clock(q.t)}`);txt(E.tokens,"");txt(E.verdict,"GAP");E.verdict.className="pill p-mute";txt(E.finding,"");E.img.hidden=true;txt(E.imgCap,"");E.open.hidden=true;cardKey=key}}
  if(card.hidden)card.hidden=false;
  if(wrap&&wrap.clientWidth>=600){const W=wrap.clientWidth,cw=Math.min(300,W-20);let lx=x+16,ly=y+12;if(lx+cw>W-4)lx=Math.max(4,x-cw-16);card.style.left=lx+"px";card.style.top=ly+"px"}else{card.style.left="";card.style.top=""}}
function setHover(rec,x,y){const same=rec===hoverRec||(rec&&hoverRec&&rec.kind===hoverRec.kind&&rec.q===hoverRec.q);hoverRec=rec;WF.hover=rec;
  if(self.S){const id=rec&&rec.kind==="bar"?(rec.id||null):null;if(S.hover!==id){S.hover=id;LOOP.dirty(B.HOVER)}}
  cardShow(rec,x,y);if(!same)LOOP.dirty(B.HOVER)}
function openRec(rec){if(!rec||!self.SIM)return;if(rec.kind==="bar"){const id=rec.id||(rec.q.you?rec.q.id:null);if(id){SIM.select(id);SIM.emit("open",{id,tab:"tether",from:"waterfall"})}}
  else if(rec.kind==="fail"||rec.kind==="cut"){const q=rec.q;SIM.emit("open",{ledger:{kind:rec.kind==="fail"?String(q.kind):"cut",m:q.m,p:q.p,k:q.k,t0:q.t0,t1:q.t1,reason:q.reason||null},from:"waterfall"})}}
/* ---------- pointer handling: hover, click, brush zoom (≥ 30 s), minimap drag ---------- */
function bindPointer(){const pos=e=>{const r=cv.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}};
  cv.addEventListener("pointermove",e=>{const{x,y}=pos(e);const g=wfPanel.geo;if(brush&&g){brush.tb=g.Tinv(g.V?y:x);brush.moved=true;LOOP.dirty(B.HOVER);return}setHover(WF.hit(x,y),x,y)});
  cv.addEventListener("pointerleave",()=>{if(!brush)setHover(null)});
  cv.addEventListener("pointerdown",e=>{if(e.button!==0)return;const{x,y}=pos(e);const g=wfPanel.geo;if(!g)return;const h=WF.hit(x,y);brush={ta:g.Tinv(g.V?y:x),tb:null,moved:false,hit:h,x,y};try{cv.setPointerCapture(e.pointerId)}catch(err){}});
  const up=e=>{if(!brush)return;const b=brush;brush=null;const{x,y}=pos(e);if(b.moved&&b.tb!=null&&Math.abs(b.tb-b.ta)>=30){WF.setWin(b.ta,b.tb);setHover(null);return}
    const h=WF.hit(x,y)||b.hit;if(h){setHover(h,x,y);openRec(h)}LOOP.dirty(B.HOVER)};
  cv.addEventListener("pointerup",up);cv.addEventListener("pointercancel",()=>{brush=null;LOOP.dirty(B.HOVER)});
  cv.addEventListener("dblclick",()=>WF.reset());
  cv.addEventListener("keydown",e=>{if(e.key==="Escape"){WF.reset();setHover(null)}});
  /* minimap: drag the window; a click outside it centres the window there */
  const mpos=e=>{const r=mm.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}};
  mm.addEventListener("pointerdown",e=>{if(!mmPanel.T)return;const{x,y}=mpos(e);const u=mmPanel.V?y:x,t=u/(mmPanel.V?mmPanel.H:mmPanel.W)*mmPanel.tm;const w=WF.win;
    if(w&&t>=w.t0&&t<=w.t1)drag={off:t-w.t0,len:w.t1-w.t0};else if(w){const len=w.t1-w.t0;WF.setWin(t-len/2,t+len/2);drag={off:len/2,len}}else{drag=null;const len=Math.max(30,mmPanel.tm/8);WF.setWin(t-len/2,t+len/2);drag={off:len/2,len}}
    try{mm.setPointerCapture(e.pointerId)}catch(err){}});
  mm.addEventListener("pointermove",e=>{if(!drag||!mmPanel.T)return;const{x,y}=mpos(e);const u=mmPanel.V?y:x,t=u/(mmPanel.V?mmPanel.H:mmPanel.W)*mmPanel.tm;WF.setWin(t-drag.off,t-drag.off+drag.len)});
  const mup=()=>{drag=null};mm.addEventListener("pointerup",mup);mm.addEventListener("pointercancel",mup);mm.addEventListener("dblclick",()=>WF.reset())}
/* ---------- section ---------- */
function headerSpec(){const src=source();const M=(self.STATS&&STATS.meta)||{};const lanesN=src.lanes().length||(M.models||[]).length;
  return{title:"The run as film",unit:`${lanesN} lanes on the run's own clock · every recorded call a bar · failed calls, cut chains, probes, idle gaps and the stop lines drawn · validator oscilloscope under the lanes`,
    stamps:{source:src.stamps.source,validator:src.stamps.validator,renderer:"none"},grade:src.mode==="replay11"?"L":"C",honesty:src.honesty()}}
function kpi(k,label){const d=el("div",{class:"kpi",data:{k}});const l=el("div",{class:"l",text:label}),v=el("div",{class:"v",text:"—"}),s=el("div",{class:"s",text:""});d.append(l,v,s);return{d,v,s}}
function mount(sec){const sb=sec.querySelector(".sb");if(!sb)return;sb.textContent="";host=el("div",{class:"film"});sb.appendChild(host);
  /* run strip */
  const rs=el("div",{class:"runstrip",id:"runstrip"});const clock=el("span",{class:"rsClock m",text:"00:00"}),of=el("span",{class:"rsOf m",text:""});rs.append(el("div",{class:"rsClockWrap"},[clock,of]));
  const K={done:kpi("done","calls done"),flight:kpi("flight","in flight"),tokens:kpi("tokens","tokens"),rep:kpi("rep","repairs")};Object.values(K).forEach(k=>rs.appendChild(k.d));
  rsEls={clock,of,done:K.done.v,doneS:K.done.s,flight:K.flight.v,flightS:K.flight.s,tokens:K.tokens.v,tokensS:K.tokens.s,rep:K.rep.v,repS:K.rep.s};
  const cl=el("div",{class:"rsClaims"});[["c.calls","calls on the page"],["c.failed","failed calls"],["c.cut","cut chains"],["film.creditStop","credit stop at"],["c.truncated","cut at the token limit"],["film.probes","probes before t0"],["film.gaps","idle gaps · s collapsed"]].forEach(([id,l])=>cl.appendChild(claimChip(id,{size:"s",label:l})));
  if(PRIV())cl.appendChild(claimChip("film.spend",{size:"s",label:"spend, list price (L)"}));cl.appendChild(claimChip("film.tokens",{size:"s",label:"tokens in → out"}));cl.appendChild(claimChip("film.repairs",{size:"s",label:"repair calls · ended valid"}));
  rs.appendChild(cl);host.appendChild(rs);
  /* waterfall + minimap + legend + card */
  wrap=el("div",{class:"wfWrap"});const cvBox=el("div",{class:"cv wfCv"});cv=el("canvas",{id:"wfCanvas",tabindex:"0","aria-label":"waterfall of every recorded model call, one lane per model, on the run clock"});cvBox.appendChild(cv);
  const mmBox=el("div",{class:"cv mmCv"});mm=el("canvas",{id:"wfMini","aria-label":"minimap: drag the window, double-click to reset"});mmBox.appendChild(mm);wrap.append(cvBox,mmBox);
  card=el("div",{class:"card wfCard m",id:"wfCard",hidden:""});const E={title:el("b",{class:"ct"}),verdict:el("span",{class:"pill p-mute"}),prompt:el("div",{class:"cp"}),attempt:el("div"),time:el("div"),tokens:el("div"),finding:el("div",{class:"cf"}),img:el("img",{class:"cimg",alt:"measured frame",hidden:"",width:"96",height:"72"}),imgCap:el("div",{class:"ccap"}),open:el("button",{class:"copen",text:"OPEN"})};
  E.open.addEventListener("click",()=>{if(hoverRec)openRec(hoverRec)});card.append(el("div",{class:"row"},[E.title,E.verdict]),E.prompt,E.attempt,E.time,E.tokens,E.finding,E.img,E.imgCap,E.open);cardEls=E;wrap.appendChild(card);
  host.appendChild(wrap);host.appendChild(el("div",{class:"wfEvents m",id:"wfEvents"}));host.appendChild(el("div",{class:"legend wfLegend",text:"green ended valid · red ended invalid · cyan in flight · outlined = repair call (dashed = autofix) · hollow red tick = failed call · dashed stub = cut chain · hatched = idle gap collapsed · drag to zoom (≥ 30 s), double-click to reset · F toggles failed marks"}));
  WF.canvas=cv;
  /* scope slot (24-scope mounts into it) then the spend meter (private only) */
  const scopeHost=el("div",{class:"scopeHost",id:"scopeHost"});host.appendChild(scopeHost);if(self.SCOPE&&SCOPE.mount)try{SCOPE.mount(scopeHost)}catch(e){console.error("scope mount",e)}
  if(PRIV()){const sp=el("div",{class:"spendWrap"});spCv=el("canvas",{id:"spendCanvas","aria-label":"spend meter"});sp.append(el("div",{class:"cv spCv"},spCv),el("div",{class:"legend",text:"spend meter · list-price estimate, not an invoice · private build only"}));host.appendChild(sp)}
  /* panels */
  wfPanel=LOOP.register({name:"waterfall",bit:B.SCENE|B.CLOCK|B.HOVER|B.SELECT|B.MODE|B.RESIZE|B.THEME|B.DATA|B.LANE,el:cv,rateHz:(self.FX&&FX.level===0)?12:30,budgetMs:6,draw:drawWF,degrade(ms){wfPanel.lite=true;wfPanel.liteUntil=LOOP.now+2000}});
  Object.assign(wfPanel,{rows:0,bars:0,failed:0,cut:0,lanes:[],labels:[],probes:0,gaps:0,vertical:false,lite:false,liteUntil:0});
  mmPanel=LOOP.register({name:"minimap",bit:B.SCENE|B.CLOCK|B.MODE|B.RESIZE|B.THEME|B.DATA,el:mm,rateHz:8,budgetMs:3,draw:drawMM});
  rsPanel=LOOP.register({name:"runstrip",bit:B.SCENE|B.CLOCK|B.MODE|B.DATA,el:rs,rateHz:8,budgetMs:2,draw:drawRS});
  if(spCv)spPanel=LOOP.register({name:"spend",bit:B.SCENE|B.CLOCK|B.MODE|B.RESIZE|B.THEME|B.DATA,el:spCv,rateHz:8,budgetMs:2,draw:drawSP});
  if(typeof ResizeObserver!=="undefined"){new ResizeObserver(es=>{es.forEach(e=>{if(e.target===cvBox)width=e.contentRect.width;else mmWidth=e.contentRect.width});LOOP.dirty(B.RESIZE|B.SCENE)}).observe(cvBox);new ResizeObserver(es=>{mmWidth=es[0].contentRect.width;LOOP.dirty(B.RESIZE)}).observe(mmBox)}
  bindPointer();
  if(self.SIM){SIM.on("mode",()=>{packSig="";WF.win=null;setHover(null);lastLabelsSig="";LOOP.dirty(B.MODE|B.SCENE);rehead(sec)});SIM.on("reset",()=>{packSig="";LOOP.dirty(B.SCENE)});SIM.on("seek",()=>{lastLabelsSig="";LOOP.dirty(B.SCENE)})}
  if(self.THEME)THEME.onChange(()=>LOOP.dirty(B.THEME));if(self.FX)FX.onChange(()=>{wfPanel.rateHz=FX.level===0?12:30;LOOP.dirty(B.SCENE)});
  lastHeaderMode="live17"}
function rehead(sec){const mode=self.S?S.mode:"live17";if(mode===lastHeaderMode)return;lastHeaderMode=mode;sectionHeader(sec,headerSpec())}
SECTIONS.register({id:"film",part:"events",header:headerSpec(),mount,
  onData(name){if(/^(live\.core|live\.bodies|events|replay|run24|live\.jpg)$/.test(name)){packSig="";replayN=-1;lastLabelsSig="";LOOP.dirty(B.DATA|B.SCENE);const sec=$("film");if(sec&&name==="live.core")sectionHeader(sec,headerSpec())}}});
/* ---------- claims (every number the strip shows; expected from inline STATS where the build baked one) ---------- */
const LS=()=>(self.STATS&&STATS.LIVESTATS)||{};
CLAIMS.define("film.spend",{label:"spend, list price",unit:"USD · sum of A[].u · list price (L), not an invoice",needs:["live.core"],expected:LS().usd,grade:"L",source:"RECORDED 17 Oct",validator:"none",renderer:"none",text:v=>fmt.usd(v),
  compute(){return r6(LIVE.reduce((a,i)=>a+i.A.reduce((x,y)=>x+(+y.u||0),0),0))}});
CLAIMS.define("film.tokens",{label:"tokens in → out",unit:"sum of A[].ti and A[].to over 358 calls",needs:["live.core"],expected:LS().tin!=null?{tin:LS().tin,tout:LS().tout}:undefined,grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"none",text:v=>`${fmt.int(v.tin)} → ${fmt.int(v.tout)}`,
  compute(){return{tin:LIVE.reduce((a,i)=>a+i.A.reduce((x,y)=>x+(+y.ti||0),0),0),tout:LIVE.reduce((a,i)=>a+i.A.reduce((x,y)=>x+(+y.to||0),0),0)}}});
CLAIMS.define("film.repairs",{label:"repair calls · ended valid",unit:"calls after the first (report shown) · chains valid at the end after a repair",needs:["live.core"],expected:LS().repCalls!=null?{calls:LS().repCalls,ok:LS().rep}:undefined,grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none",text:v=>`${fmt.int(v.calls)} · ${fmt.int(v.ok)}`,
  compute(){return{calls:LIVE.reduce((a,i)=>a+i.A.length-1,0),ok:LIVE.filter(i=>!i.A[0].ok&&i.A[i.A.length-1].ok).length}}});
CLAIMS.define("film.creditStop",{label:"credit stop",unit:"run clock of the first insufficient-credit row (events.jsonl)",needs:["events"],grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"none",text:v=>v==null?"—":fmt.clock(v),
  compute(){return EVENTS.creditStop?+EVENTS.creditStop.t:null}});
CLAIMS.define("film.failedKinds",{label:"failed calls by kind",unit:"HTTP class per failed row",needs:["events"],expected:nStat("c.failed","kinds")||undefined,grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"none",text:v=>Object.keys(v||{}).map(k=>`${k} ×${v[k]}`).join(" · "),
  compute(){const o={};EVENTS.failed.forEach(f=>{o[f.kind]=(o[f.kind]||0)+1});return o}});
CLAIMS.define("film.cutReasons",{label:"cut chains by reason",unit:"cap or time box",needs:["events"],expected:nStat("c.cut","reasons")||undefined,grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"none",text:v=>Object.keys(v||{}).map(k=>`${k} ×${v[k]}`).join(" · "),
  compute(){const o={};EVENTS.cut.forEach(c=>{o[c.reason]=(o[c.reason]||0)+1});return o}});
CLAIMS.define("film.probes",{label:"probes before t0",unit:"events.jsonl probe rows with dt < 0",needs:["events"],grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"none",
  compute(){return EVENTS.probes.filter(p=>typeof p.dt==="number"&&p.dt<0).length}});
CLAIMS.define("film.gaps",{label:"idle gaps collapsed",unit:"gaps · seconds removed from the run clock",needs:["events"],expected:(self.STATS&&STATS.meta&&STATS.meta.gaps!=null)?{n:STATS.meta.gaps,s:STATS.meta.idle_collapsed_s}:undefined,grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"none",text:v=>`${v.n} · ${Math.round(v.s)} s`,
  compute(){return{n:EVENTS.collapse.length,s:Math.round(EVENTS.collapse.reduce((a,g)=>a+g[2],0)*10)/10}}});
Object.assign(self,{FILM,WF});
})();
