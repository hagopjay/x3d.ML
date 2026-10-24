/* 06-env.js — Step 0 probes (SPEC §9). Globals: ENV, envTable. Probes at load: eval (the one tagged line), WebAssembly.validate (8-byte module) +
   instantiate (40-byte module exporting main()=42), new Worker("workers/probe.js"), a blob worker, WEBGL_debug_renderer_info, DecompressionStream, crypto.subtle.
   ENV.textDraws is filled by STAGE.textProbe(); ENV.caps by TIER.resolve(). envTable(el) renders the 7-row Step 0 table with the fallback in use.
   Test hooks: ENV (plain object), ENV.ready (Promise), #env table rows `tr[data-k]`. */
(function(){
"use strict";
const fns=[];
const ENV={eval:null,wasm:null,wasmInstantiate:null,worker:null,workerBlob:null,gl:null,renderer:null,vendor:null,webgl2:null,dpr:devicePixelRatio||1,textDraws:null,decompression:typeof DecompressionStream!=="undefined",subtle:!!(self.crypto&&crypto.subtle),
  caps:{sample:null,files:null,user:null,downloads:null},reducedMotion:matchMedia("(prefers-reduced-motion: reduce)").matches,webdriver:!!navigator.webdriver,saveData:!!(navigator.connection&&navigator.connection.saveData),width:innerWidth,ua:navigator.userAgent,notes:[],ready:null,done:false,
  onChange(f){fns.push(f)},_emit(){fns.forEach(f=>{try{f(ENV)}catch(e){}});if(self.LOOP)LOOP.dirty(LOOP.bits.DATA)}};
const T=(ms,p)=>Promise.race([p,new Promise((_,rej)=>setTimeout(()=>rej(new Error("timeout "+ms+" ms")),ms))]);
function probeEval(){try{return(new Function("return 1"))()===1}catch(e){ENV.notes.push("eval: "+String(e.message||e).slice(0,100));return false}} /*@env-probe*/
async function probeWasm(){try{ENV.wasm=WebAssembly.validate(new Uint8Array([0,97,115,109,1,0,0,0]))}catch(e){ENV.wasm=false;ENV.notes.push("wasm validate: "+String(e.message||e).slice(0,100))}
  try{const m=await WebAssembly.instantiate(new Uint8Array([0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,3,2,1,0,7,8,1,4,109,97,105,110,0,0,10,6,1,4,0,65,42,11]));ENV.wasmInstantiate=m.instance.exports.main()===42}catch(e){ENV.wasmInstantiate=false;ENV.notes.push("wasm instantiate: "+String(e.message||e).slice(0,100))}}
/* Worker probes: PROBE_MS patience, then resolve "blocked (no answer yet)" but KEEP listening — a boot under SwiftShader with eleven parts
   decoding can answer a worker ping after 5–8 s; a late answer flips the field to true and re-emits (the Step 0 table re-renders). */
const PROBE_MS=12000;
function probeAny(tag,make,field){return new Promise(res=>{let w;try{w=make()}catch(e){ENV[field]=false;ENV.notes.push(tag+": "+String(e.message||e).slice(0,100));return res()}
  let late=false;const t0=performance.now();const note=m=>{ENV.notes=ENV.notes.filter(n=>!n.startsWith(tag+":"));if(m)ENV.notes.push(tag+": "+m)};
  const fin=(ok,r,msg)=>{clearTimeout(t);ENV[field]=ok;ENV[field+"Ms"]=Math.round(performance.now()-t0);if(field==="worker")ENV.workerDetail=r||null;note(msg);try{w.terminate()}catch(e){}if(late)ENV._emit();else res()};
  const t=setTimeout(()=>{late=true;ENV[field]=false;note("no answer in "+PROBE_MS+" ms (busy boot?) — still listening");res()},PROBE_MS);
  w.onmessage=m=>fin(!!(m.data&&m.data.pong==="hi"),m.data,null);w.onerror=e=>fin(false,null,String(e&&e.message||"worker error").slice(0,100));w.postMessage("hi")})}
function probeWorker(){return probeAny("worker",()=>new Worker("workers/probe.js"),"worker")}
function probeBlobWorker(){return probeAny("blob worker",()=>new Worker(URL.createObjectURL(new Blob(["self.onmessage=e=>{let w=false;try{new WebAssembly.Module(new Uint8Array([0,97,115,109,1,0,0,0]));w=true}catch(x){}self.postMessage({pong:e.data,wasm:w})}"],{type:"text/javascript"}))),"workerBlob")}
function probeGl(){try{const c=document.createElement("canvas"),g2=c.getContext("webgl2"),gl=g2||c.getContext("webgl");if(!gl){ENV.gl="none";ENV.renderer="none";return}ENV.webgl2=!!g2;
  const dbg=gl.getExtension("WEBGL_debug_renderer_info");ENV.renderer=String(dbg?gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER));ENV.vendor=String(dbg?gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL):gl.getParameter(gl.VENDOR));
  ENV.gl=/swiftshader|llvmpipe|software|mesa offscreen|basic render/i.test(ENV.renderer)?"software":"gpu";const ext=gl.getExtension("WEBGL_lose_context");if(ext)ext.loseContext()}catch(e){ENV.gl="none";ENV.renderer="none";ENV.notes.push("webgl: "+String(e.message||e).slice(0,100))}}
ENV.probe=function(){if(ENV.ready)return ENV.ready;ENV.ready=(async()=>{ENV.eval=probeEval();probeGl();if(self.FX){FX.gl=ENV.gl;FX.auto()}ENV._emit();
  await Promise.all([probeWasm(),probeWorker(),probeBlobWorker()]);ENV.done=true;ENV._emit();return ENV})();return ENV.ready};
ENV.short=()=>`eval ${ENV.eval==null?"?":ENV.eval?"ok":"blocked"} · wasm ${ENV.wasmInstantiate==null?"?":ENV.wasmInstantiate?"ok":"blocked"} · worker ${ENV.worker==null?"?":ENV.worker?"ok":ENV.workerBlob?"blob":"blocked"} · ${ENV.gl||"?"} ${ENV.renderer||""} · dpr ${ENV.dpr}`;
function rows(){const c=ENV.caps,capTxt=["sample","files","user","downloads"].map(k=>k+(c[k]===null?" ×":c[k]?" ✓":" ?")).join(" · ");
  const st=(v,ok,bad,pend)=>v==null?(pend||"probing…"):v?ok:bad;
  return[["eval",st(ENV.eval,"allowed","blocked"),ENV.eval===false?"X_ITE Text glyphs not drawn (woff2 decoder needs eval); scenes with <Text> excluded from REPRODUCED; no other library on the page needs it":"X_ITE fonts available"],
   ["wasm",st(ENV.wasmInstantiate,"instantiate ok","blocked"),ENV.wasmInstantiate===false?"js-port cannot run (libxml2-wasm): VAL.mode none, Bench read-only, live lane off, recorded verdicts only":"js-port can run (VAL.mode "+(self.VAL?VAL.mode:"?")+")"],
   ["worker (own file)",st(ENV.worker,"ok",ENV.workerBlob?"blocked · blob worker ok":"blocked"),ENV.worker===false?(ENV.workerBlob?"same code through a blob: worker":"workers: unavailable, main thread in 8 ms slices"):"hash worker "+(self.HASH?HASH.mode:"?")],
   ["WebGL renderer",ENV.renderer==null?"probing…":`${ENV.gl} · ${ENV.renderer}${ENV.webgl2?" · WebGL2":""}`,ENV.gl==="software"?"fx 0: static page, lights-only rig, one canvas; raster live row labelled 'same answer, slower device'":ENV.gl==="none"?"stage shows the measured JPEGs; every number unchanged":"fx "+(self.FX?FX.level:"?")],
   ["capabilities",capTxt,c.sample===null?"S5 live lane: one line (no model granted); ":"live lane available; "+(c.files===null?"S15 absent":"members' desk")],
   ["fonts in Text nodes",ENV.textDraws==null?"not probed yet":ENV.textDraws?"draw":"blank",ENV.textDraws===false?"Text scenes get the chip 'text glyphs need eval: not drawn in this viewer'":"1-frame Text probe in STAGE.measure"],
   ["audio",self.__sound&&__sound.ctx?"context created":"muted until a gesture","AudioContext only after a click; sound off by default"],
   ["decode",ENV.decompression?"DecompressionStream":"fflate 0.8.2 fallback",ENV.subtle?"crypto.subtle sha-256":"sha256b (pure JS) for part checks"]]}
function envTable(target){const host=typeof target==="string"?$(target):target;if(!host)return;let tb=host.querySelector("table");
  if(!tb){tb=el("table",{class:"envTable"},[el("thead",null,el("tr",null,[el("th",{text:"probe"}),el("th",{text:"this viewer"}),el("th",{text:"fallback in use"})])),el("tbody")]);host.appendChild(tb);host.appendChild(el("div",{class:"note m",data:{k:"env-note"}}))}
  const body=tb.querySelector("tbody");const rs=rows();while(body.children.length<rs.length){const tr=el("tr",{data:{k:""}},[el("td"),el("td"),el("td")]);body.appendChild(tr)}
  rs.forEach((r,i)=>{const tr=body.children[i];tr.dataset.k=r[0];txt(tr.children[0],r[0]);txt(tr.children[1],r[1]);txt(tr.children[2],r[2])});
  txt(host.querySelector("[data-k=env-note]"),(ENV.notes.length?ENV.notes.join(" · ")+" · ":"")+(ENV.webdriver?"webdriver (test run) · ":"")+`${ENV.width} px · dpr ${ENV.dpr}${ENV.reducedMotion?" · reduced motion":""}`)}
Object.assign(self,{ENV,envTable});
})();
