/* 26-raster.js — S7 FIRST-LIGHT RASTER (SPEC-v4 S7; WORKPLAN 26-raster). Section #raster, part renders.series.
   Owns: the paired-row raster canvas (X_ITE 16.5.0 pass above, 16.5.1 pass below, for every body both passes measured: 383 live attempts + 174 replay scenes),
   first-light ticks, sort / brush / hover / click → stage, the "Show all attempts" toggle, the measured-frame thumbnails (live.jpg), and the live
   REPRODUCED / DIFFERS / "same answer, slower device" row that re-measures a chosen body through STAGE.measure in this browser.
   Globals: RASTER = {rows(), setSort(k), setAll(bool), select(key), measure(key) → Promise<R>, live(key, R), body(row), row(key), times(rec), cls(rec), panel}.
   Claims: raster.flips (paired bodies whose draws/blank/unparseable class differs between the patches; expected {pairs: MANIFEST rows of renders.151, flips: 0}),
           raster.rows (174 + 201 rows by default), raster.firstLight (median first light of the drawing rows, 16.5.0 offline; no baked expected: pending → earned).
   Test hooks: __panels.raster.{rows, rowsAll, paired, flips, samples, hover, sel, live, sort, allAttempts, scrollTop, lastDraw, builds, visible, degraded}, RASTER.measure(key), RASTER.live(key, R).
   v3 port: WORKPLAN §A assigns no v3 function to this module (the raster is a new instrument); the sample-time reconstruction below follows the v3/08 watcher rule
   (watchFrames, v3 lines 846–850: the first 8 frames, then at most one sample per 150 ms, 20 samples at most) because the passes recorded values, not timestamps.
   Honesty: every live number comes from STAGE.measure (rule 4); the live row is never counted; sample times are reconstructed from first, last, frames and say so. */
(function(){
"use strict";
const AXIS_H=16,PITCH=6,T_LIN=200,BLANK=.005;
const slug=m=>String(m).replace("/","_");
/* ---------- rows ---------- */
let rows=[],rowsAll=[],byKey=new Map(),built=0;
const cls=rec=>!rec?"missing":rec.err||rec.nb==null&&rec.nonblank==null?"unparseable":((rec.nb!=null?rec.nb:rec.nonblank)||0)>=BLANK?"draws":"blank";
/* sample k's time since load, reconstructed: frame i ≈ first + i·(last−first)/(frames−1); samples 0..7 are frames 0..7, later samples the first frame ≥ 150 ms after the previous sample */
function times(rec){const s=(rec&&rec.series)||[],n=s.length,out=new Array(n);if(!n)return out;const first=rec.first||0,last=rec.last!=null?rec.last:first,frames=Math.max(1,rec.frames||n),dtf=frames>1?(last-first)/(frames-1):0;
  let t=first;for(let k=0;k<n;k++){if(k===0)t=first;else if(k<8)t=first+k*dtf;else t=t+(dtf>0?Math.max(dtf,Math.ceil(150/dtf)*dtf):150);out[k]=Math.min(Math.max(t,first),Math.max(last,first))}return out}
const firstLight=rec=>{if(!rec||!rec.series)return null;const i=rec.series.findIndex(v=>v>0);if(i<0)return null;return times(rec)[i]};
function norm150(v){return v?{series:v.series||[],first:v.first,last:v.last,frames:v.frames,nb:v.nonblank,err:v.nonblank==null&&!(v.series&&v.series.length)?"X_ITE could not parse this file":null}:null}
function norm151(v){return v?{series:v.series||[],first:v.first,last:v.last,frames:v.frames,nb:v.nb,err:v.err||null}:null}
function build(){
  const R0=self.R150,R1=self.R151;if(!R0)return;rowsAll=[];byKey=new Map();
  const liveBy=new Map();(self.LIVE||[]).forEach(it=>liveBy.set(slug(it.m)+"/"+it.p,it));
  Object.keys(R0.live).forEach(key=>{const m=/^(.+)\/([\w-]+)_a(\d+)\.x3d$/.exec(key);if(!m)return;const it=liveBy.get(m[1]+"/"+m[2])||null,k=+m[3];const a=norm150(R0.live[key]),b=R1?norm151(R1.live[key]):null;
    if(it&&it.A[k-1]&&it.A[k-1].r&&it.A[k-1].r.err)a.err=it.A[k-1].r.err;
    const r={key,src:"live",m:it?it.m:m[1],p:m[2],c:it?it.c:"?",k,final:!!it&&it.A.length===k,onPage:!!(it&&it.A[k-1]),item:it,a,b,cls0:cls(a),cls1:b?cls(b):"missing",fl0:firstLight(a),fl1:firstLight(b),id:it?"L"+String(it.i+1).padStart(3,"0")+"·a"+k:"cut·a"+k};
    r.flip=!!b&&r.cls0!==r.cls1;rowsAll.push(r);byKey.set(key,r)});
  (self.REAL||[]).forEach(it=>{const a=norm151({nb:it.r.nb,frames:it.r.frames,first:it.r.first,last:it.r.last,err:it.r.err,series:it.r.series}),b=R1&&R1.replay[it.k]?norm151(R1.replay[it.k]):null;
    const r={key:it.k,src:"real",m:it.m,mo:it.mo,p:it.p,c:it.c,k:it.at,final:true,onPage:true,item:it,a,b,cls0:cls(a),cls1:b?cls(b):"missing",fl0:firstLight(a),fl1:firstLight(b),id:"R"+String(it.i+1).padStart(3,"0")};
    r.flip=!!b&&r.cls0!==r.cls1;rowsAll.push(r);byKey.set(it.k,r)});
  built++;applySort();}
let sortKey="first",allAttempts=false,sel=null,hover=null,live=null,brush=null;
const flOrder=r=>r.fl0==null?(r.cls0==="unparseable"?3e9:2e9):r.fl0;
function applySort(){
  rows=rowsAll.filter(r=>allAttempts||r.final);
  const by={first:(x,y)=>flOrder(x)-flOrder(y)||x.key.localeCompare(y.key),model:(x,y)=>x.m.localeCompare(y.m)||x.p.localeCompare(y.p)||x.k-y.k,category:(x,y)=>x.c.localeCompare(y.c)||flOrder(x)-flOrder(y)}[sortKey];
  rows.sort(by);if(live&&byKey.has(live.key)){const i=rows.findIndex(r=>r.key===live.key);if(i>0)rows.unshift(rows.splice(i,1)[0]);else if(i<0&&byKey.get(live.key))rows.unshift(byKey.get(live.key))}
  P.rows=rows.length;P.rowsAll=rowsAll.length;P.paired=rows.filter(r=>r.b).length;P.flips=rowsAll.filter(r=>r.flip).length;P.sort=sortKey;P.allAttempts=allAttempts;
  P.forceDraw=true;unitLine()}
/* ---------- claims ---------- */
CLAIMS.define("raster.flips",{label:"bodies whose draws / blank / unparseable class differs between X_ITE 16.5.0 and 16.5.1",unit:"of the paired bodies · 0.5 % line · viewAll(0) rig",needs:["renders.series","renders.151","live.core","replay"],
  expected:{pairs:(self.MANIFEST&&MANIFEST.parts&&MANIFEST.parts["renders.151"]&&MANIFEST.parts["renders.151"].rows)||null,flips:0},grade:"C",source:"MEASURED 24 Oct",validator:"none",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline",
  files:["parts/renders.series.txt (16.5.0, 17 Oct)","parts/renders.151.txt (16.5.1, 24 Oct)","parts/live.core.txt","parts/replay.txt","docs/RENDER-16.5.1.md"],
  fields:["class = unparseable when the pass recorded an error, draws when the best of 20 in-callback samples ≥ 0.5 % of pixels differ from the dominant colour, else blank; a flip is a different class on the two passes; pairs = bodies present in both passes (383 live attempts + 174 replay scenes)"],
  why:"both passes ran the same rig (viewer-default camera + viewAll(0), no Viewpoint bound, headless software GL); the 0 is the recorded finding of the 24 Oct pass and is recomputed here from the two parts",
  text:v=>`${v.flips} of ${v.pairs}`,compute(){if(!rowsAll.length)build();const p=rowsAll.filter(r=>r.b);return{pairs:p.length,flips:p.filter(r=>r.flip).length}}});
CLAIMS.define("raster.rows",{label:"rows in the raster",unit:"174 replay scenes + 201 live finals",needs:["live.core","replay"],expected:(self.STATS&&STATS.REALSTATS&&STATS.LIVESTATS)?STATS.REALSTATS.n+STATS.LIVESTATS.n:undefined,grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"none",
  fields:["REAL.length + LIVE.length (one row per replay scene, one per live chain's final attempt); Show all attempts adds the other live attempts"],compute(){return (self.REAL||[]).length+(self.LIVE||[]).length}});
CLAIMS.define("raster.firstLight",{label:"median first light, drawing rows",unit:"ms since load · X_ITE 16.5.0 offline · reconstructed sample time",needs:["renders.series","replay"],grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"X_ITE 16.5.0 offline",
  fields:["first non-zero of the 20 samples, placed at frame i ≈ first + i·(last−first)/(frames−1) for the first 8 frames, then the first frame ≥ 150 ms after the previous sample (the watcher's rule); median over rows that draw"],text:v=>fmt.ms(v),
  compute(){if(!rowsAll.length)build();return UTIL.median(rowsAll.filter(r=>r.final&&r.cls0==="draws"&&r.fl0!=null).map(r=>r.fl0))}});
/* ---------- DOM ---------- */
let box=null,wrap=null,canvas=null,spacer=null,card=null,cardF={},liveChip=null,liveLine=null,sortBtns=null,allBtn=null,brushLine=null,unitEl=null;
const P=LOOP.register({name:"raster",bit:LOOP.bits.DATA|LOOP.bits.THEME|LOOP.bits.RESIZE|LOOP.bits.HOVER|LOOP.bits.SELECT,budgetMs:6,draw,degrade(){P.degraded=true}});
Object.assign(P,{rows:0,rowsAll:0,paired:0,flips:0,samples:0,hover:null,sel:null,live:null,sort:sortKey,allAttempts:false,scrollTop:0,degraded:false,builds:0});
const boxH=()=>innerWidth<600?200:420;
function unitLine(){if(!unitEl)return;txt(unitEl,`${fmt.int(rows.length)} rows${allAttempts?" (every live attempt)":" (201 live finals + 174 replay scenes)"} · 20 samples per pass · 16.5.0 above, 16.5.1 below · x = ms since load, linear to ${T_LIN} then log`)}
function mount(sec){
  const sb=sec.querySelector(".sb");unitEl=sec.querySelector(".sh .unit");
  const ctl=el("div",{class:"row rs-ctl"});
  ctl.appendChild(el("span",{class:"legend",text:"Sort:"}));
  sortBtns=el("span",{class:"seg"});[["first","first light"],["model","model"],["category","category"]].forEach(([k,l])=>sortBtns.appendChild(el("button",{class:k===sortKey?"on":"",data:{k},text:l,onclick:()=>RASTER.setSort(k)})));ctl.appendChild(sortBtns);
  allBtn=el("button",{text:"Show all attempts",title:"adds the live attempts that were repaired or cut (383 − 201)",onclick:()=>RASTER.setAll(!allAttempts)});ctl.appendChild(allBtn);
  ctl.appendChild(el("button",{class:"primary",text:"RE-MEASURE HERE",title:"load the selected body (default: the hero) into STAGE.measure in this browser and compare the class with the recorded passes",onclick:()=>RASTER.measure(sel||(self.HERO&&HERO.items&&HERO.items[0]&&HERO.items[0].key))}));
  ctl.appendChild(claimChip("raster.rows",{size:"s"}));ctl.appendChild(claimChip("raster.flips",{size:"s"}));ctl.appendChild(claimChip("raster.firstLight",{size:"s"}));ctl.appendChild(claimChip("c.seven",{size:"s"}));
  sb.appendChild(ctl);
  box=el("div",{class:"rs-box"});wrap=el("div",{class:"rs-wrap cv",tabindex:"0","aria-label":"first-light raster: one row per scene, X_ITE 16.5.0 above and 16.5.1 below"});canvas=el("canvas",{class:"rs-cv"});spacer=el("div",{class:"rs-spacer"});
  wrap.append(canvas,spacer);box.appendChild(wrap);
  const legend=el("div",{class:"legend rs-legend"});legend.append(el("span",{class:"rs-k rs-k-dot",text:"dot brightness = nonblank ratio of the sample"}),el("span",{class:"rs-k rs-k-tick",text:"white tick = first light (first non-zero sample)"}),el("span",{class:"rs-k rs-k-blank",text:"amber baseline = blank on that pass"}),el("span",{class:"rs-k rs-k-hatch",text:"hatched = X_ITE could not parse"}),el("span",{class:"rs-k rs-k-live",text:"cyan = this browser (not counted)"}));
  box.appendChild(legend);
  card=el("div",{class:"rs-card card",hidden:""});["id","model","first","frames","best","cls","flip"].forEach(k=>{const d=el("div",{class:"rs-f",data:{f:k}});cardF[k]=d;card.appendChild(d)});
  const th=el("div",{class:"rs-th"});cardF.th=th;card.appendChild(th);
  const acts=el("div",{class:"row rs-acts"});cardF.stage=el("button",{text:"SHOW ON STAGE",onclick:()=>{const r=sel&&byKey.get(sel);const x=r&&RASTER.body(r);if(x&&self.STAGE)STAGE.show.load(x,{scene:{id:r.id,key:r.key,src:r.src,item:r.item}})}});
  cardF.measure=el("button",{text:"RE-MEASURE HERE",onclick:()=>RASTER.measure(sel)});cardF.close=el("button",{text:"close",onclick:()=>{sel=null;P.sel=null;card.hidden=true;P.forceDraw=true}});acts.append(cardF.stage,cardF.measure,cardF.close);card.appendChild(acts);
  box.appendChild(card);sb.appendChild(box);
  liveLine=el("div",{class:"rs-live row"});liveChip=el("span",{class:"pill p-mute rs-chip",text:"live row: press RE-MEASURE HERE"});liveLine.append(liveChip,el("span",{class:"note m rs-livenote"}));sb.appendChild(liveLine);
  brushLine=el("div",{class:"note m rs-brush"});sb.appendChild(brushLine);
  const find=el("div",{class:"rs-finding row"});find.append(gradeChip("C"),el("span",{class:"note",text:"Under this rig (viewer-default camera + viewAll(0), no Viewpoint bound) X_ITE 16.5.0 and 16.5.1 give the same class on every paired body: the flips chip above counts them."}),gradeChip("L"),el("span",{class:"note",text:"The 17 Oct report that 16.5.1 draws what 16.5.0 leaves blank (five Shroud exports) is not reproduced here; it most likely belongs to rigs that bind a scripted Viewpoint (the fly.mjs pattern), a different camera this page does not measure."}));
  sb.appendChild(find);
  P.el=canvas;IO.observe(canvas,v=>{P.visible=v;if(v)P.forceDraw=true},{rootMargin:"120px"});
  wrap.addEventListener("scroll",()=>{P.scrollTop=wrap.scrollTop;P.forceDraw=true},{passive:true});
  canvas.addEventListener("mousemove",onMove);canvas.addEventListener("mouseleave",()=>{if(!drag){hover=null;P.hover=null;if(!sel)card.hidden=true;P.forceDraw=true}});
  canvas.addEventListener("mousedown",e=>{drag={x0:e.offsetX,x:e.offsetX,moved:false}});canvas.addEventListener("mouseup",onUp);canvas.addEventListener("click",e=>{if(dragWasMove){dragWasMove=false;return}const r=rowAt(e.offsetX,e.offsetY);if(r)RASTER.select(r.key)});
  canvas.addEventListener("touchstart",e=>{const t=e.changedTouches[0],b=canvas.getBoundingClientRect();const r=rowAt(t.clientX-b.left,t.clientY-b.top);if(r){RASTER.select(r.key)}},{passive:true});
  canvas.addEventListener("dblclick",()=>{brush=null;txt(brushLine,"");P.forceDraw=true});
  ["renders.series","renders.151","live.core","replay","live.bodies","live.jpg"].forEach(n=>DATA.on(n,()=>{build();P.builds++;P.forceDraw=true;if(n==="renders.series"||n==="replay")adoptBoot()}));
  THEME.onChange(()=>{P.forceDraw=true});addEventListener("resize",debounce(()=>{applySort();P.forceDraw=true},120));
  unitLine()}
/* if 99-boot already measured the hero in this browser, its result becomes the live row without a second X_ITE load */
function adoptBoot(){if(live||!self.BOOT||!BOOT.heroMeasure||!self.HERO||!HERO.items||!HERO.items[0])return;const key=HERO.items[0].key;if(byKey.has(key))RASTER.live(key,BOOT.heroMeasure,"boot hero measure")}
/* ---------- geometry ---------- */
let W=0,H=0,ctx=null,tmax=4500;
const plotX0=()=>8,plotX1=()=>W-8;
function X(t){const x0=plotX0(),x1=plotX1(),w=x1-x0,lin=.32*w;if(t==null)return x0;if(t<=T_LIN)return x0+Math.max(0,t)/T_LIN*lin;return Math.min(x1,x0+lin+Math.log(t/T_LIN)/Math.log(tmax/T_LIN)*(w-lin))}
function Tof(x){const x0=plotX0(),x1=plotX1(),w=x1-x0,lin=.32*w;if(x-x0<=lin)return Math.max(0,(x-x0)/lin*T_LIN);return T_LIN*Math.pow(tmax/T_LIN,(x-x0-lin)/(w-lin))}
function rowAt(x,y){if(y<AXIS_H)return null;const i=Math.floor((y-AXIS_H+(wrap?wrap.scrollTop:0))/PITCH);return rows[i]||null}
let drag=null,dragWasMove=false;
function onMove(e){if(drag){drag.x=e.offsetX;if(Math.abs(drag.x-drag.x0)>3)drag.moved=true;P.forceDraw=true;return}const r=rowAt(e.offsetX,e.offsetY);const k=r?r.key:null;if(k!==hover){hover=k;P.hover=k;if(!sel)fillCard(r,e.offsetX,e.offsetY);P.forceDraw=true}}
function onUp(){if(!drag)return;if(drag.moved){const a=Tof(Math.min(drag.x0,drag.x)),b=Tof(Math.max(drag.x0,drag.x));brush={a,b};dragWasMove=true;const n=rows.filter(r=>r.fl0!=null&&r.fl0>=a&&r.fl0<=b).length,n1=rows.filter(r=>r.fl1!=null&&r.fl1>=a&&r.fl1<=b).length;
    txt(brushLine,`brush ${fmt.ms(a)} – ${fmt.ms(b)}: ${fmt.int(n)} rows first-lit inside on 16.5.0, ${fmt.int(n1)} on 16.5.1 (double-click clears)`)}drag=null;P.forceDraw=true}
function fillCard(r,x,y){if(!r){if(!sel)card.hidden=true;return}card.hidden=false;
  txt(cardF.id,`${r.id} · ${r.key}${r.onPage?"":" · body not on the page (attempt of a cut chain)"}`);
  txt(cardF.model,`${r.m}${r.mo?" · "+r.mo:""} · ${r.p} · ${r.c} · attempt ${r.k}${r.final?" (final)":""}`);
  txt(cardF.first,`first light · 16.5.0: ${r.fl0==null?"none":fmt.ms(r.fl0)} (first frame ${r.a&&r.a.first!=null?fmt.ms(r.a.first):"—"}) · 16.5.1: ${r.fl1==null?"none":fmt.ms(r.fl1)} (first frame ${r.b&&r.b.first!=null?fmt.ms(r.b.first):"—"})`);
  txt(cardF.frames,`frames watched · 16.5.0: ${r.a?fmt.int(r.a.frames||0):"—"} in ${r.a&&r.a.last!=null?fmt.ms(r.a.last):"—"} · 16.5.1: ${r.b?fmt.int(r.b.frames||0):"—"} in ${r.b&&r.b.last!=null?fmt.ms(r.b.last):"—"}`);
  txt(cardF.best,`best sample · 16.5.0: ${r.a&&r.a.nb!=null?fmt.pct(r.a.nb,2):"—"} · 16.5.1: ${r.b&&r.b.nb!=null?fmt.pct(r.b.nb,2):"—"} · 0.5 % line`);
  txt(cardF.cls,`class · 16.5.0 ${r.cls0} · 16.5.1 ${r.cls1}${r.a&&r.a.err?" · "+r.a.err:""}`);
  txt(cardF.flip,r.flip?"FLIP: the two patches disagree on this body":"same class on both patches");cardF.flip.className="rs-f "+(r.flip?"p-bad":"p-ok");
  const jpg=RASTER.thumb(r);cardF.th.textContent="";if(jpg){cardF.th.appendChild(el("span",{class:"th "+(r.cls0==="draws"?"v":r.cls0==="blank"?"x":"i")},el("img",{src:"data:image/jpeg;base64,"+jpg,width:"96",height:"72",alt:"measured frame"})));cardF.th.appendChild(el("span",{class:"legend",text:"MEASURED frame · X_ITE 16.5.0 offline · 192×144 · the frame the numbers count"}))}
  else cardF.th.appendChild(el("span",{class:"legend",text:r.src==="live"&&!DATA.loaded("live.jpg")?"thumbnail: live.jpg not loaded yet":"no thumbnail recorded for this body"}));
  cardF.stage.disabled=!RASTER.body(r);cardF.measure.disabled=!RASTER.body(r);cardF.stage.title=RASTER.body(r)?"load the raw bytes on the visible stage (STAGE.show)":"no body on the page";
  if(x!=null){const bw=box.clientWidth,cw=Math.min(380,bw-8);card.style.left=Math.max(0,Math.min(bw-cw,x+16))+"px";card.style.top=Math.min(boxH()-40,Math.max(0,y+12))+"px"}}
/* ---------- draw ---------- */
function draw(now){
  if(!canvas||!wrap)return;const w=wrap.clientWidth||600,h=boxH();const sp=Math.max(0,rows.length*PITCH+AXIS_H-h)+"px";if(spacer&&spacer.style.height!==sp)spacer.style.height=sp;
  if(!live&&rowsAll.length)adoptBoot();
  const f=fitCanvas(canvas,w,h);ctx=f.ctx;W=w;H=h;const top=wrap.scrollTop;P.scrollTop=top;P.lastDraw=now;
  tmax=4500;rowsAll.forEach(r=>{if(r.a&&r.a.last>tmax)tmax=r.a.last;if(r.b&&r.b.last>tmax)tmax=r.b.last});if(live&&live.R&&live.R.last>tmax)tmax=live.R.last;tmax=Math.ceil(tmax/500)*500;
  const bg=cssv("--p0"),fg=cssv("--fg"),dim=cssv("--dim"),line=cssv("--line"),warn=cssv("--warn"),bad=cssv("--bad"),acc=cssv("--acc"),ok=cssv("--ok");
  ctx.fillStyle=bg;ctx.fillRect(0,0,W,H);
  /* axis */
  ctx.font="500 10.5px "+cssv("--mono");ctx.fillStyle=dim;ctx.textBaseline="top";ctx.strokeStyle=line;ctx.lineWidth=1;
  [0,50,100,200,500,1000,2000,4000].concat(tmax>4500?[tmax]:[]).forEach(t=>{if(t>tmax)return;const x=Math.round(X(t))+.5;ctx.beginPath();ctx.moveTo(x,AXIS_H-3);ctx.lineTo(x,H);ctx.globalAlpha=t===T_LIN?.6:.25;ctx.stroke();ctx.globalAlpha=1;ctx.fillText(t>=1000?(t/1000)+" s":t+(t===0?" ms":""),x+2,1)});
  ctx.fillStyle=dim;ctx.textAlign="right";ctx.fillText("lin → log",W-6,1);ctx.textAlign="left";
  if(brush){ctx.fillStyle=acc;ctx.globalAlpha=.08;ctx.fillRect(X(brush.a),AXIS_H,X(brush.b)-X(brush.a),H-AXIS_H);ctx.globalAlpha=1}
  /* rows in the visible window */
  const i0=Math.max(0,Math.floor(top/PITCH)),i1=Math.min(rows.length,Math.ceil((top+H-AXIS_H)/PITCH)+1);let samples=0;
  const dotRow=(rec,y,colour,base)=>{if(!rec){ctx.fillStyle=line;ctx.globalAlpha=.5;ctx.fillRect(plotX0(),y,2,2);ctx.globalAlpha=1;return}
    const c=cls(rec);
    if(c==="unparseable"){ctx.strokeStyle=bad;ctx.globalAlpha=.45;ctx.lineWidth=1;for(let x=plotX0();x<plotX1();x+=6){ctx.beginPath();ctx.moveTo(x,y+2);ctx.lineTo(x+2,y);ctx.stroke()}ctx.globalAlpha=1;return}
    if(c==="blank"){ctx.fillStyle=cssv("--stage-bg");ctx.fillRect(plotX0(),y,plotX1()-plotX0(),2);ctx.fillStyle=warn;ctx.globalAlpha=.5;ctx.fillRect(plotX0(),y+1,plotX1()-plotX0(),1);ctx.globalAlpha=1}
    const ts=times(rec),s=rec.series||[];let lit=false;
    for(let k=0;k<s.length;k++){const v=s[k]||0,x=X(ts[k]);ctx.fillStyle=base||colour;ctx.globalAlpha=v>0?Math.min(1,.18+.82*Math.min(1,v/.5)):.14;ctx.fillRect(Math.round(x)-1,y,2,2);samples++;
      if(!lit&&v>0){lit=true;ctx.globalAlpha=1;ctx.fillStyle=base?colour:fg;ctx.fillRect(Math.round(x)-1,y-1,1,4)}}
    ctx.globalAlpha=1};
  for(let i=i0;i<i1;i++){const r=rows[i],y=AXIS_H+i*PITCH-top;
    const isLive=live&&live.key===r.key,isSel=sel===r.key,isHov=hover===r.key;
    if(isSel||isHov){ctx.fillStyle=isSel?acc:fg;ctx.globalAlpha=isSel?.14:.07;ctx.fillRect(0,y-1,W,PITCH);ctx.globalAlpha=1}
    if(r.flip){ctx.fillStyle=bad;ctx.globalAlpha=.25;ctx.fillRect(0,y-1,4,PITCH);ctx.globalAlpha=1}
    dotRow(r.a,y,fg);dotRow(r.b,y+3,fg);
    if(isLive&&live.R&&!live.R.err&&live.R.series){const rec={series:live.R.series,first:live.R.first,last:live.R.last,frames:live.R.frames,nb:live.R.nb};ctx.fillStyle=cssv("--p0");ctx.globalAlpha=.55;ctx.fillRect(plotX0(),y-1,plotX1()-plotX0(),PITCH-1);ctx.globalAlpha=1;dotRow(r.a,y,dim,dim);dotRow(rec,y,acc,acc);dotRow(r.b,y+3,dim,dim)}
    if(isLive){ctx.fillStyle=acc;ctx.fillRect(0,y-1,3,PITCH);ctx.fillStyle=acc;ctx.font="600 10.5px "+cssv("--mono");ctx.textAlign="right";ctx.fillText(live.state==="done"?"LIVE · this browser":live.state==="measuring"?"measuring…":"live: "+live.state,W-6,y-1);ctx.textAlign="left"}}
  P.samples=samples;
  if(!rows.length){ctx.fillStyle=dim;ctx.font="12px "+cssv("--mono");ctx.fillText(DATA.status["renders.series"]&&DATA.status["renders.series"].state==="refused"?"part renders.series refused: nothing to draw":"waiting for parts renders.series, renders.151, live.core, replay…",12,AXIS_H+12)}}
/* ---------- live row ---------- */
const RASTER={panel:P,rows:()=>rows,row:k=>byKey.get(k)||null,times,cls,
  setSort(k){sortKey=k;if(sortBtns)[...sortBtns.children].forEach(b=>b.classList.toggle("on",b.dataset.k===k));applySort()},
  setAll(on){allAttempts=!!on;if(allBtn)allBtn.classList.toggle("on",allAttempts);applySort()},
  body(r){if(!r)return null;if(r.src==="real")return r.item&&r.item.b||null;return r.item&&r.item.B&&r.item.B[r.k-1]||null},
  thumb(r){if(!r||r.src!=="live"||!r.item)return null;const a=r.item.A[r.k-1];return a&&a.r&&a.r.jpg||null},
  select(key){const r=byKey.get(key);if(!r)return null;sel=key;P.sel=key;fillCard(r,null,null);card.style.left="8px";card.style.top="8px";card.hidden=false;const i=rows.indexOf(r);if(i>=0&&wrap){const y=i*PITCH;if(y<wrap.scrollTop||y>wrap.scrollTop+boxH()-AXIS_H-PITCH)wrap.scrollTop=Math.max(0,y-boxH()/2)}
    P.forceDraw=true;if(self.SIM&&r.item){const sc=(self.S&&S.scenes||[]).find(s=>s.item===r.item);if(sc)SIM.select(sc.id)}return r},
  /* a measurement made elsewhere (12-hero, 40-sheet, 99-boot) becomes the live row: R is STAGE.measure.show's result for this body */
  live(key,R,note){const r=byKey.get(key);if(!r||!R||R.cancelled)return null;live={key,R,state:R.err?"X_ITE refused":R.noFrame?"no frame yet":"done",note:note||""};P.live=live;verdict(r);applySort();if(wrap)wrap.scrollTop=0;return live},
  async measure(key){key=key||(self.HERO&&HERO.items&&HERO.items[0]&&HERO.items[0].key);const r=byKey.get(key);if(!r){txt(liveChip,"live row: no such row "+key);return null}
    const xml=RASTER.body(r);if(!xml){liveChip.className="pill p-warn rs-chip";txt(liveChip,"live row: body not on the page");return null}
    if(!self.STAGE||!STAGE.measure){txt(liveChip,"live row: STAGE.measure unavailable");return null}
    live={key,R:null,state:"measuring"};P.live=live;liveChip.className="pill p-acc rs-chip";txt(liveChip,"measuring "+r.id+" in this browser…");applySort();if(wrap)wrap.scrollTop=0;
    /* the measure queue cancels an older load when a newer one arrives (99-boot's hero measure, STAGE.textProbe, another module): retry up to three times once the queue is idle */
    let R=null;for(let tries=0;tries<3;tries++){R=await STAGE.measure.show(xml,{timeoutMs:15000});if(!R.cancelled)break;txt(liveChip,"measuring "+r.id+" again (a newer load took the measure canvas)…");await later(400);for(let w=0;w<50&&STAGE.measure.busy;w++)await later(200)}
    if(R.cancelled){live.state="cancelled";liveChip.className="pill p-warn rs-chip";txt(liveChip,"live row: measurement cancelled by a newer load");return R}
    RASTER.live(key,R,"RE-MEASURE HERE");return R}};
function verdict(r){const R=live.R,gl=self.ENV&&ENV.gl?ENV.gl:"?",rig="X_ITE 16.5.0 in this browser · "+gl+" · viewAll(0), no Viewpoint bound, headlight, 192×144";
  if(R.err){liveChip.className="pill p-bad rs-chip";txt(liveChip,"X_ITE refused");txt(box.parentNode.querySelector(".rs-livenote"),`${r.id}: ${R.err} · recorded 16.5.0 ${r.cls0} · 16.5.1 ${r.cls1} · ${rig}`);live.chip="X_ITE refused";return}
  if(R.noFrame){liveChip.className="pill p-warn rs-chip";txt(liveChip,"NO FRAME YET");txt(box.parentNode.querySelector(".rs-livenote"),`${r.id}: no frame in ${fmt.ms(R.ms)} on this device · recorded 16.5.0 ${r.cls0} · 16.5.1 ${r.cls1} · ${rig}`);live.chip="NO FRAME YET";return}
  const c=cls({nb:R.nb,series:R.series}),agree=c===r.cls0,fl=firstLight({series:R.series,first:R.first,last:R.last,frames:R.frames}),slow=fl!=null&&r.fl0!=null&&fl>2*r.fl0;
  const chip=!agree?"DIFFERS":slow?"same answer, slower device":"REPRODUCED";live.chip=chip;live.cls=c;live.fl=fl;
  liveChip.className="pill rs-chip "+(!agree?"p-bad":slow?"p-warn":"p-ok");txt(liveChip,chip);
  txt(box.parentNode.querySelector(".rs-livenote"),`${r.id} · this browser ${c} (best ${fmt.pct(R.nb,2)}, ${fmt.int(R.frames)} frames, first light ${fl==null?"none":fmt.ms(fl)}) vs recorded 16.5.0 ${r.cls0} (${r.a&&r.a.nb!=null?fmt.pct(r.a.nb,2):"—"}, first light ${r.fl0==null?"none":fmt.ms(r.fl0)}) · 16.5.1 ${r.cls1} (${r.b&&r.b.nb!=null?fmt.pct(r.b.nb,2):"—"}) · ${rig} · same watcher, same thresholds, not counted`)}
SECTIONS.register({id:"raster",part:"renders.series",
  header:{title:"First-light raster",unit:"waiting for parts renders.series, renders.151, live.core, replay",stamps:{source:"RECORDED 17 Oct",validator:"none",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline"},grade:"C",
    honesty:"recorded series: 20 samples, the first 8 frames then ≤ 1 per 150 ms · X_ITE 16.5.0 (17 Oct) and 16.5.1 (24 Oct) headless software GL, viewAll(0), no Viewpoint bound (C) · sample times reconstructed from first, last, frames · live row: this device, same watcher, same thresholds, not counted"},
  mount});
Object.assign(self,{RASTER});
})();
