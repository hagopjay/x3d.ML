/* 50-tour.js — THE TOUR: 12 steps that drive the page's real controls (SPEC-v4 "Tour (12 steps)"; WORKPLAN 50-tour). Overlay #tour (template div), chip #bTour
   appended to the mast's .mastR before #tierBadge (10-curtain-mast is frozen and carries no Tour chip yet: the chip lives here until the mast owns it; requested).
   Globals: TOUR (the step array [{h, t(), ms, sec, pause, run()}] with TOUR.start(), TOUR.next(), TOUR.prev(), TOUR.running, TOUR.i, TOUR.snapshot(), TOUR.restore(snap),
   TOUR.go(sectionId)), tourShow(i), tourStop(), __tour.
   Ported from demo/tether-firehose-v3.template.html lines 906–949 (TOUR, tourShow, tourStop, the token+timer engine; v3's clk/setRate/pickScene/later are now
   00-util later(fn, ms) and 20-sim setRate/pickScene). Changed: 12 re-cut steps over the v4 sections; every run() drives a documented control of another module
   (never a private); step 11 PAUSES on the live lane's pre-flight card (LANE.preflight() only, never liveTether, never GO: the viewer presses Continue); tourStop()
   restores every control it moved (rate, clock, pause state, selection, filter, commit slider, signing, inspector tab, hero, bench text, lightbox, stage camera, scroll).
   Keys (capture phase, so the mast's ±10 s seek never fires while the tour runs): Esc stops the tour (and Director mode), ← → step. Sound: SOUND.play(kind) only when 54-sound is present and SOUND.isOn (muted by default).
   Honesty: the tour quotes numbers from STATS / LIVESTATS / REALSTATS / EVENTS / MANIFEST, never typed; injections are "simulated attacks"; the port is js-port-of-8dd0d3e.
   Test hooks: __tour {i, running, paused, snap, drove: [[control names per step]], steps: 12, stops}, TOUR.snapshot() / TOUR.restore(s), #tour .tourBox, #th #tt #tn #tbar #tPrev #tNext #tStop, #bTour.on. */
(function(){
"use strict";
const ST={i:-1,tk:0,cancels:[],snap:null};
const __tour={i:-1,running:false,paused:false,snap:null,drove:[],steps:0,stops:0};
const E={};
const fx0=()=>!!(self.FX&&FX.level===0);
const reduced=()=>fx0()||(matchMedia&&matchMedia("(prefers-reduced-motion:reduce)").matches);
function go(id){const e=typeof id==="string"?$(id):id;if(!e)return false;try{e.scrollIntoView({block:"start",behavior:reduced()?"auto":"smooth"})}catch(err){e.scrollIntoView()}return true}
/* run one control by name; failures are logged, never fatal; the test reads what each step actually drove */
function drive(name,fn){const i=ST.i;try{const r=fn();if(r===false||r==null)return r;if(i>=0)(__tour.drove[i]||(__tour.drove[i]=[])).push(name);return r}catch(e){console.warn("tour drive",name,e);return null}}
function at(ms,fn){const tk=ST.tk;const c=later(()=>{if(tk===ST.tk)try{fn()}catch(e){console.warn("tour later",e)}},ms);ST.cancels.push(c);return c}
function cancelAll(){ST.tk++;ST.cancels.forEach(c=>{try{c()}catch(e){}});ST.cancels=[]}
function cue(kind){if(self.SOUND&&SOUND.isOn&&typeof SOUND.play==="function")try{SOUND.play(kind)}catch(e){}}  /* 54-sound: play(kind) only while the viewer turned sound on; nothing at load */
const fmtClk=s=>self.fmt&&fmt.clock?fmt.clock(s):String(s);
const LS=()=>self.LIVESTATS||(self.STATS&&STATS.LIVESTATS)||{};
const RS=()=>self.REALSTATS||(self.STATS&&STATS.REALSTATS)||{};
const claim=(id,k)=>{const c=self.STATS&&STATS.claims&&STATS.claims[id];const v=c&&c.expected;return k?(v&&v[k]):v};
const firstRepaired=()=>self.S&&S.scenes.slice().reverse().find(s=>s.src==="live"&&s.item&&s.item.A&&s.item.A.length>1&&s.verdict==="valid")||null;
const topCode=()=>{try{const t=self.FLOW&&FLOW.taxonomy();const rows=t&&(t.codes||t.rows||t.first||null);if(Array.isArray(rows)&&rows.length){const r=rows.slice().sort((a,b)=>(b.n||b.total||0)-(a.n||a.total||0))[0];return r.code||r.id||r.name||null}}catch(e){}return "profile-component"};
/* ---------- snapshot / restore (shared with 52-director) ---------- */
function snapshot(){const s={x:scrollX,y:scrollY,at:performance.now()};
  if(self.S){s.rate=S.rate;s.paused=S.paused;s.done=S.done;s.clk=S.clk;s.mode=S.mode;s.sel=S.sel;s.filter=S.flags.filter||null;s.vi=S.vi;s.sealOn=!!(self.HASH&&HASH.sealOn)}
  if(self.SLIDER)s.slider={i:SLIDER.i,ref:SLIDER.ref,active:SLIDER.active};
  if(self.INSPECTOR)s.tab=INSPECTOR.tab||null;if(self.__hero)s.hero=__hero.cur;if(self.BENCH&&BENCH.text)s.bench=BENCH.text();
  s.staged=!!(self.__stage&&__stage.show.staged);return s}
function restore(s){if(!s)return false;
  if(self.FLOW&&self.S&&S.flags.filter!==s.filter){FLOW.clear();if(s.filter){S.flags.filter=s.filter;if(self.SIM)SIM.emit("filter",s.filter)}}
  if(self.SLIDER&&s.slider&&(SLIDER.i!==s.slider.i||SLIDER.active!==s.slider.active)){
    if(s.slider.active&&s.slider.i!=null)SLIDER.set(s.slider.i);
    else{SLIDER.i=s.slider.i;SLIDER.ref=s.slider.ref;SLIDER.active=!!s.slider.active;if(self.S&&s.vi!=null)S.vi=s.vi;document.querySelectorAll("#ladder .notch").forEach(b=>b.classList.remove("on"));const sl=$("commitSlider");if(sl&&s.slider.i!=null)sl.value=String(s.slider.i);if(self.LADDER&&LADDER.syncButtons)try{LADDER.syncButtons()}catch(e){}}}
  if(self.WALL&&self.HASH&&s.sealOn!=null&&!!HASH.sealOn!==s.sealOn)WALL.setSigning(s.sealOn);
  if(self.SHEET&&SHEET.closeLightbox)try{SHEET.closeLightbox()}catch(e){}
  if(self.BENCH&&s.bench!=null&&BENCH.text&&BENCH.text()!==s.bench)try{BENCH.set(s.bench)}catch(e){}
  if(self.INSPECTOR&&s.tab&&self.setTab&&INSPECTOR.tab!==s.tab)try{setTab(s.tab)}catch(e){}
  if(self.S&&self.SIM){if(s.mode&&S.mode!==s.mode&&self.MODES&&MODES.get(s.mode))MODES.set(s.mode);if(S.rate!==s.rate)SIM.setRate(s.rate);if(Math.abs(S.clk-s.clk)>0.5&&!s.done)SIM.seekTo(s.clk);
    if(s.paused&&!S.paused)SIM.pause();else if(!s.paused&&S.paused&&!S.done)SIM.resume();if(s.sel!==S.sel)SIM.select(s.sel)}
  if(self.HEROUI&&s.hero!=null&&self.__hero&&__hero.cur!==s.hero)try{HEROUI.open(s.hero,{noLoad:fx0()})}catch(e){}
  if(self.STAGE&&STAGE.show&&STAGE.show.reset)try{STAGE.show.reset()}catch(e){}
  try{scrollTo({left:s.x||0,top:s.y||0,behavior:"auto"})}catch(e){scrollTo(s.x||0,s.y||0)}
  if(self.LOOP)LOOP.dirtyAll();return true}
/* ---------- the twelve steps ---------- */
const TOUR=[
 {h:"The stage",sec:"stage",ms:9000,
  t:()=>`What you see is STAGED (lights, ground and a camera added at render time; nothing written to the file). What is counted is the 192×144 MEASURED frame beside it: X_ITE 16.5.0 offline, 16.5.1 offline, and this browser. The clock under the title is the run's own: ${fmtClk(self.LM&&LM.t_total||0)} of recorded calls at x30.`,
  run(){drive("HEROUI.open(0)",()=>self.HEROUI&&HEROUI.open(0));drive("SIM.setRate(30)",()=>self.SIM?(SIM.setRate(30),true):null);drive("SIM.resume",()=>self.SIM&&self.S&&S.paused&&!S.done?(SIM.resume(),true):null);
    if(!fx0())at(1500,()=>drive("STAGE.show.setStaged(true)",()=>self.STAGE&&STAGE.show.setStaged&&STAGE.show.setStaged(true)))}},
 {h:"The report spine and the tiles",sec:"stage",ms:9000,
  t:()=>{const r=claim("c.rates")||[];const l=r[0];return `Three tiles, three claim chips: first-try and final validity per lane${l?` (${l.firstPct} % → ${l.validPct} % for the first lane)`:""}, ${claim("c.seven")} finals valid on the fork that draw nothing, and the validator-to-model median ratio ×${self.fmt?fmt.int(claim("c.ratio","x")||0):claim("c.ratio","x")}. Under them the spine: attempt 1, the finding, "the model was sent its own report", the final. A chip is a button: it re-runs its number here.`},
  run(){drive("SIM.setRate(4)",()=>self.SIM?(SIM.setRate(4),true):null);const sp=document.querySelector("#stage .spine");if(sp)at(600,()=>go(sp));
    at(1200,()=>drive("pickScene(repaired valid)",()=>self.pickScene?pickScene(s=>s.src==="live"&&s.item&&s.item.A&&s.item.A.length>1&&s.verdict==="valid"):null));
    at(2600,()=>drive("setTab(report)",()=>self.setTab?setTab("report"):null))}},
 {h:"The repair morph",sec:"morph",ms:10000,
  t:()=>`${LS().rep} of the ${LS().bad1} first-try failures were repaired: the validator's report went back to the model and the model rewrote its file. Attempt 1 wipes to the final; the ribbon under the floor stamps each chain step as the scrub passes it. The morph is never the evidence: the two pinned measured frames are.`,
  run(){const sc=firstRepaired();drive("MORPH.open",()=>self.MORPH?MORPH.open(sc&&sc.item?{m:sc.item.m,p:sc.item.p}:0):null);at(900,()=>drive("MORPH.replay",()=>self.MORPH&&MORPH.replay?(MORPH.replay(),true):null))}},
 {h:"The dark seven",sec:"seven",ms:10000,
  t:()=>`${claim("c.seven")} finals are valid on fork@eb4b4b4 and draw nothing in X_ITE 16.5.0: under 0.5 % of the pixels differ from the background. Valid is not visible. FIND IT dollies the render-time camera to where the validator says the geometry is; the counter beside it is this browser's own ratio, never counted.`,
  run(){drive("SEVEN.open(0)",()=>self.SEVEN?SEVEN.open(0):null);at(1800,()=>drive("SEVEN.findIt",()=>self.SEVEN&&SEVEN.findIt?(SEVEN.findIt(),true):null))}},
 {h:"The run as film",sec:"film",ms:12000,
  t:()=>{const cs=self.EVENTS&&EVENTS.creditStop;return `${claim("c.calls")} calls on the run's own clock: one bar per call from request to last token, green ended valid, red invalid, cyan in flight. ${claim("c.failed")} failed calls and ${claim("c.cut")} cut chains are their own marks. At x60 the credit stop passes at ${cs?fmtClk(cs.t):"its recorded second"}: one provider account ran dry and its lane ends there. Open a bar: the inspector shows that call's tether.`},
  run(){const cs=self.EVENTS&&EVENTS.creditStop;drive("SIM.setRate(60)",()=>self.SIM?(SIM.setRate(60),true):null);
    if(cs&&self.SIM){drive("SIM.seekTo(credit stop − 20 s)",()=>(SIM.seekTo(Math.max(0,cs.t-20)),true));drive("SIM.resume",()=>{if(S.paused&&!S.done)SIM.resume();return true})}
    at(3500,()=>drive("SIM.select + emit(open tether)",()=>{const sc=self.pickScene&&pickScene(s=>s.src==="live"&&s.verdict==="valid");if(sc&&self.SIM){SIM.emit("open",{id:sc.id,tab:"tether",from:"tour"});return sc}return null}))}},
 {h:"The oscilloscope and the decade drill",sec:"film",ms:9000,
  t:()=>`Log y, 1 ms to 1000 s. The red trace is the model call, the green one the validator on the same body. Median ${claim("c.ratio","vmed")} ms against ${self.fmt?fmt.int(claim("c.ratio","mmed")||0):claim("c.ratio","mmed")} ms: ×${self.fmt?fmt.int(claim("c.ratio","x")||0):claim("c.ratio","x")}. The decade drill zooms the x span from the whole run to one millisecond, one decade per 400 ms, and back.`,
  run(){const c=$("scopeCanvas")||$("scopeHost");if(c)go(c);drive("#scopeDrill",()=>{const b=$("scopeDrill");if(b&&!b.disabled){b.click();return true}return self.SCOPE&&SCOPE.drill?SCOPE.drill():null})}},
 {h:"The matrix and the taxonomy",sec:"matrix",ms:9000,
  t:()=>`${self.LM&&LM.n_prompts||50} prompts × the lanes: fill = final verdict, depth = attempts needed, hatched = cut, × = failed. Beside it the error taxonomy: first-try codes and their fate after each repair. Clicking a ribbon filters the firehose and the matrix to those chains; the tour sets one filter and clears it when it stops.`,
  run(){at(1200,()=>drive("FLOW.filter(code)",()=>self.FLOW&&FLOW.filter?FLOW.filter(topCode(),"gone after repair 1"):null))}},
 {h:"The port re-validating the bodies",sec:"ladder",ms:12000,
  t:()=>{const can=(self.MANIFEST&&MANIFEST.canary)||{};return `Every verdict names its validator. The tour switches to the 11 Oct replay, whose chains carry the service verdict, and slides the cursor across the recorded commits: on fork@8c0a457 ${RS().flip} of the ${RS().f&&RS().f[0]?RS().f[0].valid:""} scenes the service passed flip to invalid; RE-VALIDATE stamps that recorded verdict on every stored chain. The last rail is js-port-of-8dd0d3e running in this browser over ${can.bodies||""} bodies, expected ${can.flips==null?"":can.flips} flips against the recorded canary${self.VAL&&VAL.mode==="full"?"":" (the port is not loaded in this viewer: recorded rails only)"}.`},
  run(){drive("MODES.set(replay11)",()=>self.MODES&&MODES.get("replay11")&&self.S&&S.mode!=="replay11"?(MODES.set("replay11"),true):null);drive("SIM.seekTo(end of the replay)",()=>self.SIM?(SIM.seekTo(SIM.tmax()),true):null);
    drive("SLIDER.set(8c0a457)",()=>self.SLIDER?SLIDER.set("8c0a457"):null);at(1500,()=>drive("#bRevalidate",()=>{const b=$("bRevalidate");if(b&&!b.disabled){b.click();return true}return null}));
    at(4000,()=>drive("#bRevalPort",()=>{const b=$("bRevalPort");if(b&&!b.disabled&&self.VAL&&VAL.mode==="full"&&self.PORT&&!PORT.busy&&!PORT.result){b.click();return true}return null}))}},
 {h:"The wall: tamper caught",sec:"wall",ms:12000,
  t:()=>`Every body on the page carries its own chain in the file head: a text-normalised SHA-256 per step, each step hashing the one before. The wall re-verifies all of them. Edit a scene after the fact, delete a step: the scrubber names the damage within one sweep. Injection 5 drops the component statement through a recorded step, so the chain stays VERIFIED while the verdict flips: only a re-validation on the port catches it. These are simulated attacks on recorded bodies.`,
  run(){drive("MODES.set(live17)",()=>self.MODES&&self.S&&S.mode!=="live17"?(MODES.set("live17"),true):null);drive("SIM.seekTo(900)",()=>self.SIM&&self.S&&S.clk<900?(SIM.seekTo(900),true):null);drive("SIM.setRate(30)",()=>self.SIM?(SIM.setRate(30),true):null);drive("SIM.resume",()=>self.SIM&&self.S&&S.paused&&!S.done?(SIM.resume(),true):null);
    at(1500,()=>drive("inject(edit)",()=>self.inject?inject("edit"):null));at(2600,()=>drive("inject(del)",()=>self.inject?inject("del"):null));at(3800,()=>drive("inject(nocomp)",()=>self.inject?inject("nocomp"):null));
    at(6000,()=>drive("#bReverify",()=>{const b=$("bReverify");if(b&&!b.disabled){b.click();return true}return null}))}},
 {h:"The honest gap and signing",sec:"wall",ms:12000,
  t:()=>`Flip the LAST verdict on an unsigned chain and nothing notices: no later step vouches for it. That is the stated limit of the unsigned record, so the injected count runs ahead of the caught count. Turn signing on (an HMAC stand-in, key in the page source; not Ed25519) and new chains are sealed over the head: the same attack on a sealed chain fails the seal check. The drawer beside it models the gap, and says simulated.`,
  run(){drive("inject(fliplast)",()=>self.inject?inject("fliplast"):null);at(1500,()=>drive("WALL.setSigning(true)",()=>self.WALL&&WALL.setSigning?(WALL.setSigning(true),true):null));
    at(5000,()=>drive("inject(fliplast on a sealed chain)",()=>{if(!self.S||!self.inject)return null;const sc=S.scenes.slice().reverse().find(s=>s.sealed&&s.status==="verified"&&!s.injured&&!s.tampered);if(!sc)return null;const r=inject("fliplast",sc);if(r&&self.SIM)SIM.select(r.id);return r||null}))}},
 {h:"The live lane",sec:"lane",ms:0,pause:true,
  t:()=>{if(self.LANE&&typeof LANE.preflight==="function")return "Your own Claude can write a scene into the same loop: 1 to 3 calls on your usage, the validator's report sent back on failure, every step stamped into the file head. The tour stops here on the pre-flight card and never presses GO: that is your call. Press Continue when you are done reading it.";
    const sb=document.querySelector("#lane .sb");const line=sb&&sb.innerText.trim().split("\n")[0];return `No live lane in this build: ${line||"the lane section is absent"}. Nothing is called. Press Continue.`},
  run(){drive("LANE.preflight",()=>self.LANE&&typeof LANE.preflight==="function"?(LANE.preflight(),true):null)}},
 {h:"Take it with you",sec:"deck",ms:9000,
  t:()=>`The record is plain meta lines in the file head, a few hundred bytes a step whatever the scene's size. The inspector's Receipt tab lists every claim behind a scene with its source field and stamp; PROV, OpenLineage and OTLP are projections of the same lines. Versions and licences sit in the deck; the stamps on every section name the validator commit and the X_ITE patch.`,
  run(){drive("setTab(receipt)",()=>self.setTab?(setTab("receipt"),true):null);drive("open Versions drawer",()=>{const d=$("versionsDeck");const det=d&&d.closest("details");if(det){det.open=true;return true}return null});at(3500,()=>drive("setTab(prov)",()=>self.setTab?(setTab("prov"),true):null))}}
];
__tour.steps=TOUR.length;
/* ---------- overlay ---------- */
function ensureBox(){const host=$("tour");if(!host||E.box)return;
  E.tn=el("span",{id:"tn",class:"tn m"});E.th=el("h3",{id:"th"});E.tt=el("p",{id:"tt",class:"tourText"});E.bar=el("i",{id:"tbar"});
  E.prev=el("button",{id:"tPrev",text:"◂ back",onclick:()=>TOUR.prev()});E.next=el("button",{id:"tNext",class:"primary",text:"next ▸",onclick:()=>TOUR.next()});E.stop=el("button",{id:"tStop",text:"stop",title:"Esc",onclick:()=>tourStop()});
  E.box=el("div",{class:"tourBox",role:"dialog","aria-label":"guided tour"},[el("div",{class:"tourHead"},[E.tn,E.th]),E.tt,el("div",{class:"tourBar"},E.bar),el("div",{class:"tourBtns"},[E.prev,E.next,el("span",{class:"sp"}),el("span",{class:"keys",text:"← → step · Esc stops"}),E.stop])]);
  host.appendChild(E.box)}
function bar(ms){const b=E.bar;if(!b)return;b.style.transition="none";b.style.width=ms?"0%":"100%";if(!ms)return;void b.offsetWidth;if(reduced()){b.style.width="100%";return}b.style.transition=`width ${ms}ms linear`;b.style.width="100%"}
function tourShow(i){cancelAll();i=+i||0;if(i<0)i=0;if(i>=TOUR.length){tourStop();return}
  if(ST.i<0){ST.snap=snapshot();__tour.snap=ST.snap;__tour.running=true;__tour.drove=[];const b=$("bTour");if(b)b.classList.add("on");cue("tick")}
  ST.i=i;__tour.i=i;const st=TOUR[i];ensureBox();const host=$("tour");if(host)host.hidden=false;
  txt(E.tn,`${i+1} / ${TOUR.length}`);txt(E.th,st.h);let t="";try{t=st.t()}catch(e){t=""}txt(E.tt,t);txt(E.next,st.pause?"Continue ▸":i===TOUR.length-1?"finish":"next ▸");E.prev.disabled=i===0;
  E.box.dataset.pause=st.pause?"1":"0";__tour.paused=!!st.pause;__tour.drove[i]=[];bar(st.pause?0:st.ms);
  if(st.sec)go(st.sec);cue("tick");try{st.run()}catch(e){console.warn("tour step",i,e)}
  if(!st.pause&&st.ms>0){const tk=ST.tk;ST.cancels.push(later(()=>{if(tk===ST.tk)tourShow(i+1)},st.ms))}}
function tourStop(){const was=ST.i>=0;cancelAll();const host=$("tour");if(host)host.hidden=true;ST.i=-1;__tour.i=-1;__tour.running=false;__tour.paused=false;const b=$("bTour");if(b)b.classList.remove("on");
  if(was){__tour.stops++;restore(ST.snap);ST.snap=null;cue("click")}return was}
Object.assign(TOUR,{start(i){tourShow(i||0)},next(){if(ST.i>=0)tourShow(ST.i+1);else tourShow(0)},prev(){if(ST.i>0)tourShow(ST.i-1)},stop:tourStop,show:tourShow,snapshot,restore,go,
  get running(){return ST.i>=0},get i(){return ST.i}});
/* ---------- chip + keys ---------- */
function chip(){const r=document.querySelector("#mast .mastR");if(!r||$("bTour"))return;const b=el("button",{id:"bTour",class:"chip tourChip",title:"guided tour · 12 steps · ← → step · Esc stops",text:"Tour",onclick:()=>{if(ST.i>=0)tourStop();else tourShow(0)}});
  r.insertBefore(b,$("tierBadge")||null)}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",chip);else chip();
document.addEventListener("keydown",e=>{
  if(e.key==="Escape"){let did=false;if(ST.i>=0){tourStop();did=true}if(self.DIRECTOR&&DIRECTOR.running){DIRECTOR.stop();did=true}if(did){e.preventDefault();e.stopImmediatePropagation()}return}
  if(ST.i<0||(e.target&&/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)))return;
  if(e.key==="ArrowRight"){e.preventDefault();e.stopImmediatePropagation();tourShow(ST.i+1)}else if(e.key==="ArrowLeft"){e.preventDefault();e.stopImmediatePropagation();if(ST.i>0)tourShow(ST.i-1)}},true);
Object.assign(self,{TOUR,tourShow,tourStop,__tour});
})();
