/* 99-boot.js — boot order (ARCHITECTURE §3). Global: BOOT {t0, log[], error(e, where), phase}. Wave 2 adds section mounts through SECTIONS.register in its own
   modules, never by editing this file. Global error hook: window.onerror / unhandledrejection append one line to BOOT.log, shown in #under .errors by 46-footer. */
(function(){
"use strict";
const BOOT={t0:performance.now(),log:[],phase:"start",error(e,where){const m=`${where||"error"}: ${String(e&&e.message||e).slice(0,200)}`;if(!BOOT.log.includes(m))BOOT.log.push(m);if(BOOT.log.length>40)BOOT.log.shift();if(self.LOOP)LOOP.dirty(LOOP.bits.DATA)}};
self.BOOT=BOOT;
addEventListener("error",e=>{const m=String(e.message||"");if(/ResizeObserver loop/.test(m))return;BOOT.error(e.error||m,"uncaught")});
addEventListener("unhandledrejection",e=>{const r=e.reason,m=String(r&&r.message||r);if(r instanceof Event||/Failed to fetch|mikktspace|font|stylesheet/i.test(m))return;BOOT.error(r,"unhandled")});
/* wave-1 placeholders for sections no module has claimed yet: an honest line, never a greyed stub of a feature */
const PLACEHOLDER={stage:["The stage","hero · castle an AI wrote · wave 2 (12-hero) renders the four proofs here",{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline"},"C"],
  morph:["The repair morph","attempt 1 → final · wave 2 (14-morph)",{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline"},"C"],
  seven:["The dark seven","valid on the fork, nothing drawn · wave 2 (16-seven)",{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline"},"C"],
  lane:["Live tether lane","write one yourself · wave 2 (18-lane)",{source:"LIVE: your Claude",validator:"js-port-of-8dd0d3e here",renderer:"none"},"S"],
  film:["The run as film","358 calls on the run's own clock · wave 2 (22-waterfall, 24-scope)",{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none"},"C"],
  raster:["First-light raster","wave 2 (26-raster)",{source:"RECORDED 17 Oct",validator:"none",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline"},"C"],
  matrix:["Prompt × model matrix + error taxonomy","wave 2 (28-matrix-flow)",{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none"},"S"],
  stream:["Firehose + inspector","wave 2 (30-firehose, 32-inspector)",{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline"},"C"],
  bench:["The bench","edit a scene, get the exact report · wave 2 (34-bench)",{source:"RE-RUN HERE",validator:"js-port-of-8dd0d3e here",renderer:"none"},"C"],
  wall:["Integrity wall + tamper arena","wave 2 (36-wall)",{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none"},"C"],
  ladder:["Validator ladder","the verdict braid · wave 2 (38-ladder)",{source:"RECORDED per commit",validator:"fork@8dd0d3e recorded",renderer:"none"},"C"],
  sheet:["Contact sheet","two render passes · wave 2 (40-sheet)",{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline"},"C"],
  suite:["Blender export suite + physics ledger","wave 2 (42-suite)",{source:"RECORDED 17 Oct (owner's machine)",validator:"fork@fa0b389 recorded",renderer:"none"},"C"],
  desk:["Members' desk","files capability · wave 2 (44-desk)",{source:"RECORDED 24 Oct",validator:"fork@8dd0d3e recorded",renderer:"none"},"S"]};
function placeholders(){for(const id in PLACEHOLDER){if(SECTIONS.get(id))continue;const[title,unit,stamps,grade]=PLACEHOLDER[id];SECTIONS.register({id,header:{title,unit,stamps,grade,honesty:"section not built in wave 1; the header stamps are the contract its module must keep"},
  mount(sec){const sb=sec.querySelector(".sb");if(sb&&!sb.children.length&&id!=="stage")sb.appendChild(el("div",{class:"placeholder",text:unit}))}})}}
async function boot(){
  try{BOOT.phase="fx";THEME.init();FX.init();
    BOOT.phase="env";ENV.probe().then(()=>LOOP.dirty(LOOP.bits.DATA));
    BOOT.phase="tier";TIER.resolve().then(()=>TIER.badge("tierBadge"));TIER.badge("tierBadge");
    HASH.init();
    BOOT.phase="sections";placeholders();SECTIONS.mountAll();DATA.on("*",()=>CLAIMS.runReady());MAST.init();RAIL.init();
    BOOT.phase="loop";SIM.start("live17");LOOP.start();
    BOOT.phase="curtain";CURTAIN.start();
    BOOT.phase="data";const dataP=DATA.start().catch(()=>{});
    BOOT.phase="xite";let n=0;while(!self.X3D&&n++<200)await later(50);
    if(self.X3D){STAGE.init().then(async()=>{CURTAIN.lift("stage ready");if(STAGE.show.ok&&HERO&&HERO.items&&HERO.items[0]){const r=await STAGE.show.load(HERO.items[0].body,{scene:"hero"});txt("stageMsg",r.ok?`hero ${HERO.items[0].p} · ${HERO.items[0].m} · measured frame ${fmt.pct(HERO.items[0].nb)} offline · this browser: measuring…`:r.err||"")}
      /* fx 0 (software GL): every X_ITE load compiles shaders through SwiftShader in multi-second main-thread tasks; let the parts decode first (≤ 60 s) so the data is in before the hero measure */
      if(FX.level===0)await Promise.race([DATA.ready("suite").catch(()=>{}),later(60000)]);
      if(STAGE.measure.ok&&HERO&&HERO.items&&HERO.items[0]){const m=await STAGE.measure.show(HERO.items[0].body);if(!m.cancelled){BOOT.heroMeasure=m;txt("stageMsg",`hero ${HERO.items[0].p} · ${HERO.items[0].m} · counted frame ${fmt.pct(HERO.items[0].nb)} X_ITE 16.5.0 offline · 16.5.1 offline ${fmt.pct(HERO.items[0].nb151)} · this browser: ${m.err?"X_ITE refused":m.noFrame?"no frame yet":fmt.pct(m.nb)} · ${ENV.renderer||"?"}`)}
        LOOP.idle(()=>STAGE.textProbe())}}).catch(e=>BOOT.error(e,"stage"))}
    else{BOOT.error("xite/x_ite.min.js did not load in 10 s","xite");CURTAIN.lift("no X_ITE");txt("stageMsg","X_ITE did not start in this viewer (xite/x_ite.min.js); the measured JPEGs are the counted frames")}
    BOOT.phase="val";VAL.init({eager:FX.level>0});
    await dataP;BOOT.phase="ready";BOOT.ms=Math.round(performance.now()-BOOT.t0)}
  catch(e){BOOT.error(e,"boot "+BOOT.phase);console.error("boot",e)}}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
