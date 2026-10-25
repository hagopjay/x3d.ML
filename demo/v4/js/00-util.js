/* 00-util.js — shared helpers (ARCHITECTURE §4 / 00).
   Globals: $, el, txt, cssv, fitCanvas, fmt, esc, unesc, mulberry32, later, debounce, gzRead, sectionHeader, stamp, honesty, gradeChip, IO, THEME, FX, SECTIONS, UTIL.
   Ported from v3: esc/unesc (lines 293–294), mulberry (348), clock (231), pc (486), cssv (529), later (893).
   Test hooks: window.__FX (= FX), SECTIONS.list. No DOM is touched at load except html[data-theme] / html[data-fx] by THEME.init / FX.init. */
(function(){
"use strict";
const $=id=>document.getElementById(id);
function el(tag,attrs,children){const e=document.createElement(tag);if(attrs)for(const k in attrs){const v=attrs[k];if(v==null)continue;
  if(k==="class")e.className=v;else if(k==="text")e.textContent=v;else if(k==="html")e.innerHTML=v;else if(k==="data")for(const d in v)e.dataset[d]=v[d];else if(k==="style"&&typeof v==="object")Object.assign(e.style,v);else if(k.startsWith("on")&&typeof v==="function")e.addEventListener(k.slice(2),v);else e.setAttribute(k,v)}
  if(children!=null)(Array.isArray(children)?children:[children]).forEach(c=>{if(c==null)return;e.appendChild(typeof c==="string"?document.createTextNode(c):c)});return e}
function txt(t,s){const e=typeof t==="string"?$(t):t;if(!e)return false;s=String(s);if(e.textContent===s)return false;e.textContent=s;return true}
const esc=s=>String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const unesc=s=>String(s).replace(/&quot;/g,'"').replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
/* tokens, cached per theme */
let cssCache=new Map();
function cssv(n){let v=cssCache.get(n);if(v===undefined){v=getComputedStyle(document.documentElement).getPropertyValue(n).trim();cssCache.set(n,v)}return v}
function fitCanvas(c,w,h){const dpr=Math.min(3,window.devicePixelRatio||1),W=Math.max(1,Math.round(w*dpr)),H=Math.max(1,Math.round(h*dpr));
  if(c.width!==W||c.height!==H){c.width=W;c.height=H;c.style.height=h+"px"}const ctx=c.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);return{ctx,w,h,dpr}}
const fmt={
  int:n=>n==null?"—":Math.round(n).toLocaleString("en-US"),
  num:(n,d=0)=>n==null?"—":(+n).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d}),
  pct:(x,d=1)=>x==null?"—":(x*100).toFixed(d)+"%",
  ms:ms=>ms==null?"—":ms<1000?Math.round(ms)+" ms":ms<10000?(ms/1000).toFixed(1)+" s":ms<600000?Math.round(ms/1000)+" s":Math.round(ms/60000)+" min",
  usd:v=>v==null?"—":"$"+(+v).toFixed(v<1?4:2),
  bytes:n=>n==null?"—":n<1024?n+" B":n<1048576?(n/1024).toFixed(1)+" KB":(n/1048576).toFixed(2)+" MB",
  clock:t=>{t=Math.max(0,Math.round(+t||0));return String(Math.floor(t/60)).padStart(2,"0")+":"+String(t%60).padStart(2,"0")}
};
function mulberry32(a){return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
/* later(ms) → Promise; later(fn, ms) → cancel handle */
function later(a,b){if(typeof a==="function"){const h=setTimeout(a,b||0);return()=>clearTimeout(h)}return new Promise(r=>setTimeout(r,a||0))}
function debounce(fn,ms){let h=0;const d=(...a)=>{clearTimeout(h);h=setTimeout(()=>fn(...a),ms)};d.cancel=()=>clearTimeout(h);return d}
const UTIL={
  hex:b=>Array.from(b,x=>x.toString(16).padStart(2,"0")).join(""),
  b64ToBytes:s=>{const bin=atob(s.replace(/\s+/g,"")),o=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)o[i]=bin.charCodeAt(i);return o},
  median:a=>{a=a.filter(v=>v!=null).slice().sort((x,y)=>x-y);return a.length?a[a.length>>1]:null},
  sum:(a,f)=>a.reduce((x,y)=>x+(f?f(y):y),0),
  clamp:(v,a,b)=>Math.min(b,Math.max(a,v)),
  qs:n=>new URLSearchParams(location.search).get(n),
  pc:(a,b)=>b?(100*a/b).toFixed(1)+"%":"-",
  sortedJson:o=>JSON.stringify(o,(k,v)=>v&&typeof v==="object"&&!Array.isArray(v)?Object.keys(v).sort().reduce((r,kk)=>(r[kk]=v[kk],r),{}):typeof v==="number"?Math.round(v*1e6)/1e6:v)
};
/* gzip+base64 own file → text. DecompressionStream first; fflate 0.8.2 (cdnjs, pinned) only when it is missing. */
let fflateP=null;
function fflateLoad(){return fflateP||(fflateP=new Promise((res,rej)=>{if(self.fflate)return res(self.fflate);const s=document.createElement("script");s.src="https://cdnjs.cloudflare.com/ajax/libs/fflate/0.8.2/fflate.min.js";s.onload=()=>self.fflate?res(self.fflate):rej(new Error("fflate did not define itself"));s.onerror=()=>rej(new Error("fflate fallback blocked"));document.head.appendChild(s)}))}
async function gunzipBytes(bytes){
  if(typeof DecompressionStream!=="undefined"){const ds=new DecompressionStream("gzip"),w=ds.writable.getWriter();const out=new Response(ds.readable).arrayBuffer();
    w.write(bytes).then(()=>w.close()).catch(()=>{});  /* the reader side reports the real error; the writer's rejection is not left unhandled */
    return new Uint8Array(await out)}
  const ff=await fflateLoad();return ff.gunzipSync(bytes)}
/* STALL_MS without a byte aborts the fetch with Error("stalled: …"); 03-data retries such a part once and says so in DATA.messages (a shared
   box under SwiftShader has shown a part sitting at 0 bytes for seconds; a real viewer's network can do the same). */
const STALL_MS=20000;
async function fetchB64(url,onProgress){
  const ac=typeof AbortController!=="undefined"?new AbortController():null;let got=0,total=0,timer=null;
  const arm=()=>{if(!ac)return;clearTimeout(timer);timer=setTimeout(()=>ac.abort(),STALL_MS)};arm();
  try{
  const r=await fetch(url,ac?{signal:ac.signal}:undefined);if(!r.ok)throw new Error(`${url}: HTTP ${r.status}`);
  total=+r.headers.get("content-length")||0;if(!r.body||!onProgress){const text=await r.text();return{text,total}}
  const rd=r.body.getReader(),chunks=[];for(;;){const{done,value}=await rd.read();if(done)break;chunks.push(value);got+=value.length;arm();onProgress(got,total)}
  const all=new Uint8Array(got);let o=0;chunks.forEach(c=>{all.set(c,o);o+=c.length});return{text:new TextDecoder().decode(all),total:got}}
  catch(e){if(ac&&ac.signal.aborted)throw new Error(`stalled: no bytes for ${STALL_MS/1000} s (${got}/${total||"?"} B of ${url})`);throw e}
  finally{clearTimeout(timer)}}
/* a part that fetched but will not decode is a corrupt file, not a network error: the message says "decode failed", never "Failed to fetch" */
async function gzReadBytes(url,opts){const{text}=await fetchB64(url,opts&&opts.onProgress);let b;try{b=UTIL.b64ToBytes(text)}catch(e){throw new Error("decode failed: base64: "+String(e&&e.message||e))}
  try{return await gunzipBytes(b)}catch(e){throw new Error("decode failed: gzip: "+String(e&&e.message||e))}}
async function gzRead(url,opts){return new TextDecoder().decode(await gzReadBytes(url,opts))}
/* stamps: closed vocabulary (SPEC rule 2). An unknown value renders with .stamp-unknown and check_v4.py fails on it. */
const VOCAB={
  source:["RECORDED 11 Oct","RECORDED 17 Oct","RECORDED 24 Oct","RE-RUN HERE","LIVE: your Claude","BAKED: Blender Cycles","MODELED","RECORDED per commit","RECORDED 17 Oct (owner's machine)","MEASURED 24 Oct"],
  validator:["svc@11Oct recorded","fork@8c0a457 recorded","fork@eb4b4b4 recorded","fork@8dd0d3e recorded","js-port-of-8dd0d3e here","none","fork@fa0b389 recorded"],
  renderer:["X_ITE 16.5.0 offline","X_ITE 16.5.1 offline","X_ITE 16.4.1 offline","X_ITE 16.5.0 in this browser · gpu","X_ITE 16.5.0 in this browser · software","X_ITE 16.5.0 offline + 16.5.1 offline","Cycles 5.2.2 baked","none"]};
function stamp(kind,value){const ok=(VOCAB[kind]||[]).includes(value);return el("span",{class:"stamp"+(ok?"":" stamp-unknown"),data:{k:kind},text:value||"?",title:ok?"":"not in the closed vocabulary"})}
function gradeChip(g){const G={C:"Confirmed",L:"List price / estimate",S:"Suspected"};return el("span",{class:"grade g-"+(g||"S"),text:g||"S",title:G[g]||""})}
function honesty(text){return el("div",{class:"hl",text})}
function sectionHeader(section,spec){
  const sec=typeof section==="string"?$(section):section;if(!sec)return null;const sh=sec.querySelector(".sh")||sec.appendChild(el("div",{class:"sh"}));sh.textContent="";
  sh.appendChild(el("h2",{text:spec.title||sec.id}));if(spec.unit)sh.appendChild(el("span",{class:"unit",text:spec.unit}));
  const st=el("span",{class:"stamps"});const s=spec.stamps||{};if(s.source)st.appendChild(stamp("source",s.source));if(s.validator)st.appendChild(stamp("validator",s.validator));if(s.renderer)st.appendChild(stamp("renderer",s.renderer));if(spec.grade)st.appendChild(gradeChip(spec.grade));sh.appendChild(st);
  sh.appendChild(el("i",{class:"prog"}));
  if(spec.honesty){const hl=sec.querySelector(":scope > .hl")||sec.appendChild(el("div",{class:"hl"}));hl.textContent=spec.honesty}
  return sh}
/* one IntersectionObserver per rootMargin key */
const IO=(()=>{const obs=new Map(),cb=new WeakMap();   /* callbacks keyed by element AND rootMargin: several observers may watch one element (RAIL's section highlight and a LOOP panel's visibility), each with its own callbacks */
  const get=k=>{if(!obs.has(k)){obs.set(k,new IntersectionObserver(es=>es.forEach(e=>{const m=cb.get(e.target),fs=m&&m.get(k);if(fs)fs.slice().forEach(f=>f(e.isIntersecting,e))}),{rootMargin:k==="0"?"0px":k,threshold:0}))}return obs.get(k)};
  return{observe(e,fn,opts){const k=(opts&&opts.rootMargin)||"0";let m=cb.get(e);if(!m){m=new Map();cb.set(e,m)}if(!m.has(k))m.set(k,[]);m.get(k).push(fn);get(k).observe(e)},
    unobserve(e,fn,opts){const m=cb.get(e);if(!m)return;const keys=opts&&opts.rootMargin?[opts.rootMargin]:[...m.keys()];keys.forEach(k=>{const fs=m.get(k);if(!fs)return;const left=fn?fs.filter(f=>f!==fn):[];if(left.length)m.set(k,left);else{m.delete(k);if(obs.has(k))obs.get(k).unobserve(e)}});if(!m.size)cb.delete(e)}}})();
/* theme */
const THEME=(()=>{const fns=[];let cur=null;const sys=()=>matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";
  const apply=t=>{cur=t;document.documentElement.dataset.theme=t;cssCache=new Map();fns.forEach(f=>{try{f(t)}catch(e){console.warn("theme listener",e)}})};
  return{init(){let t=null;try{t=localStorage.getItem("tf4.theme")}catch(e){}apply(t||sys());matchMedia("(prefers-color-scheme: light)").addEventListener("change",()=>{let s=null;try{s=localStorage.getItem("tf4.theme")}catch(e){}if(!s)apply(sys())})},
    get:()=>cur||document.documentElement.dataset.theme||sys(),set(t){try{localStorage.setItem("tf4.theme",t)}catch(e){}apply(t)},toggle(){THEME.set(THEME.get()==="dark"?"light":"dark")},onChange(f){fns.push(f)}}})();
/* fx level: 2 GPU, 1 GPU + reduced motion or 600–900 px, 0 software / webdriver / ?lite / phone / saveData */
const FX=(()=>{const fns=[];const o={level:2,reasons:[],gl:null,
  auto(){const r=[];let lv=2;const q=UTIL.qs("fx");if(q!=null&&/^[012]$/.test(q)){lv=+q;r.push("?fx="+q)}else{
    if(UTIL.qs("lite")==="1"){lv=0;r.push("?lite=1")}if(navigator.webdriver){lv=0;r.push("webdriver")}
    if(o.gl==="software"){lv=0;r.push("software renderer")}if(o.gl==="none"){lv=0;r.push("no WebGL")}
    if(navigator.connection&&navigator.connection.saveData){lv=0;r.push("saveData")}
    if(innerWidth<600){lv=0;r.push("phone width")}else if(innerWidth<900&&lv>1){lv=1;r.push("narrow")}
    if(matchMedia("(prefers-reduced-motion: reduce)").matches&&lv>1){lv=1;r.push("reduced motion")}}
    o.reasons=r;o.set(lv,true);return lv},
  set(n,quiet){n=UTIL.clamp(+n|0,0,2);const ch=n!==o.level;o.level=n;document.documentElement.dataset.fx=String(n);if(ch||!quiet)fns.forEach(f=>{try{f(n)}catch(e){console.warn("fx listener",e)}})},
  onChange(f){fns.push(f)},init(){o.auto()}};return o})();
/* sections registry: modules register, 99-boot mounts in template order */
const SECTIONS=(()=>{const list=[],byId=new Map();let mounted=false;
  const prog=sec=>{const p=sec.dataset.part,bar=sec.querySelector(".sh .prog");if(!p||!bar||!self.DATA)return;const st=DATA.status[p];if(!st)return;
    const f=st.state==="loaded"?1:st.state==="loading"&&st.bytes?Math.min(1,st.got/st.bytes):0;bar.style.width=(f*100).toFixed(1)+"%";bar.classList.toggle("refused",st.state==="refused"||st.state==="missing");if(st.state==="loaded")setTimeout(()=>{bar.style.opacity="0"},1200)};
  function mountOne(r){const sec=$(r.id);if(!sec||r.mounted)return;r.mounted=true;r.el=sec;try{if(r.header)sectionHeader(sec,r.header);if(r.mount)r.mount(sec)}catch(e){console.error("mount",r.id,e);if(self.BOOT)BOOT.error(e,"mount "+r.id)}
    if(r.onData&&self.DATA)DATA.on("*",(name,obj)=>{try{r.onData(name,obj)}catch(e){console.error("onData",r.id,e)}})}
  return{list,get:id=>byId.get(id),register(r){if(byId.has(r.id)){Object.assign(byId.get(r.id),r);return byId.get(r.id)}list.push(r);byId.set(r.id,r);if(mounted)mountOne(r);return r},
    mountAll(){mounted=true;document.querySelectorAll("section[id]").forEach(sec=>{const r=byId.get(sec.id);if(r)mountOne(r)});if(self.DATA)DATA.on("*",()=>document.querySelectorAll("section[data-part]").forEach(prog));if(self.LOOP)LOOP.register({name:"sectionProgress",bit:LOOP.bits.DATA,rateHz:8,draw(){document.querySelectorAll("section[data-part]").forEach(prog)}})},
    progress:prog}})();
Object.assign(self,{$,el,txt,cssv,fitCanvas,fmt,esc,unesc,mulberry32,later,debounce,gzRead,gzReadBytes,sectionHeader,stamp,honesty,gradeChip,IO,THEME,FX,SECTIONS,UTIL,__FX:FX});
})();
