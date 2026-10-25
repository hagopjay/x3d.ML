/* 01-loop.js — the one rAF loop (SPEC §7.1, §7.4). Globals: LOOP, __panels.
   Replaces v3's three timers (step 50 ms, frame 100 ms, the 400 ms poller; lines 879–889): no interval timer anywhere.
   LOOP.sim(dt) is installed by 20-sim; panels register with {name, bit, draw, always, budgetMs, degrade, el, rateHz}.
   Test hooks: __panels[name] (the panel record, panels add their counters), LOOP.frames, LOOP.stats.panel[name], LOOP.stats.frame. */
(function(){
"use strict";
const bits={SCENE:1,VERIFY:2,SELECT:4,MODE:8,HOVER:16,CLOCK:32,VAL:64,LANE:128,DATA:256,TIER:512,THEME:1024,RESIZE:2048};
const panels=new Map(),__panels={};
const LOOP={bits,panels,paused:false,running:false,frames:0,now:0,last:0,dirtyBits:0,sim:null,stats:{panel:{},frame:{p95:0,mean:0},fps:0},_once:[],_idle:[]};
const ft=[];let fi=0,fpsN=0,fpsT=0;
function p95(a){if(!a.length)return 0;const s=a.slice().sort((x,y)=>x-y);return s[Math.min(s.length-1,Math.floor(s.length*.95))]}
LOOP.register=function(p){if(!p||!p.name)throw new Error("LOOP.register needs a name");const r=Object.assign({always:false,budgetMs:4,visible:true,rateHz:0,lastDraw:0,draws:0,_t:[]},p);
  if(r.el){r.visible=false;IO.observe(r.el,v=>{r.visible=v;if(v)LOOP.dirtyBits|=r.bit||0},{rootMargin:"120px"})}  /* a panel with an element waits for the observer's first report: no draw before it is near the viewport */
  panels.set(r.name,r);__panels[r.name]=r;LOOP.stats.panel[r.name]={last:0,p95:0,n:0,over:0};return r};
LOOP.unregister=n=>{const r=panels.get(n);if(r&&r.el)IO.unobserve(r.el);panels.delete(n);delete __panels[n]};
LOOP.dirty=b=>{LOOP.dirtyBits|=b};LOOP.dirtyAll=()=>{LOOP.dirtyBits=0x7fffffff};
LOOP.onFrame=f=>LOOP._once.push(f);LOOP.idle=f=>LOOP._idle.push(f);
LOOP.pause=()=>{LOOP.paused=true};LOOP.resume=()=>{LOOP.paused=false;LOOP.last=0;if(!LOOP.running)LOOP.start()};
function tick(now){
  LOOP.frames++;LOOP.now=now;const dt=LOOP.last?Math.min(1000,now-LOOP.last):16;  /* 1 s cap: a hidden tab pauses the loop, so this only guards a stall */LOOP.last=now;const t0=performance.now();
  if(LOOP.sim&&!LOOP.paused&&!document.hidden){try{LOOP.sim(dt)}catch(e){console.error("sim",e);if(self.BOOT)BOOT.error(e,"sim")}}
  const once=LOOP._once;LOOP._once=[];once.forEach(f=>{try{f(now)}catch(e){console.error("onFrame",e)}});
  const d=LOOP.dirtyBits;LOOP.dirtyBits=0;
  for(const p of panels.values()){
    if(!p.visible&&!p.forceDraw)continue;const want=p.always||(d&(p.bit||0))||p.forceDraw;if(!want){continue}
    if(p.rateHz&&now-p.lastDraw<1000/p.rateHz){LOOP.dirtyBits|=d&(p.bit||0);continue}  /* keep the bit for the next allowed frame */
    p.forceDraw=false;const t=performance.now();try{p.draw(now,dt)}catch(e){console.error("draw",p.name,e);if(self.BOOT)BOOT.error(e,"draw "+p.name)}
    const ms=performance.now()-t,st=LOOP.stats.panel[p.name];p.lastDraw=now;p.draws++;st.last=ms;st.n++;p._t.push(ms);if(p._t.length>60)p._t.shift();st.p95=p95(p._t);
    if(ms>p.budgetMs){st.over++;if(p.degrade)try{p.degrade(ms)}catch(e){}}}
  const fms=performance.now()-t0;ft[fi++%120]=fms;if(fi%30===0){LOOP.stats.frame.p95=p95(ft);LOOP.stats.frame.mean=ft.reduce((a,b)=>a+b,0)/ft.length}
  fpsN++;if(now-fpsT>=1000){LOOP.stats.fps=fpsN;fpsN=0;fpsT=now}
  if(fms<8&&LOOP._idle.length){const n=Math.min(2,LOOP._idle.length);for(let i=0;i<n;i++){const f=LOOP._idle.shift();try{f()}catch(e){console.error("idle",e)}}}
  requestAnimationFrame(tick)}
LOOP.start=()=>{if(LOOP.running)return;LOOP.running=true;requestAnimationFrame(tick)};
document.addEventListener("visibilitychange",()=>{if(document.hidden){LOOP.pause();if(self.STAGE&&STAGE.pause)STAGE.pause()}else{LOOP.resume();if(self.STAGE&&STAGE.resume)STAGE.resume();LOOP.dirtyAll()}});
addEventListener("resize",()=>LOOP.dirty(bits.RESIZE|bits.CLOCK));
if(self.THEME)THEME.onChange(()=>LOOP.dirty(bits.THEME|bits.RESIZE));
Object.assign(self,{LOOP,__panels});
})();
