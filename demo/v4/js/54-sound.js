/* 54-sound.js — S6 sonification and the soft bed (SPEC §1 mast chip "Sound: off", §S6, §7 fx table: "sound allowed" only at fx > 0). Wave 3.
   Owns: SOUND = {on(), off(), toggle(), play(kind), allowed(), reason(), isOn} and the mast chip #bSound (a shim: 10-curtain-mast is frozen and ships no Sound chip,
   so this module appends the button to .mastR before #bTheme; request to 10-mast listed in the wave-3 report).
   Muted by default. The AudioContext is constructed only inside on(), i.e. after a user gesture (the chip click or a programmatic SOUND.on() a test drives after a click);
   nothing touches WebAudio at load (hook __sound.ctx === null until then). Synthesis with OscillatorNode / GainNode only, no audio files.
   Events (wired to SIM, never while S.ff): valid chain → tick (sine 880 Hz, 40 ms), invalid chain → thud (triangle 110→55 Hz, 160 ms),
   failed call (EVENTS.failed rows passing the run clock, live17 only; baseline re-taken on reset/seek/mode so a scrub never replays clicks) → click (square 2 kHz, 12 ms),
   integrity detection (S.detected rising) → alarm (two sawtooth bursts 660/880 Hz), plus a quiet bed (two sines 55/82.5 Hz under a 0.1 Hz LFO, −30 dB).
   At most 24 sounds per second; beyond that the cadence is thinned (the firehose at x60 would otherwise be a buzz).
   Honours fx 0 (SOUND.on() refuses, FX.onChange(0) switches off) and prefers-reduced-motion (refuses; a live media change switches off): no sound at all.
   LOOP panel "sound" (bit CLOCK|VERIFY, rateHz 20, DOM-free) polls S.detected and the failed-call count; SIM.on('scene') gives the tick/thud.
   Test hooks: __sound = {ctx (null at load), on, last (kind of the last scheduled sound), counts {tick, thud, click, alarm}, reason, failedSeen, detSeen, bed}.
   v3 had no sound (nothing ported). */
(function(){
"use strict";
const H={ctx:null,on:false,last:null,counts:{tick:0,thud:0,click:0,alarm:0},reason:"muted by default",failedSeen:0,detSeen:0,bed:false,dropped:0};
let master=null,bed=null,chip=null,recent=[];
const reduced=()=>{try{return matchMedia("(prefers-reduced-motion: reduce)").matches}catch(e){return false}};
function allowed(){if(self.FX&&FX.level===0){H.reason="fx 0: sound is off with every other effect";return false}if(reduced()){H.reason="prefers-reduced-motion: no sound";return false}return true}
function ctx(){if(H.ctx)return H.ctx;const AC=self.AudioContext||self.webkitAudioContext;if(!AC){H.reason="WebAudio unavailable";return null}
  try{H.ctx=new AC()}catch(e){H.reason="AudioContext refused: "+e.message;return null}
  master=H.ctx.createGain();master.gain.value=0;master.connect(H.ctx.destination);return H.ctx}
/* ---- synthesis: every voice is an OscillatorNode through its own GainNode envelope into master ---- */
function voice(type,f0,f1,dur,gain,at){const c=H.ctx;const o=c.createOscillator(),g=c.createGain();o.type=type;o.frequency.setValueAtTime(f0,at);if(f1&&f1!==f0)o.frequency.exponentialRampToValueAtTime(f1,at+dur);
  g.gain.setValueAtTime(0.0001,at);g.gain.exponentialRampToValueAtTime(gain,at+Math.min(0.006,dur/4));g.gain.exponentialRampToValueAtTime(0.0001,at+dur);
  o.connect(g);g.connect(master);o.start(at);o.stop(at+dur+0.02);o.onended=()=>{try{o.disconnect();g.disconnect()}catch(e){}}}
const VOICES={
  tick:at=>voice("sine",880,880,0.04,0.08,at),
  thud:at=>voice("triangle",110,55,0.16,0.22,at),
  click:at=>voice("square",2000,2000,0.012,0.06,at),
  alarm:at=>{voice("sawtooth",660,660,0.11,0.12,at);voice("sawtooth",880,880,0.11,0.12,at+0.13);voice("sawtooth",660,660,0.11,0.12,at+0.26)}};
function play(kind){if(!H.on||!H.ctx||!VOICES[kind])return false;const now=performance.now();recent=recent.filter(t=>now-t<1000);
  if(recent.length>=24&&kind!=="alarm"){H.dropped++;return false}recent.push(now);
  try{VOICES[kind](H.ctx.currentTime+0.005)}catch(e){return false}H.last=kind;H.counts[kind]++;return true}
function startBed(){if(bed||!H.ctx)return;const c=H.ctx,g=c.createGain();g.gain.value=0.03;const lfo=c.createOscillator(),lg=c.createGain();lfo.type="sine";lfo.frequency.value=0.1;lg.gain.value=0.015;lfo.connect(lg);lg.connect(g.gain);
  const o1=c.createOscillator(),o2=c.createOscillator();o1.type="sine";o1.frequency.value=55;o2.type="sine";o2.frequency.value=82.5;o1.connect(g);o2.connect(g);g.connect(master);o1.start();o2.start();lfo.start();bed={g,o1,o2,lfo,lg};H.bed=true}
function stopBed(){if(!bed)return;try{bed.o1.stop();bed.o2.stop();bed.lfo.stop();bed.g.disconnect()}catch(e){}bed=null;H.bed=false}
/* ---- switches ---- */
function baseline(){H.failedSeen=failedNow();H.detSeen=self.S?S.detected:0}
function failedNow(){if(!self.S||!self.EVENTS||!EVENTS.failed||S.mode!=="live17")return 0;const t=S.clk;let n=0;for(const f of EVENTS.failed){if((f.t1!=null?f.t1:f.t0)<=t)n++}return n}
function on(){if(!allowed()){paint();return false}const c=ctx();if(!c){paint();return false}
  if(c.state==="suspended"&&c.resume)c.resume().catch(()=>{});H.on=true;H.reason="on";baseline();startBed();
  master.gain.cancelScheduledValues(c.currentTime);master.gain.setValueAtTime(master.gain.value,c.currentTime);master.gain.linearRampToValueAtTime(1,c.currentTime+0.25);paint();return true}
function off(why){if(!H.on){if(why)H.reason=why;paint();return false}H.on=false;H.reason=why||"muted";const c=H.ctx;
  if(c&&master){master.gain.cancelScheduledValues(c.currentTime);master.gain.setValueAtTime(master.gain.value,c.currentTime);master.gain.linearRampToValueAtTime(0,c.currentTime+0.2)}
  stopBed();if(c&&c.suspend)setTimeout(()=>{if(!H.on&&c.suspend)c.suspend().catch(()=>{})},300);paint();return true}
const toggle=()=>H.on?off():on();
function paint(){if(!chip)return;txt(chip,"Sound: "+(H.on?"on":"off"));chip.setAttribute("aria-pressed",H.on?"true":"false");chip.classList.toggle("on",H.on);chip.title=H.on?"sonification on: valid tick, invalid thud, failed-call click, detection alarm, soft bed · click to mute":"muted (default) · "+H.reason+" · synthesised in the page, no audio files"}
function mountChip(){if(chip)return;const host=document.querySelector(".mastR");if(!host)return;chip=document.getElementById("bSound")||el("button",{id:"bSound",class:"chip",type:"button","aria-pressed":"false"});
  if(!chip.parentNode){const bt=document.getElementById("bTheme");if(bt&&bt.parentNode===host)host.insertBefore(chip,bt);else host.appendChild(chip)}chip.addEventListener("click",toggle);paint()}
/* ---- event wiring ---- */
function wireSim(){if(!self.SIM||wireSim.done)return;wireSim.done=true;
  SIM.on("scene",sc=>{if(!H.on||!self.S||S.ff||!sc)return;play(sc.verdict==="valid"?"tick":"thud")});
  ["reset","seek","mode"].forEach(ev=>SIM.on(ev,()=>{if(H.on)baseline()}))}
function poll(){if(!H.on||!self.S||S.ff)return;const d=S.detected||0;if(d>H.detSeen){H.detSeen=d;play("alarm")}else if(d<H.detSeen)H.detSeen=d;
  const f=failedNow();if(f>H.failedSeen){H.failedSeen=f;play("click")}else if(f<H.failedSeen)H.failedSeen=f}
const P=LOOP.register({name:"sound",bit:LOOP.bits.CLOCK|LOOP.bits.VERIFY,rateHz:20,budgetMs:1,draw(){if(!chip)mountChip();wireSim();poll()}});
if(self.FX)FX.onChange(n=>{if(n===0&&H.on)off("fx 0: sound is off with every other effect")});
try{matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change",e=>{if(e.matches&&H.on)off("prefers-reduced-motion: no sound")})}catch(e){}
document.addEventListener("visibilitychange",()=>{const c=H.ctx;if(!c||!H.on)return;if(document.hidden){if(c.suspend)c.suspend().catch(()=>{})}else if(c.resume)c.resume().catch(()=>{})});
const SOUND={on,off:()=>off(),toggle,play,allowed,reason:()=>H.reason,get isOn(){return H.on},panel:P,mountChip};
Object.assign(self,{SOUND,__sound:H});
})();
