/* 08-stage.js — the X_ITE stage (SPEC §5, S2, rule 4). Wave 1 = the MEASURE path and a plain unstaged SHOW loader; M3 adds the rig
   (applyRig / tearDownRig / orbit / dolly / cam / projectPoint / show2) behind the stubs below without changing the surface.
   Globals: STAGE, sampleFrame (window; the v3 test hook), __stage.
   Ported from v3: watchFrames (lines 846–850), clearView (851–853), sampleFrame (854–857: a setTimeout chain instead of v3's interval timer), init3dNow pixels (860–866),
   show3d's load sequence and its no-frame / nothing-drawable / slow logic (651–676), tapConsole (647–649).
   Rules: samples are taken inside X_ITE's finishEvents callback (a timer reads a cleared buffer); viewAll(0) after replaceWorld; nonblank = fraction of all pixels
   differing from the dominant colour by > 48; blank < 0.005. The measure canvas is never styled, rigged or sampled by anyone else (__stage.measure.rigNodes stays 0).
   Test hooks: window.sampleFrame (override to simulate a slow renderer), __stage, STAGE.measure.show(xml) → R, STAGE.ready. */
(function(){
"use strict";
const EMPTY="<X3D profile='Interchange' version='4.0'><Scene/></X3D>";
const DROP_RE=/Unknown node type|Unknown named or imported node|Container field|insufficient component/i;
const __stage={measure:{rigNodes:0,loads:0,last:null,ready:false,err:""},show:{staged:false,loads:0,lastHash:null,ready:false,err:"",frozen:false}};
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
  show(xml,opts){opts=opts||{};const tk=++M.token;const run=()=>measureNow(xml,opts,tk);const p=M.queue.then(run,run);M.queue=p.catch(()=>{});return p}};
async function measureNow(xml,opts,tk){
  if(!M.browser)await M.ready;if(!M.browser)return{err:"X_ITE not available: "+(__stage.measure.err||"no browser"),nb:null,frames:0,series:[],msgs:[],noFrame:true,ms:0};
  if(tk!==M.token)return{cancelled:true};
  const B=M.browser,t0=performance.now(),said=[],w=watchFrames(B,M.pixels);SAID=said;tapConsole();M.busy=true;__stage.measure.loads++;
  const R={nb:null,frames:0,series:[],first:null,last:null,msgs:said,err:null,noFrame:false,slow:false,ms:0,nodes:null,cancelled:false,renderer:self.ENV?ENV.renderer:null};
  try{await clearView(B);if(tk!==M.token)return{cancelled:true};
    const scn=await B.createX3DFromString(stripProv(xml));if(tk!==M.token)return{cancelled:true};
    w.start();await B.replaceWorld(scn);try{B.getActiveLayer().viewAll(0)}catch(e){}
    await later(650);if(tk!==M.token)return{cancelled:true};
    let px=await self.sampleFrame(w);const drop=said.some(t=>DROP_RE.test(t)),expectNone=!!opts.expectNone;let nf=px.err==="no frame";
    /* no frame is only read as "nothing drawable" when something says so (dropped nodes, or the record); otherwise the renderer may just be slow here, so wait longer */
    if(nf&&!expectNone&&!drop){px=await self.sampleFrame(w,opts.timeoutMs||12000);if(tk!==M.token)return{cancelled:true};nf=px.err==="no frame";R.slow=nf}
    R.noFrame=nf;R.ms=Math.round(performance.now()-t0);try{R.nodes=B.currentScene.rootNodes.length}catch(e){}
    if(!nf){R.nb=px.nonblank;R.frames=px.frames;R.series=px.series}R.first=w.first;R.last=w.last;R.frames=w.n;R.dropped=drop;
    R.kind=nf&&R.slow?"no frame yet":nf||(R.nb<.005&&drop)?"nothing drawable":R.nb<.005?"blank frame":"draws"}
  catch(e){if(tk!==M.token)return{cancelled:true};R.err=String(e&&e.message||e).replace(/'http[^']*'/,"the string").slice(0,200);R.kind="unparseable";R.ms=Math.round(performance.now()-t0);try{await B.replaceWorld(await B.createX3DFromString(EMPTY))}catch(_){}}
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
  setStaged(on){/* M3: re-apply or tear down the rig; wave 1 has no rig */SH.staged=false;__stage.show.staged=false;badge();return false},
  orbit(on){/* M3 */return false},reset(){/* M3: back to the staged camera */try{SH.browser&&SH.browser.getActiveLayer().viewAll(0)}catch(e){}},
  dolly(target,ms){/* M3: render-time camera move; resolves at once in wave 1 */return Promise.resolve(false)},
  cam(keyframes){/* M3 */return Promise.resolve(false)},
  pause(){try{SH.browser&&SH.browser.endUpdate()}catch(e){}},resume(){SH.frozen=false;__stage.show.frozen=false;try{SH.browser&&SH.browser.beginUpdate()}catch(e){}badge()},
  /* fx 0 (software GL / webdriver / phone): X_ITE's own render loop would eat the rAF budget (5 fps under SwiftShader), so 1.5 s after a load the
     stage keeps its last frame and stops rendering; the badge says so; orbit/resume (M3 wiring, STAGE.show.resume()) thaws it. Never on fx > 0. */
  freezeSoon(tk){if(!(self.FX&&FX.level===0))return;setTimeout(()=>{if(tk!==SH.token||!SH.browser)return;try{SH.browser.endUpdate();SH.frozen=true;__stage.show.frozen=true;badge()}catch(e){}},1500)},
  snapshot(){return new Promise(res=>{try{SH.browser.getCanvas().toBlob(b=>res(b||null),"image/png")}catch(e){res(null)}})}};
function badge(){const b=$("stageBadge");if(!b)return;const gl=self.ENV&&ENV.gl?ENV.gl:"?";txt(b,(SH.staged?"STAGED · lights + ground + camera added at render time · nothing written":"MEASURED · raw bytes · own/default viewpoint · headlight")+` · ${gl} · X_ITE 16.5.0 in this browser`+(SH.frozen?" · STATIC FRAME (software GL: rendering paused after load)":""))}
const STAGE={measure:M,show:SH,ready:null,
  applyRig(browser,xml,opts){/* M3 (SPEC §5): EnvironmentLight or three DirectionalLights, ground when the bbox is finite, Background when absent, __cam viewpoint; returns the rig handle or null */return null},
  tearDownRig(){/* M3: remove Group DEF="__stage" and __cam before the next replaceWorld */},
  projectPoint(p){/* M3 spike: SAI view matrix in 16.5.0; null → the floor ribbon falls back to a 2D strip */return null},
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
