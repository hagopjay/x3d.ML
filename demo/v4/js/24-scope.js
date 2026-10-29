/* 24-scope.js — S6.3 VALIDATOR OSCILLOSCOPE (SPEC-v4 S6.3; WORKPLAN 24-scope). Globals: SCOPE, __panels.scope.
   New in v4: v3 had no oscilloscope; the ratio came from v3's LIVESTATS vmed/mmed (demo/tether-firehose-v3.template.html line 260) and was printed as a KPI tile.
   Here it is a canvas under the waterfall: log-y 1 ms … 1000 s with decades, the model-call trace (red, one sample per call at t1, y = ms) riding over the validator
   trace (green, y = vms), verdict ticks on the baseline (green up valid, red down invalid, hollow red failed call, cyan in flight), a faint ratio band between the traces with
   the running median readout, afterglow at fx 2 only, the decade drill (x span 76 min → 1 ms one decade per 400 ms and back; reduced motion / fx 0 jumps), and the replay
   note (11 Oct recorded no validator time: the green trace is absent and #scopeNote says so). Reads FILM.source() and WF.pack() (22-waterfall) and WF.win (shared window).
   24 Oct slot: samples carry arm (A solid, B dashed) and tft (time to first token, amber trace) when the run24 part has them; the sparklines slot draws per-arm tokens/s
   under the baseline when FILM.source() lanes carry arms. Every number: CLAIMS c.ratio (02-claims) and scope.ratioX (here) are the chips; the canvas readout is the running value.
   Test hooks: __panels.scope.{samples, drawn, hasVal, span, drilling, decade, decadeLabels, ratioX, mode}, SCOPE.add(sample), SCOPE.drill(), SCOPE.samples(), SCOPE.decadeLabels(),
   #scopeNote, #scopeDrill, #scopeHost .claim[data-claim="c.ratio"], .claim[data-claim="scope.ratioX"]. */
(function(){
"use strict";
const B=LOOP.bits;
let cv=null,host=null,note=null,panel=null,width=0,noteSig="";
const added=[];let drill=null,sampleSig="",samples=[],hasVal=false;
const DEC=["1 ms","10 ms","100 ms","1 s","10 s","100 s","1000 s"];
const reduced=()=>(self.FX&&FX.level===0)||(typeof matchMedia==="function"&&matchMedia("(prefers-reduced-motion: reduce)").matches);
/* two significant digits, truncated (4610 s → 76 min, 461 s → 7.6 min, 46.1 s → 46 s, .461 s → 460 ms), as a clean string */
function sig2(x){if(!(x>0))return"0";const e=Math.floor(Math.log10(x)+1e-12),f=Math.pow(10,e-1);const m=Math.floor(x/f+1e-9);return String(parseFloat((m*f).toPrecision(2)))}
function spanLabel(s){if(s>=60)return sig2(s/60)+" min";if(s>=1)return sig2(s)+" s";return sig2(s*1000)+" ms"}
function steps(){const P=self.WF&&WF.pack();const tm=Math.max(1,(P&&P.tmax)||4610);const out=[];for(let i=0;i<7;i++)out.push(tm/Math.pow(10,i));out.push(.001);return out}
function samplesNow(){const P=WF.pack();if(!P||!self.S)return[];const clk=S.clk;let lo=0,hi=P.all.length;while(lo<hi){const m=(lo+hi)>>1;if(P.all[m].t1<=clk)lo=m+1;else hi=m}
  const sg=P.src.mode+"|"+P.total+"|"+lo+"|"+added.length;if(sg!==sampleSig){sampleSig=sg;
    samples=P.all.slice(0,lo).map(q=>({t:q.t1,ms:q.ms,vms:q.vms,ok:q.ok,lane:q.lane,arm:q.lane.arm||null,tft:q.tft,auto:q.auto,you:false})).concat(added).sort((a,b)=>a.t-b.t);hasVal=samples.some(s=>s.vms!=null&&s.vms>0)}
  return samples}
/* the running medians use the record's rule (02-claims c.ratio: sorted value at n >> 1 over every call, 0 ms validator times included, factor = mmed / max(1, vmed)) */
function running(){const ms=UTIL.median(samples.filter(s=>!s.you).map(s=>s.ms)),vms=UTIL.median(samples.filter(s=>!s.you&&s.vms!=null).map(s=>s.vms));return{mmed:ms,vmed:vms,x:ms!=null&&vms!=null?Math.round(ms/Math.max(1,vms)):null}}
function drawScope(now){if(!cv||!self.WF)return;const P=WF.pack();if(!P)return;const p=panel;const S0=self.S;const clk=S0?S0.clk:0;
  const W=width||cv.clientWidth||600,V=W<600,H=V?80:140;const{ctx}=fitCanvas(cv,W,H);const fx=self.FX?FX.level:0;const mono=cssv("--mono")||"monospace";
  const C={bg:cssv("--p0"),line:cssv("--line"),line2:cssv("--line2"),fg:cssv("--fg"),mute:cssv("--mute"),dim:cssv("--dim"),ok:cssv("--ok"),bad:cssv("--bad"),acc:cssv("--acc"),warn:cssv("--warn"),info:cssv("--info"),you:cssv("--you")};
  const sm=samplesNow();
  /* x window: the drill overrides the shared window */
  let span,x0t,x1t,dr=false;const st=steps();
  if(drill){dr=true;if(drill.jump){span=drill.dir>0?st[st.length-1]:st[0];if(drill.dir<0){drill=null;dr=false}}
    else{const el=now-drill.t0,per=400,n=st.length-1;let i=Math.min(n,Math.floor(el/per)),f=Math.min(1,(el-i*per)/per);
      if(drill.dir>0){if(i>=n){span=st[n];if(el>n*per+1200){drill={dir:-1,t0:now}}}else span=Math.exp(Math.log(st[i])+(Math.log(st[i+1])-Math.log(st[i]))*f)}
      else{const j=n-i;if(i>=n){span=st[0];drill=null;dr=false}else span=Math.exp(Math.log(st[j])+(Math.log(st[j-1])-Math.log(st[j]))*f)}
      if(drill)LOOP.dirty(B.CLOCK)}}
  if(dr){x1t=clk;x0t=clk-span}else{const w=WF.win||{t0:0,t1:Math.max(1,P.tmax)};x0t=w.t0;x1t=w.t1;span=x1t-x0t}
  const L=V?40:46,R=8,T=10,BL=V?14:22,plotW=W-L-R,plotH=H-T-BL,y0=T+plotH;const X=t=>L+plotW*(t-x0t)/Math.max(1e-9,x1t-x0t),Y=ms=>T+plotH*(1-Math.log10(Math.max(1,ms))/6);
  /* afterglow at fx 2: the previous frame fades instead of being cleared */
  if(fx>=2&&!dr){ctx.globalAlpha=.08;ctx.fillStyle=C.bg;ctx.fillRect(0,0,W,H);ctx.globalAlpha=1;ctx.clearRect(0,0,L,H);ctx.clearRect(0,0,W,T);ctx.clearRect(0,y0,W,BL)}else ctx.clearRect(0,0,W,H);
  /* decades */
  ctx.font="500 10.5px "+mono;ctx.textBaseline="alphabetic";ctx.strokeStyle=C.line;ctx.lineWidth=1;
  for(let d=0;d<=6;d++){const y=T+plotH*(1-d/6);ctx.beginPath();ctx.moveTo(L,y+.5);ctx.lineTo(W-R,y+.5);ctx.stroke();if(!V||d%2===0){ctx.fillStyle=C.dim;ctx.textAlign="right";ctx.fillText(DEC[d],L-4,y+3);ctx.textAlign="left"}}
  /* x axis labels: window edges (and the span while drilling) */
  ctx.fillStyle=C.dim;ctx.fillText(dr?`−${spanLabel(span)}`:fmt.clock(x0t),L,H-3);ctx.textAlign="right";ctx.fillText(dr?"now":fmt.clock(x1t),W-R,H-3);ctx.textAlign="left";
  ctx.save();ctx.beginPath();ctx.rect(L,T,plotW,plotH+BL);ctx.clip();
  const inWin=sm.filter(s=>s.t>=x0t&&s.t<=x1t);
  /* ratio band between the two traces */
  if(hasVal&&inWin.length>1){const pts=inWin.filter(s=>s.vms!=null&&s.vms>0&&s.ms>0);if(pts.length>1){ctx.fillStyle=C.acc;ctx.globalAlpha=.12;ctx.beginPath();pts.forEach((s,i)=>{const x=X(s.t),y=Y(s.ms);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});
    for(let i=pts.length-1;i>=0;i--)ctx.lineTo(X(pts[i].t),Y(pts[i].vms));ctx.closePath();ctx.fill();ctx.globalAlpha=1}}
  /* traces: model red (arm B dashed), validator green, tft amber */
  const trace=(pts,col,wdt,dash)=>{if(!pts.length)return;ctx.strokeStyle=col;ctx.lineWidth=wdt;ctx.setLineDash(dash||[]);if(fx>=2){ctx.shadowColor=col;ctx.shadowBlur=6}ctx.beginPath();pts.forEach((q,i)=>{if(i===0)ctx.moveTo(q.x,q.y);else ctx.lineTo(q.x,q.y)});ctx.stroke();ctx.shadowBlur=0;ctx.setLineDash([]);
    if(pts.length<40){ctx.fillStyle=col;pts.forEach(q=>ctx.fillRect(q.x-1,q.y-1,2.5,2.5))}};
  const arms=[...new Set(inWin.map(s=>s.arm||""))];
  arms.forEach(arm=>{const pts=inWin.filter(s=>(s.arm||"")===arm&&s.ms>0).map(s=>({x:X(s.t),y:Y(s.ms)}));trace(pts,C.bad,1.5,arm==="B"?[4,3]:null)});
  if(hasVal)arms.forEach(arm=>{const pts=inWin.filter(s=>(s.arm||"")===arm&&s.vms!=null&&s.vms>0).map(s=>({x:X(s.t),y:Y(s.vms)}));trace(pts,C.ok,1.5,arm==="B"?[4,3]:null)});
  const tft=inWin.filter(s=>s.tft!=null&&s.tft>0).map(s=>({x:X(s.t),y:Y(s.tft)}));if(tft.length)trace(tft,C.warn,1,[2,2]);
  const youPts=inWin.filter(s=>s.you&&s.ms>0).map(s=>({x:X(s.t),y:Y(s.ms)}));if(youPts.length){ctx.fillStyle=C.you;youPts.forEach(q=>ctx.fillRect(q.x-2,q.y-2,4,4))}
  /* verdict ticks on the baseline */
  inWin.forEach(s=>{const x=X(s.t);if(s.ok){ctx.fillStyle=C.ok;ctx.fillRect(x-.5,y0-5,1.5,5)}else{ctx.fillStyle=C.bad;ctx.fillRect(x-.5,y0,1.5,5)}});
  const ev=P.ev||{};if(!S0||S0.flags.failed!==false)(ev.failed||[]).forEach(f=>{if(f.t0>clk||f.t0<x0t||f.t0>x1t)return;const x=X(f.t0);ctx.strokeStyle=C.bad;ctx.lineWidth=1;ctx.beginPath();ctx.arc(x,y0+6,2.4,0,Math.PI*2);ctx.stroke()});
  P.all.forEach(q=>{if(q.t0<=clk&&q.t1>clk&&q.t0>=x0t&&q.t0<=x1t){const x=X(q.t0);ctx.fillStyle=C.acc;ctx.fillRect(x-.5,y0-7,1.5,7)}});
  /* decade drill: the latest finished call's two durations laid on the time axis, so the validator bar appears as the span reaches its decade */
  if(dr&&sm.length){const last=sm[sm.length-1];const bar=(ms,col,y,label)=>{if(!(ms>0))return;const xa=Math.max(L,X(clk-ms/1000)),xb=X(clk);ctx.fillStyle=col;ctx.globalAlpha=.85;ctx.fillRect(xa,y,Math.max(1.5,xb-xa),6);ctx.globalAlpha=1;ctx.fillStyle=col;ctx.textAlign="right";ctx.fillText(label,xb-2,y-2);ctx.textAlign="left"};
    bar(last.ms,C.bad,T+14,`model call ${fmt.ms(last.ms)}`);if(last.vms!=null)bar(last.vms,C.ok,T+34,`validator ${fmt.ms(last.vms)}`);else{ctx.fillStyle=C.dim;ctx.fillText("validator time not recorded",L+4,T+40)}}
  /* playhead */
  if(!dr){const x=X(clk);ctx.strokeStyle=C.warn;ctx.setLineDash([3,2]);ctx.beginPath();ctx.moveTo(x+.5,T);ctx.lineTo(x+.5,y0);ctx.stroke();ctx.setLineDash([])}
  ctx.restore();
  /* readout: the running median ratio over the calls released so far */
  const r=running();ctx.fillStyle=C.fg;ctx.font="600 12.5px "+mono;ctx.textAlign="right";
  if(r.x!=null)ctx.fillText(`×${fmt.int(r.x)} median`,W-R,T+12);else if(sm.length)ctx.fillText(hasVal?"…":"no validator time in this run",W-R,T+12);
  ctx.font="500 10.5px "+mono;ctx.fillStyle=C.dim;if(r.mmed!=null)ctx.fillText(`model ${fmt.ms(r.mmed)}${r.vmed!=null?" · validator "+fmt.ms(r.vmed):""} · ${sm.length} calls`,W-R,T+24);ctx.textAlign="left";
  Object.assign(p,{samples:sm.length,drawn:inWin.length,hasVal,span,drilling:!!drill,decade:dr?Math.round(Math.log10(Math.max(1e-9,span))*100)/100:null,ratioX:r.x,mode:P.src.mode});
  const ns=P.src.mode;if(ns!==noteSig){noteSig=ns;txt(note,ns==="replay11"?"validator time not recorded on 11 Oct · green trace absent · model latency as recorded":ns==="run24"?"validator fork@8dd0d3e in process · model ms provider-reported · tft ticks from the stream · arm B dashed":"validator fork@eb4b4b4 in process (vms) · model ms provider-reported · one sample per call at its end · log y")}}
const SCOPE={
  mount(h){host=h;h.textContent="";const head=el("header",{class:"scopeHead"});head.append(el("h3",{text:"Validator oscilloscope"}),el("span",{class:"sub",text:"log y 1 ms … 1000 s · model call red · validator green · ticks: verdicts, failed, in flight"}));
    const btn=el("button",{id:"scopeDrill",text:"decade drill",title:"x span 76 min → 1 ms one decade per 400 ms and back"});btn.addEventListener("click",()=>SCOPE.drill());head.appendChild(btn);
    head.appendChild(claimChip("c.ratio",{size:"s",label:"validator median vs model-call median"}));head.appendChild(claimChip("scope.ratioX",{size:"s",label:"× faster, median over 358 calls"}));
    note=el("span",{class:"m scopeNote",id:"scopeNote"});head.appendChild(note);h.appendChild(head);
    const box=el("div",{class:"cv scopeCv"});cv=el("canvas",{id:"scopeCanvas","aria-label":"validator oscilloscope: model call time and validator time per call on a log scale"});box.appendChild(cv);h.appendChild(box);
    panel=LOOP.register({name:"scope",bit:B.SCENE|B.CLOCK|B.MODE|B.RESIZE|B.THEME|B.DATA|B.LANE|B.HOVER,el:cv,rateHz:(self.FX&&FX.level===0)?12:30,budgetMs:4,draw:drawScope,degrade(){}});
    Object.assign(panel,{samples:0,drawn:0,hasVal:false,span:0,drilling:false,decade:null,decadeLabels:SCOPE.decadeLabels,ratioX:null,mode:""});
    if(typeof ResizeObserver!=="undefined")new ResizeObserver(es=>{width=es[0].contentRect.width;LOOP.dirty(B.RESIZE|B.SCENE)}).observe(box);
    if(self.SIM){SIM.on("mode",()=>{sampleSig="";added.length=0;drill=null;LOOP.dirty(B.MODE|B.SCENE)});SIM.on("reset",()=>{sampleSig="";LOOP.dirty(B.SCENE)})}
    if(self.FX)FX.onChange(()=>{panel.rateHz=FX.level===0?12:30});return panel},
  /* a sample from outside the record (the viewer lane): {t (run clock s; default now), ms, vms, ok, lane} */
  add(s){const t=s&&s.t!=null?+s.t:(self.S?S.clk:0);added.push({t,ms:+s.ms||0,vms:s.vms==null?null:+s.vms,ok:!!s.ok,lane:s.lane||"you",arm:null,tft:null,auto:false,you:true});sampleSig="";LOOP.dirty(B.LANE|B.SCENE);return added.length},
  clear(){added.length=0;sampleSig="";LOOP.dirty(B.SCENE)},
  samples:()=>samples,
  decadeLabels:()=>steps().map(spanLabel),
  drill(){if(drill&&!drill.jump){drill={dir:drill.dir>0?-1:1,t0:LOOP.now};LOOP.dirty(B.CLOCK);return"reverse"}
    if(reduced()){drill=drill?{dir:-1,jump:true}:{dir:1,jump:true};LOOP.dirty(B.CLOCK);return drill.dir>0?"jump in":"jump out"}
    drill={dir:1,t0:LOOP.now};LOOP.dirty(B.CLOCK);return"start"},
  drilling:()=>!!drill};
CLAIMS.define("scope.ratioX",{label:"validator vs model-call median, factor",unit:"median A[].ms ÷ median A[].vms over 358 calls, rounded",needs:["live.core"],grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none",
  expected:(self.STATS&&STATS.claims&&STATS.claims["c.ratio"]&&STATS.claims["c.ratio"].expected)?STATS.claims["c.ratio"].expected.x:undefined,text:v=>v==null?"—":"×"+fmt.int(v),
  compute(){const vmed=UTIL.median(LIVE.flatMap(i=>i.A.map(a=>a.vms))),mmed=UTIL.median(LIVE.flatMap(i=>i.A.map(a=>a.ms)));return Math.round(mmed/Math.max(1,vmed))}});
Object.assign(self,{SCOPE});
})();
