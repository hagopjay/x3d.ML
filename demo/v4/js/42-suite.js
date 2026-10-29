/* 42-suite.js — S14 BLENDER EXPORT SUITE + PHYSICS LEDGER + CROSS-DATASET LADDER STRIP (SPEC-v4 S14; WORKPLAN 42-suite). Owns #suite .sb.
   Left, EXPORT SUITE AS A REGRESSION (parts/suite → SUITE.result.suite_runs, SUITE.steps): canvas step chart of main-profile CORE failures per run
   with the flipped case ids as labelled ticks, the merged run's tier counts as a stacked bar, the 5 × 3 grid of chain pills (15 recorded chains),
   the newest run's three *.steps.json chains re-verified in-page (input = previous output; prev = SHA-256 of the previous step's canonical JSON,
   reproduced here with a sorted-key compact serialiser) with the repo file hash printed beside.
   Right, PHYSICS LEDGER · 29 STEPS: data/physics-ledger.x3d (own file, DOCTYPE stripped by the build) loaded as text; readSteps → 29 steps
   (ingest → 25 measure → 2 judge → summary) drawn as a ribbon lit step by step (40 ms each) as verify() walks it. The repo's step records carry
   lxml-C14N output hashes (rule 10); the page re-stamps the chain with its own text-normalised contentHash — every byte of every step record is kept
   except the carrier hash value, prev hashes recomputed — so verify() answers with the page hash; the repo C14N hash is quoted beside it, byte equality
   never claimed. Metric explorer over the measure steps (rigid_scale → step_ms vs n_bodies by shape; any suite → any metric); the tamper table quoted
   from SUITE.result.tamper with TRY IT for the two in-page cases (metric edited inside step 7 → broken chain, first problem at step 8; last step edited →
   still verified: the gap, unsigned); the audit case quoted; the js-port validates the carrier when VAL.mode is full. The ledger's two Cycles stills
   are blank frames: the slot reads "did not render in Blender".
   Under both: CROSS-DATASET LADDER STRIP from inline LADDER_ROWS (9 rows, commit axis, X_ITE pill, headline as a quoted claim chip, link out only when a
   row carries one on the private build: none in this build). XLAD.light(id, text) lets 44-desk light the flywheel row.
   Globals: SUITEP (the left panel), LEDGER {raw, xml, steps, status, problems, rows, pageHash, repoHash, bytes, tamper(kind), reset(), verifyNow()},
   XLAD {rows, light(id, text)}. Claims: suite.corefail, suite.flipped, suite.tiers, suite.chains, suite.inpage, ledger.steps, ledger.groups,
   ledger.records, ledger.findings, ledger.bytes, ledger.repoBytes, xlad.<id> (quoted). LOOP panels: suiteChart, metric (canvas), ledgerRibbon (animation).
   Test hooks: __ledger (= LEDGER), #ledger .step (29), #ledger .verdict[data-status], #suite .chainpill (15), #xlad .row (9), __panels.metric.samples,
   LEDGER.tamper("metric"|"last"), LEDGER.reset(). No v3 ancestor (the suite and the ledger are new in v4); verify/readSteps/sha come from 04-prov. */
(function(){
"use strict";
const disp=m=>(self.SAFEMAP&&typeof SAFEMAP==="object"&&SAFEMAP[m])||m;
/* sorted-key compact JSON at every level (Python json.dumps(sort_keys=True, separators=(",",":")) for the suite step records: no x.0 floats, ASCII only) */
function canon(o){if(o===null||typeof o!=="object")return JSON.stringify(o);if(Array.isArray(o))return"["+o.map(canon).join(",")+"]";return"{"+Object.keys(o).sort().map(k=>JSON.stringify(k)+":"+canon(o[k])).join(",")+"}"}
const hex8=h=>String(h||"").slice(0,8),hex16=h=>String(h||"").slice(0,16);
/* ---------- claims ---------- */
const runs=()=>(self.SUITE&&SUITE.result&&SUITE.result.suite_runs)||[];
const mainOf=r=>(r.profiles||[]).find(p=>p.profile==="main")||{counts:{},failed_cases:[]};
CLAIMS.define("suite.corefail",{label:"main-profile CORE failures per run",unit:"51 → 51b → 51c → upstream → merged",needs:["suite"],grade:"C",source:"RECORDED 17 Oct (owner's machine)",validator:"none",renderer:"none",text:v=>v.join(" → "),fields:["suite_runs[*].profiles[main].counts['CORE:FAIL'] in run order"],compute(){return runs().map(r=>mainOf(r).counts["CORE:FAIL"]||0)}});
CLAIMS.define("suite.flipped",{label:"cases that flipped across the runs",unit:"union of failed_cases",needs:["suite"],grade:"C",source:"RECORDED 17 Oct (owner's machine)",validator:"none",renderer:"none",text:v=>v.length+" cases",fields:["sorted union of suite_runs[*].profiles[main].failed_cases"],compute(){const s=new Set();runs().forEach(r=>(mainOf(r).failed_cases||[]).forEach(c=>s.add(c)));return[...s].sort()}});
CLAIMS.define("suite.tiers",{label:"merged run, main profile, by tier",unit:"CORE:PASS / FIDELITY:PASS / FIDELITY:WARN / ROADMAP:MISSING / ROADMAP:NEW",needs:["suite"],grade:"C",source:"RECORDED 17 Oct (owner's machine)",validator:"none",renderer:"none",text:v=>["CORE:PASS","FIDELITY:PASS","FIDELITY:WARN","ROADMAP:MISSING","ROADMAP:NEW"].map(k=>v[k]||0).join(" / "),fields:["counts of the last run's main profile"],compute(){const r=runs();return r.length?mainOf(r[r.length-1]).counts:{}}});
CLAIMS.define("suite.chains",{label:"suite chains recorded verified",unit:"5 runs × 3 profiles",needs:["suite"],grade:"C",source:"RECORDED 17 Oct (owner's machine)",validator:"none",renderer:"none",text:v=>`${v.verified} of ${v.n}`,fields:["profiles[].chain_status === 'verified' over every run"],compute(){let n=0,ok=0;runs().forEach(r=>(r.profiles||[]).forEach(p=>{n++;if(p.chain_status==="verified")ok++}));return{n,verified:ok}}});
CLAIMS.define("suite.inpage",{label:"newest run's chains re-verified in-page",unit:"3 steps.json chains · links and step hashes",needs:["suite"],grade:"C",source:"RE-RUN HERE",validator:"none",renderer:"none",text:v=>`${v.ok} of ${v.n} chains · ${v.hashes} of ${v.links} step hashes reproduced`,fields:["input_sha256 === previous output_sha256; prev === SHA-256(canonical JSON of the previous step record)"],
  compute(){const st=(self.SUITE&&SUITE.steps)||{};let n=0,ok=0,links=0,hashes=0;Object.keys(st).forEach(p=>{const a=st[p];n++;let good=true;for(let i=1;i<a.length;i++){links++;const io=a[i].input_sha256===a[i-1].output_sha256,pv=a[i].prev===sha(canon(a[i-1]));if(pv)hashes++;if(!(io&&pv))good=false}if(good)ok++});return{n,ok,links,hashes}}});
CLAIMS.define("ledger.steps",{label:"ledger steps",unit:"x3dprov.step.N metas in data/physics-ledger.x3d",grade:"C",source:"RECORDED 17 Oct (owner's machine)",validator:"none",renderer:"none",fields:["readSteps(ledger).length; expected = SUITE.result.physics.verify.steps"],compute(){return LEDGER.steps?LEDGER.steps.length:null}});
CLAIMS.define("ledger.groups",{label:"metric groups in the ledger",unit:"over the measure steps",grade:"C",source:"RECORDED 17 Oct (owner's machine)",validator:"none",renderer:"none",fields:["sum of groups.length over steps with op measure; expected = sum of SUITE.result.physics.steps[].groups"],compute(){return LEDGER.measures?LEDGER.measures.reduce((n,m)=>n+m.groups.length,0):null}});
CLAIMS.define("ledger.records",{label:"source records behind the ledger",unit:"records field of the measure steps",grade:"C",source:"RECORDED 17 Oct (owner's machine)",validator:"none",renderer:"none",fields:["sum of step.records over the measure steps; expected = the summary step's records_total"],compute(){return LEDGER.measures?LEDGER.measures.reduce((n,m)=>n+(m.records||0),0):null}});
CLAIMS.define("ledger.findings",{label:"findings judged",unit:"two judge steps, by severity",grade:"C",source:"RECORDED 17 Oct (owner's machine)",validator:"none",renderer:"none",fields:["sum of by_severity over the judge steps; expected = the summary step's findings_total"],compute(){if(!LEDGER.parsed)return null;return LEDGER.parsed.filter(j=>j.op==="judge").reduce((n,j)=>n+Object.values(j.by_severity||{}).reduce((a,b)=>a+b,0),0)}});
CLAIMS.define("ledger.bytes",{label:"ledger bytes as served",unit:"data/physics-ledger.x3d, DOCTYPE stripped by the build",grade:"C",source:"RE-RUN HERE",validator:"none",renderer:"none",text:v=>v==null?"—":fmt.int(v)+" B",fields:["UTF-8 length of the fetched text"],compute(){return LEDGER.bytes}});
CLAIMS.define("ledger.repoBytes",{label:"ledger bytes in the repo",unit:"quoted from result.json",needs:["suite"],grade:"C",source:"RECORDED 17 Oct (owner's machine)",validator:"none",renderer:"none",text:v=>v==null?"—":fmt.int(v)+" B",fields:["SUITE.result.physics.ledger_bytes (the file with its DOCTYPE)"],compute(){return SUITE.result.physics.ledger_bytes}});
(self.LADDER_ROWS||[]).forEach(r=>CLAIMS.define("xlad."+r.id,{label:r.name+" · headline",unit:"quoted, not re-measured here",expected:r.headline,compute:null,grade:r.grade||"S",source:"RECORDED per commit",validator:(r.commits||[]).map(c=>c.length>=7&&/^[0-9a-f]+$/.test(c)?"fork@"+c:c).join(", "),renderer:r.xite?"X_ITE "+r.xite:"none",text:v=>String(v),fields:["LADDER_ROWS["+r.id+"].headline, from that thread's own ledger"]}));
/* ---------- LEDGER ---------- */
const LEDGER={raw:null,xml:null,steps:null,parsed:null,measures:null,status:null,problems:[],rows:null,pageHash:null,repoHash:null,bytes:null,tampered:null,err:null,ready:null,port:null,
  load,verifyNow,tamper,reset,restamp,canon};
let host=null,ribbon=null,verdictEl=null,stepsStr=null,pristine=null,anim=null,ribbonPanel=null;
function restamp(raw){const steps=readSteps(raw);if(!steps.length)return{xml:raw,strs:[],page:contentHash(raw),repo:null};
  const page=contentHash(raw),last=JSON.parse(steps[steps.length-1][1]),repo=last.output_sha256;let prev=null;
  const strs=steps.map(([n,c])=>{let s=repo?c.split(repo).join(page):c;s=s.replace(/"prev":"[0-9a-f]{64}"/,()=>'"prev":"'+(prev?sha(prev):ZERO)+'"');prev=s;return[n,s]});
  return{xml:assemble(raw,strs),strs,page,repo}}
function assemble(raw,strs){const metas='<meta name="x3dprov.version" content="x3dprov/0.1"/>'+strs.map(([n,c])=>`<meta name="x3dprov.step.${n}" content="${esc(c)}"/>`).join("");return injectMeta(stripProv(raw),metas)}
async function load(){if(LEDGER.ready)return LEDGER.ready;LEDGER.ready=(async()=>{try{const r=await fetch("data/physics-ledger.x3d");if(!r.ok)throw new Error("HTTP "+r.status);const raw=await r.text();LEDGER.raw=raw;LEDGER.bytes=new TextEncoder().encode(raw).length;
    const rs=restamp(raw);LEDGER.xml=rs.xml;stepsStr=rs.strs;pristine=rs.strs.slice();LEDGER.pageHash=rs.page;LEDGER.repoHash=rs.repo;LEDGER.steps=readSteps(LEDGER.xml);LEDGER.parsed=LEDGER.steps.map(([,c])=>JSON.parse(c));
    LEDGER.measures=LEDGER.parsed.map((j,i)=>({n:i+1,op:j.op,agent:j.agent,suite:j.suite,groups:j.groups||[],records:j.records})).filter(m=>m.op==="measure");
    verifyNow();["ledger.steps","ledger.groups","ledger.records","ledger.findings","ledger.bytes"].forEach(id=>CLAIMS.run(id));return LEDGER}
  catch(e){LEDGER.err=String(e&&e.message||e);LEDGER.status="unavailable";if(verdictEl){txt(verdictEl,"ledger not loaded: "+LEDGER.err);verdictEl.dataset.status="unavailable"}throw e}})();return LEDGER.ready}
function verifyNow(){if(!LEDGER.xml)return null;const v=verify(LEDGER.xml,true);LEDGER.status=v.status;LEDGER.problems=v.problems||[];LEDGER.rows=v.rows||[];LEDGER.ok=v.ok;paintVerdict();startRibbon();return v}
/* TRY IT cases from result.json.tamper, done to the page's copy: "metric": one value inside step 7's record (stability) +1 % → the record changed, step 8's prev no longer matches;
   "last": a field of step 29 edited → no successor, unsigned carrier: verify() still says verified (the recorded audit with sources says evidence-mismatch) */
function tamper(kind){if(!pristine)return null;let strs=pristine.slice();
  if(kind==="metric"){const i=strs.findIndex(([n])=>n===7);if(i<0)return null;const[n,c]=strs[i];const c2=c.replace(/("groups":\[\[[^\]]*?,)(-?\d+(?:\.\d+)?(?:e-?\d+)?)(\])/,(m,a,v,z)=>a+String(+v*1.01)+z);strs[i]=[n,c2];LEDGER.tampered="metric edited inside the record (stability group 0)"}
  else if(kind==="last"){const i=strs.length-1;const[n,c]=strs[i];const c2=/"findings_total":\d+/.test(c)?c.replace(/"findings_total":(\d+)/,(m,v)=>'"findings_total":'+(+v+1)):c.replace(/"op":"summary"/,'"op":"summary","edited":true');strs[i]=[n,c2];LEDGER.tampered="LAST step edited (no successor, unsigned)"}
  else return null;
  stepsStr=strs;LEDGER.xml=assemble(LEDGER.raw,strs);LEDGER.steps=readSteps(LEDGER.xml);return verifyNow()}
function reset(){if(!pristine)return null;stepsStr=pristine.slice();LEDGER.tampered=null;LEDGER.xml=assemble(LEDGER.raw,stepsStr);LEDGER.steps=readSteps(LEDGER.xml);return verifyNow()}
const STATUS_LABEL={verified:"verified","broken":"broken-chain",stale:"stale","seal-fail":"seal-fail","no-record":"no record"};
function paintVerdict(){if(!verdictEl)return;const st=LEDGER.status||"?";verdictEl.dataset.status=st;verdictEl.className="verdict pill "+(st==="verified"?"p-ok":"p-bad");txt(verdictEl,"verify(): "+(STATUS_LABEL[st]||st));
  const d=host.querySelector("#ledgerDetail");if(d){const gap=LEDGER.tampered&&LEDGER.tampered.startsWith("LAST")&&st==="verified";
    txt(d,(LEDGER.tampered?"TRY IT · "+LEDGER.tampered+" → ":"pristine copy → ")+(STATUS_LABEL[st]||st)+(LEDGER.problems.length?" · "+LEDGER.problems[0]:"")+(gap?" · the gap: the last step has no successor and the carrier is unsigned, so the chain cannot see the edit; the recorded audit with sources says evidence-mismatch":"")+` · page hash ${hex16(LEDGER.pageHash)}… (text-normalised, verified here) · repo C14N ${hex16(LEDGER.repoHash)}… (quoted, byte equality not claimed)`)}}
function startRibbon(){if(!ribbon)return;const n=LEDGER.steps?LEDGER.steps.length:0;const bad=new Map();(LEDGER.rows||[]).forEach(r=>{if(!r.ok&&!bad.has(r.n))bad.set(r.n,r.chk)});const firstBad=bad.size?Math.min(...bad.keys()):Infinity;
  const light=k=>{[...ribbon.children].forEach((e,i)=>{const s=i+1;const on=s<=k;e.classList.toggle("lit",on&&s<firstBad);e.classList.toggle("bad",on&&s>=firstBad);e.classList.toggle("off",!on)})};
  if(self.FX&&FX.level===0||!ribbonPanel){light(n);return}
  anim={t0:0,n,light};ribbonPanel.always=true;ribbonPanel.forceDraw=true}
function ribbonDraw(now){if(!anim){ribbonPanel.always=false;return}if(!anim.t0)anim.t0=now;const k=Math.min(anim.n,Math.floor((now-anim.t0)/40)+1);anim.light(k);if(k>=anim.n){anim=null;ribbonPanel.always=false}}
/* ---------- metric explorer ---------- */
const MX={suite:"rigid_scale",metric:"step_ms_p50",canvas:null,panel:null,note:null};
function groupsFor(){const m=(LEDGER.measures||[]).find(x=>x.suite===MX.suite);if(!m)return[];return m.groups.filter(g=>g[1]===MX.metric&&typeof g[4]==="number"&&isFinite(g[4]))}
function metricsOf(suite){const m=(LEDGER.measures||[]).find(x=>x.suite===suite);if(!m)return[];return[...new Set(m.groups.filter(g=>typeof g[4]==="number").map(g=>g[1]))]}
function drawMetric(){const c=MX.canvas;if(!c||!LEDGER.measures)return;const W=Math.max(200,c.clientWidth||c.parentNode.clientWidth||400),H=180;const{ctx,w,h}=fitCanvas(c,W,H);
  ctx.clearRect(0,0,w,h);ctx.fillStyle=cssv("--p0");ctx.fillRect(0,0,w,h);const g=groupsFor(),fg=cssv("--fg"),dim=cssv("--dim"),mono=cssv("--mono")||"monospace";ctx.font="500 10.5px "+mono;ctx.fillStyle=dim;
  if(!g.length){ctx.fillText("no numeric values for "+MX.suite+" · "+MX.metric,8,20);MX.panel.samples=0;return}
  const L=46,R=12,T=14,B=28,pw=w-L-R,ph=h-T-B;const vals=g.map(x=>x[4]);const byN=g.map(x=>({name:x[0],v:x[4],n:(/_N(\d+)/.exec(x[0])||[])[1]}));const scale=byN.every(x=>x.n)&&byN.length>3;
  if(scale){/* rigid_scale-style: step_ms vs n_bodies, log-log, one polyline per shape prefix, medians per (shape, N) */
    const series=new Map();byN.forEach(x=>{const shape=x.name.replace(/_N\d+.*$/,"");if(!series.has(shape))series.set(shape,new Map());const mm=series.get(shape);const N=+x.n;if(!mm.has(N))mm.set(N,[]);mm.get(N).push(x.v)});
    const pts=[];series.forEach((mm,shape)=>mm.forEach((vs,N)=>pts.push({shape,N,v:UTIL.median(vs)})));const pos=pts.filter(p=>p.v>0&&p.N>0);if(!pos.length){ctx.fillText("values not positive: no log plot",8,20);MX.panel.samples=0;return}
    const lx=Math.log10,xs=pos.map(p=>lx(p.N)),ys=pos.map(p=>lx(p.v)),x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);const X=v=>L+(x1>x0?(lx(v)-x0)/(x1-x0):.5)*pw,Y=v=>T+ph-(y1>y0?(lx(v)-y0)/(y1-y0):.5)*ph;
    ctx.strokeStyle=cssv("--line");ctx.lineWidth=1;for(let e=Math.floor(y0);e<=Math.ceil(y1);e++){const y=Y(Math.pow(10,e));if(y<T||y>T+ph)continue;ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(L+pw,y);ctx.stroke();ctx.fillStyle=dim;ctx.fillText((e<0?Math.pow(10,e).toFixed(-e):Math.pow(10,e))+"",4,y+4)}
    for(let e=Math.floor(x0);e<=Math.ceil(x1);e++){const x=X(Math.pow(10,e));if(x<L||x>L+pw)continue;ctx.beginPath();ctx.moveTo(x,T);ctx.lineTo(x,T+ph);ctx.stroke();ctx.fillText(Math.pow(10,e)+" bodies",x-14,h-12)}
    const lanes=["--lane-1","--lane-2","--lane-3","--lane-4","--lane-5","--lane-6","--lane-7","--lane-8","--lane-9","--lane-10","--lane-11"];let i=0,n=0;
    series.forEach((mm,shape)=>{const col=cssv(lanes[i%lanes.length]);i++;const ps=pos.filter(p=>p.shape===shape).sort((a,b)=>a.N-b.N);if(!ps.length)return;ctx.strokeStyle=col;ctx.fillStyle=col;ctx.lineWidth=1.5;ctx.beginPath();ps.forEach((p,k)=>{const x=X(p.N),y=Y(p.v);if(k)ctx.lineTo(x,y);else ctx.moveTo(x,y)});ctx.stroke();ps.forEach(p=>{ctx.beginPath();ctx.arc(X(p.N),Y(p.v),2.2,0,7);ctx.fill();n++});ctx.fillText(shape,Math.min(L+pw-60,X(ps[ps.length-1].N)+4),Y(ps[ps.length-1].v)-4)});
    ctx.fillStyle=fg;ctx.fillText(`${MX.suite} · ${MX.metric} vs n_bodies (log-log, median of repeats) · ${g.length} groups`,L,10);MX.panel.samples=n;return}
  /* generic: bars (≤ 60 groups) or the sorted value line (> 60), min / median / max labelled */
  const sorted=byN.slice().sort((a,b)=>a.v-b.v),vmin=sorted[0].v,vmax=sorted[sorted.length-1].v,med=UTIL.median(vals);const Y=v=>T+ph-(vmax>vmin?(v-vmin)/(vmax-vmin):.5)*ph;
  ctx.strokeStyle=cssv("--line");ctx.beginPath();ctx.moveTo(L,T+ph);ctx.lineTo(L+pw,T+ph);ctx.stroke();ctx.fillStyle=dim;ctx.fillText(fmt.num(vmin,vmin<10?3:0),4,T+ph);ctx.fillText(fmt.num(vmax,vmax<10?3:0),4,T+8);
  const col=cssv("--acc");ctx.fillStyle=col;ctx.strokeStyle=col;
  if(sorted.length<=60){const bw=pw/sorted.length;sorted.forEach((p,k)=>{const y=Y(p.v);ctx.fillRect(L+k*bw+1,y,Math.max(1,bw-2),T+ph-y)});ctx.fillStyle=dim;sorted.filter((p,k)=>k%Math.ceil(sorted.length/6)===0).forEach(p=>{const k=sorted.indexOf(p);ctx.fillText(p.name.slice(0,14),L+k*bw,h-12)})}
  else{ctx.lineWidth=1.5;ctx.beginPath();sorted.forEach((p,k)=>{const x=L+k/(sorted.length-1)*pw,y=Y(p.v);if(k)ctx.lineTo(x,y);else ctx.moveTo(x,y)});ctx.stroke();ctx.fillStyle=dim;ctx.fillText("groups sorted by value →",L,h-12)}
  const my=Y(med);ctx.strokeStyle=cssv("--warn");ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(L,my);ctx.lineTo(L+pw,my);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=cssv("--warn");ctx.fillText("median "+fmt.num(med,med<10?3:1),L+pw-110,my-3);
  ctx.fillStyle=fg;ctx.fillText(`${MX.suite} · ${MX.metric} · ${sorted.length} groups`,L,10);MX.panel.samples=sorted.length}
function mxSelects(){const ss=host.querySelector("#mxSuite"),ms=host.querySelector("#mxMetric");if(!ss||!ms||!LEDGER.measures)return;if(!ss.options.length)LEDGER.measures.forEach(m=>{if(m.groups.some(g=>typeof g[4]==="number"))ss.appendChild(el("option",{value:m.suite,text:`step ${m.n} · ${m.agent} · ${m.suite} (${m.groups.length})`}))});
  if(![...ss.options].some(o=>o.value===MX.suite)&&ss.options.length)MX.suite=ss.options[0].value;ss.value=MX.suite;ms.textContent="";metricsOf(MX.suite).forEach(k=>ms.appendChild(el("option",{value:k,text:k})));if(![...ms.options].some(o=>o.value===MX.metric)&&ms.options.length)MX.metric=ms.options[0].value;ms.value=MX.metric;
  const fid=(LEDGER.measures.find(m=>m.suite==="x3d_fidelity")||{groups:[]}).groups.filter(g=>g[1]==="rmse_vs_x3d");const fl=host.querySelector("#mxFidelity");if(fl){fl.textContent="";fid.forEach(g=>fl.appendChild(el("span",{class:"chip",title:"x3d_fidelity · rmse_vs_x3d · record "+g[2],text:`${g[0]} ${fmt.num(g[4],3)}`})));if(fid.length)fl.prepend(el("span",{class:"legend",text:"x3d_fidelity rmse per case (quoted from step 14): "}))}
  if(MX.panel)MX.panel.forceDraw=true}
/* ---------- left: the suite as a regression ---------- */
const CH={canvas:null,panel:null};
function drawSuite(){const c=CH.canvas;if(!c)return;const W=Math.max(200,c.clientWidth||c.parentNode.clientWidth||400),H=150;const{ctx,w,h}=fitCanvas(c,W,H);ctx.clearRect(0,0,w,h);ctx.fillStyle=cssv("--p0");ctx.fillRect(0,0,w,h);
  const R=runs(),mono=cssv("--mono")||"monospace";ctx.font="500 10.5px "+mono;if(!R.length){ctx.fillStyle=cssv("--dim");ctx.fillText("suite part not loaded yet",8,20);CH.panel.samples=0;return}
  const L=28,Rm=12,T=16,B=52,pw=w-L-Rm,ph=h-T-B,vals=R.map(r=>mainOf(r).counts["CORE:FAIL"]||0),vmax=Math.max(1,...vals);const X=i=>L+(R.length>1?i/(R.length-1):.5)*pw,Y=v=>T+ph-v/vmax*ph;
  ctx.strokeStyle=cssv("--line");for(let v=0;v<=vmax;v++){ctx.beginPath();ctx.moveTo(L,Y(v));ctx.lineTo(L+pw,Y(v));ctx.stroke();ctx.fillStyle=cssv("--dim");ctx.fillText(String(v),8,Y(v)+4)}
  ctx.strokeStyle=cssv("--bad");ctx.lineWidth=2;ctx.beginPath();vals.forEach((v,i)=>{if(i)ctx.lineTo(X(i),Y(v));else ctx.moveTo(X(i),Y(v))});ctx.stroke();
  let n=0;R.forEach((r,i)=>{const v=vals[i],x=X(i),y=Y(v);ctx.fillStyle=v?cssv("--bad"):cssv("--ok");ctx.beginPath();ctx.arc(x,y,4,0,7);ctx.fill();n++;ctx.fillStyle=cssv("--fg");ctx.textAlign="center";ctx.fillText(String(v),x,y-8);ctx.fillStyle=cssv("--mute");ctx.fillText(r.run.replace("suite-run-",""),x,T+ph+12);
    const fc=mainOf(r).failed_cases||[];ctx.fillStyle=cssv("--warn");ctx.font="500 9.5px "+mono;fc.slice(0,4).forEach((cid,k)=>ctx.fillText(cid,x,T+ph+24+k*9));ctx.font="500 10.5px "+mono;ctx.textAlign="left"});
  CH.panel.samples=n}
function chainGrid(){const grid=host.querySelector("#chainGrid");if(!grid||grid.children.length)return;const R=runs();if(!R.length)return;const st=(self.SUITE&&SUITE.steps)||{};
  R.forEach(r=>{(r.profiles||[]).forEach(p=>{const newest=r===R[R.length-1],a=st[p.profile];let inpage="";if(newest&&a){let ok=true;for(let i=1;i<a.length;i++){if(!(a[i].input_sha256===a[i-1].output_sha256&&a[i].prev===sha(canon(a[i-1]))))ok=false}inpage=ok?" · in-page ✓":" · in-page ✗"}
    grid.appendChild(el("b",{class:"chainpill pill "+(p.chain_status==="verified"?"p-ok":"p-bad"),data:{run:r.run,profile:p.profile,status:p.chain_status},title:`${r.run} · ${p.profile} · ${p.file} · ${fmt.bytes(p.bytes)} · repo file sha256 ${p.file_sha256} · chain ${p.chain_status} (recorded) · verdict ${p.verdict}${newest?" · newest run: "+a.length+" steps re-verified in this page":""}`,
      text:`${r.run.replace("suite-run-","")} · ${p.profile} · ${p.chain_status}${inpage}`}))})});
  const line=host.querySelector("#chainNote");if(line){const m=R[R.length-1];txt(line,`newest run ${m.run} (${m.created}) · three steps.json chains re-verified here: input = previous output, prev = SHA-256 of the previous record's canonical JSON · repo file hashes beside each pill (quoted; the 7 MB scene files are not on the page)`)}}
function tierBar(){const bar=host.querySelector("#tierBar");if(!bar||bar.children.length)return;const R=runs();if(!R.length)return;const counts=mainOf(R[R.length-1]).counts,keys=["CORE:PASS","FIDELITY:PASS","FIDELITY:WARN","ROADMAP:MISSING","ROADMAP:NEW"],cls={"CORE:PASS":"ok","FIDELITY:PASS":"acc","FIDELITY:WARN":"warn","ROADMAP:MISSING":"dim","ROADMAP:NEW":"info"};const tot=keys.reduce((n,k)=>n+(counts[k]||0),0)||1;
  keys.forEach(k=>{const v=counts[k]||0;bar.appendChild(el("i",{class:"tier t-"+cls[k],style:{flex:String(v)},title:`${k}: ${v} of ${tot}`,text:v>=8?k.replace("ROADMAP:","").replace("FIDELITY:","FID:")+" "+v:""}))})}
/* ---------- tamper table + audit quote ---------- */
function tamperTable(){const tb=host.querySelector("#tamperBody");if(!tb||tb.children.length||!(self.SUITE&&SUITE.result&&SUITE.result.tamper))return;const T=SUITE.result.tamper;
  const row=(carrier,name,rec,action)=>tb.appendChild(el("tr",null,[el("td",{text:carrier}),el("td",{text:name}),el("td",{class:"m",text:rec}),el("td",null,action||"")]));
  Object.entries(T.physics||{}).forEach(([k,v])=>{if(k==="pristine")return row("physics ledger","pristine",String(v));const rec=typeof v==="string"?v:[v.verify&&"verify "+v.verify,v.audit_with_sources&&"audit with sources "+v.audit_with_sources,v.audit&&"audit "+v.audit,v.verify_of_record&&"verify of record "+v.verify_of_record,v.first_problem].filter(Boolean).join(" · ");
    const act=/^metric edited/.test(k)?el("button",{class:"warn tryit",data:{t:"metric"},text:"TRY IT",onclick:()=>tamper("metric")}):/^LAST step/.test(k)?el("button",{class:"warn tryit",data:{t:"last"},text:"TRY IT",onclick:()=>tamper("last")}):el("span",{class:"note",text:"recorded on the owner's machine; the sources are not here"});row("physics ledger",k,rec,act)});
  Object.entries(T.suite_main||{}).forEach(([k,v])=>row("suite main profile",k,String(v),el("span",{class:"note",text:k==="pristine"||k==="audit"?"":"7 MB scene not on the page"})));
  const au=T.physics&&T.physics["one single-repeat float value +1% in the source JSONL"];const q=host.querySelector("#auditQuote");if(q&&au)txt(q,`audit() quoted from result.json, not re-run: ${au.audit} · ${(au.named||[]).join(" · ")} · recorded on the owner's machine, sources not here`)}
/* ---------- js-port validates the carrier ---------- */
async function portCheck(){const line=host.querySelector("#portLine");if(!line||!self.VAL)return;try{if(VAL.mode==="unloaded"&&VAL.ready)await VAL.ready;if(VAL.mode!=="full"&&VAL.mode!=="semantic-only"){txt(line,`js-port-of-8dd0d3e: not run on the carrier in this view (${VAL.reason||VAL.mode}); the ledger was XSD-valid on fork@fa0b389 at build`);return}
    await LEDGER.ready;const r=await VAL.validate(LEDGER.raw);LEDGER.port=r;const xe=(r.xsd&&r.xsd.errors||[]).length,se=(r.semantic&&r.semantic.errors||[]).length;txt(line,`js-port-of-8dd0d3e on the carrier: ${r.valid?"VALID":"INVALID"} · XSD ${r.xsd&&r.xsd.valid?"valid":xe+" errors"} · ${se} semantic errors${r.ms!=null?" · "+fmt.ms(r.ms):""}${r.valid?" · agrees with the recorded XSD pass":" · DIFFERS from the recorded pass: listed above"}`)}
  catch(e){txt(line,"js-port-of-8dd0d3e: "+String(e&&e.message||e).slice(0,160))}}
if(self.VAL&&VAL.on)VAL.on(()=>{if(host)portCheck()});
/* ---------- ledger's own Cycles stills (S14 keeps the physics ledger key; the sheet keeps the scene keys) ---------- */
function ledgerStaged(){const slot=host.querySelector("#ledgerStaged");if(!slot||!self.SHEET||!SHEET.loadStaged)return;SHEET.loadStaged().then(m=>{if(!m||!m.stills)return;const key=Object.keys(m.stills).find(k=>/physics-stress\.ledger\.x3d$/.test(k));if(!key)return;const s=SHEET.stagedOf(key);if(!s)return;slot.textContent="";
    s.stills.forEach(c=>slot.appendChild(el("span",{class:"stg"+(c.blank?" noblender":c.v.url?" has":""),title:`${key} · ${c.cam} · Blender ${c.v.blender||""} ${c.v.engine||""} · sha ${hex8(c.v.sha256)}`,text:c.blank?`${c.cam}: did not render in Blender`:c.v.url?`${c.cam}: STAGED`:`${c.cam}: STAGED · no url`})));
    slot.appendChild(el("span",{class:"note m",text:" · a ledger has no geometry: the carrier is the chain, so Cycles drew an empty frame (identical bytes to other blank stills)"}))})}
/* ---------- XLAD ---------- */
const XLAD={rows:self.LADDER_ROWS||[],light(id,text){const r=host&&host.querySelector(`#xlad .row[data-id="${id}"]`);if(!r)return false;r.classList.add("lit");const n=r.querySelector(".lit-note");if(n)txt(n,text||"re-validated here");return true}};
function xlad(){const box=host.querySelector("#xlad");if(!box||box.children.length>1)return;const rows=XLAD.rows;const commits=[];rows.forEach(r=>(r.commits||[]).forEach(c=>{if(!commits.includes(c))commits.push(c)}));
  const axis=el("div",{class:"row xaxis"},[el("span",{class:"xname legend",text:"commit axis →"}),el("span",{class:"xdots"},commits.map(c=>el("i",{class:"xc",text:c,title:"validator commit "+c})))]);box.appendChild(axis);
  rows.forEach(r=>{const dots=el("span",{class:"xdots"},commits.map(c=>el("i",{class:"xc "+((r.commits||[]).includes(c)?"on":"off"),text:(r.commits||[]).includes(c)?c:"·",title:(r.commits||[]).includes(c)?r.name+" on "+c:""})));
    const link=r.link&&!(self.BUILD&&BUILD.share)?el("a",{href:r.link,target:"_blank",rel:"noopener",text:"open ↗"}):r.here?el("a",{href:r.id==="firehose-live"?"#stage":"#ladder",text:"on this page"}):el("span",{class:"note m",text:"no link in this build"});
    box.appendChild(el("div",{class:"row xrow",data:{id:r.id}},[el("span",{class:"xname",text:r.name}),dots,el("span",{class:"pill "+(r.xite?"p-acc":"p-mute"),text:r.xite?"X_ITE "+r.xite:"no renderer"}),claimChip("xlad."+r.id,{size:"s",label:"quoted, not re-measured here"}),gradeChip(r.grade),link,el("span",{class:"lit-note note m"})]))})}
/* ---------- mount ---------- */
function mount(sec){host=sec.querySelector(".sb");host.textContent="";
  const left=el("div",{class:"panel",id:"suiteLeft"},[el("header",null,[el("h3",{text:"Export suite as a regression"}),el("span",{class:"sub",text:"194 cases · Blender 5.1.0 · x3d-blender-io 78212bc · validate_x3d_export.py 2.0.0"})]),
    el("div",{class:"row"},[claimChip("suite.corefail",{size:"s"}),claimChip("suite.flipped",{size:"s"}),claimChip("suite.chains",{size:"s"}),claimChip("suite.inpage",{size:"s"})]),
    el("div",{class:"cv"},el("canvas",{id:"suiteChart"})),
    el("div",{class:"legend",text:"main-profile CORE failures per run, flipped case ids under each run"}),
    el("div",{class:"row"},[claimChip("suite.tiers",{size:"s"})]),el("div",{class:"tierBar",id:"tierBar"}),
    el("div",{class:"legend",text:"merged run, main profile, by tier"}),
    el("div",{class:"chainGrid",id:"chainGrid"}),el("div",{class:"note m",id:"chainNote"})]);
  CH.canvas=left.querySelector("#suiteChart");
  const right=el("div",{class:"panel",id:"ledger"},[el("header",null,[el("h3",{text:"Physics ledger · 29 steps"}),el("span",{class:"sub",text:"data/physics-ledger.x3d · ingest → 25 measure → 2 judge → summary · no geometry: the chain is the content"})]),
    el("div",{class:"row"},[claimChip("ledger.steps",{size:"s"}),claimChip("ledger.groups",{size:"s"}),claimChip("ledger.records",{size:"s"}),claimChip("ledger.findings",{size:"s"}),claimChip("ledger.bytes",{size:"s"}),claimChip("ledger.repoBytes",{size:"s"})]),
    el("div",{class:"ribbon",id:"ribbon"}),
    el("div",{class:"row"},[el("span",{class:"verdict pill p-mute",id:"ledgerVerdict",data:{status:"loading"},text:"verify(): loading…"}),el("button",{class:"tryit",data:{t:"metric"},text:"TRY IT · edit a metric",onclick:()=>tamper("metric")}),el("button",{class:"tryit",data:{t:"last"},text:"TRY IT · edit the last step",onclick:()=>tamper("last")}),el("button",{text:"reset",onclick:reset})]),
    el("div",{class:"note m",id:"ledgerDetail"}),
    el("div",{class:"row mx"},[el("label",{text:"suite "},el("select",{id:"mxSuite",onchange:e=>{MX.suite=e.target.value;MX.metric="";mxSelects()}})),el("label",{text:"metric "},el("select",{id:"mxMetric",onchange:e=>{MX.metric=e.target.value;MX.panel.forceDraw=true}}))]),
    el("div",{class:"cv"},el("canvas",{id:"metricChart"})),el("div",{class:"legend",text:"values read from the ledger's step records in this browser (quoted, not re-measured) · rigid_scale: step_ms vs n_bodies, medians of repeats"}),el("div",{class:"row",id:"mxFidelity"}),
    el("div",{class:"scroll tamperWrap"},el("table",{id:"tamper"},[el("thead",null,el("tr",null,["carrier","tamper case (result.json)","recorded","here"].map(h=>el("th",{text:h})))),el("tbody",{id:"tamperBody"})])),
    el("div",{class:"note m",id:"auditQuote"}),el("div",{class:"note m",id:"portLine",text:"js-port-of-8dd0d3e: waiting for the validator"}),el("div",{class:"row",id:"ledgerStaged"})]);
  MX.canvas=right.querySelector("#metricChart");ribbon=right.querySelector("#ribbon");verdictEl=right.querySelector("#ledgerVerdict");
  host.appendChild(el("div",{class:"cols-7-5 suiteCols"},[left,right]));
  host.appendChild(el("div",{class:"panel",id:"xlad"},[el("header",null,[el("h3",{text:"Cross-dataset ladder strip"}),el("span",{class:"sub",text:"each thread's headline on a shared commit axis · quoted from its own ledger, not re-measured here"})])]));
  for(let i=1;i<=29;i++)ribbon.appendChild(el("i",{class:"step off",data:{n:String(i)},text:String(i)}));
  CH.panel=LOOP.register({name:"suiteChart",bit:LOOP.bits.DATA|LOOP.bits.THEME|LOOP.bits.RESIZE,el:CH.canvas,budgetMs:3,draw:drawSuite});CH.panel.samples=0;
  ribbonPanel=LOOP.register({name:"ledgerRibbon",budgetMs:2,draw:ribbonDraw});
  MX.panel=LOOP.register({name:"metric",bit:LOOP.bits.THEME|LOOP.bits.RESIZE,el:MX.canvas,budgetMs:4,draw:drawMetric});MX.panel.samples=0;
  xlad();
  load().then(()=>{ribbon.textContent="";LEDGER.steps.forEach(([n,c])=>{let j={};try{j=JSON.parse(c)}catch(e){}ribbon.appendChild(el("i",{class:"step off",data:{n:String(n),op:j.op||""},title:`step ${n} · ${j.op||"?"} · ${j.agent||""}${j.suite?" · "+j.suite:""}${j.groups?" · "+j.groups.length+" groups":""}`,text:String(n)}))});
    mxSelects();startRibbon();paintVerdict();if(self.DATA&&DATA.loaded("suite"))setExpected();portCheck()}).catch(()=>{});
  ledgerStaged();if(self.DATA&&DATA.loaded("suite"))onData("suite")}
function setExpected(){if(!(self.SUITE&&SUITE.result&&SUITE.result.physics))return;const P=SUITE.result.physics;const c=CLAIMS.get("ledger.steps");c.expected=P.verify&&P.verify.steps;const g=CLAIMS.get("ledger.groups");g.expected=(P.steps||[]).reduce((n,s)=>n+(s.groups||0),0);
  const rc=CLAIMS.get("ledger.records");rc.expected=(P.steps||[]).reduce((n,s)=>n+(s.records||0),0);const fd=CLAIMS.get("ledger.findings");const sm=(P.steps||[]).find(s=>s.op==="summary");fd.expected=sm?sm.findings_total:undefined;
  if(LEDGER.parsed)["ledger.steps","ledger.groups","ledger.records","ledger.findings"].forEach(id=>CLAIMS.run(id))}
function onData(name){if(!host||name!=="suite")return;chainGrid();tierBar();tamperTable();setExpected();if(CH.panel)CH.panel.forceDraw=true}
SECTIONS.register({id:"suite",part:"suite",header:{title:"Blender export suite + physics ledger",unit:"194-case export suite · 29-step physics ledger · cross-dataset strip",stamps:{source:"RECORDED 17 Oct (owner's machine)",validator:"fork@fa0b389 recorded",renderer:"none"},grade:"C",
  honesty:"suite and physics chains recorded on the owner's machine 17 Oct (Blender 5.1.0; CI 5.1.2) · verified here with the page hash; repo C14N hashes quoted · audit() quoted from result.json, not re-run · env block hidden in the share build · ladder strip numbers quoted from each thread's ledger"},mount,onData});
Object.assign(self,{LEDGER,XLAD,__ledger:LEDGER,SUITEP:{canon,restamp}});
})();
