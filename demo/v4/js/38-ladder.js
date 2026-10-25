/* 38-ladder.js — S12 Validator ladder: the verdict braid, the commit slider, RE-VALIDATE 558 on the js-port. Owns section #ladder.
   Globals: LADDER (state + helpers), SLIDER (commit notches → S.vi generalised; shared with 34-bench and read by 36-wall), PORT (the in-browser corpus run).
   Ported from demo/tether-firehose-v3.template.html: bUpgrade / bRevalidate (897–898: "re-validated N scenes on <ref>: F flipped valid → invalid. Answered from the files alone."),
   svgDrift's per-commit counts (as a braid on canvas instead of an SVG), VALS strictness ladder (340). New in v4: the ten rails over the drift part (recorded verdicts per commit),
   the 383-live switch, the S-bends, the "not investigated (S)" label computed from the data, the port rail that lights only after a RE-VALIDATE here, the commit slider that
   recolours the wall's verdict bars (SLIDER.verdictOf), the labelled chip when VAL is absent (recorded rails only), the result line with MANIFEST.canary printed as expected.
   VAL surface used (ARCHITECTURE 05): VAL.init, VAL.ready, VAL.mode, VAL.reason, VAL.label, VAL.validate, VAL.validateMany(items, onProgress), VAL.on, codesOfRes, reportHtml.
   Test hooks: __panels.braid {threads, flips, rails, draws}, SLIDER.set(ref|i)/SLIDER.i/SLIDER.ref/SLIDER.active/SLIDER.verdictOf(sc), #commitSlider, #ladder .notch, #bRevalidate, #bUpgrade,
   #bRevalPort, #portLine, #ladder .valChip, #liveSwitch, PORT.result {n, agree, flips, agreeEb, codeDiffs, ms, list, via: 'VAL.canary' | 'VAL.validateMany'}, PORT.res (Map id → VAL result), SLIDER.notches (the 10-notch commit list the bench may adopt), LADDER.rails, LADDER.counts() (per rail valid counts from the data). */
(function(){
"use strict";
const BITS=LOOP.bits;
const RAILS=[{id:"svc",ref:"svc@11Oct",short:"svc@11Oct",kind:"svc",vals:"svc"},{id:"8c0a457",ref:"fork@8c0a457",short:"8c0a457",kind:"drift",vals:"f1"},{id:"c9c9788",ref:"fork@c9c9788",short:"c9c9788",kind:"drift"},{id:"688174f",ref:"fork@688174f",short:"688174f",kind:"drift"},
  {id:"76fc439",ref:"fork@76fc439",short:"76fc439",kind:"drift"},{id:"d61d4de",ref:"fork@d61d4de",short:"d61d4de",kind:"drift"},{id:"eb4b4b4",ref:"fork@eb4b4b4",short:"eb4b4b4",kind:"drift",vals:"f2"},{id:"d5598c4",ref:"fork@d5598c4",short:"d5598c4",kind:"drift"},
  {id:"8dd0d3e",ref:"fork@8dd0d3e",short:"8dd0d3e canary",kind:"canary",vals:"f3"},{id:"port",ref:"js-port-of-8dd0d3e",short:"js-port now",kind:"port",vals:"port"}];
const LIVE_PREFIX="live-2026-10-17/x3d/";
/* ---------- recorded verdicts per rail (null = no verdict recorded for this body on this rail) ---------- */
function vReplay(it,rail){if(!it)return null;if(rail.kind==="svc")return !!(it.x&&it.s);if(rail.kind==="drift"){const bc=self.DRIFT&&DRIFT.by_commit[rail.id];if(bc&&bc[it.k])return !!bc[it.k].valid;if(rail.id==="8c0a457"&&it.f1)return !!it.f1[0];if(rail.id==="eb4b4b4"&&it.f2)return !!it.f2[0];return null}
  if(rail.kind==="canary"){const v=self.DRIFT&&DRIFT.v8dd0d3e.verdicts["replay/"+it.k];return v?!!v.valid:null}
  if(rail.kind==="port"){const r=PORT.res&&PORT.res.get("R:"+it.k);return r?!!r.valid:null}return null}
function vLive(it,k,rail){if(!it)return null;const a=it.A[k];if(rail.id==="eb4b4b4")return a?!!a.ok:null;if(rail.kind==="canary"){const v=self.DRIFT&&DRIFT.v8dd0d3e.verdicts[LIVE_PREFIX+keyOf(it.m,it.p,k+1)];return v?!!v.valid:null}
  if(rail.kind==="port"){const r=PORT.res&&PORT.res.get("L:"+keyOf(it.m,it.p,k+1));return r?!!r.valid:null}return null}
function vCut(key,rail){if(rail.kind==="canary"){const v=self.DRIFT&&DRIFT.v8dd0d3e.verdicts[LIVE_PREFIX+key];return v?!!v.valid:null}if(rail.kind==="port"){const r=PORT.res&&PORT.res.get("C:"+key);return r?!!r.valid:null}return null}
const codesRec=v=>(v.xsd?[]:["xsd"]).concat(v.sem||[]);
/* ---------- SLIDER: the commit cursor (S.vi generalised) ---------- */
const SLIDER={notches:RAILS,i:null,ref:null,active:false,
  set(x){const i=typeof x==="number"?x:RAILS.findIndex(r=>r.id===x||r.ref===x||r.short===x);if(i<0||i>=RAILS.length)return null;const rail=RAILS[i];SLIDER.i=i;SLIDER.ref=rail.ref;SLIDER.active=true;
    if(rail.vals&&self.S){const vi=VALS.findIndex(v=>v.id===rail.vals);if(vi>=0)S.vi=vi}
    const sl=$("commitSlider");if(sl&&+sl.value!==i)sl.value=String(i);document.querySelectorAll("#ladder .notch").forEach(b=>b.classList.toggle("on",+b.dataset.i===i));
    if(self.S&&!S.ff)logEv("sys",`validator cursor on ${rail.ref}: wall and KPIs now read that commit's recorded verdicts${rail.kind==="port"?" (lit only where the port ran here)":""}; ${self.S?S.scenes.filter(s=>s.vref!==rail.ref).length:0} stored chains carry another ref`);
    LADDER.syncButtons();LOOP.dirty(BITS.VERIFY|BITS.SELECT|BITS.MODE|BITS.VAL);return rail},
  rail:()=>SLIDER.i==null?null:RAILS[SLIDER.i],
  /* 'valid' | 'invalid' | null (no verdict recorded for this body on this commit) | undefined (not a recorded body: use the scene's own verdict) */
  verdictOf(sc){const rail=SLIDER.rail();if(!rail||!sc)return undefined;let v;if(sc.src==="real")v=vReplay(sc.item,rail);else if(sc.src==="live")v=vLive(sc.item,sc.item.A.length-1,rail);else if(sc.port&&rail.kind==="port")v=!!sc.port.valid;else return undefined;
    if(v===null&&rail.kind==="port"&&sc.port)v=!!sc.port.valid;return v===null?null:v?"valid":"invalid"},
  availability(sc){return RAILS.map(r=>{if(!sc)return false;if(sc.src==="real")return vReplay(sc.item,r)!==null;if(sc.src==="live")return vLive(sc.item,sc.item.A.length-1,r)!==null;return r.kind==="port"&&!!sc.port})},
  followMode(){if(!self.S)return;const v=VALS[S.vi],i=RAILS.findIndex(r=>r.vals===v.id);if(i>=0){SLIDER.i=i;SLIDER.ref=RAILS[i].ref;SLIDER.active=true;const sl=$("commitSlider");if(sl)sl.value=String(i);document.querySelectorAll("#ladder .notch").forEach(b=>b.classList.toggle("on",+b.dataset.i===i))}LADDER.syncButtons()}};
/* ---------- PORT: the corpus run on js-port-of-8dd0d3e ---------- */
const PORT={res:null,result:null,busy:false,done:0,n:0,hist:{},t0:0,
  corpus(){const items=(self.WALL?WALL.corpus():[]).map(it=>{let rec=null,eb=null;
      if(it.src==="real"){const v=self.DRIFT&&DRIFT.v8dd0d3e.verdicts["replay/"+it.item.k];rec=v?{valid:!!v.valid,codes:codesRec(v)}:null;eb=it.item.f2?{valid:!!it.item.f2[0],codes:it.item.f2[1]||[]}:null}
      else if(it.src==="live"){const key=keyOf(it.item.m,it.item.p,it.k+1),v=self.DRIFT&&DRIFT.v8dd0d3e.verdicts[LIVE_PREFIX+key],a=it.item.A[it.k];rec=v?{valid:!!v.valid,codes:codesRec(v)}:null;eb=a?{valid:!!a.ok,codes:codesOf(a)}:null}
      else if(it.src==="cut"){const v=self.DRIFT&&DRIFT.v8dd0d3e.verdicts[LIVE_PREFIX+it.id.slice(2)];rec=v?{valid:!!v.valid,codes:codesRec(v)}:null}
      else if(it.src==="ledger"){const k=Object.keys((self.DRIFT&&DRIFT.v8dd0d3e.verdicts)||{}).find(x=>/ledger\.x3d$/.test(x));const v=k&&DRIFT.v8dd0d3e.verdicts[k];rec=v?{valid:!!v.valid,codes:codesRec(v)}:null}
      return{id:it.id,src:it.src,xml:it.xml,rec,eb}});return items},
  /* the body behind a recorded-verdict key (the ids VAL.canary reports): replay/<k> → REAL[].b; live-…/x3d/<model_>/<p>_a<k>.x3d → LIVE[].B[k-1] or a cut body; …ledger.x3d → LEDGER.text */
  bodyOf(id){let m=/^replay\/(.+)$/.exec(id);if(m){const it=(self.REAL||[]).find(i=>i.k===m[1]);return it?{xml:it.b,src:"real",item:it,key:"R:"+it.k}:null}
    m=/^live-[\d-]+\/x3d\/(.+?)\/([\w-]+)_a(\d+)\.x3d$/.exec(id);if(m){const it=(self.LIVE||[]).find(i=>i.m.replace("/","_")===m[1]&&i.p===m[2]),k=+m[3]-1;if(it&&it.B&&typeof it.B[k]==="string")return{xml:it.B[k],src:"live",item:it,k,key:"L:"+keyOf(it.m,it.p,k+1)};
      const cut=((self.EVENTS&&EVENTS.cut)||[]).find(c=>c.m.replace("/","_")===m[1]&&c.p===m[2]),b=cut&&cut.bodies&&cut.bodies[k],xml=typeof b==="string"?b:b&&b.xml;return typeof xml==="string"?{xml,src:"cut",key:"C:"+((b&&b.k)||keyOf(cut.m,cut.p,k+1))}:null}
    if(/ledger\.x3d$/.test(id))return self.LEDGER&&LEDGER.text?{xml:LEDGER.text,src:"ledger",key:"ledger"}:null;return null},
  /* per-body results after a run: VAL memoises by the raw body's hash, so every body on the page is looked up without a second validation */
  collect(){const res=new Map(),memo=x=>typeof x==="string"&&typeof sha==="function"?VAL.memo.get(sha(x)):null;
    (self.REAL||[]).forEach(it=>{const r=memo(it.b);if(r)res.set("R:"+it.k,r)});
    (self.LIVE||[]).forEach(it=>(it.B||[]).forEach((x,k)=>{const r=memo(x);if(r)res.set("L:"+keyOf(it.m,it.p,k+1),r)}));
    ((self.EVENTS&&EVENTS.cut)||[]).forEach(c=>(c.bodies||[]).forEach((b,i)=>{const r=memo(typeof b==="string"?b:b&&b.xml);if(r)res.set("C:"+((b&&b.k)||keyOf(c.m,c.p,i+1)),r)}));
    if(self.LEDGER&&LEDGER.text){const r=memo(LEDGER.text);if(r)res.set("ledger",r)}return res},
  codesCanary(v){return (v&&v.xsd===false?["xsd"]:[]).concat((v&&v.sem)||[])},
  async run(){if(PORT.busy)return PORT.p;if(!self.VAL)return null;await (VAL.need?VAL.need():VAL.init());if(VAL.mode!=="full"){LADDER.valChip();return null}
    PORT.busy=true;PORT.done=0;PORT.hist={};PORT.t0=performance.now();const btn=$("bRevalPort");if(btn)btn.disabled=true;
    PORT.p=(async()=>{if(self.LEDGER)await LEDGER.load();LOOP.dirty(BITS.VAL);
      const onProg=(i,n,r)=>{PORT.done=i;PORT.n=n;codesOfRes(r).forEach(c=>{PORT.hist[c]=(PORT.hist[c]||0)+1});if(!(i%8)||i===n)LOOP.dirty(BITS.VAL)};
      const miss=self.WALL?WALL.missingCut():0,exp=(self.MANIFEST&&MANIFEST.canary)||null;let R;
      if(typeof VAL.canary==="function"){
        /* 05-val's canary: every body with a recorded fork@8dd0d3e verdict, the flip rule of drift/canary.py (valid flag, XSD flag and error count, semantic code set) */
        const c=await VAL.canary(onProg);if(c.reason&&!c.bodies)throw new Error(c.reason);
        const list=c.flips.map(f=>{const b=PORT.bodyOf(f.id)||{},pc=f.port||{};return{id:f.id,src:b.src,xml:b.xml,recorded:{valid:!!(f.recorded&&f.recorded.valid),codes:PORT.codesCanary(f.recorded)},port:pc.error?{valid:null,codes:[],error:pc.error}:{valid:!!pc.valid,codes:PORT.codesCanary(pc)}}});
        /* agreement with fork@eb4b4b4 from the record: a body's port valid flag is the recorded 8dd0d3e flag unless the canary saw it flip */
        const flipV=new Map(c.flips.map(f=>[f.id,f.port&&f.port.error?null:!!(f.port&&f.port.valid)])),V=(self.DRIFT&&DRIFT.v8dd0d3e.verdicts)||{};let agreeEb=0,nEb=0;
        for(const k in V){const b=PORT.bodyOf(k);if(!b)continue;const pv=flipV.has(k)?flipV.get(k):!!V[k].valid;if(pv===null)continue;const eb=b.src==="real"?(b.item.f2?!!b.item.f2[0]:null):b.src==="live"?(b.item.A[b.k]?!!b.item.A[b.k].ok:null):null;if(eb===null)continue;nEb++;if(pv===eb)agreeEb++}
        R={n:c.bodies,nRec:c.bodies,agree:c.agree,flips:list.length,codeDiffs:list.filter(f=>f.port.valid!==null&&f.port.valid===f.recorded.valid).length,agreeEb,nEb,ms:c.ms,list,missing:miss,skipped:(c.skipped||[]).length,warnDiff:c.warnDiff||0,perBody:c.perBody||null,transport:c.transport||VAL.transport||null,groups:c.groups||null,via:"VAL.canary"};
        R.line=`${R.n} bodies · ${fmt.ms(R.ms)} on js-port-of-8dd0d3e${R.transport?" ("+R.transport+")":""} · agree with fork@8dd0d3e on ${R.agree} of ${R.n} (${R.flips} flips by the canary rule: valid flag, XSD flag and count, semantic code set; ${R.codeDiffs} of them code-set only; ${R.warnDiff} warning-set differences) · agree with fork@eb4b4b4 on ${agreeEb} of ${nEb}${exp?` · expected (recorded canary, drift/canary.py 24 Oct): ${exp.bodies} bodies, ${exp.flips} flips`:""}${R.skipped?` · ${R.skipped} bodies named by the record are not on this page${miss?` (${miss} cut-chain bodies absent from the events part)`:""}`:""}`}
      else{ /* a 05-val without canary(): the same comparison on every body on the page, through validateMany */
        const items=PORT.corpus();PORT.n=items.length;const out=await VAL.validateMany(items.map(it=>({id:it.id,xml:it.xml})),onProg);
        let list=[],codeDiffs=0,agreeEb=0,nEb=0,nRec=0;items.forEach(it=>{const r=out.get(it.id);if(!r)return;
          if(it.rec){nRec++;if(!!r.valid!==it.rec.valid)list.push({id:it.id,src:it.src,recorded:it.rec,port:{valid:!!r.valid,codes:codesOfRes(r)},res:r,xml:it.xml});else if(VAL.compare(r,it.rec.valid,it.rec.codes)==="differs")codeDiffs++}
          if(it.eb){nEb++;if(!!r.valid===it.eb.valid)agreeEb++}});
        const ms=performance.now()-PORT.t0;R={n:items.length,nRec,agree:nRec-list.length,flips:list.length,codeDiffs,agreeEb,nEb,ms,list,missing:miss,skipped:0,warnDiff:0,perBody:null,transport:VAL.transport||null,groups:null,via:"VAL.validateMany"};
        R.line=`${R.n} bodies · ${fmt.ms(ms)} on js-port-of-8dd0d3e · agree with fork@8dd0d3e on ${R.agree} of ${nRec} (${R.flips} flips of the valid flag, ${codeDiffs} code-set differences) · agree with fork@eb4b4b4 on ${agreeEb} of ${nEb}${exp?` · expected (recorded canary, drift/canary.py 24 Oct): ${exp.bodies} bodies, ${exp.flips} flips`:""}${miss?` · ${miss} cut-chain bodies absent from the events part`:""}`}
      PORT.res=PORT.collect();PORT.result=R;
      /* light the port rail on the stored scenes (never a bench row), so judge(sc, port) and the braid's 10th rail read measured verdicts */
      if(self.S)S.scenes.forEach(sc=>{if(sc.src==="bench"||!sc.item)return;const id=sc.src==="real"?"R:"+sc.item.k:sc.src==="live"?"L:"+keyOf(sc.item.m,sc.item.p,sc.item.A.length):null;const r=id&&PORT.res.get(id);if(r)sc.port=r});
      CLAIMS.define("l.portAgree",{label:"canary earned here: bodies · flips vs fork@8dd0d3e",unit:"js-port-of-8dd0d3e in this browser"+(R.via==="VAL.canary"?" · VAL.canary, the drift/canary.py flip rule":""),expected:exp?{bodies:exp.bodies,flips:exp.flips}:undefined,compute:()=>PORT.result?{bodies:PORT.result.n,flips:PORT.result.flips}:undefined,text:v=>`${v.bodies} bodies · ${v.flips} flips`,
        source:"RE-RUN HERE",validator:"js-port-of-8dd0d3e here",renderer:"none",grade:miss?"S":"C",files:["parts/replay.txt","parts/live.bodies.txt","parts/events.txt","data/physics-ledger.x3d","parts/drift.txt"],fields:["every body with a recorded fork@8dd0d3e verdict validated on the port; a flip = the valid flag, the XSD flag or count, or the semantic code set differs from the recorded verdict (drift part)"],why:miss?`${miss} cut-chain bodies named by the manifest canary are not in the events part on this page`:null});
      await CLAIMS.run("l.portAgree");LADDER.renderPort();logEv("sys",R.line);PORT.busy=false;if(btn)btn.disabled=false;LOOP.dirty(BITS.VAL|BITS.VERIFY);return PORT.result})().catch(e=>{PORT.busy=false;if(btn)btn.disabled=false;txt("portLine","RE-VALIDATE failed: "+String(e&&e.message||e));LOOP.dirty(BITS.VAL);throw e});
    return PORT.p}};
/* ---------- section ---------- */
const LADDER={rails:RAILS,sec:null,cv:null,live:false,els:{},
  counts(){const out={};const R=self.REAL||[];RAILS.forEach(r=>{let n=0,v=0;R.forEach(it=>{const x=vReplay(it,r);if(x!==null){n++;if(x)v++}});out[r.id]={n,valid:v}});return out},
  flipsBetween(a,b){const R=self.REAL||[];let vi=0,iv=0;R.forEach(it=>{const x=vReplay(it,a),y=vReplay(it,b);if(x===null||y===null)return;if(x&&!y)vi++;if(!x&&y)iv++});return{vi,iv}},
  threads(){const T=[];const R=self.REAL||[];R.forEach(it=>T.push({key:"R:"+it.k,src:"real",v:RAILS.map(r=>vReplay(it,r))}));
    if(LADDER.live){(self.LIVE||[]).forEach(it=>it.A.forEach((a,k)=>T.push({key:"L:"+keyOf(it.m,it.p,k+1),src:"live",v:RAILS.map(r=>vLive(it,k,r))})));
      const onPage=new Set((self.LIVE||[]).flatMap(it=>it.A.map((a,k)=>LIVE_PREFIX+keyOf(it.m,it.p,k+1))));Object.keys((self.DRIFT&&DRIFT.v8dd0d3e.verdicts)||{}).filter(k=>k.startsWith(LIVE_PREFIX)&&!onPage.has(k)).forEach(k=>T.push({key:"C:"+k.slice(LIVE_PREFIX.length),src:"cut",v:RAILS.map(r=>vCut(k.slice(LIVE_PREFIX.length),r))}))}
    return T},
  syncButtons(){const rail=SLIDER.rail(),b=$("bRevalidate"),u=$("bUpgrade");if(!self.S||!rail)return;const stored=S.scenes.filter(s=>(s.src==="real"||s.src==="live")&&!s.injured&&s.vref!==rail.ref);
    const can=rail.kind!=="port"?stored.some(s=>(s.src==="real"?vReplay(s.item,rail):vLive(s.item,s.item.A.length-1,rail))!==null):(self.VAL&&VAL.mode==="full");
    if(b){b.disabled=!can;txt(b,`RE-VALIDATE STORED CHAINS ON ${rail.short.toUpperCase()}`);b.title=can?`stamp a validate step with the recorded ${rail.ref} verdict on every stored chain that carries another ref`:rail.kind==="port"?"the js-port is not available in this viewer":"no recorded verdict on this commit for the stored chains"}
    if(u){const next=RAILS.slice((SLIDER.i||0)+1).find(r=>r.vals&&r.kind!=="port");u.disabled=!next;txt(u,next?"Ship next validator → "+next.short:"Latest recorded validator shipped")}},
  /* v3 bRevalidate (898), generalised to any rail with a recorded verdict; the port rail runs the js-port on each stored body */
  async revalidate(){const rail=SLIDER.rail();if(!rail||!self.S)return null;let n=0,fl=0;
    if(rail.kind==="port"){if(!self.VAL||VAL.mode!=="full")return null;for(const sc of S.scenes){if(sc.vref===rail.ref||sc.injured||!(sc.src==="real"||sc.src==="live"))continue;try{sc.port=await VAL.validate(sc.xml)}catch(e){continue}if(revalidateOne(sc,VALS.find(v=>v.id==="port")))fl++;n++}}
    else{const V=rail.vals?VALS.find(v=>v.id===rail.vals):{id:rail.id,ref:rail.ref,name:"fork",strict:2};
      S.scenes.forEach(sc=>{if(sc.vref===rail.ref||sc.injured||!(sc.src==="real"||sc.src==="live"))return;const rv=sc.src==="real"?vReplay(sc.item,rail):vLive(sc.item,sc.item.A.length-1,rail);if(rv===null)return;
        const prev=sc.verdict;let codes=[];if(sc.src==="real"){const bc=self.DRIFT&&DRIFT.by_commit[rail.id];if(bc&&bc[sc.item.k])codes=bc[sc.item.k].codes||[];else if(rail.kind==="canary"){const v=DRIFT.v8dd0d3e.verdicts["replay/"+sc.item.k];codes=v?codesRec(v):[]}else if(rail.kind==="svc")codes=rv?[]:[sc.item.x?"recorded:semantic":"recorded:xsd"]}
        else{const v=rail.kind==="canary"&&self.DRIFT&&DRIFT.v8dd0d3e.verdicts[LIVE_PREFIX+keyOf(sc.item.m,sc.item.p,sc.item.A.length)];codes=v?codesRec(v):codesOf(sc.item.A[sc.item.A.length-1])}
        const rec={op:"validate",validator:V.name||"fork",validator_ref:rail.ref,verdict:rv?"valid":"invalid",codes,ms:0,ms_src:"recorded"};if(rail.kind==="svc"){rec.recorded=true;rec.xsd_valid=!!sc.item.x;rec.semantic_valid=!!sc.item.s}
        sc.xml=addStep(sc.xml,rec,sc.xml,sc.sealed);sc.nsteps=readSteps(sc.xml).length;sc.verdict=rec.verdict;sc.vref=rail.ref;sc.status=verify(sc.xml).status;if(prev==="valid"&&rec.verdict==="invalid")fl++;n++})}
    S.revals+=n;S.flips+=fl;logEv("sys",`re-validated ${n} scenes on ${rail.ref}: ${fl} flipped valid → invalid. Answered from the files alone.`);LADDER.syncButtons();LOOP.dirty(BITS.VERIFY|BITS.SCENE|BITS.SELECT|BITS.VAL);return{n,flips:fl}},
  upgrade(){const next=RAILS.slice((SLIDER.i||0)+1).find(r=>r.vals&&r.kind!=="port");if(next)SLIDER.set(next.id);return next||null},
  valChip(){const c=LADDER.els.valChip,b=$("bRevalPort");if(!c)return;const V=self.VAL;const full=V&&V.mode==="full";
    txt(c,!V?"js-port not present in this build · recorded rails only":full?"js-port-of-8dd0d3e loaded in this viewer · RE-VALIDATE runs here, never the fork itself":V.mode==="semantic-only"?`js-port-of-8dd0d3e semantic checks only (${V.reason||"XSD not available"}) · recorded rails only for the XSD column`:V.mode==="unloaded"?"js-port-of-8dd0d3e not loaded yet · recorded rails until it is":`js-port-of-8dd0d3e not available in this viewer (${V.reason||"blocked"}) · recorded rails only`);
    c.className="chip valChip "+(full?"v":"deg");if(b){b.disabled=!full||PORT.busy;b.title=full?"validate every body on the page with the js-port and compare with the recorded verdicts":"the js-port cannot run in this viewer: the recorded rails stay, the earned figure stays empty"}},
  renderPort(){const r=PORT.result,host=LADDER.els.portOut;if(!r||!host)return;txt("portLine",r.line);host.textContent="";host.appendChild(claimChip("l.portAgree",{size:"m"}));
    if(r.list.length){const ul=el("div",{class:"flipList"});r.list.slice(0,40).forEach(f=>{const row=el("div",{class:"flip"},[el("b",{text:f.id}),el("span",{text:` recorded ${f.recorded.valid?"valid":"invalid"} [${f.recorded.codes.join(", ")||"—"}] · port ${f.port.valid?"valid":"invalid"} [${f.port.codes.join(", ")||"—"}] `}),
        el("button",{text:"open in Bench",onclick:()=>{if(self.BENCH&&BENCH.load)BENCH.load(f.xml,f.id+" (port flip)");const b=$("bench");if(b)b.scrollIntoView({behavior:"smooth"})}})]);ul.appendChild(row)});host.appendChild(ul)}
    else host.appendChild(el("span",{class:"note",text:"no flips: every valid flag the port measured here matches the recorded fork@8dd0d3e verdict"}))}};
const HONESTY="RECORDED verdicts per commit (drift/, Python fork in process, 17 Oct) · canary fork@8dd0d3e vs eb4b4b4 on 558 bodies, 0 flips (drift/canary.py, 24 Oct) · RE-RUN HERE on js-port-of-8dd0d3e: a JavaScript port of the fork at 8dd0d3e, never the fork itself · svc@11Oct was a weaker service, not an older fork";
SECTIONS.register({id:"ladder",part:"drift",header:{title:"Validator ladder: the verdict braid",unit:"9 recorded rails + the js-port rail · one thread per scene · an S-bend where a verdict flips",stamps:{source:"RECORDED per commit",validator:"fork@8dd0d3e recorded",renderer:"none"},grade:"C",honesty:HONESTY},
  mount(sec){try{mount(sec)}catch(e){console.error("ladder mount",e);if(self.BOOT)BOOT.error(e,"ladder mount")}},onData(name){if(name==="drift"||name==="replay"||name==="live.core")LOOP.dirty(BITS.DATA|BITS.VAL)}});
function mount(sec){LADDER.sec=sec;const sb=sec.querySelector(".sb");sb.textContent="";
  /* claims (expected from STATS.REALSTATS, computed from REAL + DRIFT) */
  const RS=(self.STATS&&STATS.REALSTATS)||{};
  CLAIMS.define("l.svcValid",{label:"valid on svc@11Oct",unit:"of 174 replay scenes",expected:RS.f?RS.f[0].valid:undefined,needs:["replay"],compute:()=>REAL.filter(i=>i.x&&i.s).length,source:"RECORDED 11 Oct",validator:"svc@11Oct recorded",renderer:"none",grade:"C",fields:["x and s flags recorded by the 11 Oct service"]});
  CLAIMS.define("l.flip8c0a457",{label:"valid on the service, invalid on fork@8c0a457",unit:"flips at the first fork build",expected:RS.flip,needs:["replay","drift"],compute:()=>REAL.filter(i=>i.x&&i.s&&!DRIFT.by_commit["8c0a457"][i.k].valid).length,source:"RECORDED per commit",validator:"fork@8c0a457 recorded",renderer:"none",grade:"C",fields:["svc valid and drift/by_commit 8c0a457 invalid"]});
  CLAIMS.define("l.validEb",{label:"valid on fork@eb4b4b4",unit:"of 174 replay scenes",expected:RS.f?RS.f[2].valid:undefined,needs:["replay","drift"],compute:()=>REAL.filter(i=>DRIFT.by_commit["eb4b4b4"][i.k].valid).length,source:"RECORDED per commit",validator:"fork@eb4b4b4 recorded",renderer:"none",grade:"C",fields:["drift/by_commit eb4b4b4 valid flag"]});
  const chips=el("div",{class:"row ladderChips"},[claimChip("l.svcValid",{size:"m"}),claimChip("l.flip8c0a457",{size:"m"}),claimChip("l.validEb",{size:"m"}),claimChip("c.canary",{size:"m",label:"recorded canary fork@8dd0d3e vs recorded verdicts"})]);
  sb.appendChild(chips);
  const cv=LADDER.cv=el("canvas",{id:"braidCv","aria-label":"the verdict braid: one thread per scene over ten validator rails"});
  const sw=el("input",{type:"checkbox",id:"liveSwitch"});sw.addEventListener("change",()=>{LADDER.live=sw.checked;LOOP.dirty(BITS.VAL)});
  const valChip=LADDER.els.valChip=el("span",{class:"chip valChip",text:""});
  sb.appendChild(el("div",{class:"panel braidPanel"},[el("header",null,[el("h3",{text:"The verdict braid"}),el("span",{class:"sub",id:"braidSub",text:""}),el("label",null,[sw,"383 live bodies on the rails that exist for them"]),valChip]),el("div",{class:"cv braidWrap"},[cv]),
    el("div",{class:"legend",text:"green: valid on that commit · red: invalid · grey: no verdict recorded for this body on that commit · S-bend: the verdict flipped between two commits · the js-port rail lights only after RE-VALIDATE runs here"})]));
  /* slider */
  const sl=el("input",{type:"range",id:"commitSlider",min:"0",max:String(RAILS.length-1),step:"1",value:"0","aria-label":"validator commit cursor"});sl.addEventListener("input",()=>SLIDER.set(+sl.value));
  const notches=el("div",{class:"notches"},RAILS.map((r,i)=>el("button",{class:"notch",data:{i:String(i)},text:r.short,title:r.ref,onclick:()=>SLIDER.set(i)})));
  const bRe=el("button",{id:"bRevalidate",text:"RE-VALIDATE STORED CHAINS",onclick:()=>LADDER.revalidate()}),bUp=el("button",{id:"bUpgrade",text:"Ship next validator",onclick:()=>LADDER.upgrade()});
  sb.appendChild(el("div",{class:"panel sliderPanel"},[el("header",null,[el("h3",{text:"Commit slider"}),el("span",{class:"sub",text:"the cursor recolours the wall's verdict bars and the KPI strip to that commit's recorded verdicts; notches absent for a body are grey"})]),sl,notches,el("div",{class:"row"},[bUp,bRe,el("span",{class:"note m",id:"sliderNote",text:""})])]));
  /* port run */
  const bPort=el("button",{id:"bRevalPort",class:"primary",text:"RE-VALIDATE 558 ON THE PORT",onclick:()=>PORT.run()});
  const ring=el("canvas",{id:"portRing",width:"56",height:"56","aria-label":"progress"}),hist=el("div",{class:"hist",id:"portHist"});
  const exp=(self.MANIFEST&&MANIFEST.canary)||null;
  sb.appendChild(el("div",{class:"panel portPanel"},[el("header",null,[el("h3",{text:"RE-VALIDATE on js-port-of-8dd0d3e"}),el("span",{class:"sub",text:"every body on the page (174 replay + 358 live attempts + the cut-chain bodies + the physics ledger) validated in this browser and compared with the recorded verdicts"})]),
    el("div",{class:"row"},[bPort,el("div",{class:"ring"},[ring]),el("span",{class:"note m",id:"portLine",text:exp?`expected (recorded canary, drift/canary.py 24 Oct): ${exp.bodies} bodies · ${exp.flips} flips — the earned figure appears here only after the port runs in this browser`:"no canary in the manifest"})]),
    hist,LADDER.els.portOut=el("div",{class:"portOut"})]));
  LADDER.valChip();if(self.VAL&&VAL.on)VAL.on(()=>{LADDER.valChip();LADDER.syncButtons();LOOP.dirty(BITS.VAL)});
  const P=LOOP.register({name:"braid",bit:BITS.VAL|BITS.MODE|BITS.THEME|BITS.RESIZE|BITS.DATA,rateHz:4,el:cv,budgetMs:6,draw:drawBraid});P.threads=0;P.flips=0;P.rails=RAILS.length;
  LOOP.register({name:"portProg",bit:BITS.VAL,rateHz:6,el:ring,draw:()=>drawPort(ring,hist)});
  SIM.on("reset",()=>{SLIDER.followMode()});SIM.on("mode",()=>SLIDER.followMode());SIM.on("verify",()=>{if(!S.ff)LADDER.syncButtons()});
  SLIDER.followMode()}
/* ---------- the braid ---------- */
function drawBraid(){const cv=LADDER.cv,p=__panels.braid;if(!cv)return;const cw=cv.clientWidth||600,H=innerWidth<600?220:320,{ctx,w,h}=fitCanvas(cv,cw,H);ctx.clearRect(0,0,w,h);
  const ok=cssv("--ok"),bad=cssv("--bad"),dim=cssv("--dim"),line=cssv("--line"),fg=cssv("--fg"),warn=cssv("--warn"),acc=cssv("--acc"),mono=cssv("--mono");
  const T=LADDER.threads(),n=T.length,padL=10,padR=10,top=30,bot=34,x0=padL,x1=w-padR,nr=RAILS.length,rx=i=>x0+(x1-x0)*i/(nr-1);
  /* rails */
  const counts=LADDER.counts();ctx.font="500 10.5px "+mono;ctx.textAlign="center";
  RAILS.forEach((r,i)=>{const x=rx(i),lit=r.kind!=="port"||(PORT.res&&PORT.res.size);ctx.strokeStyle=lit?line:dim;ctx.globalAlpha=lit?1:.5;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(Math.round(x)+.5,top);ctx.lineTo(Math.round(x)+.5,h-bot);ctx.stroke();ctx.globalAlpha=1;
    ctx.fillStyle=SLIDER.i===i?acc:fg;ctx.fillText(r.short,x,12);const c=counts[r.id];ctx.fillStyle=dim;ctx.fillText(c&&c.n?`${c.valid} valid`:"—",x,h-bot+14)});
  /* threads: sorted by their verdict pattern so bends cluster */
  const key=t=>t.v.map(v=>v===null?"n":v?"1":"0").join("");T.sort((a,b)=>key(a)<key(b)?-1:key(a)>key(b)?1:0);
  const span=h-top-bot-8,step=n>1?span/(n-1):0;let flips=0;ctx.lineWidth=n>200?.8:1.2;
  T.forEach((t,ti)=>{const y=top+4+ti*step;for(let i=0;i<nr-1;i++){const a=t.v[i],b=t.v[i+1],xa=rx(i),xb=rx(i+1);
      if(a===null&&b===null){ctx.strokeStyle=line;ctx.globalAlpha=.25;ctx.beginPath();ctx.moveTo(xa,y);ctx.lineTo(xb,y);ctx.stroke();ctx.globalAlpha=1;continue}
      const col=v=>v===null?dim:v?ok:bad;
      if(a!==null&&b!==null&&a!==b){flips++;const d=b?-5:5,xm=(xa+xb)/2,q=(xb-xa)*.3;  /* S-bend: dip within the segment, back on the thread's line at the next rail; colour changes at the midpoint */
        ctx.strokeStyle=col(a);ctx.beginPath();ctx.moveTo(xa,y);ctx.bezierCurveTo(xa+q,y,xm-q*.4,y+d,xm,y+d);ctx.stroke();ctx.strokeStyle=col(b);ctx.beginPath();ctx.moveTo(xm,y+d);ctx.bezierCurveTo(xm+q*.4,y+d,xb-q,y,xb,y);ctx.stroke()}
      else{ctx.strokeStyle=col(a!==null?a:b);ctx.globalAlpha=a===null||b===null?.45:.9;ctx.beginPath();ctx.moveTo(xa,y);ctx.lineTo(xb,y);ctx.stroke();ctx.globalAlpha=1}}});
  /* labels computed from the data, never typed */
  ctx.textAlign="center";ctx.font="600 10.5px "+mono;
  for(let i=1;i<nr;i++){const f=LADDER.flipsBetween(RAILS[i-1],RAILS[i]);if(!f.vi&&!f.iv)continue;const x=(rx(i-1)+rx(i))/2,parts=[];if(f.vi)parts.push(`${f.vi} valid→invalid`);if(f.iv)parts.push(`${f.iv} invalid→valid`);
    const unexplained=f.iv>0||(i>1&&LADDER.flipsBetween(RAILS[i-2],RAILS[i-1]).iv>0&&f.vi>0);ctx.fillStyle=unexplained?warn:fg;ctx.fillText(parts.join(" · ")+(unexplained?" · not investigated (S)":""),x,24)}
  p.threads=n;p.flips=flips;txt("braidSub",`${n} threads${LADDER.live?" (174 replay + live bodies)":" (174 replay)"} · ${flips} bends · ${PORT.res?"port rail measured here on "+PORT.res.size+" bodies":"port rail unlit: RE-VALIDATE to earn it"}`);
  if(SLIDER.i!=null){const x=rx(SLIDER.i);ctx.strokeStyle=acc;ctx.lineWidth=2;ctx.globalAlpha=.9;ctx.beginPath();ctx.moveTo(Math.round(x)+.5,top-4);ctx.lineTo(Math.round(x)+.5,h-bot+2);ctx.stroke();ctx.globalAlpha=1}
  const note=$("sliderNote"),rail=SLIDER.rail();if(note&&rail){const c=counts[rail.id];txt(note,`${rail.ref}${c&&c.n?` · ${c.valid} of ${c.n} replay bodies valid`:rail.kind==="port"?(PORT.res?` · measured here on ${PORT.res.size} bodies`:" · not run here yet"):" · no recorded verdict for the replay bodies"}${rail.kind==="svc"?" · a weaker service, not an older fork":""}`)}}
function drawPort(ring,hist){const ctx=ring.getContext("2d"),s=56;ctx.clearRect(0,0,s,s);const f=PORT.n?PORT.done/PORT.n:0;ctx.lineWidth=5;ctx.strokeStyle=cssv("--line");ctx.beginPath();ctx.arc(s/2,s/2,22,0,Math.PI*2);ctx.stroke();
  if(PORT.n){ctx.strokeStyle=f>=1?cssv("--ok"):cssv("--acc");ctx.beginPath();ctx.arc(s/2,s/2,22,-Math.PI/2,-Math.PI/2+Math.PI*2*f);ctx.stroke();ctx.fillStyle=cssv("--fg");ctx.font="600 10px "+cssv("--mono");ctx.textAlign="center";ctx.fillText(`${PORT.done}`,s/2,s/2+4)}
  const ents=Object.entries(PORT.hist).sort((a,b)=>b[1]-a[1]).slice(0,14),mx=Math.max(1,...ents.map(e=>e[1]));while(hist.children.length<ents.length)hist.appendChild(el("div",{class:"hrow"},[el("span",{class:"k"}),el("i",{class:"bar"}),el("span",{class:"n"})]));while(hist.children.length>ents.length)hist.removeChild(hist.lastChild);
  ents.forEach(([k,v],i)=>{const r=hist.children[i];txt(r.children[0],k);r.children[1].style.width=(100*v/mx).toFixed(0)+"%";txt(r.children[2],String(v))});
  if(PORT.busy)txt("portLine",`validating ${PORT.done} / ${PORT.n} bodies on js-port-of-8dd0d3e · ${fmt.ms(performance.now()-PORT.t0)}`)}
Object.assign(self,{LADDER,SLIDER,PORT});
})();
