/* 10-curtain-mast.js — S0 curtain, S1 mast, section rail (wave 1 minimal; wave 2 extends this file in place: chips, Tour, Direct me, Sound, phone row).
   Globals: CURTAIN, MAST, RAIL. Reads: S, SIM, MODES, DATA.status, ENV, TIER, BUILD, LM, SECTIONS.list.
   DOM: #curtain, #clk, #scrub, #bPause #bStep #bReset, #speed button[data-r], #runseg button[data-m], #mastHonesty, #envChip, #tierBadge, #versions, #bTheme, #rail.
   Keys: space pause, ←/→ ±10 s, [ ] speed, F failed marks. Test hooks: #clk text, #speed button.on, S.rate. */
(function(){
"use strict";
const RATES=[1,4,10,30,60];
const CURTAIN={lifted:false,t0:0,
  start(){const c=$("curtain");if(!c||self.FX&&FX.level===0){CURTAIN.lifted=true;return}CURTAIN.t0=performance.now();c.hidden=false;txt("curtainBadge",self.TIER?TIER.badgeText():"");CURTAIN.update();setTimeout(()=>CURTAIN.lift("2.5 s"),2500)},
  update(){const c=$("curtain");if(!c||CURTAIN.lifted)return;const st=self.DATA&&DATA.status["live.core"]||{},f=st.bytes?Math.min(1,st.got/st.bytes):0;const bar=c.querySelector(".ctBar i");if(bar)bar.style.width=(f*100).toFixed(0)+"%";
    txt(c.querySelector(".ctLines"),`X_ITE 16.5.0 · own files${self.X3D?" · loaded":" · loading"}\nvalidator js-port-of-8dd0d3e · ${self.VAL&&VAL.mode==="full"?"loaded":"not loaded"}\nrenderer: ${self.ENV&&ENV.renderer||"unknown"} · fx ${self.FX?FX.level:"?"}`);txt("curtainBadge",self.TIER?TIER.badgeText():"")},
  lift(why){const c=$("curtain");if(!c||CURTAIN.lifted)return;CURTAIN.lifted=true;CURTAIN.why=why||"";c.classList.add("lift");setTimeout(()=>{c.hidden=true},450)}};
const MAST={
  init(){const sc=$("scrub");if(sc)sc.addEventListener("input",e=>{if(self.SIM){SIM.seekTo(+e.target.value);S.paused=true}});
    const bp=$("bPause");if(bp)bp.onclick=()=>SIM.toggle();const bs=$("bStep");if(bs)bs.onclick=()=>{if(S){SIM.seekTo(S.clk+10);S.paused=true}};const br=$("bReset");if(br)br.onclick=()=>SIM.restart();
    const sp=$("speed");if(sp)sp.onclick=e=>{const b=e.target.closest("button[data-r]");if(b)SIM.setRate(+b.dataset.r)};
    const rs=$("runseg");if(rs){rs.onclick=e=>{const b=e.target.closest("button[data-m]");if(b&&!b.hidden&&MODES.get(b.dataset.m))MODES.set(b.dataset.m)};const r24=rs.querySelector("[data-m=run24]");if(r24)r24.hidden=!(BUILD&&BUILD.has_run24)}
    const bt=$("bTheme");if(bt)bt.onclick=()=>THEME.toggle();
    MAST.versions();
    document.addEventListener("keydown",e=>{if(e.target&&/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||!self.S)return;
      if(e.code==="Space"){e.preventDefault();SIM.toggle()}else if(e.key==="ArrowLeft"){SIM.seekTo(S.clk-10)}else if(e.key==="ArrowRight"){SIM.seekTo(S.clk+10)}
      else if(e.key==="["){SIM.setRate(RATES[Math.max(0,RATES.indexOf(S.rate)-1)]||1)}else if(e.key==="]"){SIM.setRate(RATES[Math.min(RATES.length-1,RATES.indexOf(S.rate)+1)]||60)}
      else if(e.key==="f"||e.key==="F"){S.flags.failed=!S.flags.failed;LOOP.dirty(LOOP.bits.SCENE)}});
    LOOP.register({name:"mast",bit:LOOP.bits.CLOCK|LOOP.bits.MODE|LOOP.bits.TIER|LOOP.bits.DATA,rateHz:12,draw:MAST.update});
    if(self.ENV)ENV.onChange(()=>{const c=$("envChip");if(c)c.title=ENV.short()});if(self.TIER)TIER.on(()=>TIER.badge("tierBadge"))},
  versions(){const v=$("versions");if(!v||!BUILD||!BUILD.versions)return;v.textContent="";BUILD.versions.forEach(x=>{const label=`${x.v}${x.label?" "+x.label:""}`;
    if(x.id&&!BUILD.share&&!x.this)v.appendChild(el("a",{href:"https://claude.ai/artifact/"+x.id,target:"_blank",rel:"noopener",text:label,title:x.title||""}));else v.appendChild(el("span",{text:label+(x.this?" (this)":""),title:x.title||""}))})},
  update(){if(!self.S)return;const tmax=SIM.tmax();txt("clk",`${fmt.clock(S.clk)} / ${fmt.clock(tmax)}`);const sc=$("scrub");if(sc&&document.activeElement!==sc){if(+sc.max!==Math.round(tmax))sc.max=Math.round(tmax)||1;sc.value=Math.round(S.clk)}
    txt("bPause",S.done?"Restart":S.paused?"Play":"Pause");document.querySelectorAll("#speed button[data-r]").forEach(b=>b.classList.toggle("on",+b.dataset.r===S.rate));document.querySelectorAll("#runseg button[data-m]").forEach(b=>b.classList.toggle("on",b.dataset.m===S.mode));
    const m=MODES.get(S.mode);txt("mastHonesty",(m&&m.honesty)||"");txt("tierBadge",self.TIER?TIER.badgeText():"");if(!CURTAIN.lifted)CURTAIN.update()}};
const RAIL={init(){const r=$("rail");if(!r)return;r.textContent="";document.querySelectorAll("main section[id]").forEach(sec=>{const a=el("a",{href:"#"+sec.id,data:{s:sec.id}},el("span",{text:(sec.querySelector(".sh h2")||{}).textContent||sec.id}));r.appendChild(a);
    IO.observe(sec,v=>{a.classList.toggle("on",v)},{rootMargin:"-40% 0px -50% 0px"})})}};
Object.assign(self,{CURTAIN,MAST,RAIL});
})();
