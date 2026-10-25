/* 12-hero.js — S2 THE STAGE (SPEC-v4 S2, §2, §5 proof; WORKPLAN 12-hero). Section #stage (overlays inside #stageView, the thesis band in #hero), part live.core.
   Owns: the thesis overlay; the MEASURED FRAME card (the 192×144 counted frame at 1:1: X_ITE 16.5.0 offline · 16.5.1 offline · this browser from STAGE.measure);
   the STAGED | MEASURED toggle (MEASURED = a fresh load of the raw bytes, no rig, prints "fresh load"; STAGED = the §5 rig applied at render time to the loaded
   world, hash unchanged); the etching plaque (prompt, lane, cost, verdict, chain status and head hash from the SIM scene once the run clock has built it, content
   hash, the credit line); the hero rail (HERO's measured JPEGs only, never a staged snapshot; auto-advance 14 s at fx ≥ 1 unless hovered, never under webdriver);
   the three claim tiles (c.rates, c.seven, c.ratio from 02-claims: known from the record first, earned when live.core lands; lane arrows brighten as the run clock
   passes each lane's last scene); the legend; the report spine (attempt 1 frame → the validator's first finding → "the model was sent its own report" → final frame,
   the diff line through DIFF, a 36 px scrub crossfade, Open the morph); a labelled Cycles slot that reads the STAGED manifest (data/staged.json via BUILD.staged, or
   an inline STAGED when BUILD.HAS_CYCLES bakes one): blank:true stills read "did not render in Blender", links only when url is set, nothing when there is no entry.
   Hooks: HEROUI.stagedManifest() (promise → manifest|null), HEROUI.stagedLines(key) / __hero.stagedLines, __hero.manifest {turntables,stills}.
   Globals: HEROUI {open(i, opts), select(key), toggle(mode), mode(), measuredCard, plaque, spine, cur(), items()}, hero_spine_pick; HERO (the inline data object) gains
   open / select / plaque / spine / measuredCard so the WORKPLAN names resolve. Claims: hero.valid_finals (expected STATS.claims['c.seven'].of), hero.seven151 (expected
   STATS.claims['c.seven'].expected), hero.ratio_x (expected STATS.claims['c.ratio'].expected.x).
   Stage default: STAGED at fx ≥ 1 (STAGE.show.setStaged(true) on the boot-loaded world: no reload, lastHash unchanged), MEASURED at fx 0 (software GL; a lights-only
   rig would carry the badge's "lights + ground + camera" text) and with ?stage=measured. Measuring another hero never pre-empts the boot measure (BOOT.heroMeasure);
   every STAGE.measure.show here is forwarded to RASTER.live(key, R, note) when the raster module is present (one X_ITE load for both).
   Keys: M toggles STAGED | MEASURED while the stage is on screen; ← → inside the rail; double-click on the stage resets the camera.
   Test hooks: __hero {cur, mode, measured (Map idx → R | {wait|pending}), loads, spinePick, auto, lanes, staged}. v3 port: none assigned (WORKPLAN §A); hashes via 04-prov. */
(function(){
"use strict";
const E={},ST={cur:0,mode:null,want:null,loads:0,measured:new Map(),auto:null,hover:false,visible:false,lanes:[],pending:null,stagedApplied:false,spinePick:null,spineT:0,sec:null};
const __hero={cur:0,mode:"measured",measured:ST.measured,loads:0,spinePick:null,auto:false,lanes:[],staged:false};
const H=()=>self.HERO&&HERO.items?HERO.items:[];
const share=()=>!!(self.BUILD&&BUILD.share);
const short=m=>String(m).replace(/^.*\//,"");
const paid=()=>(((self.LM||(self.STATS&&STATS.meta))||{}).models||[]).filter(m=>m.prov!=="nvidia");
const laneName=m=>{if(!share())return short(m);const i=paid().map(x=>x.id).indexOf(m);return i>=0?"closed-"+"ABCDEF"[i]:"open lane"};
const stampOk=(k,v)=>{if(!v)return null;const s=stamp(k,v);return s.classList.contains("stamp-unknown")?null:s};
const THESIS={h1:"X3D IS THE 3D FORMAT AN AI CAN BE HELD ACCOUNTABLE TO",h2:"VALID IS NOT THE SAME AS VISIBLE",
  p:"A model writes a scene. An exact validator says what is wrong. The model repairs with the report. The browser shows whether it draws. A hash-chained record in the file's own head ties every step together."};
const CREDIT=share()?"thesis and pipeline: x3d.io — traceability · Blender · validator plus context stack":"thesis and pipeline: HagopJay, x3d.io — ML-pipeline traceability · Blender as the AI 3D tool · the validator plus context stack";
function wantStaged(){if(ST.want!=null)return ST.want;if(UTIL.qs("stage")==="measured")return false;return !!(self.FX&&FX.level>0)}
const liveOf=it=>self.LIVE&&LIVE[it.idx]&&LIVE[it.idx].p===it.p?LIVE[it.idx]:null;
/* ---------- measured card ---------- */
const measuredCard={
  build(){E.mImg=el("img",{alt:"the counted frame: X_ITE 16.5.0 offline, 192×144",width:"192",height:"144"});E.mNf=el("span",{class:"nf",hidden:""});E.mFrame=el("span",{class:"frame"},[E.mImg,E.mNf]);
    E.m1=el("div",{class:"mc"});E.m2=el("div",{class:"mc"});E.m3=el("div",{class:"mc live"});
    E.segS=el("button",{text:"STAGED",data:{m:"staged"},onclick:e=>{e.stopPropagation();HEROUI.toggle("staged")}});E.segM=el("button",{text:"MEASURED",data:{m:"measured"},onclick:e=>{e.stopPropagation();HEROUI.toggle("measured")}});
    E.mcard=el("div",{class:"sov mcard m",role:"group","aria-label":"measured frame"},[el("h4",null,[el("span",{text:"MEASURED FRAME"}),el("small",{text:"192×144 at 1:1"})]),E.mFrame,E.m1,E.m2,E.m3,el("span",{class:"seg"},[E.segS,E.segM]),el("div",{class:"rule",text:"staging changes nothing in the file; the counted frame is the raw one"})]);
    E.mcard.addEventListener("click",()=>{if(innerWidth<=900)E.mcard.classList.toggle("full")});return E.mcard},
  update(it){if(!it)return;if(it.jpg){E.mImg.src="data:image/jpeg;base64,"+it.jpg;E.mImg.hidden=false;E.mNf.hidden=true}else{E.mImg.removeAttribute("src");E.mImg.hidden=true;E.mNf.hidden=false;txt(E.mNf,"no measured frame in HERO")}
    E.m1.textContent="";E.m1.append(el("b",{text:"X_ITE 16.5.0"}),` · swiftshader · offline 17 Oct · ${fmt.pct(it.nb,1)} of pixels differ · ${fmt.int(it.frames)} frames · last ${fmt.int(it.last)} ms`);
    txt(E.m2,`16.5.1 offline: ${it.nb151!=null?fmt.pct(it.nb151,1):"no record"}${it.text&&self.ENV&&ENV.eval===false?" · Text glyphs need eval: not drawn in this viewer":""}`);measuredCard.live(it);measuredCard.seg()},
  live(it){it=it||H()[ST.cur];if(!it)return;const R=ST.measured.get(it.idx);let s;
    if(!R)s="this browser: —";else if(R.wait)s="this browser: waits for the boot measure";else if(R.pending)s="this browser: measuring…";else if(R.err)s="this browser: X_ITE refused · "+R.err;else if(R.noFrame)s="this browser: no frame yet";else s=`this browser: ${fmt.pct(R.nb,1)} · ${R.renderer||(self.ENV&&ENV.renderer)||"?"} · ${R.frames} frames`;
    if(txt(E.m3,s)){E.m3.textContent="";const i=s.indexOf(":");E.m3.append(s.slice(0,i+1),el("b",{text:s.slice(i+1)}))}},
  seg(){const staged=!!(self.__stage&&__stage.show.staged);E.segS.classList.toggle("on",staged);E.segM.classList.toggle("on",!staged);ST.mode=staged?"staged":"measured";__hero.mode=ST.mode;__hero.staged=staged}};
/* ---------- plaque ---------- */
/* memoised per scene: readSteps + sha run once per chain, never per tick; the status is the scrubber's (20-sim), "?" prints VERIFYING */
/* ---------- the STAGED manifest (demo/v4/data/staged.json): read, never a hard-coded list ----------
   source order: self.STAGEDM (40-sheet already fetched it) → an inline STAGED global (a build that bakes one) → fetch data/staged.json when BUILD.staged
   (or ?staged=1). Every entry carries the manifest's measured flag (cycles_manifest.py: blank = under 0.5 % of pixels differ from the dominant colour by
   more than 48/255): blank:true reads "did not render in Blender" and is never presented as a render; a picture or link appears only when url is set. */
let SM=null,smP=null;
function stagedManifest(){if(smP)return smP;smP=(async()=>{try{if(self.STAGEDM&&typeof STAGEDM==="object")SM=STAGEDM;else if(typeof STAGED!=="undefined"&&STAGED&&typeof STAGED==="object")SM=STAGED;
  else if((self.BUILD&&BUILD.staged)||UTIL.qs("staged")==="1"){const r=await fetch(self.BUILD&&typeof BUILD.staged==="string"?BUILD.staged:"data/staged.json");if(r.ok)SM=await r.json()}}catch(e){__hero.stagedErr=String(e&&e.message||e)}
  __hero.manifest=SM?{turntables:Object.keys(SM.turntables||{}).length,stills:Object.keys(SM.stills||{}).length}:null;return SM})();return smP}
/* stagedLines(key): one labelled line per baked picture the manifest holds for a ledger key (turntable, then each still camera); [] when none */
function stagedLines(key){if(!SM||!key)return[];const out=[];const one=(kind,v)=>{if(!v||typeof v!=="object")return;const eng=`${v.engine||"Cycles"} · Blender ${v.blender||"?"} · ${v.importer||"x3d-blender-io"}`;
    if(v.blank===true)out.push({kind,blank:true,url:null,text:`${kind}: did not render in Blender (nonblank ${v.nonblank!=null?fmt.pct(v.nonblank,2):"—"} under the measured pixel rule, a blank frame) · ${eng}`});
    else out.push({kind,blank:false,url:v.url||null,text:`${kind}: STAGED, a baked picture, not the live renderer${v.nonblank!=null?` · nonblank ${fmt.pct(v.nonblank,2)}`:""}${v.frames>1?` · ${v.frames} frames`:""} · ${eng}${v.url?"":" · not yet uploaded"}`})};
  one("Cycles turntable",SM.turntables&&SM.turntables[key]);const st=SM.stills&&SM.stills[key];if(st&&typeof st==="object")Object.keys(st).forEach(cam=>one(`Cycles still (${cam})`,st[cam]));return out}
const CH=new Map(),HH=new Map();const bodyHash=it=>{let h=HH.get(it.idx);if(!h){h=contentHash(it.body);HH.set(it.idx,h)}return h};
function chainLine(it){const L=liveOf(it),id=self.S&&S.liveIds&&S.liveIds.get(it.idx),sc=id&&S.byId.get(id);
  if(!sc){const T=L?fmt.clock(L.T):null;return{steps:`chain ${2*it.calls+1} steps · builds when the run clock reaches ${T||"this scene"}`,head:"head: pending",id:null}}
  let m=CH.get(sc.id);if(!m||m.xml!==sc.xml){const st=readSteps(sc.xml),last=st[st.length-1];m={xml:sc.xml,n:st.length,head:last?`head ${sha(last[1]).slice(0,6)}…`:"head: —"};CH.set(sc.id,m);if(CH.size>64)CH.delete(CH.keys().next().value)}
  const status=sc.status&&sc.status!=="?"?sc.status:"verifying";
  return{steps:`chain ${m.n} steps ${String(status).toUpperCase()}`,head:m.head,id:sc.id,status}}
const plaque={
  build(){E.p1=el("div",{class:"pl l1"});E.p2=el("div",{class:"pl l2"});E.p3=el("div",{class:"pl l3"});E.p4=el("div",{class:"pl l4",text:CREDIT});E.cyc=el("div",{class:"cyc",hidden:""});
    E.plaque=el("div",{class:"sov plaque",role:"button",tabindex:"0",title:"open this scene in the firehose inspector"},[E.p1,E.p2,E.p3,E.p4,E.cyc]);
    const go=()=>{const it=H()[ST.cur];if(!it)return;const c=chainLine(it);if(c.id&&self.SIM)SIM.select(c.id);const s=$("stream");if(s)s.scrollIntoView({behavior:self.FX&&FX.level>0?"smooth":"auto",block:"start"})};
    E.plaque.addEventListener("click",go);E.plaque.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();go()}});return E.plaque},
  update(it){if(!it)return;E.p1.textContent="";E.p1.append(`${it.p} · ${it.c} · `,el("q",{text:String(it.pt||"").slice(0,90)+(String(it.pt||"").length>90?"…":"")}));
    const c=chainLine(it);E.p2.textContent="";E.p2.append(`${laneName(it.m)} · ${it.calls} call${it.calls>1?"s":""}${share()?"":" · "+fmt.usd(it.u)} · `,el("b",{class:it.ok?"ok":"bad",text:it.ok?"valid":"invalid"}),` on fork@eb4b4b4 ${it.calls>1?`after ${it.calls-1} repair${it.calls>2?"s":""}`:"first try"} · `,el("span",{class:c.id?"":"mute",text:c.steps}));
    txt(E.p3,`content hash ${bodyHash(it).slice(0,6)}… · ${c.head} · x3dprov/0.1 · page-normalised hash · Confirmed for this scene`);plaque.cycles(it)},
  tick(it){if(!it)return;const c=chainLine(it);const sp=E.p2.lastChild;if(sp&&sp.nodeType===1){if(txt(sp,c.steps))sp.className=c.id?"":"mute";}
    const s3=`content hash ${bodyHash(it).slice(0,6)}… · ${c.head} · x3dprov/0.1 · page-normalised hash · Confirmed for this scene`;txt(E.p3,s3)},
  /* the Cycles slot: every line the STAGED manifest holds for this key (blank flag read from the manifest); hidden when the manifest has nothing */
  cycles(it){const L=stagedLines(it.key);if(!L.length){E.cyc.hidden=true;E.cyc.textContent="";if(!SM)stagedManifest().then(()=>{if(SM&&H()[ST.cur]===it)plaque.cycles(it)});return}
    E.cyc.hidden=false;E.cyc.textContent="";L.forEach((l,i)=>{if(i)E.cyc.append(" · ");if(l.url&&!l.blank)E.cyc.append(el("a",{href:l.url,target:"_blank",rel:"noopener",text:l.text}));else E.cyc.append(el("span",{class:l.blank?"bad":"",text:l.text}))})}};
/* ---------- rail ---------- */
const rail={
  build(){E.strip=el("div",{class:"strip",role:"listbox","aria-label":"hero scenes"});E.cap=el("div",{class:"cap m"});
    E.rail=el("div",{class:"sov hrail"},[E.cap,E.strip,el("div",{class:"nav"},[el("button",{text:"▲","aria-label":"previous hero",onclick:()=>HEROUI.open((ST.cur+H().length-1)%H().length)}),el("button",{text:"▼","aria-label":"next hero",onclick:()=>HEROUI.open((ST.cur+1)%H().length)})])]);
    E.rail.addEventListener("pointerenter",()=>{ST.hover=true});E.rail.addEventListener("pointerleave",()=>{ST.hover=false});
    E.rail.addEventListener("keydown",e=>{if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();e.stopPropagation();const n=H().length;HEROUI.open((ST.cur+(e.key==="ArrowRight"?1:n-1))%n);const b=E.strip.children[ST.cur];if(b)b.focus()}});
    H().forEach((it,i)=>{const b=el("button",{class:"th "+(it.ok?"v":"i"),type:"button",role:"option",title:`${it.p} · ${laneName(it.m)} · measured ${fmt.pct(it.nb,1)}`,data:{i:String(i)},onclick:()=>HEROUI.open(i)},
      [el("img",{src:"data:image/jpeg;base64,"+it.jpg,alt:`measured frame of ${it.p}`,width:"128",height:"96"}),el("span",{class:"lbl",text:`${it.p} · ${laneName(it.m)}`})]);E.strip.appendChild(b)});return E.rail},
  update(){[...E.strip.children].forEach((b,i)=>{b.classList.toggle("sel",i===ST.cur);b.setAttribute("aria-selected",i===ST.cur?"true":"false")});const b=E.strip.children[ST.cur];if(b&&b.scrollIntoView)try{b.scrollIntoView({block:"nearest",inline:"nearest"})}catch(e){}
    txt(E.cap,`hero ${ST.cur+1} of ${H().length} · measured frames · ${ST.auto?"auto 14 s":"← →"}`)},
  arm(){if(ST.auto){ST.auto();ST.auto=null}__hero.auto=false;if(!(self.FX&&FX.level>0)||navigator.webdriver||(self.ENV&&ENV.reducedMotion)||H().length<2)return;
    __hero.auto=true;ST.auto=later(()=>{ST.auto=null;if(!ST.hover&&ST.visible&&!document.hidden)HEROUI.open((ST.cur+1)%H().length,{auto:true});rail.arm()},14000)}};
/* ---------- the stage: mode and loads ---------- */
function note(s){txt("stageMsg",s)}
async function show(it,staged,opts){opts=opts||{};if(!self.STAGE||!STAGE.show)return null;const sh=STAGE.show;
  if(!sh.ok){ST.pending={it,staged};note("stage not ready yet · the load follows");return null}
  const cur=self.__stage&&__stage.show.lastHash===contentHash(it.body);
  if(staged&&cur&&!opts.reload){if(!sh.staged){const ok=sh.setStaged(true,{orbit:true});note(ok?"STAGED · rig applied at render time to the loaded world · hash unchanged":"STAGED refused: "+(__stage.show.rig&&__stage.show.rig.err||"no rig"))}}
  else{ST.loads++;__hero.loads=ST.loads;const r=await sh.load(it.body,{staged,scene:"hero",orbit:true});if(r.cancelled)return r;
    if(r.ok)note(staged?`staged load · ${it.p} · ${fmt.int(r.ms)} ms · rig applied after the parse`:`fresh load · raw bytes · ${it.p} · ${fmt.int(r.ms)} ms · no rig`);else if(r.err)note(r.err)}
  measuredCard.seg();return true}
function measureFor(it){if(!it)return;const first=H()[0]&&it.idx===H()[0].idx;
  if(first){if(self.BOOT&&BOOT.heroMeasure&&!BOOT.heroMeasure.cancelled)ST.measured.set(it.idx,BOOT.heroMeasure);else if(!ST.measured.has(it.idx))ST.measured.set(it.idx,{wait:true});return}
  const have=ST.measured.get(it.idx);if(have&&!have.wait)return;
  if(!(self.BOOT&&BOOT.heroMeasure)&&self.BOOT&&performance.now()-BOOT.t0<70000){ST.measured.set(it.idx,{wait:true});return}   /* never pre-empt the boot measure */
  if(!self.STAGE||!STAGE.measure||!STAGE.measure.ok)return;ST.measured.set(it.idx,{pending:true});
  STAGE.measure.show(it.body,{timeoutMs:15000}).then(R=>{if(R.cancelled){ST.measured.delete(it.idx);return}ST.measured.set(it.idx,R);measuredCard.live();if(self.RASTER&&RASTER.live)RASTER.live(it.key,R,"hero measured card")}).catch(()=>ST.measured.delete(it.idx))}
function open(i,opts){opts=opts||{};const items=H();if(!items.length)return null;i=((+i|0)%items.length+items.length)%items.length;const it=items[i];ST.cur=i;__hero.cur=i;
  measuredCard.update(it);plaque.update(it);rail.update();measureFor(it);measuredCard.live(it);
  if(!opts.noLoad)show(it,wantStaged());if(!opts.auto)rail.arm();return it}
function toggle(mode){const it=H()[ST.cur];if(!it)return null;const staged=mode==null?!(self.__stage&&__stage.show.staged):mode==="staged";ST.want=staged;
  return show(it,staged,{reload:!staged})}
/* ---------- tiles ---------- */
/* "+ your N": when S.flags.includeMine is on (18-lane drives it and emits SIM "flags"), every tile adds the viewer's own scenes (S.viewer with src "viewer") — a count, never folded into the record's number */
function updateMine(){if(!E.mine)return;const on=!!(self.S&&S.flags&&S.flags.includeMine),n=on?((self.S&&S.viewer)||[]).filter(sc=>sc&&sc.src==="viewer").length:0;E.mine.forEach(m=>{m.hidden=!on;if(on)txt(m,`+ your ${fmt.int(n)}`)});__hero.mine=on?n:null}
function tile(id,sub){const c=CLAIMS.get(id)||{};const k=el("div",{class:"kpi ttile",data:{claim:id}});k.appendChild(claimChip(id,{size:"tile",label:""}));const mine=el("span",{class:"mine",hidden:""});k.appendChild(mine);E.mine.push(mine);k.appendChild(sub);
  const st=el("div",{class:"st"});[stampOk("source",c.source),stampOk("validator",c.validator),stampOk("renderer",c.renderer)].forEach(s=>{if(s)st.appendChild(s)});st.appendChild(gradeChip(c.grade));k.appendChild(st);return k}
function ratesSub(){const sub=el("div",{class:"sub"});E.lanes=el("div");const paint=()=>{const c=CLAIMS.get("c.rates"),v=(c&&(c.value||c.expected))||[];E.lanes.textContent="";
    sub.firstChild&&txt(sub.firstChild,`% valid, first try → end of loop · three paid lanes (${v.map(x=>x.n).join("/")} scenes) · ${c&&c.status==="earned"?"recomputed from LIVE":"from the record"}`);
    v.forEach(x=>E.lanes.append(el("span",{text:`${laneName(x.id)} ${x.firstPct} `}),el("span",{class:"arrow",data:{m:x.id},text:"→"}),el("span",{text:` ${x.validPct}  `})))};
  sub.append(el("div",{text:""}),E.lanes);CLAIMS.on("c.rates",paint);paint();return sub}
function sevenSub(){const sub=el("div",{class:"sub"});sub.append(el("div",{text:"valid on the fork, nothing drawn in X_ITE 16.5.0 and 16.5.1 (nonblank < 0.5%)"}),el("div",{class:"row"},[claimChip("c.seven",{size:"s",label:"16.5.0 pass"}),claimChip("hero.seven151",{size:"s",label:"16.5.1 pass"}),claimChip("hero.valid_finals",{size:"s",label:"valid finals"})]));return sub}
function ratioSub(){const sub=el("div",{class:"sub"});sub.append(el("div",{text:"validator median vs model-call median · the ratio computed, not typed"}),el("div",{class:"row"},[claimChip("c.calls",{size:"s",label:"calls"}),claimChip("hero.ratio_x",{size:"s",label:"× median"})]));return sub}
function defineClaims(){const sc=(self.STATS&&STATS.claims)||{},fin=i=>i.A[i.A.length-1];
  CLAIMS.define("hero.valid_finals",{label:"valid finals",unit:"final attempt valid on fork@eb4b4b4",needs:["live.core"],expected:sc["c.seven"]&&sc["c.seven"].of,grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none",compute(){return LIVE.filter(i=>fin(i).ok).length}});
  CLAIMS.define("hero.seven151",{label:"valid, blank in the 16.5.1 pass",unit:"finals valid on the fork with nonblank < 0.5% in renders.151",needs:["live.core","renders.151"],expected:sc["c.seven"]&&sc["c.seven"].expected,grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.1 offline",
    compute(){return LIVE.filter(i=>{const f=fin(i);if(!f.ok)return false;const r=R151.live[keyOf(i.m,i.p,i.A.length)];return !!r&&!r.err&&(r.nb||0)<.005}).length}});
  CLAIMS.define("hero.ratio_x",{label:"model-call median over validator median",unit:"× (rounded)",needs:["live.core"],expected:sc["c.ratio"]&&sc["c.ratio"].expected&&sc["c.ratio"].expected.x,grade:"C",source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"none",
    compute(){const med=a=>UTIL.median(a);return Math.round(med(LIVE.flatMap(i=>i.A.map(a=>a.ms)))/Math.max(1,med(LIVE.flatMap(i=>i.A.map(a=>a.vms)))))}})}
function lanesFromLive(){if(!self.LIVE||!LIVE.length)return;ST.lanes=paid().map(m=>({id:m.id,last:Math.max(0,...LIVE.filter(i=>i.m===m.id).map(i=>i.T||0))}));__hero.lanes=ST.lanes}
/* ---------- the report spine ---------- */
function hero_spine_pick(){const h=H().find(it=>it.calls>1);if(h)return{src:"hero",it:h,idx:h.idx};const o=self.MODES&&MODES.get("live17")?MODES.get("live17").order():[];const idx=o[2];
  return idx!=null&&self.LIVE&&LIVE[idx]?{src:"live",it:LIVE[idx],idx}:null}
function spineData(pick){if(!pick)return null;const it=pick.it,L=pick.src==="hero"?liveOf(it):it,A=L?L.A:null,a0=A&&A[0],aN=A&&A[A.length-1];
  const raw=a0&&((a0.xe&&a0.xe[0])||(a0.se&&a0.se[0]))||"";const finding=raw?raw.replace(/^-\s*/,"").replace(/\*\*/g,"").replace(/\s+/g," ").trim():(it.finding||"");
  return{p:it.p,m:it.m,idx:pick.idx,key:pick.src==="hero"?it.key:keyOf(it.m,it.p,it.A.length),finding,codes:a0?codesOf(a0):(it.codes||[]),rl:a0?a0.rl:it.rl,vms1:a0?a0.vms:it.vms1,vmsN:aN?aN.vms:it.vmsN,
    jpg1:a0&&a0.r&&a0.r.jpg||null,jpgN:pick.src==="hero"?it.jpg:(aN&&aN.r&&aN.r.jpg||null),nb1:a0&&a0.r?a0.r.nb:null,nbN:pick.src==="hero"?it.nb:(aN&&aN.r?aN.r.nb:null),calls:A?A.length:it.calls,
    B:L&&L.B&&L.B.length>=(A?A.length:0)?L.B:null,live:L,sceneId:self.S&&S.liveIds&&L?S.liveIds.get(L.i):null}}
const spine={
  build(){E.sp1=el("span",{class:"fr i"});E.spF=el("div",{class:"finding"});E.spV1=el("div",{class:"vline"});E.spArrow=el("div",{class:"sarrow"});E.sp2=el("span",{class:"fr v"});E.spV2=el("div",{class:"vline"});E.spDl=el("div",{class:"dl"});
    E.spA=el("img",{class:"a",alt:"attempt 1",width:"96",height:"72"});E.spB=el("img",{class:"b",alt:"final",width:"96",height:"72"});
    E.spRange=el("input",{type:"range",min:"0",max:"1",step:"0.01",value:"0","aria-label":"crossfade attempt 1 to final",oninput:e=>{ST.spineT=+e.target.value;E.spB.style.opacity=String(ST.spineT)}});
    E.spOpen=el("button",{class:"primary",text:"Open the morph",onclick:()=>{const d=spineData(ST.spinePick);if(d&&self.MORPH)MORPH.open(d.live||d.idx);const m=$("morph");if(m)m.scrollIntoView({behavior:self.FX&&FX.level>0?"smooth":"auto",block:"start"})}});
    E.spHead=el("div",{class:"sphead"});
    E.spine=el("div",{class:"spine"},[E.spHead,el("div",{class:"sprow"},[E.sp1,el("div",null,[E.spF,E.spV1])]),E.spArrow,el("div",{class:"sprow"},[E.sp2,el("div",null,[E.spV2,E.spDl])]),
      el("div",{class:"scrub"},[el("span",{class:"fade"},[E.spA,E.spB]),E.spRange]),el("div",{class:"foot"},[E.spOpen,el("span",{class:"legend",text:"the frames are the counted ones (192×144, X_ITE 16.5.0 offline); the morph shows the live render"})])]);return E.spine},
  update(){const pick=hero_spine_pick();ST.spinePick=pick;__hero.spinePick=pick?{src:pick.src,idx:pick.idx,p:pick.it.p}:null;const d=spineData(pick);if(!d){txt(E.spHead,"report spine: waits for live.core (no repaired hero inline)");return}
    txt(E.spHead,`THE REPAIR LOOP · ${d.p} · ${laneName(d.m)} · ${d.calls} calls${d.sceneId?" · "+d.sceneId:""}`);
    const fr=(host,jpg,nb,label,pending)=>{host.textContent="";if(jpg){host.appendChild(el("img",{src:"data:image/jpeg;base64,"+jpg,alt:label,width:"96",height:"72"}));host.appendChild(el("span",{class:"fx",text:`${label} · ${nb!=null?fmt.pct(nb,1):"—"}`}))}else host.appendChild(el("span",{class:"nf",text:pending}))};
    fr(E.sp1,d.jpg1,d.nb1,"attempt 1","attempt 1 frame arrives with part live.jpg");fr(E.sp2,d.jpgN,d.nbN,"final","final frame");
    E.spF.className="finding"+(d.finding?"":" none");txt(E.spF,d.finding||"the validator's first finding line arrives with part live.core");
    E.spV1.textContent="";d.codes.forEach(c=>E.spV1.appendChild(el("span",{class:"pill p-bad",text:c})));E.spV1.appendChild(el("span",{text:`INVALID on fork@eb4b4b4 in ${fmt.int(d.vms1)} ms`}));
    txt(E.spArrow,`↓ the model was sent its own report · ${fmt.int(d.rl)} characters`);
    E.spV2.textContent="";E.spV2.appendChild(el("span",{class:"pill p-ok",text:"valid"}));E.spV2.appendChild(el("span",{text:`VALID on fork@eb4b4b4 in ${fmt.int(d.vmsN)} ms · attempt ${d.calls}`}));
    if(d.B&&self.DIFF){const r=DIFF.diffRows(d.B[0],d.B[d.B.length-1],1);E.spDl.textContent="";E.spDl.append(el("b",{text:`+${r.add} −${r.del} tag lines of ${r.base}`}),` · ${fmt.pct((r.add+r.del)/Math.max(1,r.base),0)} of the scene rewritten · diff computed in this page`)}
    else txt(E.spDl,self.DIFF?"diff arrives with part live.bodies":"diff needs module 14-morph");
    if(d.jpg1)E.spA.src="data:image/jpeg;base64,"+d.jpg1;else E.spA.removeAttribute("src");if(d.jpgN)E.spB.src="data:image/jpeg;base64,"+d.jpgN;else E.spB.removeAttribute("src");E.spB.style.opacity=String(ST.spineT)}};
/* ---------- mount ---------- */
function header(){return{title:"The stage",unit:`${H().length} hero scenes · the counted frame pinned · the thesis in three numbers · the repair spine`,stamps:{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline + 16.5.1 offline"},grade:"C",
  honesty:"staged render (lights, ground, camera at render time, nothing written) · counted frame: X_ITE 16.5.0 swiftshader offline, pinned top-right, 16.5.1 twin printed · verdict fork@eb4b4b4 · Confirmed for this scene"}}
function mount(sec){ST.sec=sec;const view=$("stageView"),band=$("hero");if(!view||!band)return;defineClaims();stagedManifest();
  view.appendChild(el("div",{class:"sov thesis"},[el("h1",{text:THESIS.h1}),el("h2",{text:THESIS.h2}),el("p",{text:THESIS.p})]));
  view.appendChild(measuredCard.build());view.appendChild(plaque.build());view.appendChild(rail.build());
  view.addEventListener("dblclick",e=>{if(e.target.closest(".sov"))return;if(self.STAGE&&STAGE.show&&STAGE.show.reset)STAGE.show.reset()});
  E.mine=[];const tiles=el("div",{class:"tiles"},[tile("c.rates",ratesSub()),tile("c.seven",sevenSub()),tile("c.ratio",ratioSub())]);
  const legend=el("div",{class:"legend tiles-legend",text:"two-tone rule: grey = known from the record (stats.json) · bright = recomputed in this view from the loaded parts · red = computed and recorded disagree, both printed · click a tile for the proof drawer"});
  band.textContent="";band.appendChild(el("div",{class:"band cols-7-5"},[el("div",null,[tiles,legend]),spine.build()]));
  open(0,{noLoad:true});spine.update();
  document.addEventListener("keydown",e=>{if(e.target&&/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))return;if((e.key==="m"||e.key==="M")&&ST.visible)toggle()});
  /* visibility is owned here (IO on the view): IO keeps ONE callback per element and 10-curtain-mast's RAIL.init observes every main section, which would
     replace a LOOP panel's own `el:sec` observer (the panel would then never see the viewport) — so the panel below has no el and reads ST.visible */
  IO.observe(view,v=>{ST.visible=v;__hero.visible=v;if(v){rail.arm();if(self.LOOP)LOOP.dirty(LOOP.bits.CLOCK|LOOP.bits.DATA)}else if(ST.auto){ST.auto();ST.auto=null;__hero.auto=false}},{rootMargin:"0px"});
  if(self.FX)FX.onChange(()=>{rail.arm();if(ST.want==null&&self.__stage&&__stage.show.ready){ST.stagedApplied=false}});
  if(self.SIM&&SIM.on){SIM.on("flags",updateMine);SIM.on("viewer",updateMine);SIM.on("fresh",updateMine)}updateMine();
  LOOP.register({name:"hero",bit:LOOP.bits.CLOCK|LOOP.bits.DATA|LOOP.bits.SCENE|LOOP.bits.VERIFY,rateHz:2,budgetMs:2,draw(){updateMine();if(!ST.visible)return;const it=H()[ST.cur];if(!it)return;
    if(self.S&&E.lanes)E.lanes.querySelectorAll(".arrow").forEach(a=>{const ln=ST.lanes.find(l=>l.id===a.dataset.m);a.classList.toggle("on",!!ln&&S.clk>=ln.last)});
    plaque.tick(it);
    const R=ST.measured.get(it.idx);if(!R||R.wait){measureFor(it);measuredCard.live(it)}
    if(self.__stage&&__stage.show.ready){if(ST.pending&&STAGE.show.ok){const p=ST.pending;ST.pending=null;show(p.it,p.staged)}
      else if(!ST.stagedApplied&&__stage.show.loads>=1&&wantStaged()&&!__stage.show.staged&&STAGE.show.ok){ST.stagedApplied=true;show(it,true)}
      measuredCard.seg()}}})}
function onData(name){if(name==="live.core"){lanesFromLive();spine.update();plaque.update(H()[ST.cur])}else if(name==="live.jpg"||name==="live.bodies"||name==="renders.151")spine.update()}
const HEROUI={open,toggle,stagedManifest,stagedLines,select(key){const i=H().findIndex(it=>it.key===key||it.p===key||it.idx===key);return i>=0?open(i):null},mode:()=>ST.mode,measuredCard,plaque,spine,cur:()=>H()[ST.cur]||null,items:H,hero_spine_pick,state:ST};
SECTIONS.register({id:"stage",part:"live.core",header:header(),mount(sec){try{mount(sec)}catch(e){console.error("hero mount",e);if(self.BOOT)BOOT.error(e,"hero mount")}},onData});
if(self.HERO&&typeof HERO==="object")Object.assign(HERO,{open,select:HEROUI.select,plaque,spine,measuredCard});
__hero.updateMine=updateMine;__hero.stagedLines=stagedLines;Object.assign(self,{HEROUI,hero_spine_pick,__hero});
})();
