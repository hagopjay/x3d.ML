/* 48-ask.js — S16 ASK THE FILES + ASK BOX (SPEC-v4 S16 "Ask the files"; WORKPLAN 48-ask; ARCHITECTURE §3 tiers, sample via claude.use). Owns the "Ask the files"
   drawer prepended to #deck .sb. 46-footer owns the deck section, so this module mounts from its own LOOP panel's first draw and never re-registers "deck".
   Ported from v3 askFiles() (lines 793–816): the per-model table (scenes, calls, repairs, tokens, cost, median latency, first-try and final valid, valid-but-blank)
   and the first-attempt findings table, now read from an incremental parsed-step cache (scene id → parsed x3dprov.step.* rows; v3 re-parsed every scene on every
   tick) and reconciled against EVENTS.reconcile as claim chips (ledger calls · on the page · failed · cut calls · retries · probes). The diff worker the WORKPLAN
   names does not exist in workers/, so the tables and the context trim run on the main thread, incrementally, at 1 Hz, gated by a cheap signature.
   ASK box: TIER.caps.sample (claude.use("sample") resolved by 07-tier) gates it. Namespace null, window.claude absent or not_granted → exactly one line
   "ASK box: not available in this view …" and nothing else. Otherwise a textarea with ASK / STOP; the prompt carries the instructions, the page's own data
   (CLAIMS values with status and grade, LIVESTATS, EVENTS.reconcile, the Ask-the-files aggregates, the selected scene's parsed chain) trimmed to ≤ 32 KB, and the
   question; one tool query_steps({filter}) runs a structured filter (no eval, no new Function) over the parsed rows and returns ≤ 32 KB; members get
   files.asSampleTools() appended when the capability lists them. The answer is rendered through textContent while it streams. Nothing is fetched for an answer:
   the sample call runs on the viewer's own Claude account inside the viewer, and the page never calls any model endpoint itself.
   Globals: ASK {available, mode:"off"|"resolving"|"on", lastPrompt, lastContext, lastQuestion, lastAnswer, lastError, context(), query(filter), ask(q), stop(),
   rows(), aggregates(), trimTo(obj,max), INSTR, MAX}; __ask (= ASK). Claims: ask.ledgerCalls, ask.onPage, ask.notOnPage, ask.failedCalls, ask.cutCalls,
   ask.retries, ask.probes, ask.pageTokens, ask.reconcile. LOOP panel: ask (bit DATA|TIER|SCENE|SELECT, 1 Hz, no el: always eligible, cheap when nothing changed).
   DOM: #askDrawer > #ask (#askSub, #askBody, #askFindWrap/#askFind, #askSearch → #askHits, #askNote, #askBox). #askBox holds either #askOff alone or
   #askQ, #askGo, #askStop, #askStatus, #askCtx, #askA. Test hooks: ASK.mode, ASK.lastPrompt (contains "QUESTION:"), ASK.lastContext (≤ 32 KB as JSON),
   #askBox childElementCount === 1 when off, #askA textContent = the answer, ASK.query({op:"validate",verdict:"invalid",limit:5}). */
(function(){
"use strict";
const disp=m=>(self.SAFEMAP&&typeof SAFEMAP==="object"&&SAFEMAP[m])||m;
const MAX=32768,pc=(a,b)=>b?Math.round(100*a/b)+"%":"-",share=()=>!!(self.BUILD&&BUILD.share);
const OFF="ASK box: not available in this view (the sample capability is not granted here; the tables above are the ground truth and need no model)";
const INSTR=`You answer questions about the Tether Firehose v4 page from the CONTEXT below and from the query_steps tool when it is offered, and from nothing else: the page's own recorded data (claims with status and grade, run statistics, the ledger reconciliation, the per-model tables, the selected scene's provenance chain). Do not browse and do not invent numbers. Every number you give must appear in the CONTEXT or in a query_steps result; cite where it comes from (a claim id, a table name, or a scene id with its step number). When the context does not hold the answer say "not in the page's data". Keep the labels apart: measured, recorded, staged and simulated are different things; a verdict belongs to the validator named on it (fork@eb4b4b4 recorded, svc@11Oct recorded, js-port-of-8dd0d3e here). Answer in plain text, briefly.`;
/* ---------- parsed-step cache (v3 parsed every scene on every tick; here once per scene body) ---------- */
const cache=new Map();
function stepsOf(sc){let c=cache.get(sc.id);if(!c||c.xml!==sc.xml){let st=[];try{st=readSteps(sc.xml).map(([n,s])=>{const j=JSON.parse(s);j.n=n;return j})}catch(e){st=[]}c={xml:sc.xml,st};cache.set(sc.id,c)}return c.st}
const scenes=()=>(self.S&&S.scenes)||[];
const sig=()=>{const sc=scenes();return sc.length+"|"+(self.S?S.mode:"")+"|"+sc.reduce((n,s)=>n+(s.nsteps||0),0)+"|"+(self.S&&S.sel||"")};
let rowsSig="",rowsCache=[];
function rows(){const s=sig();if(s===rowsSig)return rowsCache;const out=[];
  scenes().forEach(sc=>{const st=stepsOf(sc);const gen=st.find(r=>r.op==="generate"||r.op==="repair");const model=sc.model||(gen&&gen.model)||"";const prompt=(gen&&gen.prompt_id)||(sc.item&&(sc.item.p||sc.item.k))||"";
    st.forEach(r=>out.push({scene:sc.id,model,prompt,n:r.n,op:r.op,kind:r.kind||null,round:r.round||null,verdict:r.verdict||null,codes:r.codes||null,finding:r.finding||null,tokens_in:r.tokens_in||null,tokens_out:r.tokens_out||null,latency_ms:r.latency_ms||null,
      usd:share()?null:(r.cost_usd_est!=null?r.cost_usd_est:r.cost_apportioned_usd!=null?r.cost_apportioned_usd:null),finish:r.finish||null,nonblank_ratio:r.nonblank_ratio!=null?r.nonblank_ratio:null,validator:r.validator_ref||r.validator||null,status:sc.status}))});
  rowsSig=s;rowsCache=out;return out}
function findingKey(v){if(v.finding){return String(v.finding).replace(/^Element '(\w+)', attribute '(\w+)': The attribute '\w+' is not allowed\.$/,(m,n,a)=>n+" has no attribute '"+a+"'").replace(/^\[profile-component\]\s+(\w+) \(component (\w+) level (\d+), not declared\).*$/,(m,n,c,l)=>"[profile-component] "+n+" needs a declared component: "+c+" level "+l).slice(0,120)}
  const codes=Array.isArray(v.codes)?v.codes.slice().sort():[];return codes.length?codes.join(" + "):"invalid · no code recorded"}
/* ---------- aggregates: the v3 per-model table and findings table ---------- */
let aggSig="",aggCache=null;
function aggregates(){const s=sig();if(s===aggSig&&aggCache)return aggCache;const byM={},fin1={};let steps=0,n=0;
  scenes().forEach(sc=>{const st=stepsOf(sc);steps+=st.length;n++;const gen=st.filter(r=>r.op==="generate"||(r.op==="repair"&&r.kind!=="deterministic"));if(!gen.length)return;const m=gen[0].model||sc.model||"?";
    const R=byM[m]||(byM[m]={id:m,scenes:0,calls:0,rep:0,tin:0,tout:0,usd:0,lat:[],first:0,valid:0,blank:0});R.scenes++;
    gen.forEach(r=>{R.calls++;if(r.op==="repair")R.rep++;R.tin+=r.tokens_in||0;R.tout+=r.tokens_out||0;R.usd+=r.cost_usd_est!=null?r.cost_usd_est:r.cost_apportioned_usd!=null?r.cost_apportioned_usd:0;if(r.latency_ms)R.lat.push(r.latency_ms)});
    const vs=st.filter(r=>r.op==="validate"),f=vs[vs.length-1],rn=st.find(r=>r.op==="render");if(vs[0]&&vs[0].verdict==="valid")R.first++;if(f&&f.verdict==="valid"){R.valid++;if(rn&&rn.nonblank_ratio<.005)R.blank++}
    const v=vs[0];if(v&&v.verdict==="invalid"&&st.indexOf(v)===1){const k=findingKey(v);const F=fin1[k]||(fin1[k]={key:k,n:0,m:{}});F.n++;F.m[m]=(F.m[m]||0)+1}});
  const list=Object.values(byM).sort((a,b)=>b.scenes-a.scenes).map(R=>Object.assign({},R,{lat:undefined,latMed:R.lat.length?UTIL.median(R.lat):null,usd:share()?null:+R.usd.toFixed(4)}));
  const tot={scenes:0,calls:0,rep:0,tin:0,tout:0,usd:0,first:0,valid:0,blank:0};list.forEach(R=>Object.keys(tot).forEach(k=>tot[k]+=R[k]||0));if(share())tot.usd=null;else tot.usd=+tot.usd.toFixed(4);
  const findings=Object.values(fin1).sort((a,b)=>b.n-a.n).map(F=>({finding:F.key,n:F.n,byModel:Object.keys(F.m).sort((a,b)=>F.m[b]-F.m[a]).map(m=>disp(m)+" "+F.m[m]).join(", ")}));
  let rec=null;if(self.S&&S.mode==="live17"&&self.LIVE&&LIVE.length){const its=scenes().map(sc=>sc.item).filter(Boolean);const c=its.reduce((a,i)=>a+(i.A?i.A.length:0),0),ti=its.reduce((a,i)=>a+(i.A||[]).reduce((x,y)=>x+(y.ti||0),0),0),to=its.reduce((a,i)=>a+(i.A||[]).reduce((x,y)=>x+(y.to||0),0),0);
    rec={scenes:its.length,recorded:{calls:c,tokens_in:ti,tokens_out:to},parsed:{calls:tot.calls,tokens_in:tot.tin,tokens_out:tot.tout},ok:tot.calls===c&&tot.tin===ti&&tot.tout===to}}
  aggSig=s;aggCache={rows:list,tot,findings,scenes:n,steps,reconcile:rec};return aggCache}
/* ---------- claims: the ledger reconciliation (events.json reconcile block) and the page-side sums ---------- */
const REC=()=>(self.EVENTS&&EVENTS.reconcile)||{};
const Q={grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"none",needs:["events"]};
CLAIMS.define("ask.ledgerCalls",Object.assign({label:"live calls in the ledger",unit:"tag 'live' rows within 600 s of the run",fields:["EVENTS.reconcile.ledger_calls (quoted)"],compute(){return REC().ledger_calls}},Q));
CLAIMS.define("ask.onPage",Object.assign({label:"calls on the page",unit:"attempts in live.json",fields:["sum of LIVE[].A.length; expected = EVENTS.reconcile.on_page"],needs:["live.core","events"],compute(){return LIVE.reduce((n,i)=>n+i.A.length,0)}},Q,{needs:["live.core","events"]}));
CLAIMS.define("ask.notOnPage",Object.assign({label:"ledger calls not on the page",unit:"failed + cut calls + retries",fields:["EVENTS.reconcile: not_on_page === failed + cut_calls + retries_in_call_layer"],text:v=>`${v.not} = ${v.failed} failed + ${v.cut} cut + ${v.retries} retries`,
  compute(){const r=REC();const v={not:r.not_on_page,failed:r.failed,cut:r.cut_calls,retries:r.retries_in_call_layer};if(v.not!==v.failed+v.cut+v.retries)throw new Error("reconcile identity fails: "+JSON.stringify(v));return v}},Q));
CLAIMS.define("ask.failedCalls",Object.assign({label:"failed calls",unit:"events.jsonl rows with an error",fields:["EVENTS.reconcile.failed; equals EVENTS.failed.length"],compute(){const r=REC();if(self.EVENTS&&EVENTS.failed&&EVENTS.failed.length!==r.failed)throw new Error("failed rows "+EVENTS.failed.length+" ≠ reconcile "+r.failed);return r.failed}},Q));
CLAIMS.define("ask.cutCalls",Object.assign({label:"calls of cut chains",unit:"the cap or the time box stopped the lane",fields:["EVENTS.reconcile.cut_calls (chains: cut_chains)"],text:v=>`${v.calls} calls · ${v.chains} chains`,compute(){const r=REC();return{calls:r.cut_calls,chains:r.cut_chains}}},Q));
CLAIMS.define("ask.retries",Object.assign({label:"retries inside the call layer",unit:"before one event was logged",fields:["EVENTS.reconcile.retries_in_call_layer, by kind"],text:v=>`${v.n} · ${Object.entries(v.kinds||{}).map(([k,c])=>k+" "+c).join(", ")}`,compute(){const r=REC();return{n:r.retries_in_call_layer,kinds:r.retry_kinds}}},Q));
CLAIMS.define("ask.probes",Object.assign({label:"probes",unit:"in the run's window · total",fields:["EVENTS.reconcile.probes_in_window · probes_total"],text:v=>`${v.inWindow} in window · ${v.total} total`,compute(){const r=REC();return{inWindow:r.probes_in_window,total:r.probes_total}}},Q));
CLAIMS.define("ask.pageTokens",{label:"tokens on the page",unit:"providers' reported counts over every attempt",grade:"C",source:"RECORDED 17 Oct",validator:"none",renderer:"none",needs:["live.core"],fields:["sum of LIVE[].A[].ti · sum of LIVE[].A[].to"],text:v=>`${fmt.int(v.tokens_in)} in · ${fmt.int(v.tokens_out)} out`,
  compute(){return{tokens_in:LIVE.reduce((n,i)=>n+i.A.reduce((a,b)=>a+(b.ti||0),0),0),tokens_out:LIVE.reduce((n,i)=>n+i.A.reduce((a,b)=>a+(b.to||0),0),0)}}});
CLAIMS.define("ask.reconcile",{label:"parsed chains vs the recorded run",unit:"calls and tokens read back from the x3dprov.step.* lines of the stamped scenes",grade:"C",source:"RE-RUN HERE",validator:"none",renderer:"none",needs:["live.core"],fields:["sum over scenes of generate/repair steps and their tokens === the recorded attempts' counts, to the token"],
  text:v=>v?`${v.parsed.calls} of ${v.recorded.calls} calls · ${fmt.int(v.parsed.tokens_in)} / ${fmt.int(v.recorded.tokens_in)} in · ${v.ok?"to the token":"not reconciled yet"}`:"live mode only",compute(){return aggregates().reconcile}});
if(self.DATA)DATA.on("events",()=>{const c=CLAIMS.get("ask.onPage");if(c&&self.EVENTS&&EVENTS.reconcile)c.expected=EVENTS.reconcile.on_page});
/* ---------- context for the ASK box, ≤ 32 KB ---------- */
function context(){const claims={};CLAIMS.list().forEach(c=>{claims[c.id]={label:c.label,unit:c.unit,value:c.value!==undefined?c.value:c.expected,status:c.status,grade:c.grade,source:c.source||null,validator:c.validator||null,renderer:c.renderer||null}});
  const ag=aggregates();const sel=self.S&&S.sel?S.byId.get(S.sel):null;const chain=sel?stepsOf(sel):null;
  const ctx={page:"Tether Firehose v4 (claude.ai artifact)",build:self.BUILD?{sha:BUILD.sha||null,date:BUILD.date||null,share:!!BUILD.share,xite:BUILD.xite||null,validator_recorded:BUILD.validator_recorded||null,port:BUILD.port||null}:null,
    run:self.LM?{models:(LM.models||[]).map(m=>m.id),validator:LM.validator||null,n_prompts:LM.n_prompts||null,max_attempts:LM.max_attempts||null}:null,mode:self.S?S.mode:null,
    livestats:self.LIVESTATS||null,reconcile:self.EVENTS?EVENTS.reconcile:null,claims,ask_the_files:{per_model:ag.rows,totals:ag.tot,findings_first_attempt:ag.findings.slice(0,12),scenes:ag.scenes,steps:ag.steps,reconcile:ag.reconcile},
    selected_scene:sel?{id:sel.id,model:sel.model,src:sel.src,status:sel.status,verdict:sel.verdict,steps:chain}:null,
    data_parts:self.DATA&&DATA.status?Object.fromEntries(Object.entries(DATA.status).map(([k,v])=>[k,v.state])):null,
    labels:{measured:"computed in this browser from the stored files",recorded:"read from the run's own files",staged:"Blender Cycles renders made afterwards",simulated:"not used for any number here"}};
  if(share()&&ctx.livestats)ctx.livestats=Object.assign({},ctx.livestats,{usd:null,per:(ctx.livestats.per||[]).map(p=>Object.assign({},p,{usd:null}))});
  return trimTo(ctx,MAX)}
const size=o=>JSON.stringify(o).length;
function trimTo(ctx,max){max=max||MAX;if(size(ctx)<=max)return ctx;ctx=JSON.parse(JSON.stringify(ctx));
  const cuts=[o=>{if(o.selected_scene&&o.selected_scene.steps&&o.selected_scene.steps.length>8)o.selected_scene.steps=o.selected_scene.steps.slice(0,4).concat([{note:"… steps elided for size …"}],o.selected_scene.steps.slice(-3))},
    o=>{if(o.ask_the_files)o.ask_the_files.findings_first_attempt=(o.ask_the_files.findings_first_attempt||[]).slice(0,5)},
    o=>{if(o.livestats&&o.livestats.per)o.livestats.per=o.livestats.per.map(p=>({id:p.id,n:p.n,first:p.first,valid:p.valid,blankValid:p.blankValid}))},
    o=>{Object.keys(o.claims||{}).forEach(k=>{const c=o.claims[k];o.claims[k]={value:c.value,status:c.status,grade:c.grade}})},
    o=>{if(o.selected_scene)o.selected_scene.steps=o.selected_scene.steps?o.selected_scene.steps.map(s=>({n:s.n,op:s.op,verdict:s.verdict,model:s.model,tokens_in:s.tokens_in,tokens_out:s.tokens_out,output_sha256:s.output_sha256})):null},
    o=>{delete o.livestats;delete o.labels},
    o=>{delete o.selected_scene},
    o=>{Object.keys(o.claims||{}).forEach(k=>{o.claims[k]=o.claims[k].value})},
    o=>{if(o.ask_the_files){delete o.ask_the_files.per_model;delete o.ask_the_files.findings_first_attempt}},
    o=>{delete o.reconcile;delete o.run;delete o.data_parts;delete o.build}];
  for(const cut of cuts){cut(ctx);ctx.trimmed=true;if(size(ctx)<=max)return ctx}
  const ids=Object.keys(ctx.claims||{});while(size(ctx)>max&&ids.length){delete ctx.claims[ids.pop()]}return ctx}
/* ---------- query_steps: a structured filter over the parsed rows, no code runs from the model ---------- */
function query(filter){filter=filter&&typeof filter==="object"?filter:{};const f=filter.filter&&typeof filter.filter==="object"?filter.filter:filter;const low=s=>String(s==null?"":s).toLowerCase();const has=(a,b)=>low(a).includes(low(b));
  let out=rows().filter(r=>(f.op==null||r.op===f.op)&&(f.model==null||has(r.model,f.model)||has(disp(r.model),f.model))&&(f.prompt==null||has(r.prompt,f.prompt))&&(f.verdict==null||r.verdict===f.verdict)&&(f.scene==null||has(r.scene,f.scene))&&(f.status==null||r.status===f.status)
    &&(f.code==null||(Array.isArray(r.codes)&&r.codes.some(c=>has(c,f.code)))||has(r.finding,f.code))&&(f.blank==null||(r.op==="render"&&r.nonblank_ratio!=null&&((r.nonblank_ratio<.005)===!!f.blank)))&&(f.minTokensOut==null||(r.tokens_out||0)>=+f.minTokensOut)&&(f.maxLatencyMs==null||(r.latency_ms||Infinity)<=+f.maxLatencyMs));
  const total=out.length;let limit=Math.max(1,Math.min(200,+f.limit||50));let res;do{res={total,shown:Math.min(limit,total),filter:f,rows:out.slice(0,limit),note:"stored rows of the scenes on the page; nothing fetched"};if(size(res)<=MAX)break;limit=Math.floor(limit/2)}while(limit>=1);
  if(size(res)>MAX)res={total,shown:0,filter:f,rows:[],note:"a single row exceeded 32 KB"};return res}
const queryTool={name:"query_steps",description:"Filter the parsed x3dprov.step.* rows of the scenes on this page (stored rows only, nothing fetched). filter fields, all optional: op (generate|repair|validate|render|…), model (substring), prompt (substring of the prompt id), verdict (valid|invalid), code (substring of a validator code or finding), scene (substring of the scene id), status (verified|broken|…), blank (true: render rows with nonblank_ratio < 0.005; false: the rest), minTokensOut, maxLatencyMs, limit (≤ 200, default 50). Returns {total, shown, rows} under 32 KB.",
  inputSchema:{type:"object",properties:{filter:{type:"object",properties:{op:{type:"string"},model:{type:"string"},prompt:{type:"string"},verdict:{type:"string"},code:{type:"string"},scene:{type:"string"},status:{type:"string"},blank:{type:"boolean"},minTokensOut:{type:"integer"},maxLatencyMs:{type:"integer"},limit:{type:"integer"}}}}},
  execute(input){return query(input&&input.filter?input.filter:input||{})}};
/* ---------- the drawer ---------- */
const ASK={available:false,mode:"off",lastPrompt:null,lastContext:null,lastQuestion:null,lastAnswer:null,lastError:null,context,query,ask,stop,rows,aggregates,trimTo,INSTR,MAX,tool:queryTool};
let drawer=null,box=null,pre=null,statusEl=null,ctxEl=null,goBtn=null,stopBtn=null,qEl=null,busy=false,ctrl=null,tableSig="",hitsQ="",offLine=OFF;
const ERR={not_granted:"not granted: the viewer declined the sample permission; the ASK box is off for this view",rate_limited:"rate limited: wait a moment, then ask again",refused:"Claude declined to answer this one",cancelled:"stopped",tools_unavailable:"tools unavailable here: asked again without the query tool",prompt_too_large:"prompt too large even after trimming",upstream_error:"upstream error: try again later",error:"failed"};
function status(s){if(statusEl)txt(statusEl,s)}
function mountDrawer(){const sb=document.querySelector("#deck .sb");if(!sb||drawer)return false;
  const cols=["model","scenes","calls","repairs","tokens in","tokens out","est. cost","median latency","valid first try","valid at the end","valid · blank"];
  drawer=el("details",{class:"drawer",id:"askDrawer"},[el("summary",{text:"Ask the files"}),el("div",{id:"ask"},[
    el("div",{class:"note m",id:"askSub",text:"no scenes stamped yet"}),
    el("div",{class:"row claims"},[claimChip("ask.ledgerCalls",{size:"s"}),claimChip("ask.onPage",{size:"s"}),claimChip("ask.notOnPage",{size:"s"}),claimChip("ask.failedCalls",{size:"s"}),claimChip("ask.cutCalls",{size:"s"}),claimChip("ask.retries",{size:"s"}),claimChip("ask.probes",{size:"s"}),claimChip("ask.pageTokens",{size:"s"}),claimChip("ask.reconcile",{size:"s"})]),
    el("div",{class:"scroll"},el("table",{class:"askTable"},[el("thead",null,el("tr",null,cols.map(h=>el("th",{text:h,class:h==="est. cost"&&share()?"hideShare":""})))),el("tbody",{id:"askBody"})])),
    el("div",{id:"askFindWrap",hidden:""},[el("div",{class:"legend",text:"first-attempt findings that the validator reported, most frequent first (fork verdicts; codes as recorded)"}),el("div",{class:"scroll"},el("table",{class:"askTable"},[el("thead",null,el("tr",null,["finding","scenes","by model"].map(h=>el("th",{text:h})))),el("tbody",{id:"askFind"})]))]),
    el("div",{class:"row"},[el("input",{id:"askSearch",type:"search",placeholder:"search steps: code, prompt id, model, verdict, scene",autocomplete:"off",oninput:e=>{hitsQ=e.target.value;search()}}),el("span",{class:"note m",id:"askHitN"})]),
    el("div",{id:"askHits",class:"hits"}),
    el("div",{class:"note m",id:"askNote",text:"Computed by parsing the x3dprov.step.* lines in each stored scene's own head: calls, tokens, price estimates, latencies, verdicts and render outcomes travel with the file, so a question like \"which model's valid scenes draw nothing?\" needs no database and no trace store. The chips reconcile the page against the run's ledger (events.json): what is on the page, what failed, what was cut, what the call layer retried."}),
    el("div",{id:"askBox",class:"askBox"})])]);
  box=drawer.querySelector("#askBox");sb.insertBefore(drawer,sb.firstChild);
  if(self.TIER){if(TIER.tier)applyTier();else{setMode("resolving",OFF.replace("(the sample capability is not granted here;","(viewer tier still resolving;"));TIER.on(applyTier)}}else setMode("off");
  return true}
function applyTier(){const s=self.TIER&&TIER.caps&&TIER.caps.sample;if(typeof s==="function")setMode("on");else setMode("off")}
function setMode(mode,line){if(mode===ASK.mode&&box&&box.children.length)return;ASK.mode=mode;ASK.available=mode==="on";if(!box)return;box.textContent="";box.dataset.mode=mode;
  if(mode!=="on"){offLine=line||OFF;box.appendChild(el("div",{class:"note m",id:"askOff",text:offLine}));pre=statusEl=ctxEl=goBtn=stopBtn=qEl=null;return}
  qEl=el("textarea",{id:"askQ",rows:"2",placeholder:"ask the page's data: which model's valid scenes draw nothing? how many calls failed? what does step 3 of the selected scene say?",onkeydown:e=>{if((e.ctrlKey||e.metaKey)&&e.key==="Enter"){e.preventDefault();ask(qEl.value)}}});
  goBtn=el("button",{id:"askGo",class:"primary",text:"ASK",onclick:()=>ask(qEl.value)});stopBtn=el("button",{id:"askStop",text:"STOP",disabled:"",onclick:stop});
  statusEl=el("span",{class:"note m",id:"askStatus",text:"answers come from this page's own data, passed in the prompt; your Claude account answers; nothing is fetched"});ctxEl=el("div",{class:"note m",id:"askCtx"});pre=el("pre",{id:"askA",class:"askA"});
  box.append(el("div",{class:"row"},[qEl,goBtn,stopBtn]),statusEl,ctxEl,pre);ctxLine()}
function ctxLine(){if(!ctxEl)return;const ag=aggregates();txt(ctxEl,`context: claims ${CLAIMS.list().length} · scenes ${ag.scenes} · steps ${ag.steps} · selected ${self.S&&S.sel?S.sel:"none"} · trimmed to ≤ ${fmt.int(MAX)} bytes · tool query_steps over ${rows().length} rows${self.TIER&&TIER.caps.files?" · files tools added for members":""}`)}
function tables(){const s=sig();if(s===tableSig)return;tableSig=s;const ag=aggregates(),body=drawer.querySelector("#askBody"),find=drawer.querySelector("#askFind"),wrap=drawer.querySelector("#askFindWrap");
  body.textContent="";const cell=(t,cls)=>el("td",{text:t==null?"—":String(t),class:cls||""});
  const rowOf=(R,bold)=>el("tr",{class:bold?"all":""},[cell(disp(R.id)),cell(R.scenes),cell(R.calls),cell(R.rep),cell(fmt.int(R.tin)),cell(fmt.int(R.tout)),cell(share()?"hidden":fmt.usd(R.usd),share()?"hideShare":""),cell(R.latMed==null?"-":fmt.ms(R.latMed)),cell(`${R.first} · ${pc(R.first,R.scenes)}`),cell(`${R.valid} · ${pc(R.valid,R.scenes)}`),cell(R.blank?String(R.blank):"0",R.blank?"warn":"")]);
  ag.rows.forEach(R=>body.appendChild(rowOf(R)));if(ag.rows.length>1)body.appendChild(rowOf(Object.assign({id:"all",latMed:null},ag.tot),true));
  find.textContent="";ag.findings.slice(0,8).forEach(F=>find.appendChild(el("tr",null,[cell(F.finding),cell(F.n),cell(F.byModel)])));wrap.hidden=!ag.findings.length;
  const rec=ag.reconcile;txt(drawer.querySelector("#askSub"),`${ag.scenes} stored scenes · ${fmt.int(ag.steps)} chain steps read in this browser${rec?(rec.ok?` · reconciles with the recorded run: ${rec.recorded.calls} calls, ${fmt.int(rec.recorded.tokens_in)} tokens in, ${fmt.int(rec.recorded.tokens_out)} out, to the token`:` · ${rec.parsed.calls} of ${rec.recorded.calls} recorded calls stamped so far`):""}`);
  if(hitsQ)search();ctxLine();const c=CLAIMS.get("ask.reconcile");if(c&&rec&&rec.ok&&c.value&&!c.value.ok)CLAIMS.run("ask.reconcile")}
function search(){const host=drawer.querySelector("#askHits"),n=drawer.querySelector("#askHitN");host.textContent="";const q=hitsQ.trim();if(!q){txt(n,"");return}
  const low=q.toLowerCase(),all=rows().filter(r=>[r.scene,r.model,disp(r.model),r.prompt,r.op,r.verdict,r.finding,...(Array.isArray(r.codes)?r.codes:[])].some(x=>x&&String(x).toLowerCase().includes(low)));
  txt(n,`${all.length} step rows match${all.length>40?" · first 40":""}`);
  all.slice(0,40).forEach(r=>host.appendChild(el("button",{class:"hit",type:"button",data:{scene:r.scene},onclick:()=>{if(self.SIM)SIM.select(r.scene)},text:`${r.scene} · step ${r.n} · ${r.op}${r.verdict?" · "+r.verdict:""}${Array.isArray(r.codes)&&r.codes.length?" · "+r.codes.slice(0,3).join(", "):""}${r.model?" · "+disp(r.model):""}`})))}
/* ---------- the call ---------- */
async function ask(q){q=String(q||"").trim();if(!q||ASK.mode!=="on"||busy)return null;const sample=TIER.caps.sample;if(typeof sample!=="function"){setMode("off");return null}
  busy=true;ctrl=new AbortController();goBtn.disabled=true;stopBtn.disabled=false;pre.textContent="";status("asking…");ASK.lastError=null;ASK.lastQuestion=q;
  let max=MAX;try{if(typeof sample.limits==="function"){const lim=await sample.limits();if(lim&&lim.maxPromptBytes)max=Math.min(MAX,Math.max(4096,lim.maxPromptBytes-INSTR.length-q.length-512))}}catch(e){}
  const ctx=trimTo(context(),max),ctxJson=JSON.stringify(ctx);const prompt=INSTR+"\n\nCONTEXT (JSON, "+ctxJson.length+" bytes, the page's own data):\n"+ctxJson+"\n\nQUESTION:\n"+q+"\n";ASK.lastPrompt=prompt;ASK.lastContext=ctx;
  let tools=[queryTool];try{const files=TIER.caps.files;if(files&&typeof files.asSampleTools==="function"){const ft=await files.asSampleTools();if(Array.isArray(ft))tools=tools.concat(ft)}}catch(e){}
  const opts={signal:ctrl.signal,onText:ev=>{if(ev&&typeof ev.text==="string")pre.textContent=ev.text},modelTier:"default",cache:false,tools};
  try{let res;try{res=await sample(prompt,opts)}catch(e){if(e&&e.code==="tools_unavailable"){status(ERR.tools_unavailable);delete opts.tools;res=await sample(prompt,opts)}else throw e}
    const text=res&&typeof res.text==="string"?res.text:typeof res==="string"?res:"";pre.textContent=text;ASK.lastAnswer=res;status(`answered${res&&res.truncated?" · truncated":""}${res&&res.modelTierApplied?" · "+res.modelTierApplied:""} · from the page's data only · check every number against the chips`);return res}
  catch(e){const code=(e&&e.code)||"error";ASK.lastError={code,message:String(e&&e.message||e)};if(e&&typeof e.text==="string"&&e.text)pre.textContent=e.text;status((ERR[code]||ERR.error)+(code==="error"||code==="upstream_error"?" · "+String(e&&e.message||e).slice(0,120):""));if(code==="not_granted")setMode("off",OFF);return null}
  finally{busy=false;ctrl=null;if(goBtn)goBtn.disabled=false;if(stopBtn)stopBtn.disabled=true}}
function stop(){if(ctrl)ctrl.abort()}
/* ---------- the panel: mount on the first draw, then keep the tables fresh at 1 Hz ---------- */
const panel=LOOP.register({name:"ask",bit:LOOP.bits.DATA|LOOP.bits.TIER|LOOP.bits.SCENE|LOOP.bits.SELECT,rateHz:1,budgetMs:4,draw(){if(!drawer&&!mountDrawer()){panel.forceDraw=true;return}tables();if(ASK.mode!=="on"&&self.TIER&&TIER.tier)applyTier()}});panel.forceDraw=true;
if(self.TIER)TIER.on(()=>{panel.forceDraw=true});
Object.assign(self,{ASK,__ask:ASK});
})();
