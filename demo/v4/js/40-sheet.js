/* 40-sheet.js — S13 CONTACT SHEET (SPEC-v4 S13; WORKPLAN 40-sheet). Owns #sheet .sb.
   160 px tiles (4:3) for every body on the page: one tile per live attempt (358, from live.core/live.bodies, thumbnails from live.jpg) and one per
   replay body (174, thumbnails inside the replay part); verdict frame (green valid / red invalid / amber chain not verified), VALID/INVALID and
   BLANK / NO DRAW / NO PARSE tags, chain pill, two pass pills `.0` (X_ITE 16.5.0 offline, renders.series + the item's own r.nb) and `.1`
   (X_ITE 16.5.1 offline, renders.151): green when both passes agree on the 0.5 % line, amber when they disagree; tiles arrive in run order
   (a tile ahead of the run clock is dimmed, lit with a 200 ms fade when its scene is released); img.src set lazily through IO; filters
   (valid / invalid / blank / repaired, lane, category); MEASURED | STAGED toggle (what a hover or click loads on STAGE.show); hover 400 ms →
   STAGE.show.load(body, {staged, scene}) through the documented API; click selects the scene and loads it; the pass-pill strip or the
   STAGED slot opens the lightbox with the MEASURED frame (nb, both patches, content hash) and, when the Cycles ledger carries a url, the
   staged render labelled STAGED; the same-bytes-two-renderers wipe exists only when BUILD.HAS_CYCLES.
   VNV strip: the 7 live + 17 replay valid-but-blank scenes as hatched tiles with why (BLANKWHY by prompt category); click → #seven.
   STAGED manifest (demo/v4/data/staged.json, keys = ledgerKey(item) exactly): read from an inline `STAGED` global when the build bakes one,
   else fetched from data/staged.json when BUILD.staged is set or ?staged=1 (test rig); otherwise no slot is drawn (never a placeholder).
   url is null everywhere in this build: the slot reads "STAGED · in the Cycles ledger · not uploaded" and lights up when a url exists.
   Blank stills are read from the manifest's measured blank flag (cycles_manifest.py: < 0.5 % of pixels differ from the dominant colour by > 48/255;
   never a list in this file); the identical-bytes rule (same sha256 as another scene's still) is the fallback only for a manifest without flags.
   A blank still reads "did not render in Blender" beside the measured frame and is never shown as a staged render.
   Globals: SHEET, STAGEDM (the loaded manifest or null), BLANKWHY. SHEET.ledgerKey(it) is a shim: 03-data's ledgerKey returns it.k when present and
   LIVE items carry k = prompt kind ("bench" | "showpiece"), so it answers "bench" for a live body; the shim answers keyOf(m, p, A.length) (requested as a core fix).
   No STAGE.measure.show call site here (hover uses STAGE.show.load only; thumbnails are the recorded offline pass), so the raster group's RASTER.live hook has no place yet. Claims: sheet.live, sheet.replay, sheet.jpg, sheet.agree, sheet.staged,
   sheet.blankStaged (+ c.seven, c.replay17 reused on the VNV strip). LOOP panel "sheet" (rateHz 4; counters tiles, lit, shown, vnv).
   Test hooks: SHEET.refresh(), SHEET.tiles (Map key → tile), SHEET.lightbox(key) / SHEET.closeLightbox(), SHEET.hoverLoad(key), SHEET.filter(name),
   SHEET.staged (toggle state), SHEET.onStage (key last loaded), __panels.sheet.{tiles,lit,shown,vnv}, #sheet .th[data-key], #vnv .th, #lightbox.
   Ported from v3 demo/tether-firehose-v3.template.html: gallery/galSig (lines 564–572: signature gate per tile instead of innerHTML), thumbOf,
   placeholder (557–562: hatched canvas placeholder, now token-coloured and 160×120), BLANKWHY/blankWhy (264–265), BADTXT (563).
   Changes from v3: every body has a tile (not the last 36 scenes); two pass pills from the 16.5.1 pass; no innerHTML; hover-stage; lightbox. */
(function(){
"use strict";
const BLANKWHY={interaction:"proximity-lit scenes that stay dark until the viewer walks up",geospatial:"geospatial scenes whose content is tiny from the default camera",hanim:"a humanoid whose boxes hang off no joint, a scene that passes the validator by saying less",animation:"an animated scene whose geometry is off-camera at the default viewpoint",object:"an object scene placed out of the default view",assembly:"an assembly placed out of the default view",showpiece:"a showpiece placed out of the default view"};
const BADTXT={unparseable:"NO PARSE","nothing drawable":"NO DRAW","blank frame":"BLANK"};
const disp=m=>(self.SAFEMAP&&typeof SAFEMAP==="object"&&SAFEMAP[m])||m;
/* shim: 03-data ledgerKey(it) returns it.k when present, and LIVE items carry k = prompt kind ("bench" | "showpiece"), so for a LIVE item it answers "bench"; the Cycles-ledger key of a LIVE item is keyOf(m, p, A.length) (ARCHITECTURE §8). Requested as a core fix; until then SHEET.ledgerKey is the documented key for any item. */
const lkey=it=>!it?null:Array.isArray(it.A)?keyOf(it.m,it.p,it.A.length||1):(it.k||null);
const hasCycles=()=>!!(self.BUILD&&(BUILD.HAS_CYCLES||BUILD.has_cycles));
const blankNb=nb=>nb!=null&&nb<.005;
/* ---------- placeholder thumbnails (v3 557): hatched, token colours, one data URL per kind per theme ---------- */
let phCache=new Map();
function placeholder(kind){const k=kind+"|"+(self.THEME?THEME.get():"dark");if(phCache.has(k))return phCache.get(k);
  const c=document.createElement("canvas");c.width=160;c.height=120;const g=c.getContext("2d");g.fillStyle=cssv("--stage-bg")||"#03050a";g.fillRect(0,0,160,120);g.strokeStyle=cssv("--line2")||"#2f415a";g.lineWidth=1;
  for(let i=-120;i<160;i+=10){g.beginPath();g.moveTo(i,120);g.lineTo(i+120,0);g.stroke()}
  g.fillStyle=cssv("--warn")||"#f0b84a";g.font="600 11px "+(cssv("--mono")||"monospace");g.textAlign="center";g.fillText(kind==="unparseable"?"PARSE FAIL":kind==="nothing drawable"?"NOTHING TO DRAW":kind==="noblender"?"DID NOT RENDER":"BLANK FRAME",80,64);
  const u=c.toDataURL("image/png");phCache.set(k,u);return u}
if(self.THEME)THEME.onChange(()=>{phCache=new Map()});
/* ---------- the STAGED manifest ---------- */
let STAGEDM=null,stagedBlank=new Set(),stagedP=null;
function stagedEntries(){const out=[];if(!STAGEDM)return out;Object.entries(STAGEDM.turntables||{}).forEach(([k,v])=>out.push({key:k,kind:"turntable",v}));
  Object.entries(STAGEDM.stills||{}).forEach(([k,o])=>Object.entries(o||{}).forEach(([cam,v])=>out.push({key:k,kind:cam,v})));return out}
/* identical-bytes rule: a still whose file sha256 equals another scene's still rendered nothing of its scene (an empty frame is the same picture for every scene) */
function detectBlank(){stagedBlank=new Set();const es=stagedEntries().filter(e=>e.kind!=="turntable");SHEET.blankRule="manifest";
  /* the manifest's measured flag (cycles_manifest.py: blank = under 0.5 % of pixels differ from the dominant colour by more than 48/255) is the rule; the identical-bytes rule is only the fallback for a manifest without flags */
  if(es.some(e=>e.v&&typeof e.v.blank==="boolean")){es.forEach(e=>{if(e.v&&e.v.blank===true)stagedBlank.add(e.key+"|"+e.kind)});return}
  SHEET.blankRule="identical-bytes";const by=new Map();es.forEach(e=>{const h=e.v&&e.v.sha256;if(!h)return;if(!by.has(h))by.set(h,new Set());by.get(h).add(e.key)});
  es.forEach(e=>{const h=e.v&&e.v.sha256;if(h&&by.get(h).size>1)stagedBlank.add(e.key+"|"+e.kind)})}
function stagedOf(key){if(!STAGEDM)return null;const t=STAGEDM.turntables&&STAGEDM.turntables[key],s=STAGEDM.stills&&STAGEDM.stills[key];if(!t&&!s)return null;
  const cams=s?Object.keys(s).map(cam=>({cam,v:s[cam],blank:stagedBlank.has(key+"|"+cam)})):[];return{key,turntable:t||null,stills:cams,anyUrl:!!((t&&t.url)||cams.some(c=>c.v.url&&!c.blank)),allBlank:!t&&cams.length>0&&cams.every(c=>c.blank)}}
function loadStaged(){if(stagedP)return stagedP;stagedP=(async()=>{
  if(typeof STAGED!=="undefined"&&STAGED&&typeof STAGED==="object"){STAGEDM=STAGED;SHEET.stagedSource="inline"}
  else if((self.BUILD&&BUILD.staged)||UTIL.qs("staged")==="1"){try{const r=await fetch(self.BUILD&&typeof BUILD.staged==="string"?BUILD.staged:"data/staged.json");if(r.ok){STAGEDM=await r.json();SHEET.stagedSource="file"}else SHEET.stagedSource="missing"}catch(e){SHEET.stagedSource="missing";SHEET.stagedErr=String(e&&e.message||e)}}
  else SHEET.stagedSource="none";
  if(STAGEDM)detectBlank();self.STAGEDM=STAGEDM;return STAGEDM})();return stagedP}
/* ---------- claims ---------- */
const mrows=n=>(self.MANIFEST&&MANIFEST.parts&&MANIFEST.parts[n]&&MANIFEST.parts[n].rows)||undefined;
const passClass=(it,k)=>{ /* draw / blank / unparseable class on 16.5.0 and 16.5.1 for a live attempt */
  const a=it.A[k-1],r0=a.r||{},r1=self.R151&&R151.live&&R151.live[keyOf(it.m,it.p,k)];const c=r=>!r?null:r.err?"u":blankNb(r.nb)?"b":"d";return{c0:c(r0),c1:r1?c(r1):null,r0,r1:r1||null}};
CLAIMS.define("sheet.live",{label:"attempt bodies on the sheet",unit:"17 Oct · one tile per attempt",expected:mrows("live.bodies"),needs:["live.core"],grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline",fields:["sum of A[].length over the 201 chains (= bodies in parts/live.bodies)"],compute(){return LIVE.reduce((n,i)=>n+i.A.length,0)}});
CLAIMS.define("sheet.replay",{label:"replay bodies on the sheet",unit:"11 Oct · one tile per scene",expected:mrows("replay"),needs:["replay"],grade:"C",source:"RECORDED 11 Oct",validator:"svc@11Oct recorded",renderer:"X_ITE 16.5.0 offline",fields:["REAL.length"],compute(){return REAL.length}});
CLAIMS.define("sheet.jpg",{label:"measured frames with a thumbnail",unit:"live attempts that drew (offline JPEG)",expected:mrows("live.jpg"),needs:["live.core","live.jpg"],grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"X_ITE 16.5.0 offline",fields:["attempts whose r.jpg is present after parts/live.jpg lands"],compute(){return LIVE.reduce((n,i)=>n+i.A.filter(a=>a.r&&a.r.jpg).length,0)}});
CLAIMS.define("sheet.agree",{label:"16.5.0 and 16.5.1 agree",unit:"draw / blank / unparseable class on the 0.5 % line, live attempts with both passes",needs:["live.core","renders.151"],grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline",text:v=>`${v.agree} of ${v.n}`,fields:["per attempt: class(16.5.0 r.nb, r.err) === class(16.5.1 R151.live[key].nb, err); blank = nb < 0.005"],
  compute(){let n=0,agree=0;LIVE.forEach(it=>it.A.forEach((a,k)=>{const p=passClass(it,k+1);if(p.c0&&p.c1){n++;if(p.c0===p.c1)agree++}}));return{n,agree}}});
CLAIMS.define("sheet.staged",{label:"bodies with a Cycles render in the ledger",unit:"demo/v4/data/staged.json keys matched to tiles",grade:"L",source:"BAKED: Blender Cycles",validator:"none",renderer:"Cycles 5.2.2 baked",text:v=>v?`${v.matched} of ${v.entries}`:"—",fields:["turntables + stills keys of staged.json that equal ledgerKey(item) of a tile (the physics ledger key lives in S14)"],
  compute(){if(!STAGEDM)return null;const keys=new Set([...Object.keys(STAGEDM.turntables||{}),...Object.keys(STAGEDM.stills||{})]);let matched=0;keys.forEach(k=>{if(SHEET.tiles.has(k))matched++});return{entries:keys.size,matched}}});
CLAIMS.define("sheet.blankStaged",{label:"stills that did not render in Blender",unit:"manifest blank flag (measured: < 0.5 % of pixels differ from the dominant colour by > 48/255)",grade:"C",source:"BAKED: Blender Cycles",validator:"none",renderer:"Cycles 5.2.2 baked",text:v=>v==null?"—":v+" stills",fields:["stills with blank:true in staged.json (measured pixel rule); identical-bytes fallback only when the manifest has no flags"],compute(){return STAGEDM?stagedBlank.size:null}});
/* ---------- state ---------- */
const SHEET={ledgerKey:lkey,tiles:new Map(),list:[],staged:false,filterName:"all",lane:"",cat:"",onStage:null,stagedSource:null,hoverMs:400,panel:null,vnvTiles:[],el:null,
  hoverLoad,select,lightbox,closeLightbox,refresh,filter,setStaged,setLane,setCat,loadStaged,stagedOf,placeholder,isBlankStill:(key,cam)=>stagedBlank.has(key+"|"+cam)};
let host=null,grid=null,gridR=null,vnvHost=null,lb=null,hoverT=null,visibleTiles=new Set(),built={live:false,replay:false,vnv:false};
/* ---------- tile records ---------- */
function liveTile(it,k){const a=it.A[k-1],key=keyOf(it.m,it.p,k);return{key,src:"live",it,k,m:it.m,p:it.p,c:it.c,final:k===it.A.length,
  ok:!!a.ok,nb:a.r?a.r.nb:null,err:a.r?a.r.err:null,kind:a.r?(a.r.err?"unparseable":blankNb(a.r.nb)?((a.r.nf||(a.r.unknown||0)>0)?"nothing drawable":"blank frame"):"draws"):"unknown",
  body:()=>it.B&&it.B[k-1]||null,jpg:()=>a.r&&a.r.jpg||null,r151:()=>self.R151&&R151.live&&R151.live[key]||null,el:null,img:null,sig:""}}
function replayTile(it){return{key:it.k,src:"replay",it,k:it.at,m:it.m,p:it.p,c:it.c,final:true,ok:!!(it.x&&it.s),nb:it.r?it.r.nb:null,err:it.r?it.r.err:null,kind:kindOf(it),
  body:()=>it.b||null,jpg:()=>it.r&&it.r.jpg||null,r151:()=>it.r&&it.r.nb151!==undefined?{nb:it.r.nb151,err:it.r.err151,frames:it.r.frames151}:null,el:null,img:null,sig:""}}
function passInfo(t){const r1=t.r151();const c=(nb,err)=>err?"u":blankNb(nb)?"b":"d";const c0=t.err?"u":t.nb==null?null:c(t.nb,null),c1=r1?c(r1.nb,r1.err):null;
  return{c0,c1,nb0:t.nb,nb1:r1?r1.nb:null,agree:c0&&c1?c0===c1:null,err1:r1?r1.err:null}}
const pct=nb=>nb==null?"—":(nb*100).toFixed(nb<.01?2:1)+"%";
function tileEl(t){
  const img=el("img",{alt:"",decoding:"async"});const vd=el("b",{class:"vd",text:t.ok?"VALID":"INVALID"});const bl=el("b",{class:"bl",text:BADTXT[t.kind]||"",hidden:t.kind==="draws"||t.kind==="unknown"?"":null});
  const cp=el("b",{class:"cp",text:"—",title:"chain: not yet on the run clock"});
  const pi=passInfo(t);const p0=el("b",{class:"pass p0 "+(pi.agree===null?"na":pi.agree?"agree":"differ"),text:".0",title:`X_ITE 16.5.0 offline · nonblank ${pct(pi.nb0)}${t.err?" · unparseable":""}`});
  const p1=el("b",{class:"pass p1 "+(pi.c1===null?"na":pi.agree?"agree":"differ"),text:".1",title:pi.c1===null?"X_ITE 16.5.1 offline: no record for this body":`X_ITE 16.5.1 offline · nonblank ${pct(pi.nb1)}${pi.err1?" · unparseable":""}${pi.agree?" · agrees on the 0.5 % line":" · DISAGREES on the 0.5 % line"}`});
  const pp=el("span",{class:"pp",title:"open the measured frame (both passes, content hash)",onclick:e=>{e.stopPropagation();lightbox(t.key)}},[p0,p1]);
  const lab=el("span",{class:"lb",text:`${t.p} · a${t.k}${t.src==="replay"?" · "+t.it.mo:""}`});
  const b=el("button",{class:"th "+(t.ok?"v":"i")+(t.src==="live"&&t.final?" fin":""),type:"button",data:{key:t.key,src:t.src,m:t.m,p:t.p,k:String(t.k),c:t.c||""},
    title:`${t.p} · ${disp(t.m)} · attempt ${t.k}${t.src==="live"?" of "+t.it.A.length:""} · ${t.ok?"valid":"invalid"} on ${t.src==="live"?"fork@eb4b4b4":"svc@11Oct"} · ${t.kind} · 16.5.0 ${pct(pi.nb0)} · 16.5.1 ${pct(pi.nb1)}`,
    "aria-label":`${t.key} ${t.ok?"valid":"invalid"}${t.kind!=="draws"?", "+t.kind:""}`},[img,el("span",{class:"tg"},[vd,bl,cp]),pp,lab]);
  b.addEventListener("mouseenter",()=>{if(innerWidth<600)return;cancelHover();hoverT=later(()=>{hoverT=null;hoverLoad(t.key)},SHEET.hoverMs)});
  b.addEventListener("mouseleave",cancelHover);b.addEventListener("click",()=>select(t.key));b.addEventListener("dblclick",e=>{e.preventDefault();lightbox(t.key)});
  t.el=b;t.img=img;t.cp=cp;t.bl=bl;IO.observe(b,v=>{if(v){visibleTiles.add(t);setSrc(t)}else visibleTiles.delete(t)},{rootMargin:"240px"});return b}
function setSrc(t){if(t.img.dataset.set==="1")return;const j=t.jpg();if(j&&t.kind==="draws"){t.img.src="data:image/jpeg;base64,"+j;t.img.dataset.set="1"}else if(t.kind!=="draws"&&t.kind!=="unknown"){t.img.src=placeholder(t.kind);t.img.dataset.set="1"}else if(t.src==="live"&&self.DATA&&DATA.status["live.jpg"]&&/loaded|refused|missing/.test(DATA.status["live.jpg"].state)){t.img.src=placeholder("blank frame");t.img.dataset.set="1"}}
function cancelHover(){if(hoverT){hoverT();hoverT=null}}
function stagedSlot(t){const s=stagedOf(t.key);if(!s)return;let slot=t.el.querySelector(".stg");if(!slot){slot=el("span",{class:"stg",onclick:e=>{e.stopPropagation();lightbox(t.key)}});t.el.appendChild(slot)}
  const lit=s.anyUrl;slot.classList.toggle("has",lit);slot.classList.toggle("noblender",s.allBlank);
  txt(slot,s.allBlank?"did not render in Blender":lit?"STAGED":"STAGED · no url");
  const cams=(s.turntable?["turntable: "+(s.turntable.url?"render":"recorded, no url")]:[]).concat(s.stills.map(c=>c.cam+": "+(c.blank?"did not render in Blender":c.v.url?"render":"recorded, no url"))).join(" · ");
  slot.title=(s.allBlank?"Blender Cycles: every staged still is a blank frame by the measured pixel rule; never shown as a staged render":lit?"STAGED · Blender Cycles render in the ledger · open":"STAGED · Blender Cycles render recorded in the ledger (sha "+((s.turntable&&s.turntable.sha256)||(s.stills[0]&&s.stills[0].v.sha256)||"").slice(0,8)+") · not uploaded in this build")+" · "+cams;
  if(hasCycles()&&lit&&!slot.querySelector(".cycles"))slot.appendChild(el("i",{class:"cycles",text:" · Cycles"}))}
/* ---------- build ---------- */
function buildGroup(which){
  if(which==="live"&&!built.live&&self.LIVE&&LIVE.length){built.live=true;const frag=document.createDocumentFragment();LIVE.forEach(it=>{for(let k=1;k<=it.A.length;k++){const t=liveTile(it,k);SHEET.tiles.set(t.key,t);SHEET.list.push(t);frag.appendChild(tileEl(t))}});grid.appendChild(frag);fillSelects()}
  if(which==="replay"&&!built.replay&&self.REAL&&REAL.length){built.replay=true;const frag=document.createDocumentFragment();REAL.forEach(it=>{const t=replayTile(it);SHEET.tiles.set(t.key,t);SHEET.list.push(t);frag.appendChild(tileEl(t))});gridR.appendChild(frag);fillSelects()}
  if(SHEET.panel){SHEET.panel.tiles=SHEET.tiles.size;SHEET.panel.forceDraw=true}
  if(STAGEDM){SHEET.list.forEach(stagedSlot);CLAIMS.run("sheet.staged")}applyFilter()}
function fillSelects(){const ls=host.querySelector("#sheetLane"),cs=host.querySelector("#sheetCat");if(!ls||!cs)return;const lanes=[...new Set(SHEET.list.map(t=>t.m))],cats=[...new Set(SHEET.list.map(t=>t.c).filter(Boolean))].sort();
  const fill=(sel,vals,label)=>{const have=new Set([...sel.options].map(o=>o.value));vals.forEach(v=>{if(!have.has(v))sel.appendChild(el("option",{value:v,text:label(v)}))})};fill(ls,lanes,disp);fill(cs,cats,c=>c)}
function buildVnv(){if(built.vnv||!(self.LIVE&&LIVE.length&&self.REAL&&REAL.length&&self.R151))return;built.vnv=true;vnvHost.textContent="";
  const live=LIVE.filter(i=>{const f=i.A[i.A.length-1];if(!f.ok||(f.r&&f.r.err))return false;const r1=R151.live[keyOf(i.m,i.p,i.A.length)];return blankNb(f.r?f.r.nb:null)&&r1&&!r1.err&&blankNb(r1.nb)}).map(i=>SHEET.tiles.get(lkey(i))).filter(Boolean);
  const rep=REAL.filter(i=>i.x&&i.s&&!(i.r&&i.r.err)&&blankNb(i.r?i.r.nb:null)).map(i=>SHEET.tiles.get(i.k)).filter(Boolean);
  const head=el("div",{class:"row vnvHead"},[el("b",{class:"vnvT",text:"VALID, NOT VISIBLE"}),claimChip("c.seven",{size:"s",label:"live finals · 16.5.0 and 16.5.1"}),claimChip("c.replay17",{size:"s",label:"replay · 16.5.0"}),el("span",{class:"note m",text:"hatched: the validator said valid, the renderer drew under 0.5 % of the frame · click a tile for S4, the dark seven"})]);
  vnvHost.appendChild(head);const strip=el("div",{class:"vnvStrip"});
  [...live,...rep].forEach(t=>{const pi=passInfo(t);const why=BLANKWHY[t.c]||"opened and read by hand: the scene says less than the validator can see";
    const b=el("button",{class:"th vnv v",type:"button",data:{key:t.key,src:t.src},title:`${t.key} · valid on ${t.src==="live"?"fork@eb4b4b4":"svc@11Oct"} · 16.5.0 ${pct(pi.nb0)} · 16.5.1 ${pct(pi.nb1)} · ${why}`,
      onclick:()=>{select(t.key,true);const s=$("seven");if(s)s.scrollIntoView({behavior:self.FX&&FX.level===0?"auto":"smooth",block:"start"})}},
      [el("img",{alt:"",src:placeholder(t.kind==="draws"?"blank frame":t.kind)}),el("span",{class:"tg"},[el("b",{class:"vd",text:"VALID"}),el("b",{class:"bl",text:BADTXT[t.kind]||"BLANK"})]),el("span",{class:"why",text:why}),el("span",{class:"lb",text:`${t.p} · ${disp(t.m).replace(/^.*\//,"")}${t.src==="replay"?" · 11 Oct":""}`})]);
    strip.appendChild(b);SHEET.vnvTiles.push(t)});
  vnvHost.appendChild(strip);if(SHEET.panel)SHEET.panel.vnv=SHEET.vnvTiles.length}
/* ---------- interaction ---------- */
function sceneOf(t){if(!self.S)return null;for(const sc of S.scenes)if(sc.item===t.it)return sc;return null}
function stageLine(t,r){const pi=passInfo(t),body=t.body();const h=body?contentHash(body).slice(0,16):"—";
  return`contact sheet · ${t.p} · ${disp(t.m)} · attempt ${t.k} · ${SHEET.staged?"STAGED (render-time lights, nothing written)":"MEASURED (raw bytes)"} · counted frame 16.5.0 offline ${pct(pi.nb0)} · 16.5.1 offline ${pct(pi.nb1)} · hash ${h}${r&&r.ok===false?" · X_ITE refused: "+(r.err||"")+"":""}`}
async function hoverLoad(key){const t=SHEET.tiles.get(key);if(!t||!self.STAGE||!STAGE.show||!STAGE.show.load)return null;const body=t.body();if(!body)return null;
  SHEET.onStage=key;const sc=sceneOf(t);const r=await STAGE.show.load(body,{staged:SHEET.staged,scene:sc||null});if(SHEET.onStage===key&&!(r&&r.cancelled))txt("stageMsg",stageLine(t,r));return r}
function select(key,noLoad){const t=SHEET.tiles.get(key);if(!t)return;cancelHover();const sc=sceneOf(t);if(sc&&self.SIM)SIM.select(sc.id);SHEET.sel=key;if(SHEET.panel)SHEET.panel.forceDraw=true;if(!noLoad)hoverLoad(key)}
function filter(name){SHEET.filterName=name||"all";host.querySelectorAll("#sheetFilters button[data-f]").forEach(b=>b.classList.toggle("on",b.dataset.f===SHEET.filterName));applyFilter()}
function setLane(v){SHEET.lane=v||"";applyFilter()}function setCat(v){SHEET.cat=v||"";applyFilter()}
function setStaged(on){SHEET.staged=!!on;host.querySelectorAll("#sheetMode button[data-st]").forEach(b=>b.classList.toggle("on",(b.dataset.st==="staged")===SHEET.staged));if(SHEET.onStage)hoverLoad(SHEET.onStage)}
function passes(t){const f=SHEET.filterName;if(SHEET.lane&&t.m!==SHEET.lane)return false;if(SHEET.cat&&t.c!==SHEET.cat)return false;
  if(f==="valid")return t.ok;if(f==="invalid")return!t.ok;if(f==="blank")return t.kind!=="draws"&&t.kind!=="unknown";if(f==="repaired")return t.src==="live"?t.it.A.length>1&&t.final&&t.ok:t.it.at>1&&t.ok;if(f==="final")return t.final;return true}
function applyFilter(){let shown=0;SHEET.list.forEach(t=>{const p=passes(t);t.el.hidden=!p;if(p)shown++});if(SHEET.panel)SHEET.panel.shown=shown;txt(host.querySelector("#sheetCount"),`${shown} of ${SHEET.list.length} tiles shown`)}
/* ---------- the loop panel: patch by signature, never rebuild ---------- */
function refresh(){if(!host)return;const mode=self.S?S.mode:null,byItem=new Map();if(self.S)S.scenes.forEach(sc=>byItem.set(sc.item,sc));let lit=0;
  SHEET.list.forEach(t=>{const own=(t.src==="live"&&mode==="live17")||(t.src==="replay"&&mode==="replay11");const sc=own?byItem.get(t.it):null;
    const state=own?(sc?"lit":"ahead"):"rec";const st=sc?sc.status:"";const sel=!!(sc&&self.S&&S.sel===sc.id)||SHEET.sel===t.key;const jp=!!t.jpg();
    if(state!=="ahead")lit++;const sig=state+"|"+st+"|"+(sel?1:0)+"|"+(jp?1:0);if(sig===t.sig)return;t.sig=sig;
    t.el.classList.toggle("ahead",state==="ahead");t.el.classList.toggle("rec",state==="rec");t.el.classList.toggle("sel",sel);
    t.el.classList.toggle("x",!!sc&&st!=="verified"&&st!=="?");t.el.classList.toggle("v",t.ok&&!(sc&&st!=="verified"&&st!=="?"));t.el.classList.toggle("i",!t.ok&&!(sc&&st!=="verified"&&st!=="?"));
    txt(t.cp,sc?(st==="verified"?"✓ "+sc.id:st==="?"?"… "+sc.id:st.toUpperCase()):"—");t.cp.title=sc?`chain ${sc.id} · ${st==="verified"?"verify(): intact":st==="?"?"not yet swept":"verify(): "+st} · ${sc.nsteps} steps`:"chain: not yet on the run clock";
    if(jp&&visibleTiles.has(t))setSrc(t)});
  if(SHEET.panel){SHEET.panel.lit=lit;SHEET.panel.tiles=SHEET.tiles.size}
  txt(host.querySelector("#sheetLit"),mode?`${lit} lit · ${SHEET.list.length-lit} ahead of the run clock`:"")}
/* ---------- lightbox: the measured frame is what the numbers count; a staged render is labelled STAGED ---------- */
function lightbox(key){const t=SHEET.tiles.get(key);if(!t)return null;if(!lb){lb=el("div",{id:"lightbox",role:"dialog","aria-label":"measured frame",hidden:""});document.body.appendChild(lb);lb.addEventListener("click",e=>{if(e.target===lb)closeLightbox()});document.addEventListener("keydown",e=>{if(e.key==="Escape"&&lb&&!lb.hidden)closeLightbox()})}
  lb.textContent="";const pi=passInfo(t),body=t.body(),hash=body?contentHash(body):null,s=stagedOf(key),r1=t.r151();
  const box=el("div",{class:"lbBox"});const head=el("div",{class:"row lbHead"},[el("h3",{text:`${t.p} · ${disp(t.m)} · attempt ${t.k}`}),el("span",{class:"pill "+(t.ok?"p-ok":"p-bad"),text:(t.ok?"VALID":"INVALID")+" on "+(t.src==="live"?"fork@eb4b4b4":"svc@11Oct")}),el("button",{text:"close",onclick:closeLightbox})]);box.appendChild(head);
  const measured=el("figure",{class:"lbPane measured"},[el("img",{alt:"measured frame",src:t.jpg()&&t.kind==="draws"?"data:image/jpeg;base64,"+t.jpg():placeholder(t.kind==="draws"?"blank frame":t.kind)}),
    el("figcaption",{class:"m"},[el("b",{class:"measured-tag",text:"MEASURED"}),el("span",{text:` · X_ITE 16.5.0 offline, software GL · nonblank ${pct(pi.nb0)}${t.it.r&&t.it.r.frames&&t.final?" · "+t.it.r.frames+" frames, last at "+t.it.r.last+" ms":""} · 16.5.1 offline ${pct(pi.nb1)}${r1&&r1.frames?" · "+r1.frames+" frames":""} · ${pi.agree===null?"second pass: no record":pi.agree?"both passes agree on the 0.5 % line":"the passes DISAGREE on the 0.5 % line"} · ${t.kind}`})])]);
  const stage=el("div",{class:"lbStage"},[measured]);
  if(s){const entries=(s.turntable?[{v:s.turntable,cam:"turntable",blank:false}]:[]).concat(s.stills);
    entries.slice(0,3).forEach(pick=>{const cap=pick.blank?"did not render in Blender: the staged still is a blank frame by the measured pixel rule · camera "+pick.cam:`STAGED · ${pick.v.blender||"Blender"} · ${pick.v.engine||"Cycles"} · importer ${pick.v.importer||"x3d-blender-io"} · a baked picture, not the live renderer · same bytes, hash ${hash?hash.slice(0,16):"—"} · ${pick.cam==="turntable"?pick.v.frames+" frames":"camera: "+(pick.v.camera||pick.cam)} · WorldInfo dropped on import (documented)`;
      const fig=el("figure",{class:"lbPane staged"+(pick.blank?" noblender":""),data:{cam:pick.cam}},[pick.v.url&&!pick.blank?el("img",{alt:"staged render",src:pick.v.url}):el("div",{class:"stgEmpty",text:pick.blank?"did not render in Blender":"STAGED · recorded in the Cycles ledger (sha "+String(pick.v.sha256||"").slice(0,12)+") · not uploaded in this build"}),
        el("figcaption",{class:"m"},[el("b",{class:"staged-tag",text:pick.blank?"BLANK STAGED FRAME":"STAGED"}),el("span",{text:" · "+cap})])]);stage.appendChild(fig);
      if(hasCycles()&&pick.v.url&&!pick.blank&&!stage.classList.contains("wipe")){const wipe=el("input",{type:"range",min:"0",max:"100",value:"50","aria-label":"wipe: Cycles still over the X_ITE measured frame",class:"cycles wipe"});const sImg=fig.querySelector("img");sImg.style.clipPath="inset(0 50% 0 0)";wipe.addEventListener("input",()=>{sImg.style.clipPath=`inset(0 ${100-wipe.value}% 0 0)`});stage.classList.add("wipe");fig.appendChild(wipe);
        stage.appendChild(el("div",{class:"cycles lbHash m",text:"same bytes, two renderers · content hash "+(hash||"—")}))}})}
  box.appendChild(stage);
  box.appendChild(el("div",{class:"note m lbFoot",text:`content hash (page text-normalised) ${hash||"body not loaded yet"} · the measured frame is the frame the numbers count · thumbnails made offline after the run, X_ITE 16.5.0 headless on software GL`}));
  lb.appendChild(box);lb.hidden=false;return lb}
function closeLightbox(){if(lb)lb.hidden=true}
/* ---------- mount ---------- */
function mount(sec){host=sec.querySelector(".sb");SHEET.el=host;host.textContent="";
  vnvHost=el("div",{id:"vnv",class:"vnvWrap"});host.appendChild(vnvHost);
  const filters=el("span",{class:"seg",id:"sheetFilters"},[["all","all"],["valid","valid"],["invalid","invalid"],["blank","blank"],["repaired","repaired"],["final","finals"]].map(([f,l])=>el("button",{data:{f},class:f==="all"?"on":"",text:l,onclick:()=>filter(f)})));
  const lane=el("select",{id:"sheetLane","aria-label":"lane",onchange:e=>setLane(e.target.value)},el("option",{value:"",text:"every lane"}));const cat=el("select",{id:"sheetCat","aria-label":"category",onchange:e=>setCat(e.target.value)},el("option",{value:"",text:"every category"}));
  const modeSeg=el("span",{class:"seg",id:"sheetMode",title:"what a hover or click loads on the stage: the raw bytes (MEASURED) or the same bytes with render-time lights (STAGED, nothing written)"},[el("button",{data:{st:"measured"},class:"on",text:"MEASURED",onclick:()=>setStaged(false)}),el("button",{data:{st:"staged"},text:"STAGED",onclick:()=>setStaged(true)})]);
  host.appendChild(el("div",{class:"row sheetBar"},[filters,lane,cat,modeSeg,el("span",{id:"sheetCount",class:"note m"}),el("span",{id:"sheetLit",class:"note m"})]));
  host.appendChild(el("div",{class:"row sheetClaims"},[claimChip("sheet.live",{size:"s"}),claimChip("sheet.replay",{size:"s"}),claimChip("sheet.jpg",{size:"s"}),claimChip("sheet.agree",{size:"s"}),claimChip("sheet.staged",{size:"s"}),claimChip("sheet.blankStaged",{size:"s"})]));
  host.appendChild(el("div",{class:"legend",text:"frame: green valid · red invalid · amber chain not verified · pills .0 .1 = X_ITE 16.5.0 / 16.5.1 offline passes, green when they agree on the 0.5 % line · dim = ahead of the run clock · hover 400 ms loads the body on the stage · double-click or the pills open the measured frame"}));
  host.appendChild(el("h3",{class:"sheetH",text:"17 Oct · one tile per attempt body"}));grid=el("div",{class:"sheetGrid",id:"sheetLive"});host.appendChild(grid);
  host.appendChild(el("h3",{class:"sheetH",text:"11 Oct · one tile per replay body"}));gridR=el("div",{class:"sheetGrid",id:"sheetReplay"});host.appendChild(gridR);
  SHEET.panel=LOOP.register({name:"sheet",bit:LOOP.bits.SCENE|LOOP.bits.SELECT|LOOP.bits.MODE|LOOP.bits.VERIFY|LOOP.bits.DATA,rateHz:4,el:host,budgetMs:6,draw(){refresh()}});
  SHEET.panel.tiles=0;SHEET.panel.lit=0;SHEET.panel.shown=0;SHEET.panel.vnv=0;
  buildGroup("live");buildGroup("replay");buildVnv();
  loadStaged().then(()=>{if(STAGEDM){SHEET.list.forEach(stagedSlot);CLAIMS.run("sheet.staged");CLAIMS.run("sheet.blankStaged")}});
  if(self.SIM){SIM.on("select",()=>{SHEET.sel=null;SHEET.panel.forceDraw=true});SIM.on("mode",()=>{SHEET.panel.forceDraw=true})}}
function onData(name){if(!host)return;if(name==="live.core"||name==="live.bodies")buildGroup("live");if(name==="replay"||name==="renders.151")buildGroup("replay");
  if(name==="live.jpg"){visibleTiles.forEach(setSrc);SHEET.list.forEach(t=>{t.sig=""});if(SHEET.panel)SHEET.panel.forceDraw=true}
  if(name==="renders.151"){SHEET.list.forEach(t=>{const pi=passInfo(t);const p1=t.el.querySelector(".p1");if(p1){p1.className="pass p1 "+(pi.c1===null?"na":pi.agree?"agree":"differ");p1.title=pi.c1===null?"X_ITE 16.5.1 offline: no record for this body":`X_ITE 16.5.1 offline · nonblank ${pct(pi.nb1)}${pi.agree?" · agrees on the 0.5 % line":" · DISAGREES on the 0.5 % line"}`}})}
  buildVnv()}
const HONESTY="MEASURED frames: X_ITE 16.5.0 offline pass, software GL (C) · second pass 16.5.1 · STAGED is render-time lighting only, never in a file"+(hasCycles()?" · CYCLES: Blender 5.2.2 CPU, importer x3d-blender-io 206f139, same bytes, baked overnight, not the renderer the numbers count":" · Cycles ledger urls not uploaded in this build: STAGED slots name the render, never show one");
SECTIONS.register({id:"sheet",part:"live.jpg",header:{title:"Contact sheet",unit:"two render passes · hover stage · 160 px tiles for every body",stamps:{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline"},grade:"C",honesty:HONESTY},mount,onData});
Object.assign(self,{SHEET,BLANKWHY,STAGEDM:null});
})();
