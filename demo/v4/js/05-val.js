/* 05-val.js — VAL facade over the js-port (SPEC §6). STUB in wave 1: the surface is frozen (ARCHITECTURE §4 / 05); M4 fills VAL._load with the
   workers/val.worker.js path (classic → blob → main thread), X3DVAL.load({base:"jsval/", precompile:["4.0"], read: xsd parts via DATA.text, onProgress}),
   memo by sha (Map 2,000), VAL.validateMany, VAL.canary over DRIFT.v8dd0d3e. Until then VAL.mode === "unloaded" and VAL.init() resolves "none"
   with a reason, so every caller branches honestly (Bench read-only, lane off, ladder recorded-only).
   Globals: VAL, reportHtml, repairText, codesOfRes. The label is "js-port-of-8dd0d3e", never "fork@". */
(function(){
"use strict";
const fns=[];
const VAL={label:"js-port-of-8dd0d3e",mode:"unloaded",reason:"validator not loaded yet",ready:null,memo:new Map(),worker:null,info:null,
  on(f){fns.push(f)},
  _set(mode,reason){VAL.mode=mode;VAL.reason=reason||"";fns.forEach(f=>{try{f(mode)}catch(e){}});if(self.LOOP)LOOP.dirty(LOOP.bits.VAL)},
  /* M4 replaces _load. It must resolve to "full" | "semantic-only" | "none" and call VAL._set. */
  _load:async function(){VAL._set("none","js-port wiring not shipped yet (M4): the exact validator cannot run in this view");return"none"},
  init(opts){if(VAL.ready)return VAL.ready;VAL.opts=opts||{};VAL.ready=VAL._load().catch(e=>{VAL._set("none","validator failed to load: "+String(e&&e.message||e).slice(0,120));return"none"});return VAL.ready},
  async validate(xml){await VAL.init();if(VAL.mode!=="full"&&VAL.mode!=="semantic-only")throw new Error("VAL unavailable: "+VAL.reason);return VAL._validate(xml)},
  _validate:async function(){throw new Error("VAL._validate not wired")},
  async validateMany(items,onProgress){const out=new Map();for(let i=0;i<items.length;i++){const r=await VAL.validate(items[i].xml);out.set(items[i].id,r);if(onProgress)onProgress(i+1,items.length,r)}return out},
  async canary(){await VAL.init();if(VAL.mode==="none")return{bodies:0,flips:[],groups:{live:0,replay:0,ledger:0},reason:VAL.reason};throw new Error("VAL.canary not wired (M4)")},
  compare(res,recordedOk,recordedCodes){if(!res)return"differs";const okSame=!!res.valid===!!recordedOk;if(!okSame)return"differs";const a=codesOfRes(res).slice().sort().join(","),b=(recordedCodes||[]).slice().sort().join(",");return a===b?"agrees":"differs"}};
function codesOfRes(res){const c=[];if(!res)return c;if(res.xsd&&res.xsd.errors&&res.xsd.errors.length)c.push("xsd");((res.semantic&&res.semantic.errors)||[]).forEach(e=>{const id=e&&(e.id||e.code);if(id&&!c.includes(id))c.push(id)});return c}
function reportHtml(res){if(!res)return'<span class="note">no report</span>';const xe=(res.xsd&&res.xsd.errors)||[],se=(res.semantic&&res.semantic.errors)||[],fx=(res.semantic&&res.semantic.fixes)||[];
  let h=`<div class="rep"><span class="pill ${res.valid?"p-ok":"p-bad"}">${res.valid?"VALID":"INVALID"}</span> on ${esc(VAL.label)}${res.ms!=null?` in ${fmt.ms(res.ms)}`:""}`;
  xe.slice(0,8).forEach(l=>{h+=`<br><b>xsd</b> ${esc(String(l).slice(0,300))}`});se.slice(0,10).forEach(e=>{h+=`<br><b>${esc(e.id||e.code||"semantic")}</b> ${esc(String(e.message||e.msg||e).slice(0,300))}`});
  fx.slice(0,6).forEach(f=>{h+=`<br><i>fix</i> ${esc(String(f.text||f.message||f).slice(0,300))}`});return h+"</div>"}
function repairText(res){const T=(typeof SYS!=="undefined"&&SYS&&SYS.REPAIR)||"The validator rejected the scene. Fix every error and return the whole corrected X3D document.\nXSD errors:\n{xsd}\nSemantic errors:\n{sem}\n";
  const xsd=((res.xsd&&res.xsd.errors)||[]).join("\n")||"none",sem=((res.semantic&&res.semantic.errors)||[]).map(e=>e.line||e.message||String(e)).join("\n")||"none";return T.replace("{xsd}",xsd).replace("{sem}",sem)}
Object.assign(self,{VAL,reportHtml,repairText,codesOfRes});
})();
