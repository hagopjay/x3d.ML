/* 28-matrix-flow.js — S8 PROMPT × MODEL MATRIX + ERROR TAXONOMY FLOW (SPEC-v4 S8; WORKPLAN 28-matrix-flow). Section #matrix, part live.core.
   Owns: the matrix canvas (50 prompt rows faceted by category × the current mode's lanes; a viewer column only when viewer scenes exist; 24 Oct arms only when
   BUILD.has_run24), its cell rules (fill = final verdict, depth = attempts needed, grey hatched = cut chain, red × = failed call, amber notch = valid but blank on
   both passes; cells fill in run order as the clock passes it.T / the event's t1), row hover = prompt text, row click = cross-model compare (every lane's body
   for that prompt: hash, attempts, verdict, codes, measured thumbnail; the first two bodies are loaded on the visible stage in turn through STAGE.show.load and
   their STAGE.show.snapshot() frames sit side by side, labelled "this browser"), the error-taxonomy Sankey (first-try codes → gone after repair 1 · still there →
   gone after repair 2 · gave up; ribbons split by lane hue; click filters firehose + matrix through S.flags.filter), and the flow-field slot for wave 3.
   Globals: MATRIX = {compare(promptId|rowIndex) → Promise, lanes(), facet(name), page(n), fieldSlot(), fieldUniforms(), cellAt(x,y), panel},
            FLOW = {filter(code, outcome, lane), clear(), taxonomy(), panel}.
   S.flags.filter (shared with 30-firehose; set here, cleared with FLOW.clear or the × chip): {kind:"taxonomy", code, outcome|null, lane|null, label, test(sc) → bool};
     test(sc) is true for a live chain whose attempt-1 codes include `code` and whose fate for that code matches `outcome` (and lane when given). SIM.emit("filter", f) on change.
   Flow-field slot (wave 3, 56-field): MATRIX.fieldSlot() is the div #matrixField behind the Sankey canvas (position absolute, inset 0). 56-field appends its WebGL
     canvas there at fx 2 and sets the div's data-mode="gl" (the 2D fallback canvas .fl-2d is then hidden by CSS); uniforms come from MATRIX.fieldUniforms() →
     {u_thr: 0.005, u_bad: fraction of released chains invalid at the end, u_det: S.detected}. Until then this module draws a static 2D streamline texture at fx ≥ 1 (nothing at fx 0).
   Claims: flow.profile_component (first-try profile-component codes gone after repair 1), flow.xsd_gone (xsd gone after repair 1), flow.xsd_stayed (xsd still there after
     repair 1: gone after repair 2 + gave up); expected values are STATS.sankey (claims.py), never typed (the WORKPLAN's ids profile_component_58 / xsd_gone_76 / xsd_stayed_55
     carried SPEC-prose numbers; stats.json wins: 54 / 63 / 34).
   Test hooks: __panels.matrix.{cells, filled, cut, failed, rows, cols, filtered, hover, sel, facet, page, lastDraw, visible, degraded}, __panels.flow.{ribbons, nodes, total, source, hover, lastDraw, visible},
     __panels.field2d.{visible, lastDraw}, MATRIX.compare / cellAt / page, FLOW.filter / clear.
   v3 port: WORKPLAN §A assigns no v3 function here (the matrix and the taxonomy flow are new); codesOf/findingOf (03-data) supply the codes as v3 did (lines 228–229). */
(function(){
"use strict";
const CELL_W=26,CELL_H=14,LABEL_W=66,HEAD_H=58,FACET_GAP=6,BLANK=.005;
const OUT1=["gone after repair 1","still there"],OUT2=["gone after repair 2","gave up"];
const CATS=["object","assembly","animation","interaction","hanim","geospatial","showpiece"];
/* ---------- prompts (inline, in prompts_live order) ---------- */
const prompts=(self.PROMPTS||[]).map(p=>({id:p.prompt_id,c:p.category,text:p.prompt}));
const promptIx=new Map(prompts.map((p,i)=>[p.id,i]));
/* ---------- lanes ---------- */
function lanes(){const mode=self.S?S.mode:"live17";let L;
  if(mode==="replay11"){const seen=new Map();(self.REAL||[]).forEach(it=>{const id=it.m+" · "+it.mo;if(!seen.has(id))seen.set(id,{id,m:it.m,mo:it.mo,hue:seen.size})});L=[...seen.values()]}
  else if(mode==="run24"&&self.RUN24&&RUN24.items){const seen=new Map();RUN24.items.forEach(it=>{const id=it.m+(it.arm?" · "+it.arm:"");if(!seen.has(id))seen.set(id,{id,m:it.m,arm:it.arm,hue:seen.size})});L=[...seen.values()]}
  else L=((self.LM&&LM.models)||(self.STATS&&STATS.meta.models)||[]).map((m,i)=>({id:m.id,m:m.id,hue:i,stopped:(self.LM&&LM.lanes&&LM.lanes[m.id])||null}));
  if(self.S&&S.viewer&&S.viewer.length)L.push({id:"you",m:"you",viewer:true,hue:-1});return L}
const laneHue=l=>l.viewer?cssv("--you"):cssv("--lane-"+((l.hue%11)+1));
/* ---------- chains per cell ---------- */
function chainsFor(mode){const map=new Map();
  if(mode==="replay11")(self.REAL||[]).forEach(it=>{map.set(it.p+"|"+it.m+" · "+it.mo,{it,src:"real"})});
  else if(mode==="run24"&&self.RUN24&&RUN24.items)RUN24.items.forEach(it=>map.set(it.p+"|"+it.m+(it.arm?" · "+it.arm:""),{it,src:"live"}));
  else (self.LIVE||[]).forEach(it=>map.set(it.p+"|"+it.m,{it,src:"live"}));
  if(self.S&&S.viewer)S.viewer.forEach(sc=>{const p=sc.item&&sc.item.p||sc.promptId||"?";map.set(p+"|you",{sc,src:"viewer"})});return map}
function released(mode){if(mode==="live17")return idx=>S.liveIds.has(idx);const set=new Set();(self.S&&S.scenes||[]).forEach(sc=>{if(sc.item)set.add(sc.item)});return it=>set.has(it)}
/* ---------- taxonomy (first-try codes and their fate) ---------- */
function fateOf(cs,c){return cs.length>1&&!cs[1].includes(c)?"gone after repair 1":cs.length>2&&!cs[2].includes(c)?"gone after repair 2":"gave up"}
let TAX=null,taxN=0;
function taxonomy(){if(TAX&&TAX.n===(self.LIVE||[]).length&&TAX.n)return TAX;
  const codes1={},outcome={},byLane={},chains={};const lanesIx=new Map((self.LM&&LM.models||STATS.meta.models).map((m,i)=>[m.id,i]));
  if(self.LIVE&&LIVE.length){LIVE.forEach(it=>{const cs=it.A.map(codesOf);cs[0].forEach(c=>{codes1[c]=(codes1[c]||0)+1;const o=fateOf(cs,c);outcome[c]=outcome[c]||{};outcome[c][o]=(outcome[c][o]||0)+1;if(o!=="gone after repair 1")outcome[c]["still there"]=(outcome[c]["still there"]||0)+1;
      byLane[c]=byLane[c]||{};byLane[c][o]=byLane[c][o]||{};const li=lanesIx.get(it.m);byLane[c][o][li]=(byLane[c][o][li]||0)+1;chains[c]=chains[c]||{};(chains[c][o]=chains[c][o]||[]).push(it.i)})});
    TAX={n:LIVE.length,codes1,outcome,byLane,chains,source:"computed"}}
  else{const sk=self.STATS&&STATS.sankey;TAX={n:0,codes1:sk?sk.codes1:{},outcome:sk?sk.outcome:{},byLane:null,chains:null,source:"baked"}}
  TAX.order=Object.keys(TAX.codes1).sort((a,b)=>TAX.codes1[b]-TAX.codes1[a]||a.localeCompare(b));TAX.total=Object.values(TAX.codes1).reduce((a,b)=>a+b,0);taxN++;return TAX}
const sk=(self.STATS&&STATS.sankey)||{codes1:{},outcome:{}};const skOut=(c,o)=>(sk.outcome[c]||{})[o]||0;
CLAIMS.define("flow.profile_component",{label:"profile-component findings on the first try, gone after repair 1",unit:"of the chains whose first attempt carried the code",needs:["live.core"],expected:{n:sk.codes1["profile-component"]||0,gone:skOut("profile-component","gone after repair 1")},
  grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none",files:["parts/live.core.txt A[].x, A[].se"],fields:[sk.rule||"codes of attempt 1 per chain; gone after repair 1 = absent from attempt 2's codes"],text:v=>`${v.gone} of ${v.n}`,
  compute(){const t=taxonomy();return{n:t.codes1["profile-component"]||0,gone:(t.outcome["profile-component"]||{})["gone after repair 1"]||0}}});
CLAIMS.define("flow.xsd_gone",{label:"XSD failures on the first try, gone after repair 1",unit:"of the chains whose first attempt failed the schema",needs:["live.core"],expected:{n:sk.codes1.xsd||0,gone:skOut("xsd","gone after repair 1")},
  grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none",files:["parts/live.core.txt A[].x"],fields:[sk.rule||""],text:v=>`${v.gone} of ${v.n}`,
  compute(){const t=taxonomy();return{n:t.codes1.xsd||0,gone:(t.outcome.xsd||{})["gone after repair 1"]||0}}});
CLAIMS.define("flow.xsd_stayed",{label:"XSD failures still there after repair 1",unit:"then gone after repair 2 · gave up",needs:["live.core"],expected:{still:skOut("xsd","still there"),gone2:skOut("xsd","gone after repair 2"),gaveUp:skOut("xsd","gave up")},
  grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none",files:["parts/live.core.txt A[].x"],fields:[sk.rule||""],text:v=>`${v.still} → ${v.gone2} · ${v.gaveUp}`,
  compute(){const t=taxonomy(),o=t.outcome.xsd||{};return{still:o["still there"]||0,gone2:o["gone after repair 2"]||0,gaveUp:o["gave up"]||0}}});
/* ---------- state ---------- */
let facet="all",page=0,hover=null,sel=null,cmpId=null,cmpToken=0;
const PM=LOOP.register({name:"matrix",bit:LOOP.bits.SCENE|LOOP.bits.MODE|LOOP.bits.HOVER|LOOP.bits.SELECT|LOOP.bits.THEME|LOOP.bits.RESIZE|LOOP.bits.DATA|LOOP.bits.CLOCK,rateHz:10,budgetMs:5,draw:drawMatrix,degrade(){PM.degraded=true}});
Object.assign(PM,{cells:0,filled:0,cut:0,failed:0,rows:0,cols:0,filtered:0,hover:null,sel:null,facet,page:0,degraded:false});
const PF=LOOP.register({name:"flow",bit:LOOP.bits.DATA|LOOP.bits.THEME|LOOP.bits.RESIZE|LOOP.bits.HOVER|LOOP.bits.SELECT|LOOP.bits.MODE,rateHz:10,budgetMs:5,draw:drawFlow});
Object.assign(PF,{ribbons:0,nodes:0,total:0,hover:null,lastDraw:0});
const PX=LOOP.register({name:"field2d",bit:LOOP.bits.THEME|LOOP.bits.RESIZE,budgetMs:6,draw:drawField});
let mx=null,mxCard=null,mxF={},tabs=null,pager=null,cmp=null,cmpTitle=null,fl=null,flCard=null,flF={},filterChip=null,field=null,field2d=null,unitEl=null,fieldLegend=null;
const isPhone=()=>innerWidth<600;
const visibleRows=()=>{let rs=prompts.map((p,i)=>({p,i}));if(facet!=="all")rs=rs.filter(r=>r.p.c===facet);const ps=isPhone()?10:Infinity;if(rs.length>ps){const np=Math.ceil(rs.length/ps);page=Math.min(page,np-1);rs=rs.slice(page*ps,(page+1)*ps)}return rs};
/* ---------- mount ---------- */
function mount(sec){
  const sb=sec.querySelector(".sb");unitEl=sec.querySelector(".sh .unit");
  const grid=el("div",{class:"mx-grid"});
  const left=el("div",{class:"mx-left"});
  tabs=el("div",{class:"tabs mx-tabs"});[["all","all 50"]].concat(CATS.map(c=>[c,c])).forEach(([k,l])=>tabs.appendChild(el("button",{class:k===facet?"on":"",data:{f:k},text:l,onclick:()=>MATRIX.facet(k)})));left.appendChild(tabs);
  const cvbox=el("div",{class:"cv mx-cvbox"});mx=el("canvas",{class:"mx-cv","aria-label":"prompt × model matrix"});cvbox.appendChild(mx);left.appendChild(cvbox);
  pager=el("div",{class:"row mx-pager",hidden:""});pager.append(el("button",{text:"‹",onclick:()=>MATRIX.page(page-1)}),el("span",{class:"legend mx-pageinfo"}),el("button",{text:"›",onclick:()=>MATRIX.page(page+1)}));left.appendChild(pager);
  const leg=el("div",{class:"legend mx-legend"});leg.append(el("span",{class:"mx-k k-ok",text:"fill = valid at the end"}),el("span",{class:"mx-k k-bad",text:"never valid"}),el("span",{class:"mx-k k-first",text:"left stripe = first try"}),el("span",{class:"mx-k k-depth",text:"depth = attempts needed (1 light · 3 dark)"}),el("span",{class:"mx-k k-cut",text:"hatched = chain cut (cap / time box)"}),el("span",{class:"mx-k k-x",text:"× = failed call"}),el("span",{class:"mx-k k-notch",text:"amber notch = valid, blank on both passes"}),el("span",{class:"mx-k k-empty",text:"empty = no call reached the page"}));left.appendChild(leg);
  mxCard=el("div",{class:"mx-card card",hidden:""});["prompt","cell","render","events"].forEach(k=>{mxF[k]=el("div",{class:"mx-f",data:{f:k}});mxCard.appendChild(mxF[k])});left.appendChild(mxCard);
  grid.appendChild(left);
  const right=el("div",{class:"mx-right"});
  const ch=el("div",{class:"row mx-cmphead"});cmpTitle=el("span",{class:"legend",text:"cross-model compare: click a prompt row"});ch.append(cmpTitle,el("a",{href:"#stage",class:"legend",text:"↑ stage"}));right.appendChild(ch);
  cmp=el("div",{class:"mx-cmp"});right.appendChild(cmp);
  const fh=el("div",{class:"row fl-head"});fh.append(el("span",{class:"legend",text:"error taxonomy: first-try finding codes → fate after each repair · ribbons by lane hue · click a ribbon to filter the firehose and the matrix"}),claimChip("flow.profile_component",{size:"s"}),claimChip("flow.xsd_gone",{size:"s"}),claimChip("flow.xsd_stayed",{size:"s"}));
  filterChip=el("button",{class:"pill p-acc fl-filter",hidden:"",onclick:()=>FLOW.clear()});fh.appendChild(filterChip);right.appendChild(fh);
  const flbox=el("div",{class:"cv fl-cvbox"});field=el("div",{class:"mx-field",id:"matrixField",data:{slot:"field",mode:"2d"},"aria-hidden":"true"});field2d=el("canvas",{class:"fl-2d"});field.appendChild(field2d);flbox.appendChild(field);
  fl=el("canvas",{class:"fl-cv","aria-label":"error taxonomy flow"});flbox.appendChild(fl);right.appendChild(flbox);
  flCard=el("div",{class:"fl-card card",hidden:""});["a","b","c"].forEach(k=>{flF[k]=el("div",{class:"fl-f"});flCard.appendChild(flF[k])});flbox.appendChild(flCard);
  fieldLegend=el("div",{class:"legend fl-lanes"});right.appendChild(fieldLegend);
  grid.appendChild(right);sb.appendChild(grid);
  PM.el=mx;IO.observe(mx,v=>{PM.visible=v;if(v)PM.forceDraw=true},{rootMargin:"120px"});PF.el=fl;IO.observe(fl,v=>{PF.visible=v;PX.visible=v;if(v){PF.forceDraw=true;PX.forceDraw=true}},{rootMargin:"120px"});
  mx.addEventListener("mousemove",e=>{const c=MATRIX.cellAt(e.offsetX,e.offsetY);const k=c?c.row+"|"+c.col:null;if(k!==(hover&&hover.row+"|"+hover.col)){hover=c;PM.hover=k;fillMxCard(c,e.offsetX,e.offsetY);PM.forceDraw=true}});
  mx.addEventListener("mouseleave",()=>{hover=null;PM.hover=null;if(!sel)mxCard.hidden=true;PM.forceDraw=true});
  mx.addEventListener("click",e=>{const c=MATRIX.cellAt(e.offsetX,e.offsetY);if(!c)return;sel=c;PM.sel=c.row+"|"+c.col;fillMxCard(c,e.offsetX,e.offsetY);MATRIX.compare(c.p.id,c.lane?c.lane.id:null);PM.forceDraw=true});
  fl.addEventListener("mousemove",e=>{const r=ribbonAt(e.offsetX,e.offsetY);const k=r?r.key:null;if(k!==(PF.hover)){PF.hover=k;fillFlCard(r,e.offsetX,e.offsetY);PF.forceDraw=true}});
  fl.addEventListener("mouseleave",()=>{PF.hover=null;flCard.hidden=true;PF.forceDraw=true});
  fl.addEventListener("click",e=>{const r=ribbonAt(e.offsetX,e.offsetY);if(!r)return;const f=self.S&&S.flags.filter;if(f&&f.code===r.code&&f.outcome===r.outcome&&f.lane===(r.lane||null))FLOW.clear();else FLOW.filter(r.code,r.outcome,r.lane||null)});
  if(self.SIM){SIM.on("mode",()=>{sel=null;PM.sel=null;cmp.textContent="";txt(cmpTitle,"cross-model compare: click a prompt row");PM.forceDraw=true;PF.forceDraw=true;unitLine()});SIM.on("reset",()=>{PM.forceDraw=true});SIM.on("filter",()=>{PM.forceDraw=true;PF.forceDraw=true})}
  DATA.on("live.core",()=>{TAX=null;taxonomy();PM.forceDraw=true;PF.forceDraw=true;unitLine()});DATA.on("events",()=>{PM.forceDraw=true});DATA.on("live.jpg",refreshThumbs);DATA.on("live.bodies",()=>{if(cmpId)MATRIX.compare(cmpId,null,{noLoad:true})});
  THEME.onChange(()=>{PM.forceDraw=true;PF.forceDraw=true;PX.forceDraw=true});FX.onChange(()=>{PX.forceDraw=true});addEventListener("resize",debounce(()=>{PM.forceDraw=true;PF.forceDraw=true;PX.forceDraw=true},120));
  unitLine()}
function unitLine(){if(!unitEl)return;const L=lanes(),n=self.S&&S.mode==="replay11"?(self.REAL||[]).length:(self.LIVE||[]).length;txt(unitEl,`${prompts.length} prompts × ${L.length} lanes · ${fmt.int(n)} chains · first-try codes → fate after each repair${self.BUILD&&BUILD.has_run24?" · 24 Oct arms included":""}`)}
/* ---------- matrix geometry ---------- */
let geo={rows:[],cols:[],cellW:CELL_W,x0:LABEL_W,W:0,H:0};
function layout(width){const rs=visibleRows(),L=lanes();const avail=Math.max(60,width-LABEL_W-8);const cellW=Math.max(CELL_W,Math.min(60,Math.floor(avail/Math.max(1,L.length))));
  let y=HEAD_H,lastC=null;const rows=rs.map(r=>{if(lastC&&r.p.c!==lastC&&facet==="all")y+=FACET_GAP;lastC=r.p.c;const o={p:r.p,i:r.i,y};y+=CELL_H;return o});
  geo={rows,cols:L.map((l,i)=>({lane:l,x:LABEL_W+i*cellW})),cellW,x0:LABEL_W,W:LABEL_W+L.length*cellW+2,H:y+2};return geo}
function cellAt(x,y){const r=geo.rows.find(o=>y>=o.y&&y<o.y+CELL_H);if(!r)return null;const c=geo.cols.find(o=>x>=o.x&&x<o.x+geo.cellW);return{row:r.i,col:c?geo.cols.indexOf(c):-1,p:r.p,lane:c?c.lane:null}}
function evMaps(){const F=new Map(),C=new Map();if(self.EVENTS){EVENTS.failed.forEach(f=>{const k=f.p+"|"+f.m;(F.get(k)||F.set(k,[]).get(k)).push(f)});EVENTS.cut.forEach(c=>C.set(c.p+"|"+c.m,c))}return{F,C}}
function hatch(ctx,x,y,w,h,colour){ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.strokeStyle=colour;ctx.globalAlpha=.6;ctx.lineWidth=1;for(let k=-h;k<w;k+=4){ctx.beginPath();ctx.moveTo(x+k,y+h);ctx.lineTo(x+k+h,y);ctx.stroke()}ctx.restore()}
function drawMatrix(now){
  if(!mx)return;const mode=self.S?S.mode:"live17",wrapW=(mx.parentNode.parentNode||mx.parentNode).clientWidth||300;layout(isPhone()?wrapW:Math.min(wrapW,LABEL_W+lanes().length*60+2));
  const cw=Math.max(geo.W,isPhone()?wrapW:geo.W),cwS=cw+"px";if(mx.style.width!==cwS)mx.style.width=cwS;const {ctx}=fitCanvas(mx,cw,geo.H);PM.lastDraw=now;
  const bg=cssv("--p0"),fg=cssv("--fg"),mute=cssv("--mute"),dim=cssv("--dim"),line=cssv("--line"),ok=cssv("--ok"),bad=cssv("--bad"),warn=cssv("--warn"),acc=cssv("--acc"),p2=cssv("--p2");
  ctx.fillStyle=bg;ctx.fillRect(0,0,mx.width,mx.height);ctx.font="500 10.5px "+cssv("--mono");ctx.textBaseline="middle";
  const chains=chainsFor(mode),rel=released(mode),{F,C}=evMaps(),clk=self.S?S.clk:0,tmaxNow=self.SIM?SIM.tmax():0,filter=self.S&&S.flags.filter;
  let cells=0,filled=0,cut=0,failed=0,filtered=0;const R151l=self.R151&&R151.live;const byItem=filter&&filter.test?new Map((self.S&&S.scenes||[]).map(s=>[s.item,s])):null;
  /* column heads */
  /* lane names run up at 55° from each column's foot so long model ids never overlap (the hover card carries the full id) */
  geo.cols.forEach(c=>{ctx.save();ctx.translate(c.x+geo.cellW/2+4,HEAD_H-5);ctx.rotate(-Math.PI*55/180);ctx.fillStyle=laneHue(c.lane);ctx.textAlign="left";ctx.textBaseline="middle";const nm=c.lane.viewer?"you":String(c.lane.id).replace(/^.*\//,"").slice(0,24);ctx.fillText(nm,0,0);ctx.restore()});
  geo.rows.forEach(r=>{
    const hovRow=hover&&hover.row===r.i,selRow=sel&&sel.row===r.i;
    if(hovRow||selRow){ctx.fillStyle=selRow?acc:fg;ctx.globalAlpha=selRow?.12:.06;ctx.fillRect(0,r.y,geo.W,CELL_H);ctx.globalAlpha=1}
    ctx.fillStyle=mute;ctx.textAlign="left";ctx.fillText(r.p.id,4,r.y+CELL_H/2);
    geo.cols.forEach((c,ci)=>{cells++;const x=c.x+1,y=r.y+1,w=geo.cellW-2,h=CELL_H-2;const key=r.p.id+"|"+c.lane.id,ch=chains.get(key);
      ctx.fillStyle=p2;ctx.fillRect(x,y,w,h);
      let dimmed=false;
      if(ch&&ch.src!=="viewer"){const it=ch.it,isRel=mode==="live17"?rel(it.i):rel(it);
        if(isRel){filled++;const A=it.A||null,att=A?A.length:(it.at||1),finOk=A?!!A[A.length-1].ok:!!(it.x&&it.s),nb=A?(A[A.length-1].r&&A[A.length-1].r.nb)||0:(it.r&&it.r.nb)||0,err=A?!!(A[A.length-1].r&&A[A.length-1].r.err):!!(it.r&&it.r.err);
          let blank=!err&&nb<BLANK;if(blank&&A&&R151l){const r1=R151l[keyOf(it.m,it.p,A.length)];if(r1&&!r1.err&&(r1.nb||0)>=BLANK)blank=false}if(blank&&!A&&it.r&&it.r.nb151!=null&&it.r.nb151>=BLANK)blank=false;
          if(byItem){const sc=byItem.get(it);const m=sc?filter.test(sc):false;if(m)filtered++;else dimmed=true}
          const firstOk=A?!!A[0].ok:(it.at===1?finOk:!!(it.earlier&&it.earlier[0]&&it.earlier[0][0]&&it.earlier[0][1]));
          ctx.fillStyle=finOk?ok:bad;ctx.globalAlpha=(att>=3?1:att===2?.68:.38)*(dimmed?.25:1);ctx.fillRect(x,y,w,h);ctx.globalAlpha=dimmed?.25:1;
          ctx.fillStyle=firstOk?ok:bad;ctx.fillRect(x,y,3,h);ctx.fillStyle=cssv("--p0");ctx.globalAlpha*=.9;ctx.fillRect(x+3,y,1,h);ctx.globalAlpha=1;  /* left stripe = first try, fill = final */
          if(blank&&!dimmed){ctx.fillStyle=warn;ctx.beginPath();ctx.moveTo(x+w-6,y);ctx.lineTo(x+w,y);ctx.lineTo(x+w,y+6);ctx.closePath();ctx.fill()}
          if(att>1&&geo.cellW>=30){ctx.fillStyle=cssv("--stage-bg");ctx.globalAlpha=.8;ctx.textAlign="right";ctx.fillText(String(att),x+w-2,y+h/2);ctx.globalAlpha=1}}
        else{ctx.fillStyle=line;ctx.globalAlpha=.6;ctx.fillRect(x,y,w,h);ctx.globalAlpha=1}}
      else if(ch&&ch.src==="viewer"){if(self.S&&S.flags.includeMine)filled++;ctx.fillStyle=cssv("--you");ctx.globalAlpha=.7;ctx.fillRect(x,y,w,h);ctx.globalAlpha=1}
      else if(c.lane.stopped){ctx.strokeStyle=line;ctx.setLineDash([2,2]);ctx.strokeRect(x+.5,y+.5,w-1,h-1);ctx.setLineDash([])}
      if(mode==="live17"){const cc=C.get(key);if(cc&&clk>=Math.min(cc.t1||0,tmaxNow)){cut++;hatch(ctx,x,y,w,h,dim)}  /* three glm time boxes fired after the last page attempt: they land when the run clock ends */
        const ff=(F.get(key)||[]).filter(f=>clk>=(f.t1||0));if(ff.length){failed+=ff.length;ctx.strokeStyle=bad;ctx.lineWidth=1.2;for(let k=0;k<Math.min(3,ff.length);k++){const cx=x+3+k*5,cy=y+h-4;ctx.beginPath();ctx.moveTo(cx-2,cy-2);ctx.lineTo(cx+2,cy+2);ctx.moveTo(cx+2,cy-2);ctx.lineTo(cx-2,cy+2);ctx.stroke()}ctx.lineWidth=1}}
      if(hover&&hover.row===r.i&&hover.col===ci){ctx.strokeStyle=fg;ctx.strokeRect(x+.5,y+.5,w-1,h-1)}})});
  /* facets are the prompt-id prefixes (obj, asm, anim, int, hanim, geo, sp); the gap between facets is the only extra mark */
  Object.assign(PM,{cells,filled,cut,failed,rows:geo.rows.length,cols:geo.cols.length,filtered:filter?filtered:0,facet,page});
  if(pager){const rs=facet==="all"?prompts:prompts.filter(p=>p.c===facet),ps=isPhone()?10:Infinity,np=Math.ceil(rs.length/ps);pager.hidden=!(np>1);if(np>1)txt(pager.querySelector(".mx-pageinfo"),`rows ${page*ps+1}–${Math.min(rs.length,(page+1)*ps)} of ${rs.length}`)}}
function fillMxCard(c,x,y){if(!c){if(!sel)mxCard.hidden=true;return}mxCard.hidden=false;const mode=self.S?S.mode:"live17";
  txt(mxF.prompt,`${c.p.id} · ${c.p.c} · ${c.p.text}`);
  const ch=c.lane?chainsFor(mode).get(c.p.id+"|"+c.lane.id):null;txt(mxF.render,"");
  if(!c.lane)txt(mxF.cell,"hover a cell for the lane's chain · click the row to compare every lane's body");
  else if(!ch){const ev=evMaps(),cc=ev.C.get(c.p.id+"|"+c.lane.id),ff=ev.F.get(c.p.id+"|"+c.lane.id)||[];txt(mxF.cell,`${c.lane.id}: no chain reached the page${cc?" · chain CUT ("+cc.reason+" at run second "+fmt.int(cc.t1)+(cc.t1>(self.LM&&LM.t_total||0)?", after the last page attempt":"")+", "+cc.calls+" call"+(cc.calls===1?"":"s")+" recorded off the page)":""}${ff.length?" · "+ff.length+" failed call"+(ff.length===1?"":"s")+" ("+ff.map(f=>f.kind).join(", ")+")":""}${c.lane.stopped?" · lane "+c.lane.stopped:""}`)}
  else if(ch.src==="viewer")txt(mxF.cell,`your run · ${ch.sc.id} · ${ch.sc.verdict} · excluded from every aggregate`);
  else{const it=ch.it,A=it.A||null,att=A?A.length:it.at,fin=A?A[A.length-1]:null,ok=A?!!fin.ok:!!(it.x&&it.s),codes=A?codesOf(A[0]):(it.f2&&it.f2[1])||[];
    txt(mxF.cell,`${c.lane.id} · ${att} attempt${att===1?"":"s"} · ${ok?"VALID at the end":"never valid"} · first-try codes: ${codes.length?codes.join(", "):"none"}${A?" · "+fmt.usd(A.reduce((a,b)=>a+b.u,0)):""}`);
    const r0=A?fin.r:it.r,r1=A?(self.R151&&R151.live[keyOf(it.m,it.p,A.length)]):(it.r&&{nb:it.r.nb151,err:it.r.err151});
    txt(mxF.render,`measured frame · X_ITE 16.5.0 offline ${r0?(r0.err?"unparseable":fmt.pct(r0.nb||0,2)):"—"} · 16.5.1 offline ${r1?(r1.err?"unparseable":r1.nb==null?"—":fmt.pct(r1.nb||0,2)):"—"} · 0.5 % line`)}
  if(c.lane&&ch&&ch.src!=="viewer"){const ev=evMaps(),ff=ev.F.get(c.p.id+"|"+c.lane.id)||[];txt(mxF.events,ff.length?`${ff.length} failed call${ff.length===1?"":"s"} before a retry (${ff.map(f=>f.kind).join(", ")})`:"")}else txt(mxF.events,"");
  if(x!=null){const bw=mx.parentNode.parentNode.clientWidth,cw=Math.min(360,bw-8);mxCard.style.left=Math.max(0,Math.min(bw-cw,x+14))+"px";mxCard.style.top=Math.max(0,y+40)+"px"}}
/* ---------- cross-model compare ---------- */
let urls=[],cmpCards=[];
/* the measured thumbnail (live.jpg) of each compare card, filled in place when the part lands so the stage snapshots beside it survive */
function refreshThumbs(){cmpCards.forEach(c=>{const jpg=c.A&&c.fin.r&&c.fin.r.jpg;if(c.measPic.dataset.done==="1")return;c.measPic.textContent="";
  c.measPic.appendChild(jpg?el("span",{class:"th "+(c.ok?"v":"i")},el("img",{src:"data:image/jpeg;base64,"+jpg,width:"96",height:"72",alt:"measured frame"})):el("span",{class:"placeholder mx-noth",text:c.A&&!DATA.loaded("live.jpg")?"live.jpg loading":"no thumbnail recorded"}));
  c.measPic.appendChild(el("span",{class:"legend",text:"MEASURED · X_ITE 16.5.0 offline · the counted frame"}));if(jpg||!c.A||DATA.loaded("live.jpg"))c.measPic.dataset.done="1"})}
async function compare(pid,laneId,opts){opts=opts||{};if(typeof pid==="number")pid=prompts[pid]&&prompts[pid].id;if(!pid||!cmp)return null;const mode=self.S?S.mode:"live17";cmpId=pid;const tk=++cmpToken;
  const P=prompts[promptIx.get(pid)];const chains=chainsFor(mode),L=lanes();const items=L.map(l=>({lane:l,ch:chains.get(pid+"|"+l.id)})).filter(x=>x.ch&&x.ch.src!=="viewer");
  txt(cmpTitle,`cross-model compare · ${pid} · ${P?P.c:""} · ${items.length} lane${items.length===1?"":"s"} · ${P?P.text:""}`);
  urls.forEach(u=>{try{URL.revokeObjectURL(u)}catch(e){}});urls=[];cmp.textContent="";const cards=[];
  items.forEach(x=>{const it=x.ch.it,A=it.A||null,att=A?A.length:it.at,fin=A?A[A.length-1]:null,ok=A?!!fin.ok:!!(it.x&&it.s),body=A?(it.B&&it.B[A.length-1])||null:it.b||null,codes=A?codesOf(A[0]):(it.f2&&it.f2[1])||[];
    const card=el("div",{class:"card mx-cc"+(x.lane.id===laneId?" sel":"")});card.style.borderTopColor=laneHue(x.lane);
    card.appendChild(el("div",{class:"row"},[el("b",{text:x.lane.id}),el("span",{class:"pill "+(ok?"p-ok":"p-bad"),text:ok?"valid":"invalid"}),el("span",{class:"legend",text:`${att} attempt${att===1?"":"s"}`})]));
    card.appendChild(el("div",{class:"legend m",text:`page hash ${body?contentHash(body).slice(0,16)+"…":"body not loaded"} · first-try codes ${codes.length?codes.join(", "):"none"}`}));
    const r0=A?fin.r:it.r,r1=A?(self.R151&&R151.live[keyOf(it.m,it.p,A.length)]):(it.r&&{nb:it.r.nb151,err:it.r.err151});
    card.appendChild(el("div",{class:"legend",text:`16.5.0 offline ${r0?(r0.err?"unparseable":fmt.pct(r0.nb||0,2)):"—"} · 16.5.1 offline ${r1?(r1.err?"unparseable":r1.nb==null?"—":fmt.pct(r1.nb||0,2)):"—"}`}));
    const pics=el("div",{class:"row mx-pics"});const measPic=el("span",{class:"mx-pic mx-meas"});pics.appendChild(measPic);
    const livePic=el("span",{class:"mx-pic mx-live"},[el("span",{class:"placeholder mx-noth",text:"this browser: not loaded"}),el("span",{class:"legend",text:"this browser"})]);pics.appendChild(livePic);card.appendChild(pics);
    const b=el("button",{text:"SHOW ON STAGE",disabled:body?null:"",title:body?"STAGE.show.load: raw bytes, own/default viewpoint":"body not on the page yet",onclick:()=>stageOne(x,body,livePic,++cmpToken)});card.appendChild(el("div",{class:"row"},[b,el("span",{class:"legend",text:body?"":"waiting for live.bodies"})]));
    cmp.appendChild(card);cards.push({x,body,livePic,measPic,A,fin,ok})});
  cmpCards=cards;refreshThumbs();
  if(!items.length)cmp.appendChild(el("div",{class:"placeholder",text:"no chain for this prompt in this mode"}));
  if(opts.noLoad)return cards;
  /* two bodies side by side: load the first two lanes' bodies in turn on the one visible stage and keep each snapshot in its card */
  const two=cards.filter(c=>c.body).slice(0,2);for(const c of two){if(tk!==cmpToken)break;await stageOne(c.x,c.body,c.livePic,tk)}return cards}
/* shim (request to 08-stage noted): the stage's WebGL buffer is cleared after compositing (X_ITE's PreserveDrawingBuffer is off), so a snapshot taken from a
   timer is black; like the measure path, the frame is copied inside X_ITE's finishEvents callback through the exported watchFrames, then read as a PNG. */
function grabFrames(B){const off=document.createElement("canvas");let got=0;const w=watchFrames(B,()=>{try{const cv=B.getCanvas();if(off.width!==cv.width||off.height!==cv.height){off.width=cv.width;off.height=cv.height}off.getContext("2d").drawImage(cv,0,0);got++}catch(e){}return{nonblank:0}});w.start();
  return{stop:()=>w.stop(),latest:()=>got?off:null,get n(){return w.n}}}
async function stageOne(x,body,livePic,tk){if(!self.STAGE||!STAGE.show||!body)return null;const it=x.ch.it;const sc={id:"cmp·"+x.lane.id,key:ledgerKey(it),src:x.ch.src,item:it};
  livePic.firstChild.textContent="loading on the stage…";const B=STAGE.show.browser,g=self.watchFrames&&B?grabFrames(B):null;
  const r=await STAGE.show.load(body,{scene:sc});if(!r.ok){if(g)g.stop();livePic.firstChild.textContent=r.cancelled?"superseded by a newer load":"X_ITE refused: "+(r.err||"");return r}
  /* let the scene's first frames land (at fx 0 the stage freezes 1.5 s after the load; SwiftShader may need a few seconds for the first one) */
  const n0=g?g.n:0,t0=performance.now();while(performance.now()-t0<(FX.level===0?4000:1500)){await later(100);if(g&&g.n>=n0+2)break;if(!g&&self.__stage&&__stage.show.frozen)break}
  await later(150);let blob=null;if(g){const c=g.latest();g.stop();if(c)blob=await new Promise(res=>{try{c.toBlob(b=>res(b||null),"image/png")}catch(e){res(null)}})}
  if(tk!==cmpToken)return r;
  if(!blob)blob=await STAGE.show.snapshot();const gl=self.ENV&&ENV.gl?ENV.gl:"?",staged=self.__stage&&__stage.show.staged;
  livePic.textContent="";if(blob){const u=URL.createObjectURL(blob);urls.push(u);livePic.appendChild(el("span",{class:"th v"},el("img",{src:u,width:"96",height:"72",alt:"stage snapshot"})))}else livePic.appendChild(el("span",{class:"placeholder mx-noth",text:"snapshot unavailable"}));
  livePic.appendChild(el("span",{class:"legend",text:`this browser · X_ITE 16.5.0 · ${gl} · ${staged?"STAGED":"MEASURED (unstaged)"} · hash ${__stage&&__stage.show.lastHash?__stage.show.lastHash.slice(0,12)+"…":"?"}`}));return r}
/* ---------- Sankey ---------- */
let bands=[],nodesDrawn=[];
function flowLayout(W,H){const t=taxonomy(),total=Math.max(1,t.total),pad=18,gap=4,top=22,slot=11;const codes=t.order;const free=H-top-pad-gap*Math.max(0,codes.length-1);
  /* a code node keeps at least one label slot (11 px) of column height, so the small codes' labels never run off the canvas; the band scale takes what is left */
  const scale0=free/total,extra=codes.reduce((a,c)=>a+Math.max(0,slot-t.codes1[c]*scale0),0),scale=Math.max(.1,(free-extra)/total);
  const nodeW=10,x0=8,x1=W*.5-nodeW/2,x2=W-8-nodeW;let y=top;const col0=codes.map(c=>{const h=t.codes1[c]*scale;const n={id:c,x:x0,y,h,n:t.codes1[c],col:0};y+=Math.max(h,slot)+gap;return n});
  const sum=(o)=>codes.reduce((a,c)=>a+((t.outcome[c]||{})[o]||0),0);const g1=sum("gone after repair 1"),st=sum("still there"),g2=sum("gone after repair 2"),gu=sum("gave up");
  const col1=[{id:"gone after repair 1",x:x1,y:top,h:g1*scale,n:g1,col:1},{id:"still there",x:x1,y:top+g1*scale+gap*3,h:st*scale,n:st,col:1}];
  const stillY=col1[1].y;const col2=[{id:"gone after repair 2",x:x2,y:stillY,h:g2*scale,n:g2,col:2},{id:"gave up",x:x2,y:stillY+g2*scale+gap*2,h:gu*scale,n:gu,col:2}];
  /* bands: code → outcome1 (per lane), still(code) → outcome2 (per lane) */
  const L=((self.LM&&LM.models)||STATS.meta.models);const out=[];const off0=new Map(col0.map(n=>[n.id,0])),off1=new Map(col1.map(n=>[n.id,0])),off2=new Map(col2.map(n=>[n.id,0]));const stillByCode=new Map();
  col0.forEach(n=>{OUT1.forEach(o=>{const cnt=(t.outcome[n.id]||{})[o]||0;if(!cnt)return;const tgt=col1.find(q=>q.id===o);const laneParts=t.byLane?Object.entries((t.byLane[n.id]||{})).filter(([oo])=>o==="still there"?oo!=="gone after repair 1":oo===o).reduce((acc,[,m])=>{Object.entries(m).forEach(([li,k])=>acc[li]=(acc[li]||0)+k);return acc},{}):{"-1":cnt};
    const startY1=tgt.y+off1.get(o);if(o==="still there")stillByCode.set(n.id,{y:startY1,h:cnt*scale});
    Object.keys(laneParts).sort((a,b)=>+a-+b).forEach(li=>{const k=laneParts[li],h=k*scale;out.push({key:n.id+"→"+o+"·"+li,code:n.id,outcome:o,lane:li==="-1"?null:(L[+li]&&L[+li].id)||null,li:+li,n:k,x0:n.x+nodeW,y0:n.y+off0.get(n.id),x1:tgt.x,y1:tgt.y+off1.get(o),h,col:0});off0.set(n.id,off0.get(n.id)+h);off1.set(o,off1.get(o)+h)})})});
  col0.forEach(n=>{const sb=stillByCode.get(n.id);if(!sb)return;let yy=sb.y;OUT2.forEach(o=>{const cnt=(t.outcome[n.id]||{})[o]||0;if(!cnt)return;const tgt=col2.find(q=>q.id===o);const laneParts=t.byLane?Object.entries((t.byLane[n.id]||{})[o]||{}).reduce((acc,[li,k])=>(acc[li]=k,acc),{}):{"-1":cnt};
    Object.keys(laneParts).sort((a,b)=>+a-+b).forEach(li=>{const k=laneParts[li],h=k*scale;out.push({key:n.id+"→"+o+"·"+li,code:n.id,outcome:o,lane:li==="-1"?null:(L[+li]&&L[+li].id)||null,li:+li,n:k,x0:x1+nodeW,y0:yy,x1:tgt.x,y1:tgt.y+off2.get(o),h,col:1});yy+=h;off2.set(o,off2.get(o)+h)})})});
  return{nodes:col0.concat(col1,col2),bands:out,nodeW,t}}
function bandPath(ctx,b){const xm=(b.x0+b.x1)/2;ctx.beginPath();ctx.moveTo(b.x0,b.y0);ctx.bezierCurveTo(xm,b.y0,xm,b.y1,b.x1,b.y1);ctx.lineTo(b.x1,b.y1+b.h);ctx.bezierCurveTo(xm,b.y1+b.h,xm,b.y0+b.h,b.x0,b.y0+b.h);ctx.closePath()}
function bandYAt(b,x){if(x<b.x0||x>b.x1)return null;const xm=(b.x0+b.x1)/2;let lo=0,hi=1;for(let i=0;i<24;i++){const t=(lo+hi)/2,xt=b.x0*(1-t)**3+3*xm*(1-t)**2*t+3*xm*(1-t)*t*t+b.x1*t**3;if(xt<x)lo=t;else hi=t}const t=(lo+hi)/2,y=b.y0*(1-t)**3+3*b.y0*(1-t)**2*t+3*b.y1*(1-t)*t*t+b.y1*t**3;return[y,y+b.h]}
function ribbonAt(x,y){for(let i=bands.length-1;i>=0;i--){const r=bandYAt(bands[i],x);if(r&&y>=r[0]&&y<=r[1])return bands[i]}return null}
function drawFlow(now){if(!fl)return;const W=fl.parentNode.clientWidth||400,H=isPhone()?340:420;const {ctx}=fitCanvas(fl,W,H);PF.lastDraw=now;ctx.clearRect(0,0,W,H);
  const lay=flowLayout(W,H);bands=lay.bands;nodesDrawn=lay.nodes;const t=lay.t,filter=self.S&&S.flags.filter,hov=PF.hover;
  const fg=cssv("--fg"),mute=cssv("--mute"),dim=cssv("--dim"),p3=cssv("--p3"),L=((self.LM&&LM.models)||STATS.meta.models);
  ctx.font="500 10.5px "+cssv("--mono");ctx.textBaseline="top";ctx.fillStyle=dim;ctx.fillText("first-try codes",8,4);ctx.textAlign="center";ctx.fillText("after repair 1",W/2,4);ctx.textAlign="right";ctx.fillText("after repair 2",W-8,4);ctx.textAlign="left";
  bands.forEach(b=>{const on=filter?filter.code===b.code&&(!filter.outcome||filter.outcome===b.outcome)&&(!filter.lane||filter.lane===b.lane):true;const h=hov===b.key;
    ctx.fillStyle=b.lane==null?mute:cssv("--lane-"+((b.li%11)+1));ctx.globalAlpha=h?.9:on?(filter?.75:.5):.08;bandPath(ctx,b);ctx.fill()});ctx.globalAlpha=1;
  let lastY0=-99,lastY2=-99;
  lay.nodes.forEach(n=>{ctx.fillStyle=p3;ctx.fillRect(n.x,n.y,lay.nodeW,Math.max(1,n.h));ctx.fillStyle=n.col===0&&filter&&filter.code===n.id?cssv("--acc"):fg;ctx.textBaseline="middle";
    const label=`${n.id} ${n.n}`;
    if(n.col===0){const y=Math.max(n.y+Math.max(5,n.h/2),lastY0+11);lastY0=y;ctx.textAlign="left";ctx.fillText(label,n.x+lay.nodeW+4,y)}
    else if(n.col===1){ctx.textAlign="left";ctx.fillText(label,n.x+lay.nodeW+4,n.y+Math.max(6,Math.min(n.h/2,12)))}
    else{const y=Math.max(n.y+Math.max(5,n.h/2),lastY2+11);lastY2=y;ctx.textAlign="right";ctx.fillText(label,n.x-4,y)}});
  ctx.textAlign="left";ctx.textBaseline="top";ctx.fillStyle=dim;ctx.fillText(t.source==="baked"?"baked from stats.json until live.core lands":`computed from ${t.n} chains · ${t.total} first-try code instances`,8,H-14);
  Object.assign(PF,{ribbons:bands.length,nodes:lay.nodes.length,total:t.total,source:t.source});
  if(fieldLegend){const want=L.map((m,i)=>m.id).join("|");if(fieldLegend.dataset.k!==want){fieldLegend.dataset.k=want;fieldLegend.textContent="";L.forEach((m,i)=>{const s=el("span",{class:"fl-lane",text:m.id});s.style.color=cssv("--lane-"+((i%11)+1));fieldLegend.appendChild(s)})}}}
function fillFlCard(b,x,y){if(!b){flCard.hidden=true;return}flCard.hidden=false;const t=taxonomy();txt(flF.a,`${b.code} → ${b.outcome}${b.lane?" · "+b.lane:""}: ${b.n} chain${b.n===1?"":"s"}`);
  txt(flF.b,`${b.code}: ${t.codes1[b.code]||0} first-try · gone after repair 1 ${(t.outcome[b.code]||{})["gone after repair 1"]||0} · still there ${(t.outcome[b.code]||{})["still there"]||0} → gone after repair 2 ${(t.outcome[b.code]||{})["gone after repair 2"]||0} · gave up ${(t.outcome[b.code]||{})["gave up"]||0}`);
  txt(flF.c,"click to filter the firehose and the matrix to these chains");const bw=fl.parentNode.clientWidth,cw=Math.min(340,bw-8);flCard.style.left=Math.max(0,Math.min(bw-cw,x+12))+"px";flCard.style.top=Math.max(0,y+12)+"px"}
/* ---------- flow-field slot: 2D fallback (static streamlines; the animated GLSL field is 56-field's) ---------- */
function drawField(now){if(!field2d||!field)return;const W=field.clientWidth||400,H=field.clientHeight||380;const {ctx}=fitCanvas(field2d,W,H);ctx.clearRect(0,0,W,H);if(FX.level===0||field.dataset.mode==="gl")return;
  const rnd=mulberry32(7);ctx.strokeStyle=cssv("--acc");ctx.globalAlpha=.05;ctx.lineWidth=1;const k=2*Math.PI/Math.max(120,W/3);
  for(let i=0;i<48;i++){let x=rnd()*W,y=rnd()*H;ctx.beginPath();ctx.moveTo(x,y);for(let s=0;s<60;s++){const vx=Math.cos(y*k+x*k*.3)+.6,vy=Math.sin(x*k*.8)*.8;x+=vx*4;y+=vy*4;if(x<0||x>W||y<0||y>H)break;ctx.lineTo(x,y)}ctx.stroke()}ctx.globalAlpha=1}
/* ---------- filter ---------- */
const FLOW={panel:PF,taxonomy,
  filter(code,outcome,lane){if(!self.S)return null;const t=taxonomy();const f={kind:"taxonomy",code,outcome:outcome||null,lane:lane||null,label:`${code}${outcome?" → "+outcome:""}${lane?" · "+lane:""}`,
    test(sc){if(!sc||sc.src!=="live"||!sc.item||!sc.item.A)return false;const cs=sc.item.A.map(codesOf);if(!cs[0].includes(code))return false;if(lane&&sc.item.m!==lane)return false;return !outcome||fateOf(cs,code)===outcome||(outcome==="still there"&&fateOf(cs,code)!=="gone after repair 1")}};
    S.flags.filter=f;if(filterChip){filterChip.hidden=false;txt(filterChip,"filter: "+f.label+" ×")}if(self.SIM)SIM.emit("filter",f);LOOP.dirty(LOOP.bits.SCENE|LOOP.bits.SELECT|LOOP.bits.MODE);PM.forceDraw=true;PF.forceDraw=true;return f},
  clear(){if(!self.S)return;S.flags.filter=null;if(filterChip)filterChip.hidden=true;if(self.SIM)SIM.emit("filter",null);LOOP.dirty(LOOP.bits.SCENE|LOOP.bits.SELECT|LOOP.bits.MODE);PM.forceDraw=true;PF.forceDraw=true}};
const MATRIX={panel:PM,compare,lanes,cellAt,prompts,
  facet(k){facet=k;page=0;if(tabs)[...tabs.children].forEach(b=>b.classList.toggle("on",b.dataset.f===k));PM.forceDraw=true},
  page(n){page=Math.max(0,n|0);PM.forceDraw=true},
  fieldSlot(){return field},
  fieldUniforms(){const sc=(self.S&&S.scenes)||[];const n=sc.filter(s=>s.src==="live").length,bad=sc.filter(s=>s.src==="live"&&s.verdict!=="valid").length;return{u_thr:BLANK,u_bad:n?bad/n:0,u_det:(self.S&&S.detected)||0}}};
SECTIONS.register({id:"matrix",part:"live.core",
  header:{title:"Prompt × model matrix + error taxonomy",unit:"50 prompts × 5 lanes · first-try codes → fate after each repair",stamps:{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline"},grade:"S",
    honesty:"one sample per prompt per model on 17 Oct (24 Oct: n per run.json samples when that run is baked) · Suspected as a rate, Confirmed for these scenes · codes fork@eb4b4b4 as recorded · blank notch needs both passes under 0.5 %"},
  mount});
Object.assign(self,{MATRIX,FLOW});
})();
