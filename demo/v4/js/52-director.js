/* 52-director.js — DIRECTOR MODE ("Direct me"): a 100 s film over the same sections as the tour (SPEC-v4 "Director mode"; WORKPLAN 52-director).
   Overlay #director (template div) holds the .letterbox element (two 56 px bars, the Barlow title with the letter-spacing animation, the shot counter, the stamp line)
   while the film runs and is emptied when it stops. Chip #bDirect appended to the mast's .mastR before #tierBadge (the frozen mast has no Direct me chip yet: requested).
   Globals: DIRECTOR {start(opts), stop(), go(i), running, shot, shots: SHOTS, rate}, __director.
   Shots: 9 × {t (film second), title, cam(bbox) → keyframes | null, run()}; camera moves go through STAGE.show.cam(keyframes) (08-stage M3 rig: camMove/camPath over
   __cam, a camera-only rig on a measured stage) and STAGE.show.reset() at the end; keyframes are built from STAGE.layerBBox(STAGE.show.browser) at shot time, never typed.
   fx 0 / reduced motion: titles only, no camera moves (the stage is a static frame there). Sound: SOUND.play(kind) only when 54-sound is present and SOUND.isOn (muted by default; its bed belongs to SOUND.on()).
   Stop (button, Esc, or the end of the film) restores scroll, clock, rate, selection, slider, bench text, lightbox and the stage camera through TOUR.snapshot()/TOUR.restore().
   Timers: one later() per shot (no setInterval); DIRECTOR.start({rate}) scales the film clock (tests run it at rate 8); DIRECTOR.go(i) jumps to shot i and reschedules the rest.
   Test hooks: __director {running, shot, shots: 9, titles: [titles shown so far], started, stopped, cams, letterbox}, .letterbox present while running, .dirTitle text, #bDirect.on. */
(function(){
"use strict";
const fx0=()=>!!(self.FX&&FX.level===0);
const reduced=()=>fx0()||(self.matchMedia&&matchMedia("(prefers-reduced-motion:reduce)").matches);
const __director={running:false,shot:-1,shots:0,titles:[],started:0,stopped:0,cams:0,letterbox:false};
const ST={tk:0,cancels:[],snap:null,t0:0,rate:1,shot:-1,lb:null,title:null,sub:null,count:null};
function at(ms,fn){const tk=ST.tk;const c=later(()=>{if(tk===ST.tk)try{fn()}catch(e){console.warn("director later",e)}},Math.max(0,ms));ST.cancels.push(c);return c}
function cancelAll(){ST.tk++;ST.cancels.forEach(c=>{try{c()}catch(e){}});ST.cancels=[]}
const snd=kind=>{if(self.SOUND&&SOUND.isOn&&typeof SOUND.play==="function")try{SOUND.play(kind)}catch(e){}};  /* 54-sound: play(kind) only while the viewer turned sound on */
function go(id){const e=typeof id==="string"?$(id):id;if(!e)return false;try{e.scrollIntoView({block:"start",behavior:reduced()?"auto":"smooth"})}catch(err){e.scrollIntoView()}return true}
const fmtClk=s=>self.fmt&&fmt.clock?fmt.clock(s):String(s);
/* camera helpers: targets from the live bbox (centre + size), never typed poses */
function bbox(){try{const B=self.STAGE&&STAGE.show&&STAGE.show.browser;if(!B||!STAGE.layerBBox)return null;const b=STAGE.layerBBox(B);return b&&!b.empty?b:null}catch(e){return null}}
const add=(a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]];
function cam(frames){if(reduced()||!self.STAGE||!STAGE.show||!STAGE.show.cam||!frames||!frames.length)return Promise.resolve(false);__director.cams++;return STAGE.show.cam(frames).catch(()=>false)}
function dollyIn(bb){const c=bb.center,d=Math.max(bb.size[0],bb.size[1],bb.size[2])||1;return[{position:add(c,[.6*d,.45*d,2.2*d]),lookAt:c,ms:0},{position:add(c,[.25*d,.2*d,1.15*d]),lookAt:c,ms:9000}]}
function wide(bb){const c=bb.center,d=Math.max(bb.size[0],bb.size[1],bb.size[2])||1;return[{position:add(c,[-.4*d,.35*d,2.6*d]),lookAt:c,ms:5000}]}
/* ---------- the nine shots (film seconds; the film is 100 s) ---------- */
const SHOTS=[
 {t:0,title:"The stage",sub:()=>"staged · lights, ground, camera at render time · the measured frame is what the numbers count",
  run(){go("stage");if(self.HEROUI)HEROUI.open(0);if(self.SIM){SIM.setRate(30);if(self.S&&S.paused&&!S.done)SIM.resume()}
    at(400,()=>{if(!fx0()&&self.STAGE&&STAGE.show.setStaged)try{STAGE.show.setStaged(true)}catch(e){}const bb=bbox();if(bb)cam(dollyIn(bb))})}},
 {t:12,title:"The repair",sub:()=>`${(self.LIVESTATS||{}).rep||""} of ${(self.LIVESTATS||{}).bad1||""} first-try failures repaired from the validator's own report`,
  run(){go("morph");if(self.MORPH){const sc=self.S&&S.scenes.slice().reverse().find(s=>s.src==="live"&&s.item&&s.item.A&&s.item.A.length>1&&s.verdict==="valid");try{MORPH.open(sc&&sc.item?{m:sc.item.m,p:sc.item.p}:0)}catch(e){}at(800,()=>{if(MORPH.replay)MORPH.replay()})}}},
 {t:24,title:"The dark seven",sub:()=>`${self.STATS&&STATS.claims&&STATS.claims["c.seven"]?STATS.claims["c.seven"].expected:""} valid finals that draw nothing · FIND IT`,
  run(){go("seven");if(self.SEVEN){try{SEVEN.open(0)}catch(e){}at(1500,()=>{if(SEVEN.findIt)SEVEN.findIt()})}}},
 {t:36,title:"The run as film",sub:()=>{const cs=self.EVENTS&&EVENTS.creditStop;return `x60 through the credit stop${cs?" at "+fmtClk(cs.t):""} · one bar per call`},
  run(){go("film");const cs=self.EVENTS&&EVENTS.creditStop;if(self.SIM){SIM.setRate(60);if(cs)SIM.seekTo(Math.max(0,cs.t-30));if(self.S&&S.paused&&!S.done)SIM.resume()}}},
 {t:50,title:"The wall",sub:()=>"a simulated edit after the fact · the scrubber names the damage within one sweep",
  run(){go("wall");at(1200,()=>{if(self.inject){const sc=inject("edit");if(sc&&self.SIM)SIM.select(sc.id)}});at(6000,()=>{const b=$("bReverify");if(b&&!b.disabled)b.click()})}},
 {t:62,title:"The ladder",sub:()=>"the validator cursor on fork@8c0a457 · re-validating the stored chains from the recorded verdicts",
  run(){go("ladder");if(self.SLIDER)try{SLIDER.set("8c0a457")}catch(e){}at(1500,()=>{const b=$("bRevalidate");if(b&&!b.disabled)b.click()})}},
 {t:74,title:"The bench",sub:()=>"the hero's attempt 1 · the exact report from js-port-of-8dd0d3e · APPLY one named fix",
  run(){go("bench");if(self.BENCH&&BENCH.loadHero)try{BENCH.loadHero()}catch(e){}at(4500,()=>{const a=document.querySelector("#bench .repApply, #bench button[data-fix]");if(a&&!a.disabled)a.click()})}},
 {t:86,title:"The sheet",sub:()=>"every body on the page · two offline passes · the measured frame in the lightbox",
  run(){go("sheet");at(1200,()=>{if(self.SHEET&&SHEET.lightbox&&SHEET.tiles&&SHEET.tiles.size){const k=SHEET.tiles.keys().next().value;try{SHEET.lightbox(k)}catch(e){}}})}},
 {t:94,title:"The rail",sub:()=>"twelve measured heroes · a last wide shot",
  run(){if(self.SHEET&&SHEET.closeLightbox)try{SHEET.closeLightbox()}catch(e){}go("stage");if(self.HEROUI)try{HEROUI.open(0,{noLoad:true})}catch(e){}at(300,()=>{const bb=bbox();if(bb)cam(wide(bb));else if(self.STAGE&&STAGE.show.reset)try{STAGE.show.reset()}catch(e){}})}}
];
const LEN=100;__director.shots=SHOTS.length;
/* ---------- letterbox ---------- */
function ensureLB(){const host=$("director");if(!host)return null;if(ST.lb)return ST.lb;
  ST.title=el("div",{class:"dirTitle"});ST.sub=el("div",{class:"dirSub m"});ST.count=el("span",{class:"n"});
  const stop=el("button",{class:"dirStop",text:"Stop",title:"Esc",onclick:()=>DIRECTOR.stop()});
  ST.lb=el("div",{class:"letterbox","aria-label":"director mode"},[ST.title,ST.sub,el("div",{class:"dirShot"},[ST.count,stop]),el("div",{class:"dirStamp",text:`DIRECTOR · ${LEN} s film · same recorded data · camera moves ${reduced()?"off (fx 0: titles only)":"render-time only"} · js-port-of-8dd0d3e · X_ITE 16.5.0`})]);
  host.textContent="";host.appendChild(ST.lb);host.hidden=false;__director.letterbox=true;return ST.lb}
function showTitle(sh){const t=ST.title;if(!t)return;t.classList.remove("in","out");txt(t,sh.title);let s="";try{s=sh.sub()}catch(e){}txt(ST.sub,s);void t.offsetWidth;t.classList.add("in");__director.titles.push(sh.title);
  at(5200,()=>{t.classList.remove("in");t.classList.add("out")})}
function schedule(from){cancelAll();const now=performance.now();for(let i=from+1;i<SHOTS.length;i++){const ms=(SHOTS[i].t-SHOTS[from].t)*1000/ST.rate;at(ms,()=>play(i))}
  at((LEN-SHOTS[from].t)*1000/ST.rate,()=>DIRECTOR.stop("end"))}
function play(i){const sh=SHOTS[i];if(!sh)return;ST.shot=i;__director.shot=i;if(ST.count)txt(ST.count,`SHOT ${i+1} / ${SHOTS.length} · ${sh.t} s`);showTitle(sh);snd("tick");try{sh.run()}catch(e){console.warn("director shot",i,e)}}
const DIRECTOR={shots:SHOTS,
  start(opts){opts=opts||{};if(ST.shot>=0)return false;if(self.tourStop&&self.__tour&&__tour.running)tourStop();ST.rate=Math.max(.1,+opts.rate||1);__director.rate=ST.rate;
    ST.snap=self.TOUR&&TOUR.snapshot?TOUR.snapshot():{x:scrollX,y:scrollY};__director.started++;__director.running=true;__director.titles=[];__director.cams=0;
    ensureLB();const b=$("bDirect");if(b)b.classList.add("on");
    const from=Math.max(0,Math.min(SHOTS.length-1,opts.from|0));ST.t0=performance.now();play(from);schedule(from);return true},
  go(i){if(ST.shot<0)return false;i=Math.max(0,Math.min(SHOTS.length-1,i|0));play(i);schedule(i);return true},
  stop(why){const was=ST.shot>=0;cancelAll();ST.shot=-1;__director.shot=-1;__director.running=false;const host=$("director");if(host){host.textContent="";host.hidden=true}ST.lb=null;ST.title=null;ST.sub=null;ST.count=null;__director.letterbox=false;
    const b=$("bDirect");if(b)b.classList.remove("on");if(was){__director.stopped++;__director.why=why||"stop";snd("click");
      if(self.SHEET&&SHEET.closeLightbox)try{SHEET.closeLightbox()}catch(e){}if(self.TOUR&&TOUR.restore)TOUR.restore(ST.snap);else{try{scrollTo(ST.snap.x||0,ST.snap.y||0)}catch(e){}if(self.STAGE&&STAGE.show.reset)try{STAGE.show.reset()}catch(e){}}ST.snap=null}return was},
  get running(){return ST.shot>=0},get shot(){return ST.shot},get rate(){return ST.rate}};
function chip(){const r=document.querySelector("#mast .mastR");if(!r||$("bDirect"))return;const b=el("button",{id:"bDirect",class:"chip dirChip",title:`Direct me · a ${LEN} s film over the same data · Esc stops`,text:"Direct me",onclick:()=>{if(ST.shot>=0)DIRECTOR.stop();else DIRECTOR.start()}});
  r.insertBefore(b,$("tierBadge")||null)}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",chip);else chip();
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&ST.shot>=0){DIRECTOR.stop();e.preventDefault()}},true);
Object.assign(self,{DIRECTOR,__director});
})();
