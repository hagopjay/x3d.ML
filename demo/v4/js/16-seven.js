/* 16-seven.js — S4 THE DARK SEVEN (SPEC-v4 S4; WORKPLAN 16-seven). Section #seven, part live.bodies.
   Owns: the 7-tile strip (measured frames, near-black, nb printed as a percentage and as the raw ratio), the MEASURED-forced stage (a lazy STAGE.show2 instance:
   raw bytes, no rig, the scene's own or default viewpoint, headlight; created on reveal, disposed 2.5 s after leave), FIND IT (SAI facts → one explicit dolly of
   the render-time camera: a framing of the layer bbox the validator passed, a walk-up into the ProximitySensor box for the interaction cases, and for the H-Anim
   case no move but the honest line), the distance counter, the live ratio ticking from the instance's pixels() (this browser, never counted), RESET, MEASURE HERE
   (STAGE.measure.show on the counted path, forwarded to RASTER.live when the raster module is present), and a card per scene (BLANKWHY, X_ITE console lines, the
   record's render step, verdict pills fork@eb4b4b4 + js-port-of-8dd0d3e, pass pills 16.5.0 · 16.5.1, the proposed validator warning text).
   Globals: SEVEN {list, ids(), open(ref), findIt(), reset(), measure(), cur(), state}, BLANKWHY (v3 line 264; 40-sheet exports the same table).
   Claims: seven.ids (sorted keys of the finals valid on eb4b4b4 whose 16.5.0 frame is under 0.5%; expected STATS.claims['c.seven'].ids sorted),
           seven.pass151 (how many of those are under 0.5% in the 16.5.1 pass too; expected STATS.claims['c.seven'].expected).
   Test hooks: __seven {list, ids, cur, loaded, loads, inst, staged (always false), find:{kind, dist, phase}, ratio, samples, plan}.
   fx 0 / reduced motion: the dolly is a 2-frame cut with the same counter end values; the ratio is still sampled from the live frame. */
(function(){
"use strict";
const BLANKWHY=self.BLANKWHY||{interaction:"proximity-lit scenes that stay dark until the viewer walks up",geospatial:"geospatial scenes whose content is tiny from the default camera",hanim:"a humanoid whose boxes hang off no joint, a scene that passes the validator by saying less"};
const WARNTXT={geospatial:"Proposed warning [geo-no-local-viewpoint]: a GeoLocation / GeoOrigin scene binds no Viewpoint or GeoViewpoint that frames its located content; the default camera sits at a geocentric distance and the first frame is empty. Suggested text: \"GeoLocation present but no viewpoint frames the located geometry: the scene opens on an empty frame.\"",
  interaction:"Proposed warning [dark-until-proximity]: every light in the scene is switched by a ProximitySensor ROUTE and the headlight is off; until the viewer enters the sensor box the frame is black. Suggested text: \"All lights depend on a ProximitySensor; the scene opens dark.\"",
  hanim:"Proposed warning [hanim-unreached-geometry]: Shape nodes sit in an HAnimSegment that no HAnimJoint of the skeleton references, so the humanoid places no geometry. Suggested text: \"HAnimSegment with geometry is attached to no joint: nothing is drawn.\""};
const V={sub:(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],add:(a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]],scale:(a,s)=>[a[0]*s,a[1]*s,a[2]*s],len:a=>Math.hypot(a[0],a[1],a[2]),norm:a=>{const l=Math.hypot(a[0],a[1],a[2])||1;return[a[0]/l,a[1]/l,a[2]/l]},cross:(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]};
const E={},ST={pending:0,disposeWanted:false,list:[],cur:null,inst:null,loaded:null,loading:false,loads:0,gen:0,visible:false,leave:null,finding:false,moving:false,find:null,pose0:null,ratio:null,samples:0,port:new Map(),sec:null};
const __seven={pending:0,list:[],ids:[],cur:null,loaded:null,loads:0,inst:null,staged:false,find:null,ratio:null,samples:0,plan:null};
const short=m=>String(m).replace(/^.*\//,"");
const share=()=>!!(self.BUILD&&BUILD.share);
const laneName=m=>{if(!share())return short(m);const paid=(((self.LM||(self.STATS&&STATS.meta))||{}).models||[]).filter(x=>x.prov!=="nvidia").map(x=>x.id);const i=paid.indexOf(m);return i>=0?"closed-"+"ABCDEF"[i]:"open lane"};
const fin=i=>i.A[i.A.length-1];
const statIds=()=>((self.STATS&&STATS.claims&&STATS.claims["c.seven"]&&STATS.claims["c.seven"].ids)||[]).slice();
const rule150=i=>{const f=fin(i);return !!f.ok&&!!f.r&&!f.r.err&&(f.r.nb||0)<.005};
const bodyOf=x=>x&&x.live&&x.live.B&&x.live.B.length>=x.live.A.length?x.live.B[x.live.A.length-1]:null;
const fmtDist=m=>m==null||!Number.isFinite(m)?"—":m>=10000?fmt.int(m/1000)+" km":m>=1000?fmt.num(m/1000,2)+" km":m>=10?fmt.num(m,1)+" m":fmt.num(m,2)+" m";
const isGeo=(F,body)=>!!(F&&F.geo)||/<GeoLocation|<GeoViewpoint|<GeoOrigin/.test(body||"");
/* ---------- the list ---------- */
function build(){const ids=statIds(),ord=k=>{const i=ids.indexOf(k);return i<0?1e3:i};let list;
  if(self.LIVE&&LIVE.length)list=LIVE.filter(rule150).map(i=>{const f=fin(i),key=keyOf(i.m,i.p,i.A.length),r1=self.R151&&R151.live&&R151.live[key]||null;
    return{key,m:i.m,p:i.p,c:i.c,live:i,nb:f.r.nb||0,nb151:r1?r1.nb:null,err151:r1?r1.err||null:null,has151:!!r1,frames:f.r.frames,frames151:r1?r1.frames:null,last:f.r.last,nodes:f.r.nodes,msgs:f.r.msgs||[],jpg:f.r.jpg||null,calls:i.A.length,ok:!!f.ok}});
  else list=(self.STATS&&STATS.seven||[]).map(s=>({key:s.key,m:s.m,p:s.p,c:s.c,live:null,nb:s.nb,nb151:s.nb151,has151:s.nb151!=null,frames:s.frames,frames151:s.frames151,msgs:[],jpg:null,calls:null,ok:true,fromStats:true}));
  list.sort((a,b)=>ord(a.key)-ord(b.key)||a.key.localeCompare(b.key));ST.list=list;__seven.list=list.map(x=>x.key);__seven.ids=list.map(x=>x.key).slice().sort();
  if(E.strip){E.strip.textContent="";list.forEach((x,i)=>{const b=el("button",{class:"th "+(x.ok?"v":"i")+(ST.cur&&ST.cur.key===x.key?" sel":""),type:"button",title:`${x.p} · ${laneName(x.m)} · ${x.c} · nonblank ${fmt.pct(x.nb,2)} (ratio ${x.nb})`,data:{key:x.key},onclick:()=>SEVEN.open(x.key)},
      [x.jpg?el("img",{src:"data:image/jpeg;base64,"+x.jpg,alt:`measured frame of ${x.p}, near black`,width:"128",height:"96"}):el("span",{style:{display:"block",width:"128px",height:"96px"}}),el("span",{class:"nb",text:`BLANK · ${fmt.pct(x.nb,2)}`}),el("span",{class:"lbl",text:`${x.p} · ${laneName(x.m)}`})]);E.strip.appendChild(b)});
    txt(E.ph,`${list.length} finals valid on fork@eb4b4b4 whose X_ITE 16.5.0 frame is under 0.5% nonblank${list[0]&&list[0].fromStats?" · from the record until live.core lands":" · recomputed from LIVE"} · each opened and read by hand`)}
  if(ST.cur){const again=list.find(x=>x.key===ST.cur.key);if(again){ST.cur=again;__seven.cur=again.key;renderCard(again)}}else if(list.length&&E.strip)SEVEN.open(0,{noLoad:true})}
/* ---------- the stage instance ---------- */
function ensureInst(){if(ST.inst||!self.STAGE||!STAGE.show2||!self.X3D||!E.host)return false;ST.inst=STAGE.show2(E.host,{name:"seven"});__seven.inst=ST.inst;txt(E.badge,"MEASURED · raw bytes · own/default viewpoint · headlight · creating the X_ITE instance…");if(ST.cur)loadCur();return true}
/* deferred while a load is pending (see 14-morph): the IO leave must never null the instance a loadCur is awaiting */
function disposeInst(){if(ST.pending>0){ST.disposeWanted=true;return false}ST.disposeWanted=false;if(ST.inst)try{ST.inst.dispose()}catch(e){}ST.inst=null;__seven.inst=null;ST.loaded=null;__seven.loaded=null;txt(E.badge,"stage disposed off screen · MEASURED mode is forced here");return true}
async function loadCur(){const x=ST.cur,inst=ST.inst;if(!x||!inst)return;const body=bodyOf(x);if(!body){say("the body arrives with part live.bodies");return}const gen=++ST.gen;ST.pending++;__seven.pending=ST.pending;
  try{await loadInner(x,inst,body,gen)}finally{ST.pending--;__seven.pending=ST.pending;if(ST.pending===0&&ST.disposeWanted&&!ST.visible)disposeInst()}}
async function loadInner(x,inst,body,gen){const stale=()=>gen!==ST.gen||ST.inst!==inst;ST.loading=true;ST.loaded=null;__seven.loaded=null;counter("—","loading");ratio(null,"loading…");say("");
  const r=await inst.load(body,{staged:false,scene:"seven"});if(stale()){if(gen===ST.gen)ST.loading=false;return}ST.loading=false;if(!r.ok){say(r.err?"X_ITE refused this scene: "+r.err:"load failed");return}
  ST.loaded=x.key;__seven.loaded=x.key;ST.loads++;__seven.loads=ST.loads;ST.pose0=inst.pose();txt(E.badge,inst.label());counter("—","FIND IT moves the camera to the geometry");await later(700);if(stale())return;await sampleOnce()}
function say(s){txt(E.msg,s)}
function line(s){txt(E.line,s)}
function counter(v,small){txt(E.cnum,typeof v==="number"?fmtDist(v):String(v));txt(E.csmall,small||"")}
function ratio(nb,note){ST.ratio=nb;__seven.ratio=nb;txt(E.rnum,nb==null?`this browser: ${note||"—"}`:`this browser: ${fmt.pct(nb,2)}`);txt(E.rsmall,nb==null?"":"live frame · not counted · the same rule: pixels differing from the dominant colour · ratio "+nb)}
async function sampleOnce(){const inst=ST.inst;if(!inst||!inst.ok)return null;const r=await inst.pixels();ST.samples++;__seven.samples=ST.samples;if(r&&r.nonblank!=null)ratio(r.nonblank);else ratio(null,"renderer could not deliver a frame here");return r}
async function sampleLoop(){let after=0;while(ST.moving||after<4){await sampleOnce();if(!ST.moving)after++;await later(250)}}
/* ---------- FIND IT: the plan from SAI facts ---------- */
function planFind(inst,x){const F=inst.facts()||{},P=inst.placed()||{shapes:0,placed:0,unreached:0},bb=inst.bbox(),pose=inst.pose(),body=bodyOf(x)||"";
  if(!pose)return{kind:"nopose",F,P,bb};
  if(F.hanim||!bb||bb.empty||P.placed===0||!bb.size.every(Number.isFinite))return{kind:"none",F,P,bb};
  const c=bb.center,s=bb.size,ext=Math.max(...s)||1;
  if(F.prox&&F.proxBox&&F.proxBox.size){const pc=F.proxBox.center,ps=F.proxBox.size;const pos=[pc[0],pc[1],pc[2]+Math.min(Math.abs(ps[2])*.2,2)];
    return{kind:"walk",position:pos,lookAt:[c[0],pc[1],c[2]-Math.max(1,ext)],up:[0,1,0],from:pose.position,dist:V.len(V.sub(pos,pose.position)),F,P,bb,geo:isGeo(F,body)}}
  /* framing direction: the original camera's bearing projected on the ground plane (local Y up; the radial up for a geocentric bbox), lifted 28° above the
     horizon (a standing viewer's overview: the located markers are metres tall and hundreds of metres apart, so the frame is the scene's own horizon with the content
     in it) — the 25 Oct probe showed a geospatial default camera sits BELOW the located content, and from below the solid faces cull to a blank frame */
  const up=V.len(c)>1e5?V.norm(c):[0,1,0],d0=V.sub(pose.position,c),along=d0[0]*up[0]+d0[1]*up[1]+d0[2]*up[2];let h=V.sub(d0,V.scale(up,along));
  if(V.len(h)<1e-6)h=V.cross(up,Math.abs(up[0])<.9?[1,0,0]:[0,0,1]);h=V.norm(h);const pitch=12*Math.PI/180,dir=V.norm(V.add(V.scale(h,Math.cos(pitch)),V.scale(up,Math.sin(pitch))));
  let fov=Math.PI/4;try{const f=inst.browser.getActiveLayer().getViewpoint().getFieldOfView();if(f>0&&f<Math.PI)fov=f}catch(e){}
  const d=Math.max(ext/2/Math.tan(fov/2)*1.1,ext*.05,.5),pos=V.add(c,V.scale(dir,d));
  return{kind:"frame",position:pos,lookAt:c,up,from:pose.position,dist:V.len(V.sub(pos,pose.position)),F,P,bb,geo:isGeo(F,body)}}
async function findIt(){const inst=ST.inst,x=ST.cur;if(!x)return null;
  if(!inst||!inst.ok){say("renderer could not start here: X_ITE gave no browser for this section");ratio(null,"renderer could not start");return null}
  if(ST.loading||ST.loaded!==x.key){say("the scene is still loading; FIND IT follows the load");return null}if(ST.finding)return null;ST.finding=true;
  const plan=planFind(inst,x);ST.find={kind:plan.kind,dist:plan.dist||0,phase:"plan"};__seven.find=ST.find;__seven.plan={kind:plan.kind,dist:plan.dist,bbox:plan.bb&&!plan.bb.empty?plan.bb.size.map(v=>+v.toFixed(2)):null,placed:plan.P&&plan.P.placed,shapes:plan.P&&plan.P.shapes};
  try{
    if(plan.kind==="nopose"){say("renderer could not report a camera pose here");ratio(null,"renderer could not report a pose");return plan}
    if(plan.kind==="none"){counter("0","shapes placed");say(`0 shapes placed${plan.F&&plan.F.hanim?" · HAnim skeleton with no attached geometry":" · no finite geometry reached in the layer"} · ${fmt.int(plan.P.shapes)} Shape nodes in the file, ${fmt.int(plan.P.unreached)} reached by no joint or group`);
      line("the loop converged on a scene that passes by saying less");ST.find.phase="none";await sampleOnce();return plan}
    const total=plan.dist;counter(total,"to the geometry");line("");
    say(plan.kind==="walk"?"walking into the ProximitySensor box · the scene's own ROUTE lights it, nothing injected":`dolly to a framing of the ${plan.bb.size.map(v=>fmtDist(v)).join(" × ")} box the validator passed${plan.geo?" · geospatial: the default camera sat "+fmtDist(total)+" away":""}`);
    ST.moving=true;const sampling=sampleLoop();ST.find.phase="moving";
    await inst.dolly({position:plan.position,lookAt:plan.lookAt,up:plan.up,onStep:(t,p)=>counter(V.len(V.sub(plan.position,p)),"to go")},3500);
    ST.moving=false;ST.find.phase="arrived";counter(0,`arrived · travelled ${fmtDist(total)}`);await sampling;return plan}
  finally{ST.finding=false;ST.moving=false}}
async function reset(){const inst=ST.inst;if(!inst||!inst.ok||!ST.pose0)return false;ST.moving=false;const ok=await inst.dolly({position:ST.pose0.position,q:ST.pose0.q},0);counter("—","back at the scene's own camera");line("");say("");await later(300);await sampleOnce();return ok}
/* the counted path: STAGE.measure on the same bytes (192×144, the watcher of 08-stage), forwarded to the raster's live row */
async function measure(){const x=ST.cur;if(!x||!self.STAGE||!STAGE.measure||!STAGE.measure.ok)return null;const body=bodyOf(x);if(!body)return null;say("measuring on the counted path (192×144, same watcher)…");
  const R=await STAGE.measure.show(body,{timeoutMs:15000});if(R.cancelled)return R;say(R.err?"measure canvas: X_ITE refused · "+R.err:R.noFrame?"measure canvas: no frame yet":`measure canvas: ${fmt.pct(R.nb,2)} · ${R.frames} frames · ${R.kind} · this browser, not counted`);
  if(self.RASTER&&RASTER.live)RASTER.live(x.key,R,"dark seven");return R}
/* ---------- the card ---------- */
function renderCard(x){const c=E.card;c.textContent="";if(!x)return;const L=x.live,f=L?fin(L):null;
  c.appendChild(el("h4",{text:`${x.p} · ${x.c} · ${laneName(x.m)}${x.calls?" · "+x.calls+" call"+(x.calls>1?"s":""):""}`}));
  c.appendChild(el("div",{class:"why",text:BLANKWHY[x.c]||"opened and read by hand: the scene says less than the validator can see"}));
  c.appendChild(el("div",{class:"k",text:"X_ITE said (offline pass console)"}));c.appendChild(el("div",{class:"v",text:x.msgs&&x.msgs.length?x.msgs.join(" · "):"X_ITE said nothing: no console line recorded for this load"}));
  /* Blender stills from the STAGED manifest, when it holds this key: the blank flag is read from the manifest (12-hero's reader), never a list here */
  const SL=self.HEROUI&&HEROUI.stagedLines?HEROUI.stagedLines(x.key):[];if(SL.length){c.appendChild(el("div",{class:"k",text:"Blender, from the STAGED manifest (not a browser frame)"}));c.appendChild(el("div",{class:"v"},SL.map(l=>el("div",{class:l.blank?"bad":"",text:l.text}))))}
  c.appendChild(el("div",{class:"k",text:"the record's render step"}));
  c.appendChild(el("div",{class:"v"},[el("b",{text:`nonblank ${fmt.pct(x.nb,2)} (ratio ${x.nb})`}),` · ${x.nodes!=null?fmt.int(x.nodes)+" nodes · ":""}${x.frames!=null?fmt.int(x.frames)+" frames":""}${x.last!=null?" · last "+fmt.int(x.last)+" ms":""} · x_ite@16.5.0 headless swiftshader (offline, after the run)`]));
  c.appendChild(el("div",{class:"k",text:"verdicts"}));const pills=el("div",{class:"pills"});c.appendChild(pills);
  pills.appendChild(el("span",{class:"pill p-ok",text:"valid on fork@eb4b4b4"+(f?" · "+fmt.int(f.vms)+" ms":"")}));
  const port=ST.port.get(x.key);if(port)pills.appendChild(el("span",{class:"pill "+(port.cmp==="agrees"?"p-ok":"p-warn"),text:port.cmp==="agrees"?"valid on js-port-of-8dd0d3e (re-run here)":"js-port-of-8dd0d3e differs: "+port.detail}));
  else if(self.VAL&&VAL.mode==="full"&&bodyOf(x)){pills.appendChild(el("span",{class:"pill p-mute",text:"js-port-of-8dd0d3e: running…"}));VAL.validate(bodyOf(x)).then(res=>{const cmp=VAL.compare(res,true,f?codesOf(f):[]);ST.port.set(x.key,{cmp,detail:`port says ${res.valid?"valid":"invalid"} · ${codesOfRes(res).join(",")||"no codes"}`});if(ST.cur===x)renderCard(x)}).catch(e=>{ST.port.set(x.key,{cmp:"differs",detail:"port error: "+String(e&&e.message||e).slice(0,80)});if(ST.cur===x)renderCard(x)})}
  else pills.appendChild(el("span",{class:"pill p-mute",text:self.VAL&&VAL.mode==="none"?"js-port-of-8dd0d3e: not available here ("+String(VAL.reason||"").slice(0,70)+")":"js-port-of-8dd0d3e: not loaded in this view; recorded verdict shown"}));
  c.appendChild(el("div",{class:"k",text:"render passes"}));const pp=el("div",{class:"pills"});c.appendChild(pp);
  pp.appendChild(el("span",{class:"pill p-warn",text:`16.5.0 BLANK ${fmt.pct(x.nb,2)}`}));pp.appendChild(el("span",{class:"pill "+(x.has151?(x.err151?"p-bad":(x.nb151||0)<.005?"p-warn":"p-ok"):"p-mute"),text:x.has151?(x.err151?"16.5.1 could not parse":`16.5.1 ${(x.nb151||0)<.005?"BLANK":"DRAWS"} ${fmt.pct(x.nb151,2)}`):"16.5.1: no record"}));
  c.appendChild(el("div",{class:"k",text:"submit a validator warning"}));c.appendChild(el("div",{class:"warnbox",text:WARNTXT[x.c]||"Proposed warning: a scene that is valid on the schema and the semantic rules yet draws nothing in two renderer patches; the pattern is read by hand above."}));
  if(!share())c.appendChild(el("div",{class:"v",text:"fork issue link: owner to supply (private build only)"}))}
/* ---------- open ---------- */
function open(ref,opts){opts=opts||{};const x=typeof ref==="number"?ST.list[ref]:typeof ref==="string"?ST.list.find(y=>y.key===ref||y.p===ref||keyOf(y.m,y.p,y.calls||0)===ref):ref;if(!x)return null;ST.cur=x;__seven.cur=x.key;
  E.strip.querySelectorAll("button.th").forEach(b=>b.classList.toggle("sel",b.dataset.key===x.key));renderCard(x);counter("—","");ratio(null,"—");say("");line("");ST.find=null;__seven.find=null;__seven.plan=null;
  if(ST.visible)ensureInst();if(ST.inst&&!opts.noLoad)loadCur();else if(ST.inst&&opts.noLoad&&ST.loaded!==x.key)loadCur();return x}
function headerSpec(){const sc=(self.STATS&&STATS.claims&&STATS.claims["c.seven"])||{};return{title:"The dark seven",unit:`${sc.expected!=null?fmt.int(sc.expected):"?"} of ${sc.of!=null?fmt.int(sc.of):"?"} valid finals draw nothing in X_ITE 16.5.0 and 16.5.1 · the stage is MEASURED only here`,
  stamps:{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline"},grade:"C",
  honesty:"raw bytes, no staging in this section · counted frames X_ITE 16.5.0 and 16.5.1 offline · live frame this browser (not counted) · 7 of 178, each opened and read by hand · Confirmed for these scenes, the H-Anim pattern Suspected (one case)"}}
function mount(sec){ST.sec=sec;sectionHeader(sec,headerSpec());const sb=sec.querySelector(".sb");if(!sb)return;sb.textContent="";if(self.HEROUI&&HEROUI.stagedManifest)HEROUI.stagedManifest().then(m=>{if(m&&ST.cur)renderCard(ST.cur)});
  E.ph=el("div",{class:"ph legend"});E.strip=el("div",{class:"sstrip"});
  E.host=el("div",{class:"shost",style:{position:"absolute",inset:"0"}});E.badge=el("div",{class:"sbadge m",text:"MEASURED · raw bytes · own/default viewpoint · headlight · the X_ITE instance is created when this section scrolls into view"});
  E.cnum=el("span",{text:"—"});E.csmall=el("small",{text:""});E.counter=el("div",{class:"scounter"},[E.cnum,E.csmall]);
  E.rnum=el("span",{text:"this browser: —"});E.rsmall=el("small",{text:""});E.ratio=el("div",{class:"sratio m"},[E.rnum,E.rsmall]);E.msg=el("div",{class:"smsg m"});E.line=el("div",{class:"smsg m",style:{top:"auto",bottom:"96px",color:"var(--warn)"}});
  E.stage=el("div",{class:"sstage"},[E.host,E.badge,E.counter,E.ratio,E.msg,E.line]);
  E.ctl=el("div",{class:"sctl"},[el("button",{class:"primary",text:"FIND IT",title:"dolly the render-time camera to the geometry the validator passed",onclick:()=>SEVEN.findIt()}),el("button",{text:"RESET",onclick:()=>SEVEN.reset()}),el("button",{text:"MEASURE HERE",title:"the counted path: STAGE.measure on the same bytes, 192×144",onclick:()=>SEVEN.measure()}),
    el("span",{class:"legend",text:"MEASURED mode forced: no lights, ground or camera injected; the point is what the renderer saw. The dolly is one explicit camera move, labelled."})]);
  E.card=el("div",{class:"card scard"});
  sb.append(E.ph,E.strip,el("div",{class:"sgrid"},[el("div",null,[E.stage,E.ctl]),E.card]));
  /* observed on the stage box, not the section: IO keeps one callback per element and the LOOP panel below observes the section */
  IO.observe(E.stage,v=>{ST.visible=v;if(v){if(ST.leave){ST.leave();ST.leave=null}ensureInst()}else{if(ST.leave)ST.leave();ST.leave=later(()=>{ST.leave=null;if(!ST.visible)disposeInst()},2500)}},{rootMargin:"64px"});
  LOOP.register({name:"seven",bit:LOOP.bits.DATA,always:true,rateHz:4,budgetMs:1,draw(){if(ST.visible&&!ST.inst&&self.X3D)ensureInst()}});   /* no el: see 14-morph (RAIL.init observes every section; IO keeps one callback per element) */
  CLAIMS.define("seven.ids",{label:"the dark seven, by key",unit:"finals valid on fork@eb4b4b4 whose X_ITE 16.5.0 frame is under 0.5% nonblank",needs:["live.core"],expected:statIds().sort(),grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline",text:v=>`${v.length} scenes`,
    compute(){return LIVE.filter(rule150).map(i=>keyOf(i.m,i.p,i.A.length)).sort()}});
  CLAIMS.define("seven.pass151",{label:"of those, blank in the 16.5.1 pass too",unit:"renders.151 nonblank under 0.5%",needs:["live.core","renders.151"],expected:self.STATS&&STATS.claims&&STATS.claims["c.seven"]?STATS.claims["c.seven"].expected:undefined,grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.1 offline",
    compute(){return LIVE.filter(rule150).filter(i=>{const r=R151.live[keyOf(i.m,i.p,i.A.length)];return !!r&&!r.err&&(r.nb||0)<.005}).length}});
  E.ph.appendChild(claimChip("seven.ids",{size:"s",label:"keys match the record"}));E.ph.appendChild(claimChip("seven.pass151",{size:"s",label:"blank in 16.5.1 too"}));E.ph=el("div",{class:"legend"});E.strip.before(E.ph);
  if(self.VAL&&VAL.on)VAL.on(()=>{if(ST.cur)renderCard(ST.cur)});build()}
function onData(name){if(name==="live.core"||name==="live.bodies"||name==="live.jpg"||name==="renders.151")build()}
const SEVEN={get list(){return ST.list},ids:()=>ST.list.map(x=>x.key),open,findIt,reset,measure,cur:()=>ST.cur,state:ST};
SECTIONS.register({id:"seven",part:"live.bodies",mount(sec){try{mount(sec)}catch(e){console.error("seven mount",e);if(self.BOOT)BOOT.error(e,"seven mount")}},onData});
__seven.dispose=disposeInst;Object.assign(self,{SEVEN,BLANKWHY,__seven});
})();
