/* 08-stage.js — the X_ITE stage (SPEC §5, S2, rule 4). Wave 1 = the MEASURE path and a plain unstaged SHOW loader; M3 adds the rig
   (applyRig / tearDownRig / orbit / dolly / cam / projectPoint / show2) behind the stubs below without changing the surface.
   Globals: STAGE, sampleFrame (window; the v3 test hook), __stage.
   Ported from v3: watchFrames (lines 846–850), clearView (851–853), sampleFrame (854–857: a setTimeout chain instead of v3's interval timer), init3dNow pixels (860–866),
   show3d's load sequence and its no-frame / nothing-drawable / slow logic (651–676), tapConsole (647–649).
   Rules: samples are taken inside X_ITE's finishEvents callback (a timer reads a cleared buffer); viewAll(0) after replaceWorld; nonblank = fraction of all pixels
   differing from the dominant colour by > 48; blank < 0.005. The measure canvas is never styled, rigged or sampled by anyone else (__stage.measure.rigNodes stays 0).
   Test hooks: window.sampleFrame (override to simulate a slow renderer), __stage, STAGE.measure.show(xml) → R, STAGE.ready.
   M3 (wave 2, story agent) implemented the documented stubs in place: setStaged, orbit, reset, dolly, cam, applyRig, tearDownRig, projectPoint, show2 (see the M3 block below). */
(function(){
"use strict";
const EMPTY="<X3D profile='Interchange' version='4.0'><Scene/></X3D>";
const DROP_RE=/Unknown node type|Unknown named or imported node|Container field|insufficient component/i;
const __stage={measure:{rigNodes:0,loads:0,last:null,ready:false,err:"",pending:0},show:{staged:false,loads:0,lastHash:null,ready:false,err:"",frozen:false}};
/* one console tap for the life of the page (v3 647): what X_ITE says about the load in flight */
let SAID=null,tapped=false;
function tapConsole(){if(tapped)return;tapped=true;const wrap=f=>(...a)=>{if(SAID&&SAID.length<6){const t=a.map(String).join(" ").replace(/\s+/g," ");if(!/font|stylesheet|mikktspace|Content Security|Fetch API/i.test(t))SAID.push(t.slice(0,260))}f.apply(console,a)};console.error=wrap(console.error);console.warn=wrap(console.warn)}
function watchFrames(B,grab){const F=typeof B.finishEvents==="function"?B.finishEvents():B.endEvents(),key=Symbol(),w={on:true,t0:null,n:0,first:null,last:null,best:null,series:[],ns:0,lastS:-1e9};
  F.addFieldCallback(key,()=>{if(!w.on||w.t0===null)return;const t=Math.round(performance.now()-w.t0);w.n++;if(w.first===null)w.first=t;w.last=t;
    if(w.ns<20&&(w.ns<8||t-w.lastS>=150)){w.ns++;w.lastS=t;try{const g=grab();w.series.push(g.nonblank);if(!w.best||g.nonblank>w.best.nonblank)w.best=g}catch(e){}}});
  w.start=()=>{w.t0=performance.now()};w.stop=()=>{w.on=false;try{F.removeFieldCallback(key)}catch(e){}};return w}
/* X_ITE keeps showing the previous world's last frame while a new one is swapped in: clear first (v3 851) */
async function clearView(B){const e=await B.createX3DFromString(EMPTY),w0=watchFrames(B,()=>({nonblank:0}));w0.start();await B.replaceWorld(e);
  const t=performance.now();while(w0.n<2&&performance.now()-t<400)await later(20);w0.stop()}
/* resolves once the watcher has a sample (plus 350 ms for more frames), or {err:"no frame"} after ms; tests replace this to simulate a slow renderer */
self.sampleFrame=(w,ms=2500)=>new Promise(resolve=>{if(!w){resolve({err:"no frame"});return}const t0=performance.now(),out=()=>({nonblank:w.best.nonblank,frames:w.n,series:w.series.slice()});let seen=null;
  const poll=()=>{const now=performance.now();if(w.best&&seen===null)seen=now;
    if(seen!==null&&now-seen>=350)resolve(out());else if(now-t0>=ms)resolve(w.best?out():{err:"no frame"});else setTimeout(poll,40)};setTimeout(poll,40)});
function pixelsOf(B){const cv=B.getCanvas(),w=cv.width,h=cv.height,t2=document.createElement("canvas");t2.width=w;t2.height=h;const cx=t2.getContext("2d",{willReadFrequently:true});cx.drawImage(cv,0,0);const d=cx.getImageData(0,0,w,h).data;
  const cnt=new Map();for(let i=0;i<d.length;i+=16){const k=(d[i]>>3)<<10|(d[i+1]>>3)<<5|(d[i+2]>>3);cnt.set(k,(cnt.get(k)||0)+1)}let bg=0,best=-1;for(const[k,v]of cnt)if(v>best){best=v;bg=k}
  const r0=(bg>>10&31)<<3,g0=(bg>>5&31)<<3,b0=(bg&31)<<3;let diff=0,n=0;for(let i=0;i<d.length;i+=4){n++;if(Math.abs(d[i]-r0)+Math.abs(d[i+1]-g0)+Math.abs(d[i+2]-b0)>48)diff++}return{nonblank:+(diff/n).toFixed(4)}}
async function makeCanvas(mount,opts){if(!self.X3D)throw new Error("X_ITE not loaded (xite/x_ite.min.js)");
  const c=document.createElement("x3d-canvas");["splashScreen","contextMenu","notifications","timings"].forEach(a=>c.setAttribute(a,"false"));if(opts&&opts.attrs)for(const k in opts.attrs)c.setAttribute(k,opts.attrs[k]);mount.appendChild(c);
  for(let i=0;i<120&&!c.browser;i++)await later(50);if(!c.browser)throw new Error("x3d-canvas gave no browser in 6 s");
  try{if(typeof XCSS==="string"&&XCSS){const st=document.createElement("style");st.textContent=XCSS;c.shadowRoot.appendChild(st)}const br=c.shadowRoot.querySelector(".x_ite-private-browser");if(br)br.style.display="block"}catch(e){}
  try{if(opts&&opts.autoUpdate===false)c.browser.setBrowserOption("AutoUpdate",false)}catch(e){}
  return c}
/* ---------- MEASURE ---------- */
const M={ready:null,browser:null,canvas:null,busy:false,token:0,queue:Promise.resolve(),
  pixels:()=>pixelsOf(M.browser),
  show(xml,opts){opts=opts||{};const tk=++M.token;__stage.measure.pending=(__stage.measure.pending||0)+1;const run=()=>measureNow(xml,opts,tk);const p=M.queue.then(run,run);M.queue=p.catch(()=>{});p.finally(()=>{__stage.measure.pending--}).catch(()=>{});return p}};  /* __stage.measure.pending: loads queued or running (the perf gate waits for 0: each load is a SwiftShader shader compile) */  /* FIFO: every caller gets its own R; a newer load never cancels an older one (integration: hero, raster, seven and the inspector all measure) */
async function measureNow(xml,opts,tk){
  if(!M.browser)await M.ready;if(!M.browser)return{err:"X_ITE not available: "+(__stage.measure.err||"no browser"),nb:null,frames:0,series:[],msgs:[],noFrame:true,ms:0};
  
  const B=M.browser,t0=performance.now(),said=[],w=watchFrames(B,M.pixels);SAID=said;tapConsole();M.busy=true;__stage.measure.loads++;
  const R={nb:null,frames:0,series:[],first:null,last:null,msgs:said,err:null,noFrame:false,slow:false,ms:0,nodes:null,cancelled:false,renderer:self.ENV?ENV.renderer:null};
  try{await clearView(B);
    const scn=await B.createX3DFromString(stripProv(xml));
    w.start();await B.replaceWorld(scn);try{B.getActiveLayer().viewAll(0)}catch(e){}
    await later(650);
    let px=await self.sampleFrame(w);const drop=said.some(t=>DROP_RE.test(t)),expectNone=!!opts.expectNone;let nf=px.err==="no frame";
    /* no frame is only read as "nothing drawable" when something says so (dropped nodes, or the record); otherwise the renderer may just be slow here, so wait longer */
    if(nf&&!expectNone&&!drop){px=await self.sampleFrame(w,opts.timeoutMs||12000);nf=px.err==="no frame";R.slow=nf}
    R.noFrame=nf;R.ms=Math.round(performance.now()-t0);try{R.nodes=B.currentScene.rootNodes.length}catch(e){}
    if(!nf){R.nb=px.nonblank;R.frames=px.frames;R.series=px.series}R.first=w.first;R.last=w.last;R.frames=w.n;R.dropped=drop;
    R.kind=nf&&R.slow?"no frame yet":nf||(R.nb<.005&&drop)?"nothing drawable":R.nb<.005?"blank frame":"draws"}
  catch(e){R.err=String(e&&e.message||e).replace(/'http[^']*'/,"the string").slice(0,200);R.kind="unparseable";R.ms=Math.round(performance.now()-t0);try{await B.replaceWorld(await B.createX3DFromString(EMPTY))}catch(_){}}
  finally{w.stop();if(SAID===said)SAID=null;M.busy=false}
  R.msgs=said.map(t=>t.replace(/^XML Parser:\s*/,"").replace(/\.?\s*You probably have insufficient.*$/,""));__stage.measure.last=R;return R}
/* ---------- SHOW (plain loader in wave 1; M3 stages it) ---------- */
const SH={ready:null,browser:null,canvas:null,staged:false,token:0,lastHash:null,scene:null,loads:0,
  async load(xml,opts){opts=opts||{};if(!SH.browser)await SH.ready;if(!SH.browser)return{ok:false,err:"X_ITE not available: "+(__stage.show.err||"no browser")};
    const tk=++SH.token,B=SH.browser,t0=performance.now();SH.scene=opts.scene||null;SH.staged=false;__stage.show.staged=false;
    try{STAGE.tearDownRig();await clearView(B);if(tk!==SH.token)return{ok:false,cancelled:true};
      const scn=await B.createX3DFromString(stripProv(xml));if(tk!==SH.token)return{ok:false,cancelled:true};await B.replaceWorld(scn);try{B.getActiveLayer().viewAll(0)}catch(e){}
      SH.lastHash=contentHash(xml);__stage.show.lastHash=SH.lastHash;__stage.show.loads=++SH.loads;
      if(opts.staged&&self.FX&&FX.level>0){const r=STAGE.applyRig(B,xml,opts);SH.staged=!!r;__stage.show.staged=SH.staged}
      badge();SH.freezeSoon(tk);return{ok:true,ms:Math.round(performance.now()-t0),staged:SH.staged}}
    catch(e){if(tk!==SH.token)return{ok:false,cancelled:true};const err=String(e&&e.message||e).slice(0,200);txt("stageMsg","X_ITE refused this scene: "+err);try{await B.replaceWorld(await B.createX3DFromString(EMPTY))}catch(_){}return{ok:false,err}}},
  /* M3: apply the rig to the loaded world (lights only at fx 0) or tear it down; thaws a frozen stage for the change and re-freezes it (fx 0) */
  setStaged(on,opts){if(!SH.browser)return false;if(on){if(!SH.staged){const r=STAGE.applyRig(SH.browser,null,opts||{});SH.staged=!!r}}else{STAGE.tearDownRig(SH.browser);SH.staged=false}
    __stage.show.staged=SH.staged;badge();if(SH.frozen){SH.resume();SH.freezeSoon(SH.token)}return SH.staged},
  orbit(on){/* M3: page-side orbit of __cam at rAF (fx ≥ 1 only; paused by drag, resumed by double-click) */const r=rigOf(SH.browser);if(!r||!r.cam)return false;return orbitOn(r,on)},
  reset(){/* M3: back to the staged camera (clears the drag offsets); without a rig = viewAll(0) as in wave 1 */return rigReset(SH)},
  dolly(target,ms){/* M3: render-time camera move of __cam over ms (a 2-frame cut at fx 0 / reduced motion); resolves true when the pose is reached */return camMove(SH,target,ms)},
  cam(keyframes){/* M3: a sequence of dolly targets [{position, orientation|lookAt, ms}] */return camPath(SH,keyframes)},
  pause(){try{SH.browser&&SH.browser.endUpdate()}catch(e){}},resume(){SH.frozen=false;__stage.show.frozen=false;try{SH.browser&&SH.browser.beginUpdate()}catch(e){}badge()},
  /* fx 0 (software GL / webdriver / phone): X_ITE's own render loop would eat the rAF budget (5 fps under SwiftShader), so 1.5 s after a load the
     stage keeps its last frame and stops rendering; the badge says so; orbit/resume (M3 wiring, STAGE.show.resume()) thaws it. Never on fx > 0. */
  freezeSoon(tk){if(!(self.FX&&FX.level===0))return;setTimeout(()=>{if(tk!==SH.token||!SH.browser)return;try{SH.browser.endUpdate();SH.frozen=true;__stage.show.frozen=true;badge()}catch(e){}},1500)},
  snapshot(){return new Promise(res=>{try{SH.browser.getCanvas().toBlob(b=>res(b||null),"image/png")}catch(e){res(null)}})}};
function badge(){const b=$("stageBadge");if(!b)return;const gl=self.ENV&&ENV.gl?ENV.gl:"?";txt(b,(SH.staged?"STAGED · lights + ground + camera added at render time · nothing written":"MEASURED · raw bytes · own/default viewpoint · headlight")+` · ${gl} · X_ITE 16.5.0 in this browser`+(SH.frozen?" · STATIC FRAME (software GL: rendering paused after load)":""))}
/* ---------- M3 (story agent, wave 2): the rig, the render-time camera, projectPoint and the show2 factory (SPEC §5, S2–S4; ARCHITECTURE §4 / 08, §8) ----------
   Everything below is render-time SAI work on a loaded world: nodes are created through currentScene.createNode and hung under Group DEF="__stage"
   (lights, a bound NavigationInfo with the headlight off, a Background when the scene has none, a ground Shape at fx ≥ 1) plus a Viewpoint DEF="__cam";
   nothing is ever serialised, hashed or sampled from this canvas (every number comes from STAGE.measure). tearDownRig removes the rig before the next
   replaceWorld. Camera moves (orbit, dolly, cam) run page-side in one LOOP panel ("stageRig", lazily registered) by writing __cam.position/orientation.
   fx 0 interplay: a frozen instance (endUpdate after load) is thawed with inst.resume() before a move and re-frozen with inst.freezeSoon(inst.token)
   when the move ends; at fx 0 a move is a 2-frame cut (same end values), there is no orbit, and the rig is lights only (no ground, no camera).
   Spike result (24 Oct, X_ITE 16.5.0): getActiveLayer() returns the internal layer node; layer.getViewpoint() the bound viewpoint with getUserPosition /
   getUserOrientation / getViewMatrix / getProjectionMatrixWithLimits(near, far, viewport); matrices are row-vector (v · M, translation at 12..14);
   a Box3 class is reachable as createNode("Group").getValue().childBBox.constructor and layer.getBBox(box) gives the union bbox; so projectPoint works
   and the floor ribbon can project. A WebGL read-back outside X_ITE's finishEvents callback is black (even with preserveDrawingBuffer), so snapshot()
   and pixels() grab inside that callback. EnvironmentLight exists in 16.5.0 but an SH-only light without textures is unverified on a GPU, so the
   three-DirectionalLight rig is the default (STAGE.rigOpts.env = true switches, documented as unverified).
   Test hooks: __stage.show.rig (summary of the live rig), __stage.show.orbit, __stage.show2 {created, live, loads}, STAGE.rigOpts, STAGE.sceneFacts(B). */
const LIGHTS=[[-.6,-1,-.4,.9],[.8,-.3,.6,.35],[.2,.6,-1,.5]];   /* key, fill, rim: direction xyz, intensity (SPEC §5) */
const RIGS=new WeakMap(),RIGSET=new Set(),JOBS=new Set(),HOOKED=new WeakSet();let Box3C=null,panelOn=false,groundUrl=null;
const rigOpts={env:false,orbitPeriodMs:28000,breathDeg:6,ellipse:1.35};
const fxLevel=()=>self.FX?FX.level:2,reduced=()=>fxLevel()===0||(self.ENV&&ENV.reducedMotion);
/* vectors and quaternions (page math; X_ITE's internal classes are not exported) */
const V={sub:(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],add:(a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]],scale:(a,s)=>[a[0]*s,a[1]*s,a[2]*s],len:a=>Math.hypot(a[0],a[1],a[2]),
  norm:a=>{const l=Math.hypot(a[0],a[1],a[2])||1;return[a[0]/l,a[1]/l,a[2]/l]},cross:(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],dot:(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],
  lerp:(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t],of:v=>v?[+v.x||0,+v.y||0,+v.z||0]:[0,0,0]};
const Q={fromAxisAngle(ax,ang){const n=V.norm(ax),s=Math.sin(ang/2);return[n[0]*s,n[1]*s,n[2]*s,Math.cos(ang/2)]},
  toAxisAngle(q){let[x,y,z,w]=q;const l=Math.hypot(x,y,z,w)||1;x/=l;y/=l;z/=l;w/=l;const ang=2*Math.acos(Math.max(-1,Math.min(1,w))),s=Math.sqrt(Math.max(0,1-w*w));return s<1e-6?[0,1,0,0]:[x/s,y/s,z/s,ang]},
  slerp(a,b,t){let d=a[0]*b[0]+a[1]*b[1]+a[2]*b[2]+a[3]*b[3];if(d<0){b=b.map(v=>-v);d=-d}if(d>.9995){const r=a.map((v,i)=>v+(b[i]-v)*t),l=Math.hypot(r[0],r[1],r[2],r[3])||1;return r.map(v=>v/l)}
    const th=Math.acos(d),s=Math.sin(th),wa=Math.sin((1-t)*th)/s,wb=Math.sin(t*th)/s;return a.map((v,i)=>v*wa+b[i]*wb)},
  /* X3D's default camera looks down -Z with +Y up; the quaternion that turns that frame to look from eye at target */
  lookAt(eye,target,up){const f=V.norm(V.sub(target,eye));let u=up||[0,1,0];if(Math.abs(V.dot(f,u))>.999)u=Math.abs(f[2])<.9?[0,0,1]:[1,0,0];const z=V.scale(f,-1),x=V.norm(V.cross(u,z)),y=V.cross(z,x);
    const m00=x[0],m01=y[0],m02=z[0],m10=x[1],m11=y[1],m12=z[1],m20=x[2],m21=y[2],m22=z[2],tr=m00+m11+m22;
    if(tr>0){const s=Math.sqrt(tr+1)*2;return[(m21-m12)/s,(m02-m20)/s,(m10-m01)/s,s/4]}if(m00>m11&&m00>m22){const s=Math.sqrt(1+m00-m11-m22)*2;return[s/4,(m01+m10)/s,(m02+m20)/s,(m21-m12)/s]}
    if(m11>m22){const s=Math.sqrt(1+m11-m00-m22)*2;return[(m01+m10)/s,s/4,(m12+m21)/s,(m02-m20)/s]}const s=Math.sqrt(1+m22-m00-m11)*2;return[(m02+m20)/s,(m12+m21)/s,s/4,(m10-m01)/s]},
  ofRot:r=>r?Q.fromAxisAngle([+r.x||0,+r.y||0,+r.z||0],+r.angle||0):[0,0,0,1]};
const easeIO=t=>t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
function hexRgb(h){const m=/^#?([0-9a-f]{6})$/i.exec(String(h||"").trim());if(!m)return[.012,.02,.04];const n=parseInt(m[1],16);return[(n>>16&255)/255,(n>>8&255)/255,(n&255)/255]}
function box3(sc){if(Box3C)return Box3C;try{Box3C=sc.createNode("Group").getValue().childBBox.constructor}catch(e){Box3C=null}return Box3C}
/* what the loaded world contains (SAI walk over node types; the opt-outs of SPEC §5 are read from the graph, not from a regex) */
function sceneFacts(B){const F={geo:false,hanim:false,prox:false,proxBox:null,navNone:false,jumpFalse:false,hasVp:false,vpType:null,hasBg:false,hasNav:false,navType:null,headlight:true,lights:0,text:false,shapes:0,nodes:0,err:null};
  try{const sc=B.currentScene,C=self.X3D.X3DConstants,seen=new Set();
    const walk=(n,d)=>{if(!n||d>14||seen.has(n))return;seen.add(n);let t="";try{t=n.getNodeTypeName()}catch(e){return}F.nodes++;
      if(/^Geo/.test(t))F.geo=true;if(/^HAnim/.test(t))F.hanim=true;
      if(t==="ProximitySensor"){F.prox=true;try{F.proxBox={center:V.of(n.center),size:V.of(n.size)}}catch(e){}}
      else if(t==="NavigationInfo"){F.hasNav=true;try{const ty=Array.from(n.type,String);F.navType=ty;if(ty.some(x=>/NONE/i.test(x)))F.navNone=true;F.headlight=n.headlight!==false}catch(e){}}
      else if(/Viewpoint$/.test(t)){if(!F.hasVp)F.vpType=t;F.hasVp=true;try{if(n.jump===false)F.jumpFalse=true}catch(e){}}
      else if(/Background$/.test(t))F.hasBg=true;else if(/Light$/.test(t))F.lights++;else if(t==="Text")F.text=true;else if(t==="Shape")F.shapes++;
      if(t==="Appearance"||t==="Material"||/Interpolator$|Sensor$|^Metadata/.test(t))return;
      for(const f of n.getFieldDefinitions()){const dt=f.dataType;if(dt===C.SFNode){try{const c=n[f.name];if(c)walk(c,d+1)}catch(e){}}else if(dt===C.MFNode){try{for(const c of n[f.name])walk(c,d+1)}catch(e){}}}};
    for(const n of sc.rootNodes)walk(n,0)}catch(e){F.err=String(e&&e.message||e).slice(0,120)}
  return F}
/* union bbox of what the layer renders: {size, center, min, max, empty} in the scene's coordinates (local when a GeoOrigin is present, geocentric otherwise) */
function layerBBox(B){try{const sc=B.currentScene,L=B.getActiveLayer(),Bx=box3(sc);if(!Bx)return null;const bb=new Bx();L.getBBox(bb);if(bb.isEmpty())return{empty:true,size:[0,0,0],center:[0,0,0],min:[0,0,0],max:[0,0,0]};
  const s=V.of(bb.size),c=V.of(bb.center);return{empty:false,size:s,center:c,min:V.sub(c,V.scale(s,.5)),max:V.add(c,V.scale(s,.5))}}catch(e){return null}}
/* Shapes that X_ITE actually places: reached through the rendered fields only (children; Switch's whichChoice; HAnimHumanoid's skeleton and skin), with a non-empty bbox */
function placedShapes(B){const out={shapes:0,placed:0,unreached:0,err:null};try{const sc=B.currentScene,C=self.X3D.X3DConstants,Bx=box3(sc),seen=new Set(),all=new Set();
  const count=(n,d,rendered)=>{if(!n||d>16)return;let t="";try{t=n.getNodeTypeName()}catch(e){return}
    if(t==="Shape"){if(!all.has(n)){all.add(n);out.shapes++}if(rendered&&!seen.has(n)){seen.add(n);try{const bb=new Bx();n.getValue().getBBox(bb);if(!bb.isEmpty())out.placed++}catch(e){}}return}
    const fields=n.getFieldDefinitions();const kids=name=>{try{const v=n[name];return v==null?[]:(typeof v[Symbol.iterator]==="function"&&typeof v!=="string")?Array.from(v):[v]}catch(e){return[]}};
    let renderFields=null;if(t==="HAnimHumanoid")renderFields=["skeleton","skin"];else if(t==="Switch"){let w=-1;try{w=+n.whichChoice}catch(e){}const ch=kids("children");ch.forEach((c,i)=>count(c,d+1,rendered&&i===w));renderFields=[]}
    else if(t==="Inline"||t==="Appearance"||t==="Material"||/Interpolator$|Sensor$|^Metadata|Viewpoint$|^Geo(Origin)$/.test(t))renderFields=[];
    for(const f of fields){if(f.dataType!==C.SFNode&&f.dataType!==C.MFNode)continue;const isRender=renderFields?renderFields.includes(f.name):f.name==="children"||f.name==="child"||f.name==="geometry"||f.name==="shape";
      for(const c of kids(f.name))count(c,d+1,rendered&&isRender)}};
  for(const n of sc.rootNodes)count(n,0,true);out.unreached=out.shapes-seen.size}catch(e){out.err=String(e&&e.message||e).slice(0,120)}return out}
function groundTexture(){if(groundUrl)return groundUrl;try{const c=document.createElement("canvas");c.width=c.height=64;const g=c.getContext("2d"),gr=g.createRadialGradient(32,32,2,32,32,32),[r,gg,b]=hexRgb(cssv("--etch")).map(x=>Math.round(x*255));
  gr.addColorStop(0,`rgba(${r},${gg},${b},.5)`);gr.addColorStop(.55,`rgba(${r},${gg},${b},.18)`);gr.addColorStop(1,`rgba(${r},${gg},${b},0)`);g.fillStyle=gr;g.fillRect(0,0,64,64);groundUrl=c.toDataURL("image/png")}catch(e){groundUrl=null}return groundUrl}
function instOf(x){return x&&x.browser!==undefined&&x.resume?x:(x===SH.browser?SH:null)}
function rigOf(B){return B?RIGS.get(B)||null:null}
function rigSummary(r){return r?{lights:r.lights,ground:r.ground,bg:r.bg,nav:r.nav,camera:r.camera,orbit:r.orbit,lightsOnly:r.lightsOnly,reasons:r.reasons.slice(),bbox:r.bbox?r.bbox.size.map(x=>+x.toFixed(3)):null,facts:{geo:r.facts.geo,hanim:r.facts.hanim,prox:r.facts.prox,ownViewpoint:r.facts.hasVp,shapes:r.facts.shapes}}:null}
/* the camera node: bound at the pose the stage shows now (no visible jump), or at the author's own Viewpoint pose when the scene has one (the measured frame keeps viewAll) */
function ensureCam(rig,authored){if(rig.cam)return rig.cam;const B=rig.browser,sc=B.currentScene,L=B.getActiveLayer(),vp=L.getViewpoint();let p,o,c;
  if(authored){p=V.of(vp.getPosition());o=Q.ofRot(vp.getOrientation());c=V.of(vp.getCenterOfRotation());if(!V.len(c)&&rig.bbox&&!rig.bbox.empty)c=rig.bbox.center.slice()}
  else{p=V.of(vp.getUserPosition());o=Q.ofRot(vp.getUserOrientation());c=V.of(vp.getUserCenterOfRotation())}
  const cam=sc.createNode("Viewpoint");cam.description="__cam: render-time stage camera, never written";const aa=Q.toAxisAngle(o);
  cam.position=new X3D.SFVec3f(p[0],p[1],p[2]);cam.orientation=new X3D.SFRotation(aa[0],aa[1],aa[2],aa[3]);cam.centerOfRotation=new X3D.SFVec3f(c[0],c[1],c[2]);
  try{const fov=vp.getFieldOfView();if(typeof fov==="number"&&fov>0&&fov<Math.PI)cam.fieldOfView=fov}catch(e){}
  sc.addNamedNode("__cam",cam);sc.addRootNode(cam);cam.set_bind=true;rig.cam=cam;rig.pose={position:p,q:o,center:c};rig.base={position:p.slice(),q:o.slice(),center:c.slice()};return cam}
function camOnlyRig(B,inst){let rig=rigOf(B);if(rig)return rig;rig={browser:B,inst:inst||null,group:null,cam:null,facts:sceneFacts(B),lightsOnly:true,camOnly:true,lights:0,ground:false,bg:false,nav:false,camera:true,orbit:false,orbitPaused:false,reasons:["camera only (no lights, no ground): a dolly on a measured stage"],bbox:layerBBox(B),pose:null,base:null};
  ensureCam(rig,false);RIGS.set(B,rig);RIGSET.add(rig);return rig}
function setPose(rig,p,q,clear){if(!rig.cam)return;const aa=Q.toAxisAngle(q);try{rig.cam.position=new X3D.SFVec3f(p[0],p[1],p[2]);rig.cam.orientation=new X3D.SFRotation(aa[0],aa[1],aa[2],aa[3]);rig.pose.position=p.slice();rig.pose.q=q.slice();
  if(clear){const vp=rig.browser.getActiveLayer().getViewpoint();if(vp.setUserPosition){vp.setUserPosition(new X3D.SFVec3f(p[0],p[1],p[2]).getValue());vp.setUserOrientation(new X3D.SFRotation(aa[0],aa[1],aa[2],aa[3]).getValue())}}}catch(e){}}
function currentPose(B){try{const vp=B.getActiveLayer().getViewpoint();return{position:V.of(vp.getUserPosition()),q:Q.ofRot(vp.getUserOrientation()),center:V.of(vp.getUserCenterOfRotation())}}catch(e){return null}}
function rigApply(B,xml,opts){opts=opts||{};if(!B||!B.currentScene||!self.X3D)return null;tearDown(B);const sc=B.currentScene,F=sceneFacts(B);if(F.err&&!F.nodes)return null;
  const fx=fxLevel(),lightsOnly=fx===0||!!opts.lightsOnly,rig={browser:B,inst:opts.inst||instOf(B),group:null,cam:null,facts:F,lightsOnly,camOnly:false,lights:0,ground:false,bg:false,nav:false,camera:false,orbit:false,orbitPaused:false,orbitAllowed:false,pose:null,base:null,bbox:null,reasons:[],t0:performance.now()};
  try{const group=sc.createNode("Group");sc.addNamedNode("__stage",group);rig.group=group;
    if(F.hanim)rig.reasons.push("HAnim scene keeps its lights");
    else{if(rigOpts.env){const e=sc.createNode("EnvironmentLight");e.intensity=1;e.global=true;group.children.push(e);rig.lights=1;rig.reasons.push("EnvironmentLight (SH only, unverified on GPU)")}
      else LIGHTS.forEach(([x,y,z,i])=>{const d=sc.createNode("DirectionalLight");d.direction=new X3D.SFVec3f(x,y,z);d.intensity=i;d.ambientIntensity=.08;d.global=true;group.children.push(d);rig.lights++});
      if(F.prox)rig.reasons.push("ProximitySensor scene keeps the headlight");
      else if(F.headlight!==false){const nav=sc.createNode("NavigationInfo");nav.headlight=false;if(F.navType&&F.navType.length){try{nav.type=new X3D.MFString(...F.navType)}catch(e){}}group.children.push(nav);rig.nav=true;rig._nav=nav}}
    rig.bbox=layerBBox(B);
    if(!lightsOnly){const bb=rig.bbox;
      if(bb&&!bb.empty&&bb.size.every(Number.isFinite)&&Math.max(...bb.size)<5e3&&!F.geo){const url=groundTexture();const ext=Math.max(...bb.size),s=Math.max(40,3*ext);
        const sh=sc.createNode("Shape"),ap=sc.createNode("Appearance"),mt=sc.createNode("Material"),rc=sc.createNode("Rectangle2D"),tr=sc.createNode("Transform");
        mt.diffuseColor=new X3D.SFColor(.35,.4,.48);mt.transparency=.15;ap.material=mt;if(url){const tx=sc.createNode("ImageTexture");tx.url=new X3D.MFString(url);ap.texture=tx}
        rc.size=new X3D.SFVec2f(s,s);rc.solid=false;sh.appearance=ap;sh.geometry=rc;tr.translation=new X3D.SFVec3f(bb.center[0],bb.min[1]-.01,bb.center[2]);tr.rotation=new X3D.SFRotation(1,0,0,-Math.PI/2);tr.children.push(sh);group.children.push(tr);rig.ground=true}
      else rig.reasons.push(F.geo?"Geo scene: no ground":"no finite bbox: no ground");
      if(!F.hasBg){const bg=sc.createNode("Background");const c=hexRgb(cssv("--stage-bg"));bg.skyColor=new X3D.MFColor(new X3D.SFColor(c[0],c[1],c[2]));group.children.push(bg);rig._bg=bg;rig.bg=true}}
    sc.addRootNode(group);
    if(rig._nav)rig._nav.set_bind=true;if(rig._bg)rig._bg.set_bind=true;
    if(lightsOnly)rig.reasons.push(fx===0?"fx 0: lights only, no ground, no camera, no orbit":"lights only by request");
    else if(F.geo)rig.reasons.push("Geo scene: no camera injection");else if(F.navNone||F.jumpFalse)rig.reasons.push("scene drives its own camera (NavigationInfo NONE or jump=false)");
    else{ensureCam(rig,F.hasVp);rig.camera=true;rig.orbitAllowed=fx>0&&(!F.hasVp||!!opts.orbitAnyway);
      if(F.hasVp&&!opts.orbitAnyway)rig.reasons.push("own Viewpoint ("+F.vpType+"): pose kept, orbit on request");
      if(rig.orbitAllowed&&opts.orbit!==false)orbitOn(rig,true)}
    RIGS.set(B,rig);RIGSET.add(rig);if(B===SH.browser){__stage.show.rig=rigSummary(rig);__stage.show.orbit=rig.orbit}return rig}
  catch(e){rig.err=String(e&&e.message||e);console.warn("rig",e);try{tearDown(B)}catch(_){}return null}}
function tearDown(B){B=B||SH.browser;const rig=B?RIGS.get(B):null;if(!rig)return;for(const j of JOBS)if(j.rig===rig){JOBS.delete(j);try{j.resolve(false)}catch(e){}}
  try{const sc=B.currentScene;if(rig._nav)try{rig._nav.set_bind=false}catch(e){}if(rig._bg)try{rig._bg.set_bind=false}catch(e){}
    if(rig.cam){try{rig.cam.set_bind=false}catch(e){}try{sc.removeRootNode(rig.cam)}catch(e){}try{sc.removeNamedNode("__cam")}catch(e){}}
    if(rig.group){try{sc.removeRootNode(rig.group)}catch(e){}try{sc.removeNamedNode("__stage")}catch(e){}}}catch(e){}
  RIGS.delete(B);RIGSET.delete(rig);if(B===SH.browser){__stage.show.rig=null;__stage.show.orbit=false}}
/* ---- the one panel: orbit and camera tweens ---- */
function ensurePanel(){if(panelOn||!self.LOOP)return;panelOn=true;LOOP.register({name:"stageRig",bit:0,always:true,budgetMs:3,draw(now){
  for(const rig of RIGSET)if(rig.orbit&&!rig.orbitPaused&&!rig.moving&&rig.cam&&fxLevel()>0)orbitStep(rig,now);
  for(const j of JOBS)jobStep(j,now)}})}
function orbitOn(rig,on){rig.orbit=!!on&&fxLevel()>0;rig.orbitPaused=false;if(rig.orbit){const base=rig.base||currentPose(rig.browser);if(!base){rig.orbit=false;return false}const c=rig.pose.center,d=V.sub(base.position,c),D=V.len(d)||1;
    rig.orb={t0:performance.now(),c,D,e0:Math.asin(Math.max(-1,Math.min(1,d[1]/D))),th0:Math.atan2(d[0],d[2]),from:{position:base.position.slice(),q:base.q.slice()}};ensurePanel();hookCanvas(rig);if(rig.inst&&rig.inst.frozen)rig.inst.resume()}
  if(rig.browser===SH.browser)__stage.show.orbit=rig.orbit;return rig.orbit}
function orbitStep(rig,now){const o=rig.orb;if(!o)return;const t=(now-o.t0)/1000,k=Math.sqrt(rigOpts.ellipse),th=o.th0+2*Math.PI*(t*1000)/rigOpts.orbitPeriodMs,e=o.e0+rigOpts.breathDeg*Math.PI/180*Math.sin(2*Math.PI*t/14);
  let p=V.add(o.c,[o.D*Math.cos(e)*Math.sin(th)*k,o.D*Math.sin(e),o.D*Math.cos(e)*Math.cos(th)/k]);let q=Q.lookAt(p,o.c,[0,1,0]);
  if(t<2){const u=easeIO(t/2);p=V.lerp(o.from.position,p,u);q=Q.slerp(o.from.q,q,u)}setPose(rig,p,q,false)}
function hookCanvas(rig){const inst=rig.inst,cv=inst&&inst.canvas;if(!cv||HOOKED.has(cv))return;HOOKED.add(cv);
  cv.addEventListener("pointerdown",()=>{const r=rigOf(inst.browser);if(r)r.orbitPaused=true},{passive:true});
  cv.addEventListener("dblclick",()=>{const r=rigOf(inst.browser);if(r)rigReset(inst)})}
function rigReset(inst){inst=instOf(inst)||SH;const rig=rigOf(inst.browser);if(!rig||!rig.cam){try{inst.browser&&inst.browser.getActiveLayer().viewAll(0)}catch(e){}return false}
  if(inst.frozen)inst.resume();setPose(rig,rig.base.position,rig.base.q,true);rig.orbitPaused=false;if(rig.orbit)rig.orb.t0=performance.now();if(rig.orb)rig.orb.from={position:rig.base.position.slice(),q:rig.base.q.slice()};
  if(fxLevel()===0)inst.freezeSoon(inst.token);return true}
/* a camera move: target {position:[x,y,z], orientation:[x,y,z,angle]|q:[x,y,z,w]|lookAt:[x,y,z], up?} over ms; fx 0 / reduced motion = a 2-frame cut with the same end values */
function camMove(inst,target,ms){inst=instOf(inst)||SH;return new Promise(resolve=>{const B=inst.browser;if(!B||!target){resolve(false);return}
  let rig=rigOf(B);if(!rig||!rig.cam){rig=camOnlyRig(B,inst)}if(!rig.cam){resolve(false);return}
  const from=rig.pose?{position:rig.pose.position.slice(),q:rig.pose.q.slice()}:currentPose(B);const to={position:target.position?target.position.slice():from.position.slice(),q:target.q?target.q.slice():target.orientation?Q.fromAxisAngle(target.orientation.slice(0,3),target.orientation[3]):target.lookAt?Q.lookAt(target.position||from.position,target.lookAt,target.up):from.q.slice()};
  if(inst.frozen)inst.resume();rig.moving=true;ensurePanel();const cut=reduced()||!(ms>0);
  JOBS.add({rig,inst,from,to,t0:performance.now(),ms:cut?0:ms,frames:0,cut,resolve,onStep:target.onStep||null})})}
function jobStep(j,now){const t=j.ms?Math.min(1,(now-j.t0)/j.ms):1,u=easeIO(t),p=V.lerp(j.from.position,j.to.position,u),q=Q.slerp(j.from.q,j.to.q,u);setPose(j.rig,p,q,t>=1);
  if(j.onStep)try{j.onStep(t,p)}catch(e){}j.frames++;
  if(t>=1&&j.frames>=2){JOBS.delete(j);j.rig.moving=false;j.rig.base={position:j.to.position.slice(),q:j.to.q.slice(),center:j.rig.pose.center.slice()};if(j.rig.orb)j.rig.orb.from=j.rig.base;
    if(fxLevel()===0)j.inst.freezeSoon(j.inst.token);try{j.resolve(true)}catch(e){}}}
async function camPath(inst,keyframes){let ok=true;for(const k of keyframes||[]){ok=(await camMove(inst,k,k.ms!=null?k.ms:1200))&&ok}return ok}
/* grab inside X_ITE's finishEvents callback (a read-back outside it is black); thaws a frozen instance and re-freezes it after */
function grabFrame(inst,fn,timeoutMs){return new Promise(res=>{const B=inst.browser;if(!B){res(null);return}let F,key=Symbol(),done=false;try{F=B.finishEvents()}catch(e){res(null);return}
  const wasFrozen=!!inst.frozen;if(wasFrozen)inst.resume();
  const fin=r=>{if(done)return;done=true;clearTimeout(t);setTimeout(()=>{try{F.removeFieldCallback(key)}catch(e){}},0);if(wasFrozen&&fxLevel()===0)inst.freezeSoon(inst.token);res(r)};
  const t=setTimeout(()=>fin(null),timeoutMs||6000);
  try{F.addFieldCallback(key,()=>{let r=null;try{r=fn(B.getCanvas())}catch(e){}fin(r)})}catch(e){fin(null)}})}
function project(B,p){try{const L=B.getActiveLayer(),vp=L.getViewpoint(),nav=L.getNavigationInfo(),rect=L.getViewport().getRectangle(),Vm=vp.getViewMatrix(),Pm=vp.getProjectionMatrixWithLimits(vp.getNearDistance(nav),vp.getFarDistance(nav),rect);
  const mul=(v,M)=>[0,1,2,3].map(j=>v[0]*M[j]+v[1]*M[4+j]+v[2]*M[8+j]+v[3]*M[12+j]),e=mul([p[0],p[1],p[2],1],Vm),c=mul(e,Pm);if(!(Math.abs(c[3])>1e-12))return null;
  const nx=c[0]/c[3],ny=c[1]/c[3],nz=c[2]/c[3];if(!Number.isFinite(nx)||!Number.isFinite(ny)||!Number.isFinite(nz))return null;const cv=B.getCanvas(),w=cv.clientWidth||rect[2],h=cv.clientHeight||rect[3];
  return{x:(nx+1)/2*w,y:(1-ny)/2*h,z:nz,behind:e[2]>0,ndc:[nx,ny,nz]}}catch(e){return null}}
/* ---- show2: more visible instances with the show surface (morph 2-up, dark-seven stage); created lazily by their sections, disposed on leave ---- */
__stage.show2={created:0,live:0,loads:0};
function makeShow(mount,opts){opts=opts||{};const I={name:opts.name||"show2",mount,canvas:null,browser:null,ready:null,token:0,loads:0,lastHash:null,staged:false,frozen:false,scene:null,disposed:false,err:"",
  async load(xml,o){o=o||{};if(!I.browser)await I.ready;if(!I.browser||I.disposed)return{ok:false,err:"X_ITE not available: "+(I.err||"no browser")};const tk=++I.token,B=I.browser,t0=performance.now();I.scene=o.scene||null;I.staged=false;
    try{tearDown(B);await clearView(B);if(tk!==I.token)return{ok:false,cancelled:true};const scn=await B.createX3DFromString(stripProv(xml));if(tk!==I.token)return{ok:false,cancelled:true};await B.replaceWorld(scn);try{B.getActiveLayer().viewAll(0)}catch(e){}
      I.lastHash=contentHash(xml);I.loads++;__stage.show2.loads++;I.frozen=false;if(o.staged){const r=rigApply(B,xml,Object.assign({inst:I},o));I.staged=!!r}I.freezeSoon(tk);return{ok:true,ms:Math.round(performance.now()-t0),staged:I.staged}}
    catch(e){if(tk!==I.token)return{ok:false,cancelled:true};const err=String(e&&e.message||e).replace(/'http[^']*'/,"the string").slice(0,200);try{await B.replaceWorld(await B.createX3DFromString(EMPTY))}catch(_){}return{ok:false,err}}},
  setStaged(on,o){if(!I.browser)return false;if(on){if(!I.staged){const r=rigApply(I.browser,null,Object.assign({inst:I},o||{}));I.staged=!!r}}else{tearDown(I.browser);I.staged=false}if(I.frozen){I.resume();I.freezeSoon(I.token)}return I.staged},
  pause(){try{I.browser&&I.browser.endUpdate()}catch(e){}},resume(){I.frozen=false;try{I.browser&&I.browser.beginUpdate()}catch(e){}},
  freezeSoon(tk){if(fxLevel()!==0)return;setTimeout(()=>{if(tk!==I.token||!I.browser||I.disposed)return;for(const j of JOBS)if(j.inst===I)return;const r=rigOf(I.browser);if(r&&r.orbit)return;try{I.browser.endUpdate();I.frozen=true}catch(e){}},1500)},
  snapshot(type){return grabFrame(I,cv=>{const t=document.createElement("canvas");t.width=cv.width;t.height=cv.height;t.getContext("2d").drawImage(cv,0,0);return t.toDataURL(type||"image/jpeg",.85)})},
  pixels(){return grabFrame(I,cv=>pixelsOf({getCanvas:()=>cv}))},
  facts(){return I.browser?sceneFacts(I.browser):null},bbox(){return I.browser?layerBBox(I.browser):null},placed(){return I.browser?placedShapes(I.browser):null},
  pose(){return I.browser?currentPose(I.browser):null},setPose(p,q){const r=I.browser&&(rigOf(I.browser)||camOnlyRig(I.browser,I));if(r&&r.cam)setPose(r,p,q,false)},
  dolly(target,ms){return camMove(I,target,ms)},cam(k){return camPath(I,k)},reset(){return rigReset(I)},orbit(on){const r=I.browser&&rigOf(I.browser);return r?orbitOn(r,on):false},project(p){return I.browser?project(I.browser,p):null},rig(){return rigSummary(rigOf(I.browser))},
  label(){const gl=self.ENV&&ENV.gl?ENV.gl:"?";return(I.staged?"STAGED · lights + ground + camera added at render time · nothing written":"MEASURED · raw bytes · own/default viewpoint · headlight")+` · ${gl} · X_ITE 16.5.0 in this browser`+(I.frozen?" · STATIC FRAME (software GL: rendering paused after load)":"")},
  dispose(){if(I.disposed)return;I.disposed=true;I.token++;try{tearDown(I.browser)}catch(e){}try{I.browser&&I.browser.endUpdate()}catch(e){}try{I.canvas&&I.canvas.remove()}catch(e){}if(I.browser)__stage.show2.live--;I.browser=null;I.canvas=null}};
  Object.defineProperty(I,"ok",{get:()=>!!I.browser});
  I.ready=(async()=>{try{I.canvas=await makeCanvas(mount,{attrs:opts.attrs||{}});if(I.disposed){try{I.canvas.remove()}catch(e){}return null}I.browser=I.canvas.browser;__stage.show2.created++;__stage.show2.live++}catch(e){I.err=String(e&&e.message||e)}return I.browser})();return I}
const STAGE={measure:M,show:SH,ready:null,rigOpts,sceneFacts,layerBBox,placedShapes,
  show2(mount,opts){/* M3 lazy factory: another visible instance with the show surface (load/setStaged/pause/resume/freezeSoon/snapshot/pixels/dolly/reset/orbit/project/dispose) */return makeShow(mount,opts)},
  applyRig(browser,xml,opts){/* M3 (SPEC §5): three DirectionalLights (or EnvironmentLight when rigOpts.env), headlight off through a bound NavigationInfo, ground when the bbox is finite (fx ≥ 1), Background when absent, __cam viewpoint; opt-outs read from the loaded graph; returns the rig handle or null */return rigApply(browser||SH.browser,xml,opts)},
  tearDownRig(browser){/* M3: remove Group DEF="__stage" and __cam (unbinding what the rig bound) before the next replaceWorld */tearDown(browser||SH.browser)},
  projectPoint(p,browser){/* M3 spike (works in 16.5.0): world point [x,y,z] → {x, y (CSS px on the canvas), z, behind, ndc} through the bound viewpoint's view and projection matrices; null when the SAI gives no matrix */return project(browser||SH.browser,p)},
  pause(){SH.pause();try{M.browser&&M.browser.endUpdate()}catch(e){}},resume(){SH.resume();try{M.browser&&M.browser.beginUpdate()}catch(e){}},
  async textProbe(){const xml="<X3D profile='Immersive' version='4.0'><Scene><Viewpoint position='0 0 9'/><Shape><Appearance><Material diffuseColor='1 0.8 0.2'/></Appearance><Text string='\"TETHER\"'><FontStyle family='\"SANS\"' size='2' justify='\"MIDDLE\" \"MIDDLE\"'/></Text></Shape></Scene></X3D>";
    const r=await M.show(xml,{timeoutMs:6000,expectNone:true});if(r.cancelled)return null;const ok=!r.err&&!r.noFrame&&(r.nb||0)>=.005;if(self.ENV){ENV.textDraws=ok;ENV._emit()}return ok},
  init(){if(STAGE.ready)return STAGE.ready;STAGE.ready=(async()=>{
    M.ready=(async()=>{try{M.canvas=await makeCanvas($("measureMount"),{autoUpdate:false});M.browser=M.canvas.browser;__stage.measure.ready=true}catch(e){__stage.measure.err=String(e&&e.message||e);console.warn("measure canvas",e)}return M.browser})();
    SH.ready=(async()=>{try{const mount=$("stageView");if(!mount)return null;SH.canvas=await makeCanvas(mount,{});SH.browser=SH.canvas.browser;__stage.show.ready=true;badge()}catch(e){__stage.show.err=String(e&&e.message||e);console.warn("show canvas",e)}return SH.browser})();
    await Promise.all([M.ready,SH.ready]);return STAGE})();return STAGE.ready}};
Object.defineProperty(M,"ok",{get:()=>!!M.browser});Object.defineProperty(SH,"ok",{get:()=>!!SH.browser});
Object.assign(self,{STAGE,__stage,watchFrames,clearView});
})();
