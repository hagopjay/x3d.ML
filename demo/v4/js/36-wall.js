/* 36-wall.js — S11 Integrity wall + tamper arena (SPEC S11.1–S11.6, rules 5, 7, 10, 11). Owns section #wall.
   Globals: WALL (wall state + helpers), inject (the v3 injection entry point, kinds 1–6), GAP (the "Model the gap (simulated)" drawer), LEDGER (physics-ledger text loader).
   Ported from demo/tether-firehose-v3.template.html: drawWall (535–550: geometry, status palette, invalid bar, blank notch, scrubber head, click → select),
   inject + LABEL (473–487: kinds edit/del/flipmid/fliplast; kinds 5/6 are new and go through addStep so the chain stays VERIFIED), kpis (503–519: the four S11 tiles),
   logEv display (#alerts), bSeal (892: HASH.sealOn, labelled HMAC stand-in), genSyn/synthXml/MODELS_SYN/DEFECT_FIX/drawsNothing/judge synthetic branch/schematic (333–420, 552–560)
   into the GAP drawer with mulberry32(S.seed) instead of Math.random. New in v4: continuity trace, flashes/pulses/comet (fx ≥ 1 only), exceptions-only dim, hover popover,
   tamper ghost on STAGE.show (SAI, render-time, never serialised), port re-validation after an injection (VAL), RE-VERIFY ALL through HASH.build/HASH.batch.
   Test hooks: __panels.wall {cells, rows, breaks, draws}, __panels.ttd, WALL.state, WALL.reverify.last, WALL.ghostState, #wall .kpi (4), #alerts, #bSeal, [data-f=edit|del|flipmid|fliplast|nocomp|misnest],
   #bReverify + #rvLine, S.sealOn (mirror of HASH.sealOn), GAP.run(n)/GAP.revalidate()/GAP.signature()/GAP.scenes, #gapLog, #gapDrawer. S.inj / S.detected count integrity injections (1–4) as in v3. */
(function(){
"use strict";
const BITS=LOOP.bits;
const STATUS_COL={verified:"--ok",stale:"--warn",broken:"--bad","seal-fail":"--bad","?":"--dim","no-record":"--dim"};
const PORTV=()=>VALS.find(v=>v.id==="port");
const WALL={state:{exceptions:false,hover:null,ack:new Set()},anim:new Map(),ghostState:{tried:0,ok:false,err:null},reverify:{busy:false,last:null},lastReport:null,sec:null,cv:null,pop:null,geom:null,injValidity:0,
  population(){return self.S?S.scenes.filter(s=>s.src!=="bench"&&(S.flags.includeMine||s.src!=="viewer")):[]},   /* bench rows (B-00n) stay out of every wall aggregate; viewer rows follow the include-mine flag */
  currentRef(){if(self.SLIDER&&SLIDER.active&&SLIDER.ref)return SLIDER.ref;return self.S?VALS[S.vi].ref:"?"},
  verdictOf(sc){if(self.SLIDER&&SLIDER.active){const v=SLIDER.verdictOf(sc);return v===undefined?sc.verdict:v}return sc.verdict}};
/* ---------- physics ledger (data/physics-ledger.x3d, own file; the one repo-stamped head on this page) ---------- */
const LEDGER={p:null,text:null,load(){if(LEDGER.p)return LEDGER.p;LEDGER.p=fetch("data/physics-ledger.x3d").then(r=>{if(!r.ok)throw new Error("HTTP "+r.status);return r.text()}).then(t=>{LEDGER.text=t;return t}).catch(e=>{LEDGER.err=String(e&&e.message||e);return null});return LEDGER.p}};
/* ---------- the corpus every body on the page forms (shared with 38-ladder): one chain per body ---------- */
function corpus(){const out=[];
  (self.REAL||[]).forEach(it=>{out.push({id:"R:"+it.k,src:"real",item:it,xml:it.b,steps:[
    {step:{op:"generate",model:it.m,provider:"vllm_l4",condition:it.mo==="grounded"?"report_repair":"oneshot",prompt_id:it.p,prompt_sha256:String(it.psha||"").slice(0,16),tokens_in:it.ti,tokens_out:it.to,latency_ms:it.lat,ms:it.lat,ms_src:"recorded",input_sha256:"none"}},
    {step:{op:"validate",validator:"x3d-mcp-svc",validator_ref:"svc@11Oct",verdict:it.x&&it.s?"valid":"invalid",recorded:true,xsd_valid:!!it.x,semantic_valid:!!it.s,ms:0,ms_src:"not recorded"}}]})});
  (self.LIVE||[]).forEach(it=>(it.B||[]).forEach((xml,k)=>{const a=it.A[k];if(!a)return;out.push({id:"L:"+keyOf(it.m,it.p,k+1),src:"live",item:it,k,xml,steps:[
    {step:Object.assign({op:k?"repair":"generate",model:it.m,prompt_id:it.p,prompt_sha256:String(it.psha||"").slice(0,16),tokens_in:a.ti,tokens_out:a.to,latency_ms:a.ms,finish:a.fin,run_s:a.t0,ms:a.ms,ms_src:"recorded"},k?{kind:"model",round:k,report_shown:true,fixes:codesOf(it.A[k-1])}:{condition:"oneshot",input_sha256:"none"})},
    {step:{op:"validate",validator:"fork",validator_ref:(self.LM&&LM.validator)||"fork@eb4b4b4",verdict:a.ok?"valid":"invalid",codes:codesOf(a),ms:a.vms,ms_src:"measured"}}]})}));
  ((self.EVENTS&&EVENTS.cut)||[]).forEach(c=>(c.bodies||[]).forEach((b,i)=>{const xml=typeof b==="string"?b:b.xml,key=(b&&b.k)||keyOf(c.m,c.p,i+1);if(!xml)return;out.push({id:"C:"+key,src:"cut",cut:c,xml,steps:[
    {step:{op:"generate",model:c.m,prompt_id:c.p,condition:"oneshot",finish:"cut: "+(c.reason||"stopped"),ms:0,ms_src:"missing",input_sha256:"none"}}]})}));
  if(LEDGER.text)out.push({id:"ledger",src:"ledger",xml:LEDGER.text,steps:null});
  return out}
const missingCut=()=>{const E=self.EVENTS;if(!E||!E.cut)return 0;return E.cut.reduce((n,c)=>n+Math.max(0,(c.calls||0)-((c.bodies&&c.bodies.length)||0)),0)};
WALL.corpus=corpus;WALL.missingCut=missingCut;
/* ---------- section ---------- */
function headerSpec(){const m=self.S&&S.mode==="replay11";return{title:"Integrity wall + tamper arena",unit:`one cell per stored chain · the scrubber re-verifies every head meta, all the time · ${m?"174 replay chains":"201 live chains"}`,
  stamps:{source:m?"RECORDED 11 Oct":"RECORDED 17 Oct",validator:m?"svc@11Oct recorded":"fork@eb4b4b4 recorded",renderer:"none"},grade:"C",
  honesty:"chains built in this page (text-normalised SHA-256, not the repo's lxml C14N) · seal = HMAC stand-in with a key in the page source, not Ed25519 (signing card unanswered) · tamper demonstrations are simulated attacks on real recorded chains · last-step flip undetected while unsigned (C)"}}
SECTIONS.register({id:"wall",part:"live.bodies",header:headerSpec(),mount(sec){try{mount(sec)}catch(e){console.error("wall mount",e);if(self.BOOT)BOOT.error(e,"wall mount")}}});
function kpi(l,cls){const d=el("div",{class:"kpi "+cls},[el("div",{class:"l",text:l}),el("div",{class:"v",text:"—"}),el("div",{class:"s",text:""})]);return d}
function mount(sec){WALL.sec=sec;const sb=sec.querySelector(".sb");sb.textContent="";
  const K=WALL.kpis={ver:kpi("chains verified","ok"),inj:kpi("injected / caught","ok"),ttd:kpi("time to detect","acc"),rev:kpi("need re-validation","ok")};
  sb.appendChild(el("div",{class:"kpis wallKpis"},[K.ver,K.inj,K.ttd,K.rev]));
  sb.appendChild(el("div",{class:"legend",text:"dim = known from the record · bright = replayed or recomputed in this view · time to detect is measured on this page's playback clock"}));
  const cv=el("canvas",{id:"wallCv",tabindex:"0","aria-label":"integrity wall: one cell per stored chain; click a cell to select its scene"});WALL.cv=cv;
  const pop=WALL.pop=el("div",{class:"wallPop",hidden:""},[el("img",{alt:"measured frame",width:"96",height:"72"}),el("div",{class:"t"})]);
  const exc=el("input",{type:"checkbox",id:"wallExc"});exc.addEventListener("change",()=>{WALL.state.exceptions=exc.checked;LOOP.dirty(BITS.VERIFY)});
  sb.appendChild(el("div",{class:"panel wallPanel"},[
    el("header",null,[el("h3",{text:"Integrity wall"}),el("span",{class:"sub",id:"wallSub",text:""}),el("label",{class:"excLbl"},[exc,"show only exceptions"])]),
    el("div",{class:"cv wallCv"},[cv,pop]),
    el("div",{class:"legend wallLegend"},[sw("--ok","chain verified"),sw("--warn","stale (content differs from the head)"),sw("--bad","broken or seal fail"),sw("--info","bottom bar: verdict invalid"),sw("--warn","top-right notch: valid, blank frame"),sw("--acc","cyan frame: scrubber head"),sw("--fg","right edge: continuity trace, one line per row, a gap where a chain is broken")])]));
  cv.addEventListener("mousemove",onMove);cv.addEventListener("mouseleave",()=>{WALL.state.hover=null;pop.hidden=true;LOOP.dirty(BITS.HOVER)});cv.addEventListener("click",onClick);
  cv.addEventListener("keydown",e=>{if(e.key==="Enter"&&WALL.state.hover!=null)onClick(null,WALL.state.hover)});
  /* arena */
  const inj=[["edit","1 · Edit a scene after the fact","coordinate edit: the shape jumps 9 units; the stage shows a red wireframe ghost at the original position (render-time only)"],["del","2 · Delete a step","a step meta removed from the head"],["flipmid","3 · Flip an old verdict","an interior validate step's verdict edited"],["fliplast","4 · Flip the LAST verdict","the honest gap: no later step vouches for it while unsigned"],["nocomp","5 · Drop the component statement","recorded as a transform step: the chain stays VERIFIED, the js-port verdict flips"],["misnest","6 · Mis-nest a Shape in a Group","recorded as a transform step: geometry lands directly in a Group; the js-port verdict flips"]]
    .map(([k,l,t])=>el("button",{class:"inj",data:{f:k},title:t,text:l,onclick:()=>{const sc=inject(k);if(sc)SIM.select(sc.id)}}));
  const seal=el("button",{id:"bSeal",text:"Signing: off",title:"HMAC stand-in: the key is in the page source on purpose; real signing (Ed25519) waits for the owner's word and is not on this page",onclick:()=>WALL.setSigning(!HASH.sealOn)});
  const ttd=el("canvas",{id:"ttd","aria-label":"time to detect per caught injection"});
  sb.appendChild(el("div",{class:"wallGrid"},[
    el("div",{class:"panel arena"},[el("header",null,[el("h3",{text:"Tamper arena"}),el("span",{class:"sub",text:"simulated attacks on real recorded chains · 1–4 break integrity, 5–6 break validity"})]),
      el("div",{class:"injRow"},inj),
      el("div",{class:"row"},[seal,el("span",{class:"note sealNote",text:"seal = HMAC stand-in, key in the page source (SECRET) · NOT a real signature: no key material, Ed25519 stays on the owner's card · new chains only"})]),
      el("div",{class:"note m",id:"injStatus",text:"no injection yet · pick one: the scrubber names the damage within one sweep"}),
      el("div",{class:"note m",id:"portSays",text:""})]),
    el("div",{class:"panel"},[el("header",null,[el("h3",{text:"Detection log"}),el("span",{class:"sub",text:"40 lines · run clock · the scrubber speaks here"})]),
      el("div",{class:"alerts m",id:"alerts","aria-live":"polite"}),
      el("div",{class:"ttdWrap cv"},[ttd]),el("div",{class:"sub",text:"time to detect, seconds on this page's playback clock (wall seconds from the injection to the scrubber's verdict)"})])]));
  /* RE-VERIFY ALL */
  const rvBtn=el("button",{id:"bReverify",class:"primary",text:"RE-VERIFY ALL",title:"one chain per body on the page, built and verified in the hash worker",onclick:()=>reverifyAll()});
  sb.appendChild(el("div",{class:"row reverify"},[rvBtn,el("i",{class:"bar"},el("b",{id:"rvBar"})),el("span",{class:"note m",id:"rvLine",text:"every body on the page becomes a chain (generate + validate from the record), built and verified in the hash worker · page-normalised hash"})]));
  sb.appendChild(el("div",{class:"row",id:"rvClaim"}));
  /* drawer */
  sb.appendChild(GAP.build());
  /* panels */
  const P=LOOP.register({name:"wall",bit:BITS.SCENE|BITS.VERIFY|BITS.SELECT|BITS.MODE|BITS.HOVER|BITS.THEME|BITS.RESIZE|BITS.VAL|BITS.DATA,always:FX.level>0,rateHz:FX.level>0?30:6,el:cv,budgetMs:4,draw:drawWall});P.cells=0;P.rows=0;P.breaks=0;
  LOOP.register({name:"ttd",bit:BITS.VERIFY|BITS.THEME|BITS.RESIZE|BITS.MODE,rateHz:4,el:ttd,budgetMs:2,draw:()=>drawTTD(ttd)});
  LOOP.register({name:"wallKpi",bit:BITS.SCENE|BITS.VERIFY|BITS.SELECT|BITS.MODE|BITS.VAL|BITS.CLOCK,rateHz:4,draw:drawKpis});
  LOOP.register({name:"alerts",bit:BITS.VERIFY|BITS.SCENE|BITS.MODE|BITS.CLOCK,rateHz:4,el:$("alerts"),draw:drawAlerts});
  FX.onChange(n=>{P.always=n>0;P.rateHz=n>0?30:6;LOOP.dirty(BITS.VERIFY)});
  SIM.on("scene",sc=>{if(S.ff)return;anim(sc.id).born=performance.now()});
  SIM.on("verify",xs=>{if(S.ff)return;const now=performance.now();xs.forEach(sc=>{const a=anim(sc.id);a.pulse=now;if(sc.detected&&!a.det)a.det=now})});
  SIM.on("reset",()=>{WALL.anim.clear();WALL.state.ack.clear();WALL.state.hover=null;if(self.S)S.sealOn=HASH.sealOn;LOOP.dirty(BITS.VERIFY|BITS.MODE)});
  SIM.on("mode",()=>{sectionHeader(sec,headerSpec());if(self.S)S.sealOn=HASH.sealOn});
  if(self.S)S.sealOn=HASH.sealOn;
  if(self.VAL&&VAL.on)VAL.on(()=>LOOP.dirty(BITS.VAL));
  drawKpis();drawAlerts()}
function sw(tok,text){return el("span",{class:"lg"},[el("i",{style:{background:`var(${tok})`}}),text])}
function anim(id){let a=WALL.anim.get(id);if(!a){a={born:0,pulse:0,det:0};WALL.anim.set(id,a);if(WALL.anim.size>800){const k=WALL.anim.keys().next().value;WALL.anim.delete(k)}}return a}
/* ---------- wall geometry (v3 535–538, cells 14 px at 1500 wide, 10 px on phone) ---------- */
function geom(cw){const trace=30,gap=2,cell=cw>=760?14:cw>=480?12:10,cap=Math.min(WIN,Math.max(1,(self.S&&S.order.length)||0,(self.S&&S.scenes.length)||0));
  const cols=Math.max(6,Math.floor((cw-trace-gap)/(cell+gap))),rows=Math.max(1,Math.ceil(cap/cols));return{trace,gap,cell,cap,cols,rows,h:rows*(cell+gap)+gap,gw:gap+cols*(cell+gap)}}
function cellAt(x,y){const g=WALL.geom;if(!g||x<0||x>g.gw||y<0)return null;const c=Math.floor((x-g.gap)/(g.cell+g.gap)),r=Math.floor((y-g.gap)/(g.cell+g.gap));if(c<0||c>=g.cols||r<0)return null;const i=r*g.cols+c;return self.S&&S.scenes[i]?i:null}
function drawWall(now){const cv=WALL.cv,p=__panels.wall;if(!cv||!self.S)return;const cw=cv.clientWidth||600,g=WALL.geom=geom(cw);const{ctx,w,h}=fitCanvas(cv,cw,g.h);ctx.clearRect(0,0,w,h);
  const col={},fx=FX.level>0;for(const k in STATUS_COL)col[k]=cssv(STATUS_COL[k]);const info=cssv("--info"),acc=cssv("--acc"),warn=cssv("--warn"),bad=cssv("--bad"),fg=cssv("--fg"),line=cssv("--line"),you=cssv("--you"),ok=cssv("--ok");
  const sc=S.scenes,n=sc.length,exc=WALL.state.exceptions,hov=WALL.state.hover;let breaks=0;const rowBroken=new Array(g.rows).fill(0);
  for(let i=0;i<g.cap;i++){const c=i%g.cols,r=Math.floor(i/g.cols),x=g.gap+c*(g.cell+g.gap),y=g.gap+r*(g.cell+g.gap),s=sc[i];
    if(!s){ctx.globalAlpha=.3;ctx.fillStyle=line;ctx.fillRect(x,y,g.cell,g.cell);ctx.globalAlpha=1;continue}
    const st=s.status,base=col[st]||col["?"],a=WALL.anim.get(s.id);let alpha=1;
    if(exc&&st==="verified"&&!s.injured)alpha=.25;
    ctx.globalAlpha=alpha;ctx.fillStyle=base;ctx.fillRect(x,y,g.cell,g.cell);
    if(fx&&a){const tb=now-a.born,tp=now-a.pulse;
      if(a.born&&tb<180){ctx.globalAlpha=alpha*(1-tb/180);ctx.fillStyle=fg;ctx.fillRect(x,y,g.cell,g.cell)}
      else if(a.pulse&&tp<80){ctx.globalAlpha=alpha*.8;ctx.fillStyle=fg;ctx.fillRect(x,y,g.cell,g.cell)}
      if(a.det){const td=now-a.det;if(td<400&&(td%200)<100){ctx.globalAlpha=1;ctx.fillStyle=bad;ctx.fillRect(x-1,y-1,g.cell+2,g.cell+2)}}
      if(st==="stale"&&!WALL.state.ack.has(s.id)){ctx.globalAlpha=.35+.35*Math.sin(now/159);ctx.fillStyle=warn;ctx.fillRect(x-1,y-1,g.cell+2,g.cell+2)}}
    ctx.globalAlpha=alpha;
    const vd=WALL.verdictOf(s);
    if(vd===null){ctx.fillStyle=line;ctx.fillRect(x,y+g.cell-3,g.cell,3)}else if(vd==="invalid"){const bar=Math.max(3,Math.round(g.cell/6));ctx.fillStyle=info;ctx.fillRect(x,y+g.cell-bar,g.cell,bar)}
    if(s.blank&&vd==="valid"){ctx.fillStyle=warn;ctx.fillRect(x+g.cell-4,y+1,3,3)}
    if(s.src==="viewer"||s.src==="bench"){ctx.strokeStyle=you;ctx.lineWidth=1;ctx.strokeRect(x+.5,y+.5,g.cell-1,g.cell-1)}
    ctx.globalAlpha=1;
    if(!verifyOk(st)){breaks++;rowBroken[r]++}
    if(S.sel===s.id){ctx.strokeStyle=fg;ctx.lineWidth=1.5;ctx.strokeRect(x-1,y-1,g.cell+2,g.cell+2)}
    if(hov===i){ctx.strokeStyle=acc;ctx.lineWidth=1;ctx.strokeRect(x-2.5,y-2.5,g.cell+5,g.cell+5)}}
  /* scrubber head + comet (fx ≥ 1) */
  if(n){const head=S.scr%n;if(fx)for(let k=1;k<=6;k++){const i=(head-k+n)%n,x=g.gap+(i%g.cols)*(g.cell+g.gap),y=g.gap+Math.floor(i/g.cols)*(g.cell+g.gap);ctx.globalAlpha=(7-k)/14;ctx.strokeStyle=acc;ctx.lineWidth=1;ctx.strokeRect(x-.5,y-.5,g.cell+1,g.cell+1)}
    ctx.globalAlpha=1;const x=g.gap+(head%g.cols)*(g.cell+g.gap),y=g.gap+Math.floor(head/g.cols)*(g.cell+g.gap);ctx.strokeStyle=acc;ctx.lineWidth=2;ctx.strokeRect(x-1.5,y-1.5,g.cell+3,g.cell+3)}
  /* continuity trace: one 1 px line per row of cells; continuous while every head meta's prev hash matches; a gap + red where a chain is broken */
  const tx0=g.gw+6,tx1=cw-4;for(let r=0;r<g.rows;r++){const y=g.gap+r*(g.cell+g.gap)+Math.floor(g.cell/2)+.5,inRow=Math.min(g.cols,Math.max(0,n-r*g.cols));if(!inRow)continue;
    if(!rowBroken[r]){ctx.globalAlpha=.7;ctx.strokeStyle=ok;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(tx0,y);ctx.lineTo(tx1,y);ctx.stroke()}
    else{const mid=(tx0+tx1)/2;ctx.globalAlpha=.7;ctx.strokeStyle=ok;ctx.beginPath();ctx.moveTo(tx0,y);ctx.lineTo(mid-3,y);ctx.stroke();ctx.globalAlpha=1;ctx.strokeStyle=bad;ctx.beginPath();ctx.moveTo(mid+3,y);ctx.lineTo(tx1,y);ctx.stroke();ctx.fillStyle=bad;ctx.fillRect(mid-1,y-3,2,6)}}
  ctx.globalAlpha=1;p.cells=n;p.rows=g.rows;p.breaks=breaks;p.cap=g.cap;
  txt("wallSub",`${n} stored · ${n-sc.filter(s=>s.status==="verified").length} not verified · scrubber at cell ${n?S.scr%n:0} · verdicts on ${WALL.currentRef()}`)}
const verifyOk=st=>st==="verified"||st==="?";
function onMove(e){const r=WALL.cv.getBoundingClientRect(),i=cellAt(e.clientX-r.left,e.clientY-r.top);if(i!==WALL.state.hover){WALL.state.hover=i;LOOP.dirty(BITS.HOVER)}
  const pop=WALL.pop;if(i==null){pop.hidden=true;return}const sc=S.scenes[i],img=pop.querySelector("img"),t=pop.querySelector(".t");pop.hidden=false;
  const jpg=thumbOf(sc);if(jpg){if(img.dataset.id!==sc.id){img.src="data:image/jpeg;base64,"+jpg;img.dataset.id=sc.id}img.hidden=false}else img.hidden=true;
  txt(t,`${sc.id} · ${sc.model||"?"}\n${WALL.verdictOf(sc)||"not recorded"} on ${sc.vref||WALL.currentRef()} · ${sc.status}${sc.blank&&sc.verdict==="valid"?" · blank frame":""}${sc.injured?" · INJECTED "+sc.injured.type:""}${sc.sealed?" · sealed":""}`);
  const x=e.clientX-r.left,y=e.clientY-r.top;pop.style.left=Math.max(0,Math.min(r.width-230,x+14))+"px";pop.style.top=(y+14)+"px"}
function thumbOf(sc){try{if(sc.src==="live"){const a=sc.item.A[sc.item.A.length-1];return a&&a.r&&a.r.jpg||null}if(sc.src==="real")return sc.item.r&&sc.item.r.jpg||null}catch(e){}return null}
function onClick(e,idx){const i=idx!=null?idx:(()=>{const r=WALL.cv.getBoundingClientRect();return cellAt(e.clientX-r.left,e.clientY-r.top)})();if(i==null)return;const sc=S.scenes[i];WALL.state.ack.add(sc.id);SIM.select(sc.id)}
/* ---------- KPI quartet (v3 503–519, the four S11 tiles) ---------- */
function setKpi(k,v,s,cls){const d=WALL.kpis[k];txt(d.querySelector(".v"),v);txt(d.querySelector(".s"),s);d.className="kpi "+cls;d.title=`${d.querySelector(".l").textContent}: ${v} · ${s}`}
function drawKpis(){if(!self.S||!WALL.kpis)return;const pop=WALL.population(),tot=pop.length,ver=pop.filter(s=>s.status==="verified").length,ref=WALL.currentRef(),stale=pop.filter(s=>s.vref!==ref).length,miss=S.inj-S.detected;
  setKpi("ver",UTIL.pc(ver,tot),`${ver} of ${tot} · page-normalised hash`,"ok");
  setKpi("inj",`${S.inj} / ${S.detected}`,(miss?`${miss} undetected (last-step flip while unsigned)`:S.inj?"none missed":"integrity injections 1–4")+(WALL.injValidity?` · +${WALL.injValidity} validity injections (verdict column)`:""),miss?"warn":"ok");
  setKpi("ttd",S.ttd.length?(S.ttd.reduce((a,b)=>a+b,0)/S.ttd.length).toFixed(2)+" s":"—","mean · on this page's playback clock · scrubber sweep","acc");
  setKpi("rev",fmt.int(stale),`last verdict on an older ref than ${ref}`,stale?"warn":"ok")}
/* ---------- detection log (logEv lines; 40 shown) ---------- */
function drawAlerts(){const host=$("alerts");if(!host||!self.S)return;const rows=S.alerts.slice(0,40);while(host.children.length<rows.length)host.appendChild(el("div"));while(host.children.length>rows.length)host.removeChild(host.lastChild);
  rows.forEach((a,i)=>{const d=host.children[i];if(d.dataset.k!==a.kind){d.className="al "+a.kind;d.dataset.k=a.kind}txt(d,`${fmt.clock(a.t)} · ${a.msg}`)})}
/* ---------- TTD strip chart ---------- */
function drawTTD(c){if(!self.S)return;const cw=c.clientWidth||300,{ctx,w,h}=fitCanvas(c,cw,48);ctx.clearRect(0,0,w,h);const v=S.ttd.slice(-40);ctx.strokeStyle=cssv("--line");ctx.beginPath();ctx.moveTo(0,h-.5);ctx.lineTo(w,h-.5);ctx.stroke();if(!v.length){ctx.fillStyle=cssv("--dim");ctx.font="500 10.5px "+cssv("--mono");ctx.fillText("no detection yet",6,h/2+4);return}
  const mx=Math.max(1,...v),bw=Math.max(3,Math.min(14,Math.floor(w/v.length)-2));v.forEach((t,i)=>{const bh=Math.max(2,Math.round((t/mx)*(h-14)));ctx.fillStyle=cssv("--bad");ctx.fillRect(4+i*(bw+2),h-bh-1,bw,bh)});
  ctx.fillStyle=cssv("--dim");ctx.font="500 10.5px "+cssv("--mono");ctx.fillText(`max ${mx.toFixed(2)} s · ${v.length} caught`,6,10)}
/* ---------- signing switch (v3 892): HASH.sealOn, mirrored on S.sealOn for the v3 hook ---------- */
WALL.setSigning=function(on){HASH.sealOn=!!on;if(self.S)S.sealOn=HASH.sealOn;const b=$("bSeal");if(b){txt(b,"Signing: "+(HASH.sealOn?"on (new chains, HMAC stand-in)":"off"));b.classList.toggle("on",HASH.sealOn)}
  logEv("sys","signing "+(HASH.sealOn?"enabled: new chains sealed with the HMAC stand-in (key in the page source; not Ed25519)":"disabled"));LOOP.dirty(BITS.VERIFY|BITS.MODE)};
/* ---------- injections (v3 475–487 + kinds 5/6) ---------- */
const LABEL={edit:"coordinate edit (shape moved 9 units)",del:"step deletion",flipmid:"interior verdict flip",fliplast:"last-step verdict flip",nocomp:"component statement dropped",misnest:"Shape mis-nested in a Group"};
const VEC3_RE=/translation=(["'])\s*(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s*\1/;
function pickTarget(kind){const pool=S.scenes.filter(s=>s.status==="verified"&&!s.injured&&!s.tampered&&s.nsteps>=3&&(s.src==="live"||s.src==="real")&&(kind!=="nocomp"||/<component\b/.test(stripProv(s.xml)))&&(kind!=="misnest"||/<Shape\b[^>]*>[\s\S]*?<\/Shape>/.test(s.xml)));
  if(!pool.length)return null;const pref=kind==="edit"?pool.filter(s=>VEC3_RE.test(stripProv(s.xml))):pool,P=pref.length?pref:pool;const rnd=mulberry32(((S.seed|0)*7919+S.inj*31+WALL.injValidity*17+1)|0);return P[Math.floor(rnd()*P.length)]}
function inject(type,target,opts){opts=opts||{};if(!self.S)return null;if(!LABEL[type]){console.warn("inject: unknown kind",type);return null}
  let sc=target||pickTarget(type);if(!sc){txt("injStatus",`no eligible chain for "${LABEL[type]}" in the window yet (needs a verified, un-injected chain${type==="nocomp"?" whose body carries a <component> statement":""})`);return null}
  const pre=sc.xml;let x=pre;const all=readSteps(x);
  if(type==="edit"){const m=VEC3_RE.exec(stripProv(x));if(m){const q=m[1],nx=+(+m[2]+9).toFixed(4);x=x.replace(m[0],()=>`translation=${q}${nx} ${m[3]} ${m[4]}${q}`)}else x=x.replace(/<Scene\b[^>]*>/,s=>s+"<WorldInfo info='\"edited after the fact\"'/>")}
  else if(type==="del"){const n=all.length>2?2:1;x=x.replace(new RegExp(`<meta name="x3dprov\\.step\\.${n}" content="[^"]*"/>`),"")}
  else if(type==="flipmid"){const st=all.find(([n,c])=>n>=2&&n<all.length&&JSON.parse(c).verdict)||all[1];const j=JSON.parse(st[1]);if(j.verdict)j.verdict=j.verdict==="valid"?"invalid":"valid";else j.note="edited";x=setStepJson(x,st[0],j)}
  else if(type==="fliplast"){const st=all[all.length-1],j=JSON.parse(st[1]);if(j.verdict)j.verdict=j.verdict==="valid"?"invalid":"valid";else if(j.model)j.model=j.model+"-x";else j.note="edited";x=setStepJson(x,st[0],j)}
  else if(type==="nocomp"){const after=x.replace(/<component\b[^>]*\/>\s*/,"");if(after===x){txt("injStatus",`${sc.id} carries no <component> statement to drop`);return null}
    x=addStep(x,{op:"transform",agent:"tamper arena (this page)",agent_ref:"simulated attack on a recorded chain",kind:"drop component statement",detail:"first <component> statement removed from the head; recorded as a step, so the chain stays intact",ms:0,ms_src:"none"},after,sc.sealed)}
  else if(type==="misnest"){const o=x.search(/<Shape\b[^>]*>/);if(o<0)return null;const oe=x.indexOf(">",o)+1,c=x.indexOf("</Shape>",oe);if(c<0)return null;const after=x.slice(0,o)+"<Group>"+x.slice(oe,c)+"</Group>"+x.slice(c+8);
    x=addStep(x,{op:"transform",agent:"tamper arena (this page)",agent_ref:"simulated attack on a recorded chain",kind:"mis-nest Shape in Group",detail:"the first <Shape> became a <Group>: its geometry and appearance now sit directly in a grouping node; recorded as a step, so the chain stays intact",ms:0,ms_src:"none"},after,sc.sealed)}
  sc.xml=x;sc.nsteps=readSteps(x).length;
  if(type==="nocomp"||type==="misnest"){sc.tampered={t:performance.now(),type,recorded:true};sc.status=verify(x).status;WALL.injValidity++;
    logEv("inj",`${sc.id}: ${LABEL[type]}, recorded as a transform step · chain ${sc.status.toUpperCase()} (integrity and validity are different questions) · re-validating on js-port-of-8dd0d3e…`);
    txt("injStatus",`${sc.id} · ${LABEL[type]} · chain ${sc.status.toUpperCase()} · the verdict column is what changes`)}
  else{sc.injured={t:performance.now(),type,pre};sc.detected=false;sc.status="verified";S.inj++;
    logEv("inj",`${sc.id}: injected ${LABEL[type]} (${sc.sealed?"sealed":"unsealed"} chain)`);txt("injStatus",`${sc.id} · ${LABEL[type]} · ${sc.sealed?"sealed":"unsealed"} chain · waiting for the scrubber…`);
    if(type==="edit"&&opts.stage!==false)ghost(sc,pre,x).catch(e=>{WALL.ghostState.err=String(e&&e.message||e)})}
  portCheck(sc,type).catch(()=>{});LOOP.dirty(BITS.VERIFY|BITS.SELECT);return sc}
/* after any injection the body goes to the port: 5/6 are stamped (revalidateOne), 1–4 only report (a stamp would heal the evidence) */
async function portCheck(sc,type){const V=PORTV();let res=null,note="";
  try{if(self.VAL){await (VAL.need?VAL.need():VAL.init());if(VAL.mode==="full"||VAL.mode==="semantic-only")res=await VAL.validate(sc.xml);else note=VAL.reason||VAL.mode}}catch(e){note=String(e&&e.message||e)}
  if(res){sc.port=res;const codes=codesOfRes(res);WALL.lastReport={id:sc.id,res,codes};
    if(sc.tampered&&sc.tampered.type===type&&V){const flipped=revalidateOne(sc,V);logEv(flipped?"det":"sys",`${sc.id}: js-port-of-8dd0d3e says ${res.valid?"VALID":"INVALID"}${codes.length?" ["+codes.join(", ")+"]":""} · chain ${sc.status.toUpperCase()}${flipped?" · verdict flipped valid → invalid with the chain intact":""}`)}
    else logEv("sys",`${sc.id}: js-port-of-8dd0d3e says ${res.valid?"VALID":"INVALID"}${codes.length?" ["+codes.join(", ")+"]":""} · integrity is the scrubber's question`);
    txt("portSays",`js-port-of-8dd0d3e on ${sc.id}: ${res.valid?"VALID":"INVALID"}${codes.length?" · "+codes.join(", "):""} · ${fmt.ms(res.ms||0)} · measured here, not recorded`)}
  else{sc.portNote=note;txt("portSays",`js-port-of-8dd0d3e not available in this viewer (${note||"not loaded"}): recorded verdict shown, not re-validated`);if(sc.tampered)logEv("sys",`${sc.id}: js-port unavailable (${note||"not loaded"}); recorded ${sc.verdict} verdict kept, chain ${sc.status.toUpperCase()}`)}
  LOOP.dirty(BITS.VERIFY|BITS.VAL)}
/* tamper ghost: the edited body on STAGE.show, plus a red wireframe at the pre-edit position built through the SAI (render-time, never serialised, never hashed, never on the measure canvas) */
async function ghost(sc,pre,post){const G=WALL.ghostState;G.tried++;G.ok=false;G.err=null;if(!self.STAGE||!STAGE.show||!STAGE.show.ok||!self.X3D){G.err="stage not available";return}
  const r=await STAGE.show.load(post,{scene:sc});if(!r||!r.ok){G.err=r&&r.err||"load failed";return}
  const m=/<Transform\b[^>]*translation=(["'])\s*(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s*\1[^>]*>([\s\S]*?)<\/Transform>/.exec(stripProv(pre));if(!m){G.err="no translated Transform in the pre-edit body";return}
  const inner=m[5]||"",num=re=>{const k=re.exec(inner);return k?k[1].trim().split(/\s+/).map(Number):null},size=num(/<Box\b[^>]*size=["']([^"']+)["']/)||(num(/<Sphere\b[^>]*radius=["']([^"']+)["']/)||num(/<Cylinder\b[^>]*radius=["']([^"']+)["']/)||num(/<Cone\b[^>]*bottomRadius=["']([^"']+)["']/)||[[1]]).map(x=>x*2),sz=size.length>=3?size:[size[0],size[0],size[0]];
  try{const B=STAGE.show.browser,scn=B.currentScene,F=self.X3D;STAGE.show.resume();
    const sw=scn.createNode("Switch"),tr=scn.createNode("Transform"),sh=scn.createNode("Shape"),ap=scn.createNode("Appearance"),mat=scn.createNode("Material"),fp=scn.createNode("FillProperties"),box=scn.createNode("Box");
    const set3=(node,f,v)=>{if(F.SFVec3f)node[f]=new F.SFVec3f(v[0],v[1],v[2]);else{node[f].x=v[0];node[f].y=v[1];node[f].z=v[2]}};
    set3(tr,"translation",[+m[2],+m[3],+m[4]]);set3(box,"size",sz);if(F.SFColor){mat.emissiveColor=new F.SFColor(1,.36,.46);mat.diffuseColor=new F.SFColor(0,0,0)}fp.filled=false;fp.hatched=false;
    ap.material=mat;ap.fillProperties=fp;sh.appearance=ap;sh.geometry=box;tr.children.push(sh);sw.children.push(tr);sw.whichChoice=0;scn.addRootNode(sw);
    G.ok=true;G.at=[+m[2],+m[3],+m[4]];G.scene=sc.id;txt("stageMsg",`${sc.id} · TAMPERED: coordinate edit, shape moved 9 units · red wireframe = pre-edit position, drawn at render time only (not in the file) · page hash ${contentHash(post).slice(0,12)}… ≠ head output`);
    if(STAGE.show.freezeSoon)STAGE.show.freezeSoon(STAGE.show.token)}
  catch(e){G.err=String(e&&e.message||e).slice(0,160)}}
/* ---------- RE-VERIFY ALL: one chain per body, built in the hash worker and verified there (S11.4) ---------- */
async function reverifyAll(){const RV=WALL.reverify;if(RV.busy)return RV.p;RV.busy=true;const btn=$("bReverify"),bar=$("rvBar");if(btn)btn.disabled=true;
  RV.p=(async()=>{const t0=performance.now();await LEDGER.load();const items=corpus(),n=items.length;let built=0,ids=[],xmls=[];
    const prog=(k,phase)=>{if(bar)bar.style.width=(100*k/Math.max(1,n)).toFixed(1)+"%";txt("rvLine",`${phase} ${k} / ${n} chains · hash worker ${HASH.mode}${missingCut()?` · ${missingCut()} cut-chain bodies absent from the events part`:""}`)};
    for(let i=0;i<n;i+=24){const slice=items.slice(i,i+24);const out=await Promise.all(slice.map(it=>it.steps?HASH.build(it.xml,it.steps.map(s=>({step:s.step,after:s.after??it.xml,seal:false}))):Promise.resolve(it.xml)));
      out.forEach((x,j)=>{ids.push(slice[j].id);xmls.push(x)});built+=slice.length;prog(built,"building")}
    /* page-built chains must verify; a repo-stamped head (the physics ledger, steps:null) carries the repo's lxml C14N hash, which this page cannot reproduce:
       its links are checked (status "stale" = every step links, only the head hash is the repo's, as expected), never counted as verified or as broken */
    let ok=0,bad=[],stampedLinked=0;const isStamped=it=>!it.steps;
    for(let i=0;i<n;i+=96){const st=await HASH.batch(ids.slice(i,i+96),xmls.slice(i,i+96));st.forEach((r,j)=>{const it=items[i+j];if(isStamped(it)){if(r.ok||r.status==="stale")stampedLinked++;else bad.push(ids[i+j]+":"+r.status)}else if(r.ok)ok++;else bad.push(ids[i+j]+":"+r.status)});prog(Math.min(n,i+96),"verifying")}
    const ms=performance.now()-t0,stamped=items.filter(isStamped),nBuilt=n-stamped.length,led=items.find(it=>it.id==="ledger");let repo="";
    if(led){const steps=readSteps(led.xml),head=steps.length?JSON.parse(steps[steps.length-1][1]):null;repo=head?` (physics ledger, ${steps.length} steps: links intact, repo C14N hash ${String(head.output_sha256||"").slice(0,12)}… beside page hash ${contentHash(led.xml).slice(0,12)}…, byte equality not claimed)`:""}
    const exp=(self.MANIFEST&&MANIFEST.canary&&MANIFEST.canary.bodies)||null,miss=missingCut();
    const line=`${ok} of ${nBuilt} page-built chains verified in ${fmt.ms(ms)} · page-normalised hash (${HASH.mode}) · ${stampedLinked} of ${stamped.length} repo-stamped head${stamped.length===1?"":"s"} linked${repo}${exp?` · manifest canary set ${exp} bodies, ${ok+stampedLinked} accounted for here`:""}${miss?` · ${miss} cut-chain bodies absent from the events part (not on this page)`:""}${bad.length?` · NOT verified: ${bad.slice(0,6).join(", ")}`:""}`;
    RV.last={n,ok,built:nBuilt,stampedLinked,ms,bad,stamped:stamped.length,expected:exp,missing:miss,line};txt("rvLine",line);if(bar)bar.style.width="100%";
    CLAIMS.define("w.reverify",{label:"chains re-verified in this page",unit:"one chain per body on the page (the repo-stamped ledger: links checked, head hash is the repo's)",expected:exp,compute:()=>RV.last?RV.last.ok+RV.last.stampedLinked:undefined,source:"RE-RUN HERE",validator:"none",renderer:"none",grade:miss?"S":"C",files:["parts/live.bodies.txt","parts/replay.txt","parts/events.txt","data/physics-ledger.x3d"],fields:["generate + validate from the record per body, addStep in the hash worker, verify there; the ledger carries its own 29 steps"],why:miss?`${miss} cut-chain bodies are in the manifest canary set but not in the events part on this page`:null});
    await CLAIMS.run("w.reverify");const host=$("rvClaim");if(host){host.textContent="";host.appendChild(claimChip("w.reverify",{size:"m"}));host.appendChild(el("span",{class:"note",text:"expected = manifest canary set; the chip goes red when fewer bodies are on the page than the manifest names"}))}
    logEv("sys",line);RV.busy=false;if(btn)btn.disabled=false;LOOP.dirty(BITS.VERIFY);return RV.last})().catch(e=>{RV.busy=false;if(btn)btn.disabled=false;txt("rvLine","RE-VERIFY ALL failed: "+String(e&&e.message||e));throw e});
  return RV.p}
WALL.reverifyAll=reverifyAll;
/* ---------- S11.6 Model the gap (simulated): the v3 synthetic world in a drawer of its own (333–420, 552–560), seeded ---------- */
const MODELS_SYN=[{id:"qwen3-8b",p1:.07,pr:.35,price:.20,tok:[900,2600],lat:[9,22]},{id:"qwen2.5-coder-14b-awq",p1:.40,pr:.55,price:.35,tok:[700,2200],lat:[7,18]},{id:"gpt-oss-20b",p1:.33,pr:.60,price:.45,tok:[800,2800],lat:[6,16]},{id:"frontier-A",p1:.57,pr:.82,price:3.0,tok:[600,2000],lat:[3,9]},{id:"frontier-B",p1:.46,pr:.78,price:1.2,tok:[600,2200],lat:[2,7]}];
const DEFECT_FIX={"xsd-invalid":"xsdFixed","profile-component":"compFixed","containerfield-type-mismatch":"hardFixed","route-invalid-from-field":"latentFixed","interpolator-key-length":"late2Fixed"};
const drawsNothing=t=>(t.noComp&&!t.compFixed)||(t.hard&&!t.hardFixed);
function synthXml(t){const sh=t.shp.map((s,i)=>{const tr=`translation="${s.x} ${s.y} ${s.z}"`,geo=t.noComp?(i%2?`<Circle2D radius="0.8"/>`:`<Rectangle2D size="1.4 1"/>`):`<${s.k}/>`;
    return t.hard&&!t.hardFixed?`<Transform DEF="T${i}" ${tr}><Group><${s.k}/></Group></Transform>`:`<Transform DEF="T${i}" ${tr}><Shape DEF="S${i}"><Appearance><Material diffuseColor="${s.c}"/></Appearance>${geo}</Shape></Transform>`}).join("");
  const route=t.latent&&!t.latentFixed?`<ROUTE fromNode="T0" fromField="translation_chg" toNode="T1" toField="translation"/>`:"";
  const anim=t.late2?`<TimeSensor DEF="TS" loop="true" cycleInterval="4"/><OrientationInterpolator DEF="OI" key="${t.late2Fixed?"0 1":"0 0.5 1"}" keyValue="0 1 0 0 0 1 0 3.14"/><ROUTE fromNode="TS" fromField="fraction_changed" toNode="OI" toField="set_fraction"/><ROUTE fromNode="OI" fromField="value_changed" toNode="T0" toField="rotation"/>`:"";
  return `<X3D profile="Interchange" version="4.0"><head>${t.compFixed?"<component name='Geometry2D' level='1'/>":""}</head><Scene><Viewpoint position="0 0 9"${t.xsd&&!t.xsdFixed?' fieldOfView="wide"':""}/>${sh}${route}${anim}</Scene></X3D>`}
function judgeSyn(t,V){const codes=[];if(t.xsd&&!t.xsdFixed)codes.push("xsd-invalid");
  if(V.strict>=1){if(t.noComp&&!t.compFixed)codes.push("profile-component");if(t.hard&&!t.hardFixed)codes.push("containerfield-type-mismatch");if(t.latent&&!t.latentFixed)codes.push("route-invalid-from-field")}
  if(V.strict>=2&&t.late2&&!t.late2Fixed)codes.push("interpolator-key-length");return{verdict:codes.length?"invalid":"valid",codes}}
const GAP={scenes:[],seq:0,vi:0,VALS:VALS.filter(v=>v.id==="svc"||v.id==="f1"||v.id==="f2"),seed:1,flips:0,revals:0,log:[],cv:null,R:null,mod:{},
  build(){const sel=el("select",{id:"gapVal",title:"the modeled validator: strictness levels mirror the recorded ladder"},GAP.VALS.map((v,i)=>el("option",{value:String(i),text:v.ref})));sel.addEventListener("change",()=>{GAP.vi=+sel.value;GAP.render()});
    const seed=el("input",{type:"number",id:"gapSeed",min:"1",max:"99999",value:"1",title:"mulberry32 seed: the same seed replays the same modeled world"});
    const d=el("details",{class:"drawer modeled",id:"gapDrawer"},[el("summary",{text:"Model the gap (simulated) · MODELED · nothing here was called"}),el("div",null,[
      el("div",{class:"row"},[stamp("source","MODELED"),stamp("validator","none"),stamp("renderer","none"),gradeChip("S"),el("span",{class:"note warnNote",text:"SIMULATED: every body, verdict and timing below is modeled with a seeded generator (mulberry32). Nothing was called, nothing here enters a claim, the wall, the firehose, the tiles or Ask the files. The drawer exists to prove one point: a validator that cannot see a defect lets a blank scene through."})]),
      el("div",{class:"row"},[el("label",null,["seed",seed]),el("button",{class:"warn",id:"gapRun",text:"RUN 40 SCENES (simulated)",onclick:()=>{GAP.seed=+seed.value||1;GAP.run(40)}}),el("label",null,["validator",sel]),el("button",{class:"warn",id:"gapReval",text:"RE-VALIDATE (simulated)",onclick:()=>GAP.revalidate()}),el("span",{class:"note m",id:"gapPoint",text:""})]),
      el("div",{class:"gapGrid"},[el("div",{class:"cv"},[GAP.cv=el("canvas",{id:"gapWall","aria-label":"mini wall of the modeled population"})]),el("div",{class:"scroll gapFh"},[el("table",{id:"gapFh"},[el("thead",null,el("tr",null,["id","model","verdict","validator","frame","chain"].map(h=>el("th",{text:h})))),el("tbody")])])]),
      el("div",{class:"alerts m",id:"gapLog"})])]);return d},
  run(n){GAP.R=mulberry32(GAP.seed|0);GAP.scenes=[];GAP.seq=0;GAP.flips=0;GAP.revals=0;GAP.log=[];GAP.mod={};MODELS_SYN.forEach(m=>GAP.mod[m.id]={n:0,valid:0});for(let i=0;i<(n||40);i++)genSyn();GAP.say(`modeled ${GAP.scenes.length} scenes on ${GAP.VALS[GAP.vi].ref} (seed ${GAP.seed}) · ${GAP.scenes.filter(s=>s.verdict==="valid").length} valid, ${GAP.scenes.filter(s=>s.verdict==="valid"&&s.blank).length} of them modeled blank`);GAP.render();return GAP.scenes},
  revalidate(){const V=GAP.VALS[GAP.vi];let n=0,fl=0;GAP.scenes.forEach(sc=>{if(sc.vref===V.ref)return;const prev=sc.verdict,j=judgeSyn(sc.truth,V);sc.xml=addStep(sc.xml,{op:"validate",validator:V.name,validator_ref:V.ref,verdict:j.verdict,codes:j.codes,ms:0,ms_src:"modeled"},sc.xml,false);sc.nsteps=readSteps(sc.xml).length;sc.verdict=j.verdict;sc.vref=V.ref;sc.status=verify(sc.xml).status;if(prev==="valid"&&j.verdict==="invalid")fl++;n++});
    GAP.revals+=n;GAP.flips+=fl;GAP.say(`re-validated ${n} scenes on ${V.ref}: ${fl} flipped valid → invalid (modeled). Answered from the stamped files alone.`);GAP.render();return{n,flips:fl}},
  say(m){GAP.log.unshift(m);if(GAP.log.length>12)GAP.log.pop();const h=$("gapLog");if(h){while(h.children.length<GAP.log.length)h.appendChild(el("div",{class:"al sys"}));while(h.children.length>GAP.log.length)h.removeChild(h.lastChild);GAP.log.forEach((t,i)=>txt(h.children[i],t))}},
  signature(){return GAP.scenes.map(s=>s.id+":"+s.status+":"+s.verdict+":"+s.nsteps+":"+(s.blank?1:0)).join(",")},
  render(){const c=GAP.cv;if(c){const cw=c.clientWidth||400,cell=14,gap=2,cols=Math.max(4,Math.floor((cw-gap)/(cell+gap))),rows=Math.max(1,Math.ceil(Math.max(1,GAP.scenes.length)/cols)),h=rows*(cell+gap)+gap,{ctx,w}=fitCanvas(c,cw,h);ctx.clearRect(0,0,w,h);
      GAP.scenes.forEach((s,i)=>{const x=gap+(i%cols)*(cell+gap),y=gap+Math.floor(i/cols)*(cell+gap);ctx.fillStyle=cssv(STATUS_COL[s.status]||"--dim");ctx.fillRect(x,y,cell,cell);if(s.verdict==="invalid"){ctx.fillStyle=cssv("--info");ctx.fillRect(x,y+cell-3,cell,3)}if(s.blank&&s.verdict==="valid"){ctx.fillStyle=cssv("--warn");ctx.fillRect(x+cell-4,y+1,3,3)}});
      ctx.strokeStyle=cssv("--warn");ctx.lineWidth=1;ctx.strokeRect(.5,.5,w-1,h-1)}
    const tb=document.querySelector("#gapFh tbody");if(tb){tb.textContent="";GAP.scenes.slice().reverse().slice(0,40).forEach(s=>tb.appendChild(el("tr",null,[s.id,s.model,s.verdict,s.vref,s.blank?"modeled blank":"modeled "+fmt.pct(s.nb||0,0),s.status].map(v=>el("td",{text:String(v)})))))}
    const valid=GAP.scenes.filter(s=>s.verdict==="valid"),bv=valid.filter(s=>s.blank).length;txt("gapPoint",GAP.scenes.length?`${bv} of ${valid.length} valid scenes draw nothing on ${GAP.VALS[GAP.vi].ref} (modeled): a validator that cannot see a defect lets a blank scene through`:"")}};
function genSyn(){const R=GAP.R,rr=(a,b)=>a+R()*(b-a),pick=a=>a[(R()*a.length)|0],m=pick(MODELS_SYN),id="S-"+String(++GAP.seq).padStart(4,"0"),rep=R()<.6,V=GAP.VALS[GAP.vi],clean=R()<m.p1,n=2+((R()*4)|0);
  const t={xsd:false,noComp:false,hard:false,latent:false,late2:false,xsdFixed:false,compFixed:false,hardFixed:false,latentFixed:false,late2Fixed:false,shp:[]};
  for(let i=0;i<n;i++)t.shp.push({k:pick(["Box","Sphere","Cone","Cylinder"]),c:[R().toFixed(2),R().toFixed(2),R().toFixed(2)].join(" "),x:+rr(-3,3).toFixed(2),y:+rr(-1.5,1.5).toFixed(2),z:+rr(-2,2).toFixed(2)});
  if(!clean){const d=R(),blind=()=>{if(R()<.7)t.noComp=true;else t.hard=true};if(d<.5)t.xsd=true;else if(d<.6)blind();else{t.xsd=true;blind()}t.latent=R()<.25;t.late2=R()<.05}
  const sc={id,src:"syn",model:m.id,mode:rep?"repair":"oneshot",truth:t,sealed:false,status:"?",nsteps:0,vref:"",verdict:"",xml:"",nb:null,blank:false};
  const M=GAP.mod[m.id];M.n++;let x=synthXml(t);const tin=Math.round(rr(m.tok[0],m.tok[1])*.35),tout=Math.round(rr(m.tok[0],m.tok[1])),lat=Math.round(rr(m.lat[0],m.lat[1])*1000);
  x=addStep(x,{op:"generate",model:m.id,provider:"sim",condition:rep?"report_repair":"oneshot",prompt_sha256:sha("p"+id).slice(0,16),tokens_in:tin,tokens_out:tout,latency_ms:lat,ms:lat,ms_src:"simulated",input_sha256:"none"},x,false);
  const vst=()=>{const j=judgeSyn(t,V);x=addStep(x,{op:"validate",validator:V.name,validator_ref:V.ref,verdict:j.verdict,codes:j.codes,ms:Math.round(rr(120,900)),ms_src:"modeled"},x,false);return j};
  let v=vst();
  if(v.verdict==="invalid"&&rep){for(let round=1;round<=3&&v.verdict==="invalid";round++){const shown=judgeSyn(t,V).codes,ok=R()<m.pr;if(ok)shown.forEach(c=>{if(DEFECT_FIX[c])t[DEFECT_FIX[c]]=true});
      x=addStep(x,{op:"repair",kind:"model",model:m.id,round,report_shown:true,fixes:ok?shown:[],ms:Math.round(lat*.5),ms_src:"simulated"},synthXml(t),false);v=vst()}}
  if(v.verdict==="valid"){M.valid++;const blank=drawsNothing(t),nb=blank?0:+rr(.08,.6).toFixed(3);sc.nb=nb;sc.blank=blank;sc.drawKind=blank?"nothing drawable":"draws";
    x=addStep(x,{op:"render",renderer:"modeled from the scene's defects (no renderer ran)",load_ok:true,nodes:t.shp.length,nonblank_ratio:nb,no_frame:blank?1:0,unknown_nodes:blank?t.shp.length:0,ms:Math.round(rr(900,2600)),ms_src:"modeled"},x,false)}
  sc.xml=x;sc.nsteps=readSteps(x).length;sc.vref=V.ref;sc.verdict=v.verdict;sc.status=verify(x).status;GAP.scenes.push(sc);return sc}
Object.assign(self,{WALL,inject,GAP,LEDGER});
})();
