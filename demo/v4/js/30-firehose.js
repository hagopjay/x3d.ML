/* 30-firehose.js — S9 firehose (SPEC S9, §7.1, §11). Global: FH.
   Owns: the #stream section registration (header + honesty per mode), the toolbar before #fh, ONE <table> inside #fh (thead + tbody: a top spacer row,
   ≤ POOL pool rows keyed by scene id, a bottom spacer row), the tag-line strips (64×10 ImageBitmap per scene: one column per tag line coloured by node
   family, repair-touched lines brighter), the filters (lane · verdict · arm · kind) and the S.flags.filter chip. 32-inspector mounts after #fh via FH.onMount.
   Ported from v3 demo/tether-firehose-v3.template.html: fh() + fhSig (523–531), CH (496), renderBadge (519), row click / Enter (899–900).
   Changes: a 40-row pool over two spacer rows, rows reconciled by key (moved, never rebuilt) and patched with txt(); failed calls (EVENTS.failed → ids F-nnn)
   and cut chains (EVENTS.cut → ids C-nnn) are rows of their own as the run clock passes them and are never scenes; the verdict column follows S.vi through
   judge() as the ladder slider moves; render = the .0 (16.5.0) and .1 (16.5.1) offline passes; port = sc.port when the js-port filled it; 360 retained (WIN).
   One LOOP panel "firehose" (SCENE|VERIFY|SELECT|HOVER|MODE|CLOCK|DATA|VAL|THEME|RESIZE, 4 Hz). ZERO DOM writes while LOOP.paused: the draw keeps its bit
   for the next frame and returns (check_v4_perf.py watches #fh for mutations over 5 s paused).
   Emits: a row click → SIM.select(id) (SIM "select"); hover → S.hover + LOOP.dirty(HOVER). Listens: SIM "select" (scrolls the row into view when the
   selection came from elsewhere: waterfall, hero rail, sheet tiles, wall), SIM "mode", DATA, THEME.
   Test hooks: #fh tr[data-id] (visible pool rows, newest first), __panels.firehose.{rows,total,first,patched,draws}, FH.rows(), FH.events(), FH.eventOf(id),
   FH.geom(), FH.filter, FH.setFilter({lane,verdict,arm,kind}), FH.update(id), FH.scrollTo(id), FH.strip(sc), FH.POOL, FH.rowH. */
(function(){
"use strict";
const POOL=40,OVER=6;
const COLS=["t","id","model","mode","steps","vref","verdict","render","port","chain","strip"];
const HEAD={t:"t",id:"scene",model:"model",mode:"mode",steps:"steps",vref:"validator",verdict:"verdict",render:"render .0 .1",port:"port",chain:"chain",strip:"tag lines"};
const TITLE={t:"run clock when the chain's last call finished (replay: page clock)",id:"scene id; INJ = tampered in this view",model:"model (lane colour)",mode:"oneshot or repair × n",steps:"x3dprov steps in the file's head · 🔒 sealed",vref:"validator the verdict column shows (ladder slider)",verdict:"verdict at that validator",render:".0 = X_ITE 16.5.0 offline pass · .1 = 16.5.1 offline pass · % of pixels differing from the background",port:"js-port-of-8dd0d3e verdict when it ran on this scene in this browser",chain:"verify() of the head metas in this browser",strip:"one column per tag line, coloured by node family; repair-touched lines brighter"};
const CH={verified:["p-ok","VERIFIED"],stale:["p-warn","STALE"],broken:["p-bad","BROKEN"],"seal-fail":["p-bad","SEAL FAIL"],"no-record":["p-mute","NO RECORD"],"?":["p-mute","?"]};
const HEADERS={
  live17:{title:"Firehose + inspector",unit:"every recorded chain on the run's own clock · failed calls and cut chains as rows of their own · click a row to inspect",stamps:{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline"},grade:"C",
    honesty:"rows = the recorded chains replayed on the run clock; failed calls and cut chains come from events.jsonl as rows of their own and are never counted as scenes · chain status = verify() in this browser · render pills = the 16.5.0 and 16.5.1 offline passes · Confirmed"},
  replay11:{title:"Firehose + inspector",unit:"the 174 replay bodies, 2 s apart on the page clock · click a row to inspect",stamps:{source:"RECORDED 11 Oct",validator:"svc@11Oct recorded",renderer:"X_ITE 16.5.0 offline"},grade:"C",
    honesty:"no run clock was recorded on 11 Oct: rows are spaced 2 s apart on the page clock · verdict = the service that was live on 11 Oct; later forks apply through the ladder · chain status = verify() in this browser · Confirmed"},
  run24:{title:"Firehose + inspector",unit:"the 24 Oct run on its own clock · arms A and B · click a row to inspect",stamps:{source:"RECORDED 24 Oct",validator:"fork@8dd0d3e recorded",renderer:"none"},grade:"C",
    honesty:"rows = the recorded 24 Oct chains on the run clock · autofix rows are deterministic repairs, never model calls · chain status = verify() in this browser · Confirmed"}};
const pad3=n=>String(n).padStart(3,"0");
const setClass=(e,c)=>{if(e.className!==c)e.className=c};
const setPill=(sp,cls,text,title)=>{setClass(sp,"pill "+cls);txt(sp,text);if(title!==undefined&&sp.title!==title)sp.title=title};
const FH={POOL,rowH:24,filter:{lane:"",verdict:"",arm:"",kind:""},panel:null,el:null,table:null,body:null,spTop:null,spBot:null,pool:[],userScrollAt:0,_mountFns:[],onMount(f){FH._mountFns.push(f)}};
/* ---------- event rows: failed calls and cut chains (EVENTS, live17 only) ---------- */
let evCache=[],evMap=new Map(),evKey="",progScroll=false;
function events(){const E=self.EVENTS,mode=self.S?S.mode:null;if(!E||!E.failed||mode!=="live17"){if(evKey!=="none"){evKey="none";evCache=[];evMap=new Map()}return evCache}
  const key=mode+"|"+E.failed.length+"|"+E.cut.length;if(key===evKey)return evCache;evKey=key;const out=[];
  E.failed.forEach((f,i)=>out.push({id:"F-"+pad3(i+1),kind:"failed",t:f.t1!=null?f.t1:f.t0,ev:f,m:f.m,p:f.p,k:f.k,code:String(f.kind),n:i+1}));
  E.cut.forEach((c,i)=>out.push({id:"C-"+pad3(i+1),kind:"cut",t:c.t1,ev:c,m:c.m,p:c.p,k:c.k,calls:c.calls,reason:c.reason,n:i+1}));
  out.sort((a,b)=>a.t-b.t);evCache=out;evMap=new Map(out.map(e=>[e.id,e]));return out}
const eventOf=id=>{events();return evMap.get(id)||null};
/* the scene a cut chain became, when its last recorded attempt is on the page */
function sceneOfEvent(e){if(!self.S||!self.LIVE)return null;const idx=LIVE.findIndex(it=>it.m===e.m&&it.p===e.p);if(idx<0)return null;const id=S.liveIds.get(idx);return id?S.byId.get(id)||null:null}
/* ---------- rows: scenes + events, newest first, filtered ---------- */
let rowsCache=[],rowsKey="",lastS=null,armsSeen="";
const verdictAt=(sc,V)=>V&&self.judge?judge(sc,V):{verdict:sc.verdict,codes:[]};
const armOf=sc=>(sc.item&&sc.item.arm)||(sc.run==="24oct"?"A":"");
function flagKey(){const g=S.flags.filter;if(!g)return"";if(typeof g==="function")return"fn:"+(g.key||g.name||"");return g.key||g.label||JSON.stringify(g)}
function matchObj(sc,g){const it=sc.item||{};
  if(typeof g.test==="function")return!!g.test(sc);  /* 28-matrix-flow taxonomy filter {kind:'taxonomy',code,outcome,lane,label,test(sc)}: its own predicate decides */
  if(g.ids){const has=g.ids.has?g.ids.has(sc.id):g.ids.includes(sc.id);if(!has)return false}
  if(g.model&&sc.model!==g.model)return false;if(g.lane&&sc.model!==g.lane)return false;if(g.verdict&&sc.verdict!==g.verdict)return false;
  if(g.src&&sc.src!==g.src)return false;if(g.kind&&sc.drawKind!==g.kind)return false;if(g.category&&it.c!==g.category)return false;if(g.prompt&&it.p!==g.prompt)return false;
  if(g.code){const A=it.A;if(!A||!A.length)return false;if(!codesOf(A[0]).includes(g.code))return false}
  return true}
function passes(r,V){const f=FH.filter,g=S.flags.filter;
  if(f.lane&&(r.sc?r.sc.model:r.m)!==f.lane)return false;
  if(r.sc){const sc=r.sc;
    if((sc.src==="bench"||sc.src==="viewer")&&!S.flags.includeMine&&S.sel!==sc.id)return false;  /* the viewer's own browser work: shown when S.flags.includeMine, or while selected (bench → inspector hand-off) */
    if(f.verdict&&verdictAt(sc,V).verdict!==f.verdict)return false;
    if(f.arm&&armOf(sc)!==f.arm)return false;
    if(f.kind){if(f.kind==="viewer"){if(sc.src!=="viewer"&&sc.src!=="bench")return false}else if(f.kind==="failed"||f.kind==="cut")return false;else if((sc.drawKind||"unknown")!==f.kind)return false}
    if(g){if(typeof g==="function"){if(!g(sc))return false}else if(!matchObj(sc,g))return false}
    return true}
  if(r.kind==="failed"&&S.flags.failed===false)return false;
  if(f.verdict||f.arm||g)return false;
  if(f.kind&&f.kind!==r.kind)return false;
  return true}
function rows(){if(!self.S)return[];const ev=events();let nEv=0;while(nEv<ev.length&&(ev[nEv].t<=S.clk||S.done))nEv++;  /* S.done: 3 cut chains ended after the last body arrived (t1 > t_total); they are released when the run completes */
  const V=S.vi!=null&&self.VALS?VALS[S.vi]:null;
  const key=[S.mode,S.scenes.length,S.seq,S.viewer.length,nEv,S.vi,FH.filter.lane,FH.filter.verdict,FH.filter.arm,FH.filter.kind,S.flags.failed?1:0,S.done?1:0,S.flags.includeMine?1:0,S.viewer.length?S.sel:"",flagKey(),S.scenes.length?S.scenes[0].id:""].join("|");
  if(key===rowsKey&&lastS===S)return rowsCache;rowsKey=key;lastS=S;
  const out=[],arms=new Set();
  S.scenes.forEach((sc,i)=>{const a=armOf(sc);if(a)arms.add(a);const r={id:sc.id,kind:"scene",sc,t:sc.T!=null?sc.T:sc.born,seq:i};if(passes(r,V))out.push(r)});
  for(let i=0;i<nEv;i++)if(passes(ev[i],V))out.push(ev[i]);
  out.sort((a,b)=>(b.t-a.t)||((b.seq||0)-(a.seq||0)));rowsCache=out;
  const ak=[...arms].sort().join(",");if(ak!==armsSeen){armsSeen=ak;armOptions([...arms].sort())}
  return out}
/* ---------- tag-line strips ---------- */
const FAMS=[["hanim",/^HAnim/,"--lane-6"],["geo",/^Geo/,"--lane-9"],
  ["head",/^(X3D|head|meta|Scene|component|unit|ProtoDeclare|ProtoBody|ProtoInterface|ProtoInstance|ExternProtoDeclare|IS|connect|Layer\w*|LayoutGroup|field|fieldValue)$/,"--dim"],
  ["anim",/^(TimeSensor|\w+Interpolator|ROUTE|Script|\w+Sequencer|\w+Trigger|\w+Filter|BooleanToggle|\w+Chaser|\w+Damper)$/,"--warn"],
  ["sensor",/Sensor$/,"--lane-8"],
  ["env",/^(\w*Light|Background|TextureBackground|Fog|LocalFog|Viewpoint|OrthoViewpoint|NavigationInfo|WorldInfo|Sound|AudioClip|ClipPlane)$/,"--lane-7"],
  ["geometry",/^(Box|Sphere|Cone|Cylinder|Torus|Plane|Text|FontStyle|Extrusion|ElevationGrid|Indexed\w+|Triangle\w*|Quad\w*|LineSet|PointSet|Coordinate|Normal|Color|ColorRGBA|TextureCoordinate\w*|Rectangle2D|Disk2D|Circle2D|Arc2D|ArcClose2D|Polyline2D|Polypoint2D|TriangleSet2D|Nurbs\w+|Geometry|geometry)$/,"--acc"],
  ["appearance",/^(Appearance|\w*Material|\w*Texture\w*|LineProperties|FillProperties|PointProperties|\w*Shader\w*|appearance|material)$/,"--info"],
  ["structure",/^(Transform|Group|Switch|LOD|Collision|Inline|Billboard|Anchor|StaticGroup|Shape|CAD\w+|USE|DEF)$/,"--mute"]];
let famCol=null,stripGen=0;const strips=new Map();
const famColours=()=>famCol||(famCol=FAMS.map(f=>cssv(f[2])).concat([cssv("--fg")]));
const tagLines=x=>x.replace(/\r/g,"").replace(/>\s*</g,">\n<").split("\n").filter(l=>l.trim());
function famOf(line){const m=/^<\/?([A-Za-z][\w.-]*)/.exec(line);if(!m)return FAMS.length;const t=m[1];for(let i=0;i<FAMS.length;i++)if(FAMS[i][1].test(t))return i;return FAMS.length}
function strip(sc){if(!sc||!sc.xml)return null;const k=sc.id+"|"+sc.xml.length;const s=strips.get(k);if(s&&s.gen===stripGen)return s.bmp;
  const lines=tagLines(stripProv(sc.xml)),n=lines.length,W=64,H=10,dpr=Math.min(2,devicePixelRatio||1);
  const B=sc.item&&sc.item.B;let first=null;if(sc.src==="live"&&B&&B.length>1&&typeof B[0]==="string")first=new Set(tagLines(stripProv(B[0])));
  const cv=typeof OffscreenCanvas!=="undefined"?new OffscreenCanvas(W*dpr,H*dpr):Object.assign(document.createElement("canvas"),{width:W*dpr,height:H*dpr});
  const g=cv.getContext("2d");g.scale(dpr,dpr);g.clearRect(0,0,W,H);const cols=famColours();
  if(n){const per=n<=W?W/n:1,buckets=n<=W?n:W;
    for(let c=0;c<buckets;c++){const i0=n<=W?c:Math.floor(c*n/W),i1=n<=W?c+1:Math.max(i0+1,Math.floor((c+1)*n/W));let fam=FAMS.length,touched=false,closing=true;
      for(let i=i0;i<i1;i++){const f=famOf(lines[i]);if(f<fam)fam=f;if(first&&!first.has(lines[i]))touched=true;if(!/^<\//.test(lines[i]))closing=false}
      g.globalAlpha=first?(touched?1:.38):(closing?.45:.82);g.fillStyle=cols[fam];const x=n<=W?c*per:c;g.fillRect(x,0,Math.max(1,per),H)}}
  const bmp=cv.transferToImageBitmap?cv.transferToImageBitmap():cv;
  if(strips.size>=600)strips.delete(strips.keys().next().value);strips.set(k,{bmp,gen:stripGen});return bmp}
function drawStrip(canvas,sc,ev){const{ctx,w,h}=fitCanvas(canvas,64,10);ctx.clearRect(0,0,w,h);
  if(sc){const b=strip(sc);if(b)ctx.drawImage(b,0,0,w,h);return}
  if(ev){ctx.strokeStyle=cssv(ev.kind==="cut"?"--warn":"--bad");ctx.lineWidth=1;if(ev.kind==="cut"){ctx.setLineDash([3,2]);ctx.beginPath();ctx.moveTo(0,5.5);ctx.lineTo(w,5.5);ctx.stroke();ctx.setLineDash([])}else{ctx.strokeRect(1.5,1.5,5,7)}}}
/* ---------- render pills (the two offline passes) ---------- */
function pillOf(nb,err,nf){if(err)return["p-bad","UNPARSEABLE"];if(nb==null)return["p-dim","—"];if(nf)return["p-warn","NO DRAW"];if(nb<.005)return["p-warn","BLANK"];return["p-ok",(nb*100).toFixed(0)+"%"]}
function renderPills(sc){const it=sc.item;
  if(sc.src==="live"&&it&&it.A){const f=it.A[it.A.length-1],r=f.r||{},k=self.renderOf?renderOf(it,it.A.length):{r151:null},r1=k.r151;return[pillOf(r.err?null:r.nb,r.err,r.nf||sc.drawKind==="nothing drawable"),r1?pillOf(r1.err?null:r1.nb,r1.err,false):["p-dim","—"]]}
  if(sc.src==="real"&&it&&it.r){const r=it.r;return[pillOf(r.err?null:r.nb,r.err,r.nf||sc.drawKind==="nothing drawable"),r.nb151!==undefined?pillOf(r.err151?null:r.nb151,r.err151,false):["p-dim","—"]]}
  if(sc.nb!=null)return[pillOf(sc.nb,false,false),["p-dim","—"]];return[["p-dim","—"],["p-dim","—"]]}
const portOf=sc=>sc.port?(sc.port.valid?"valid":"invalid"):"";
/* ---------- the pool ---------- */
function mkRow(){const tr=el("tr",{class:"r",tabindex:"0"});
  COLS.forEach(c=>{const td=el("td",{class:c});
    if(c==="id"){td.append(el("span",{class:"idt"}),el("span",{class:"pill tag"}));td.lastChild.hidden=true}
    else if(c==="model")td.append(el("i",{class:"dot"}),el("span",{class:"name"}));
    else if(c==="verdict"||c==="chain"||c==="port")td.append(el("span",{class:"pill"}));
    else if(c==="render")td.append(el("span",{class:"pill r0"}),el("span",{class:"pill r1"}));
    else if(c==="strip")td.append(el("canvas",{width:"64",height:"10"}));
    tr.append(td)});return tr}
let laneList=[],laneCols=new Map(),inFlip=false;
function laneColour(model,src){if(src==="viewer"||src==="bench")return cssv("--you");let c=laneCols.get(model);if(c===undefined){const i=laneList.indexOf(model);c=i>=0?cssv("--lane-"+((i%11)+1)):cssv("--dim");laneCols.set(model,c)}return c}
function patchRow(tr,r,ctx){const sc=r.sc;let sig;const sel=ctx.sel===r.id?1:0,hov=ctx.hov===r.id?1:0;
  if(sc){let v=verdictAt(sc,ctx.V);const rp=renderPills(sc);
    if(self.SLIDER&&SLIDER.active&&typeof SLIDER.verdictOf==="function"){const sv=SLIDER.verdictOf(sc);if(sv===null)v={verdict:"not recorded",note:"not recorded for this text (36-wall slider)"};else if(sv!==undefined)v={verdict:String(sv),note:""}}  /* 36-wall slider: its verdict for the slid text; null = grey */
    r.v=v;r.rp=rp;
    sig=[r.id,sc.status,v.verdict,v.note?1:0,sc.nsteps,sc.sealed?1:0,sc.injured?1:0,sc.tampered?1:0,sc.detected?1:0,sc.vref,ctx.V?ctx.V.ref:"",rp[0][1],rp[1][1],portOf(sc),sel,hov,ctx.gen,sc.mode].join("|")}
  else{r.link=r.kind==="cut"?sceneOfEvent(r):null;sig=[r.id,sel,hov,ctx.gen,r.link?r.link.id:""].join("|")}
  if(tr.__sig===sig)return false;const newId=tr.__id!==r.id;tr.__sig=sig;tr.__id=r.id;if(tr.dataset.id!==r.id)tr.dataset.id=r.id;
  const td=tr.children,cls="r"+(sc?"":" ev ev-"+r.kind)+(sel?" sel":"")+(hov?" hov":"")+(sc&&sc.injured?" inj":"")+(newId&&ctx.anim?(inFlip?" in1":" in2"):"");if(newId&&ctx.anim)inFlip=!inFlip;setClass(tr,cls);
  txt(td[0],fmt.clock(r.t));
  if(sc){const it=sc.item||{},v=r.v,rp=r.rp,tag=td[1].lastChild;txt(td[1].firstChild,sc.id);
    const tg=sc.tampered?["p-bad","TAMPERED"]:sc.injured?["p-bad","INJ"]:sc.src==="viewer"?["p-you","YOU"]:sc.src==="bench"?["p-you","BENCH"]:null;if(tg){setPill(tag,tg[0],tg[1]);if(tag.hidden)tag.hidden=false}else if(!tag.hidden)tag.hidden=true;
    const lc=laneColour(sc.model,sc.src);if(tr.__lane!==lc){tr.__lane=lc;td[2].style.setProperty("--lane",lc)}txt(td[2].lastChild,String(sc.model||"").replace("-awq",""));
    txt(td[3],sc.mode||"");txt(td[4],String(sc.nsteps)+(sc.sealed?" 🔒":""));txt(td[5],(ctx.V?ctx.V.ref:sc.vref||"").replace("fork@","f@"));
    setPill(td[6].firstChild,v.note?"p-mute":v.verdict==="valid"?"p-ok":"p-bad",v.verdict||"?",v.note||"");
    setPill(td[7].children[0],rp[0][0],rp[0][1]);setPill(td[7].children[1],rp[1][0],rp[1][1]);
    const po=portOf(sc);setPill(td[8].firstChild,po?(po==="valid"?"p-ok":"p-bad"):"p-dim",po||"—",po?"js-port-of-8dd0d3e in this browser":"js-port-of-8dd0d3e: not run on this scene yet");
    const c=CH[sc.status]||CH["?"];setPill(td[9].firstChild,c[0],c[1]);
    if(newId||tr.__gen!==ctx.gen){tr.__gen=ctx.gen;drawStrip(td[10].firstChild,sc,null)}
    if(newId){const ttl=`${sc.id} · ${it.p||""} · ${sc.model} · ${sc.mode} · ${sc.src}`;if(tr.title!==ttl)tr.title=ttl}}
  else{const e=r,tag=td[1].lastChild;txt(td[1].firstChild,e.id);setPill(tag,e.kind==="failed"?"p-bad":"p-warn",e.kind==="failed"?"FAILED CALL":"CUT CHAIN");if(tag.hidden)tag.hidden=false;
    const lc=laneColour(e.m,"");if(tr.__lane!==lc){tr.__lane=lc;td[2].style.setProperty("--lane",lc)}txt(td[2].lastChild,String(e.m||"").replace("-awq",""));
    const link=r.link;
    txt(td[3],e.kind==="failed"?`call ${e.k} · ${e.p}`:`cut after ${e.calls} call${e.calls===1?"":"s"} · ${e.p}${link?" → "+link.id:""}`);txt(td[4],"—");txt(td[5],"—");
    setPill(td[6].firstChild,e.kind==="failed"?"p-bad":"p-warn",e.kind==="failed"?(e.code==="credit"?"CREDIT OUT":e.code):e.reason,"");
    setPill(td[7].children[0],"p-dim","—");setPill(td[7].children[1],"p-dim","—");setPill(td[8].firstChild,"p-dim","—","");
    setPill(td[9].firstChild,e.kind==="failed"?"p-mute":"p-warn",e.kind==="failed"?"NO CHAIN":"CUT");
    if(newId||tr.__gen!==ctx.gen){tr.__gen=ctx.gen;drawStrip(td[10].firstChild,null,e)}
    if(newId){const ttl=e.kind==="failed"?`failed call: the provider answered ${e.code} at ${fmt.clock(e.t)} on ${e.m} · ${e.p} attempt ${e.k}; no body came back, so there is no scene and no chain · events.jsonl row ${e.n} of ${EVENTS.failed.length} (kind only) · never counted as a scene`
      :`cut chain: ${e.reason} stopped ${e.m} on ${e.p} after ${e.calls} call${e.calls===1?"":"s"} · events.jsonl cut ${e.n} of ${EVENTS.cut.length}${link?" · its last recorded attempt is on the page as "+link.id:""}${self.SIM&&e.t>SIM.tmax()?" · ended at "+fmt.clock(e.t)+", after the last body arrived, so it is released when the run completes":""}`;if(tr.title!==ttl)tr.title=ttl}}
  return true}
const setH=(sp,h)=>{if(sp.__h!==h){sp.__h=h;sp.firstChild.style.height=h+"px"}};
let lastTopId=null,measured=false,queued=false,fromRow=false;
function draw(){const p=FH.panel;if(!self.S||!FH.body)return;
  if(self.LOOP&&LOOP.paused){LOOP.dirtyBits|=p.bit;return}  /* no DOM write while paused; the bit survives to the next frame */
  const R=rows(),total=R.length,rowH=FH.rowH,elx=FH.el;p.total=total;
  /* rows appended at the top while the reader is scrolled down: keep what they look at in place */
  if(lastTopId&&total&&R[0].id!==lastTopId&&elx.scrollTop>rowH){const k=R.findIndex(r=>r.id===lastTopId);if(k>0)elx.scrollTop+=k*rowH}
  lastTopId=total?R[0].id:null;
  const maxFirst=Math.max(0,total-POOL),first=Math.max(0,Math.min(Math.floor(elx.scrollTop/rowH)-OVER,maxFirst)),count=Math.min(POOL,total);
  const want=new Array(count),byId=new Map();FH.pool.forEach(tr=>{if(tr.__id)byId.set(tr.__id,tr)});
  const used=new Set();for(let i=0;i<count;i++){const r=R[first+i],tr=byId.get(r.id);if(tr&&!used.has(tr)){want[i]=tr;used.add(tr)}}
  const spare=FH.pool.filter(tr=>!used.has(tr));
  for(let i=0;i<count;i++)if(!want[i]){let tr=spare.pop();if(!tr){tr=mkRow();FH.pool.push(tr);FH.body.insertBefore(tr,FH.spBot)}want[i]=tr;used.add(tr)}
  let prev=FH.spTop;for(let i=0;i<count;i++){const tr=want[i],ref=prev.nextSibling;if(ref!==tr)FH.body.insertBefore(tr,ref);prev=tr}
  const V=S.vi!=null&&self.VALS?VALS[S.vi]:null,ctx={sel:S.sel,hov:S.hover,V,gen:stripGen,anim:self.FX&&FX.level>0};let patched=0;
  for(let i=0;i<count;i++){const tr=want[i];if(tr.hidden)tr.hidden=false;if(patchRow(tr,R[first+i],ctx))patched++}
  spare.forEach(tr=>{if(!tr.hidden){tr.hidden=true;tr.__sig="";tr.__id=null;tr.removeAttribute("data-id")}});
  if(!measured&&count){const h=want[0].getBoundingClientRect().height;if(h>8){FH.rowH=h;measured=true;document.documentElement.style.setProperty("--fh-row",h+"px")}}
  setH(FH.spTop,first*FH.rowH);setH(FH.spBot,Math.max(0,total-first-count)*FH.rowH);
  p.rows=count;p.first=first;p.patched+=patched;status(R,total)}
function kick(){if(queued||!self.LOOP)return;queued=true;LOOP.onFrame(()=>{queued=false;if(FH.panel)draw()})}
/* ---------- toolbar and status ---------- */
let bar,stat,laneSel,verdictSel,armSel,armLab,kindSel,fchip,fchipL,statN,statHint;
function sel(opts,title){const s=el("select",{title});opts.forEach(([v,l])=>s.appendChild(el("option",{value:v,text:l})));return s}
function laneOptions(){const m=self.MODES&&MODES.current;const lanes=m?(m.lanes()||[]):[];const key=lanes.join(",");if(key===laneSel.__key)return;laneSel.__key=key;laneList=lanes;laneCols=new Map();
  laneSel.textContent="";laneSel.appendChild(el("option",{value:"",text:"all lanes"}));lanes.forEach(l=>laneSel.appendChild(el("option",{value:l,text:String(l).replace("-awq","")})));if(self.S&&S.viewer&&S.viewer.length)laneSel.appendChild(el("option",{value:"viewer",text:"you"}));
  if(FH.filter.lane&&!lanes.includes(FH.filter.lane))FH.filter.lane="";laneSel.value=FH.filter.lane}
function armOptions(arms){armSel.textContent="";armSel.appendChild(el("option",{value:"",text:"all arms"}));arms.forEach(a=>armSel.appendChild(el("option",{value:a,text:"arm "+a})));const on=arms.length>0;if(armLab.hidden===on)armLab.hidden=!on;if(!on)FH.filter.arm=""}
function buildBar(){bar=el("div",{class:"fhBar"});
  laneSel=sel([["","all lanes"]],"lane");verdictSel=sel([["","all verdicts"],["valid","valid"],["invalid","invalid"]],"verdict at the validator the column shows");
  armSel=sel([["","all arms"]],"arm (24 Oct run)");kindSel=sel([["","all kinds"],["draws","draws"],["blank frame","blank frame"],["nothing drawable","nothing drawable"],["unparseable","unparseable"],["failed","failed calls"],["cut","cut chains"],["viewer","your scenes"]],"what the row is");
  armLab=el("label",null,["arm",armSel]);armLab.hidden=true;
  fchipL=el("span",{class:"fl"});fchip=el("span",{class:"fchip"},["filter:",fchipL,el("button",{type:"button",title:"clear the filter set by another panel",text:"×",onclick:()=>{S.flags.filter=null;if(self.SIM)SIM.emit("filter",null);LOOP.dirty(LOOP.bits.SCENE);kick()}})]);fchip.hidden=true;
  bar.append(el("label",null,["lane",laneSel]),el("label",null,["verdict",verdictSel]),armLab,el("label",null,["kind",kindSel]),fchip);
  [[laneSel,"lane"],[verdictSel,"verdict"],[armSel,"arm"],[kindSel,"kind"]].forEach(([s,k])=>s.addEventListener("change",()=>{FH.filter[k]=s.value;kick()}));
  statN=el("span");statHint=el("span",{class:"mutec"});
  stat=el("div",{class:"fhStat"},[statN,el("span",null,["failed calls ",claimChip("c.failed",{size:"s",label:""})]),el("span",null,["cut chains ",claimChip("c.cut",{size:"s",label:""})]),statHint])}
function status(R,total){const g=S.flags.filter;const lab=g?(typeof g==="function"?(g.label||"custom"):(g.label||g.code||g.model||g.lane||g.kind||g.verdict||g.category||"set")):"";
  if(fchip.hidden===!!g)fchip.hidden=!g;if(g)txt(fchipL,lab);
  const win=self.WIN||360,scenes=S.scenes.length,ev=R.length-R.filter(r=>r.sc).length;
  txt(statN,`newest first · ${total} row${total===1?"":"s"} shown · ${scenes} scene${scenes===1?"":"s"} in the window of ${win}${ev?" · "+ev+" event row"+(ev===1?"":"s"):""}${S.flags.failed===false?" · failed marks hidden (F)":""}`);
  const hidden=S.sel&&!R.some(r=>r.id===S.sel)&&(S.byId.has(S.sel)||eventOf(S.sel));txt(statHint,hidden?" · the selected row is hidden by a filter":"");
  if(laneSel&&(laneSel.__mode!==S.mode||laneSel.__nv!==S.viewer.length)){laneSel.__mode=S.mode;laneSel.__nv=S.viewer.length;laneOptions()}}
/* ---------- mount ---------- */
function mount(sec){const sb=sec.querySelector(".sb");let fh=$("fh");if(!fh){fh=el("div",{id:"fh"});sb.appendChild(fh)}FH.el=fh;
  buildBar();sb.insertBefore(bar,fh);sb.insertBefore(stat,fh.nextSibling);
  fh.textContent="";const thead=el("thead",null,el("tr",null,COLS.map(c=>el("th",{class:c,text:HEAD[c],title:TITLE[c]})))),tbody=el("tbody");
  FH.spTop=el("tr",{class:"sp","aria-hidden":"true"},el("td",{colspan:String(COLS.length)}));FH.spBot=el("tr",{class:"sp","aria-hidden":"true"},el("td",{colspan:String(COLS.length)}));tbody.append(FH.spTop,FH.spBot);
  FH.table=el("table",{class:"fhTable"},[thead,tbody]);FH.body=tbody;fh.appendChild(FH.table);
  fh.addEventListener("scroll",()=>{if(progScroll)progScroll=false;else FH.userScrollAt=performance.now();kick()},{passive:true});  /* a scroll the page made itself (scrollTo) is not the reader's */
  tbody.addEventListener("click",e=>{const tr=e.target.closest("tr.r");if(tr&&tr.dataset.id&&self.SIM){fromRow=true;SIM.select(tr.dataset.id)}});
  tbody.addEventListener("keydown",e=>{if(e.key!=="Enter"&&e.key!==" ")return;const tr=e.target.closest("tr.r");if(tr&&tr.dataset.id){e.preventDefault();fromRow=true;SIM.select(tr.dataset.id)}});
  tbody.addEventListener("pointerover",e=>{const tr=e.target.closest("tr.r");const id=tr?tr.dataset.id||null:null;if(self.S&&S.hover!==id){S.hover=id;LOOP.dirty(LOOP.bits.HOVER)}});
  fh.addEventListener("pointerleave",()=>{if(self.S&&S.hover){S.hover=null;LOOP.dirty(LOOP.bits.HOVER)}});
  FH.panel=LOOP.register({name:"firehose",bit:LOOP.bits.SCENE|LOOP.bits.VERIFY|LOOP.bits.SELECT|LOOP.bits.HOVER|LOOP.bits.MODE|LOOP.bits.CLOCK|LOOP.bits.DATA|LOOP.bits.VAL|LOOP.bits.THEME|LOOP.bits.RESIZE,rateHz:4,budgetMs:4,draw});
  FH.panel.rows=0;FH.panel.total=0;FH.panel.first=0;FH.panel.patched=0;
  if(self.SIM){SIM.on("select",id=>{if(fromRow){fromRow=false;kick();return}if(id)FH.scrollTo(id);else kick()});SIM.on("mode",m=>{const h=HEADERS[m]||HEADERS.live17;sectionHeader(sec,h);rowsKey="";kick()});SIM.on("reset",()=>{rowsKey="";lastTopId=null;kick()});SIM.on("filter",()=>{rowsKey="";LOOP.dirty(LOOP.bits.SCENE);kick()})}
  if(self.THEME)THEME.onChange(()=>{stripGen++;famCol=null;laneCols=new Map();kick()});
  FH._mountFns.forEach(f=>{try{f(sec)}catch(e){console.error("stream mount",e);if(self.BOOT)BOOT.error(e,"mount stream (inspector)")}});
  kick()}
SECTIONS.register({id:"stream",header:HEADERS.live17,part:"live.bodies",mount});
/* ---------- API ---------- */
FH.rows=rows;FH.events=events;FH.eventOf=eventOf;FH.sceneOfEvent=sceneOfEvent;FH.strip=strip;FH.draw=draw;FH.kick=kick;
FH.geom=()=>({rowH:FH.rowH,first:FH.panel?FH.panel.first:0,count:FH.panel?FH.panel.rows:0,total:FH.panel?FH.panel.total:0,top:FH.spTop?FH.spTop.__h||0:0,bottom:FH.spBot?FH.spBot.__h||0:0,pool:FH.pool.length});
FH.setFilter=o=>{Object.assign(FH.filter,o||{});if(laneSel)laneSel.value=FH.filter.lane;if(verdictSel)verdictSel.value=FH.filter.verdict;if(armSel)armSel.value=FH.filter.arm;if(kindSel)kindSel.value=FH.filter.kind;kick()};
FH.update=id=>{const tr=FH.pool.find(t=>t.__id===id);if(tr)tr.__sig="";kick()};
FH.scrollTo=id=>{if(!FH.el)return false;const R=rows(),i=R.findIndex(r=>r.id===id);if(i<0){kick();return false}
  if(performance.now()-FH.userScrollAt>800){const top=Math.max(0,i*FH.rowH-FH.el.clientHeight/2+FH.rowH/2);if(Math.abs(FH.el.scrollTop-top)>=1){progScroll=true;FH.el.scrollTop=top}}kick();return true};
FH.laneColour=laneColour;
Object.assign(self,{FH});
})();
