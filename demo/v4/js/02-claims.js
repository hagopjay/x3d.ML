/* 02-claims.js — claim registry, claim chips, proof drawer (SPEC rule 1, rule 3). Globals: CLAIMS, claimChip, proofDrawer, __claims.
   The ten headline claims of demo/v4/data/stats.json are defined here from STATS (expected + rule); their compute() runs over LIVE / REAL / EVENTS / MANIFEST
   once the parts land (03-data fires DATA bits). The hero module (12) renders the same ids as tiles; other modules define their own ids.
   Test hooks: __claims (Map id → spec), CLAIMS.status(id), CLAIMS.run(id). */
(function(){
"use strict";
const map=new Map(),listeners=new Map();
const emit=(id,ev)=>{(listeners.get(id)||[]).concat(listeners.get("*")||[]).forEach(f=>{try{f(ev,id)}catch(e){console.warn("claim listener",e)}})};
const defEq=(a,b)=>UTIL.sortedJson(a)===UTIL.sortedJson(b);
function face(c){if(c.text)try{return c.text(c.value!==undefined?c.value:c.expected)}catch(e){}const v=c.value!==undefined?c.value:c.expected;
  if(v==null)return"—";if(typeof v==="number")return fmt.num(v,Number.isInteger(v)?0:2);if(typeof v==="string")return v;return JSON.stringify(v)}
const CLAIMS={
  define(id,spec){const st=(self.STATS&&STATS.claims&&STATS.claims[id])||{};
    const c=Object.assign({id,label:id,unit:"",compute:null,expected:st.expected,source:st.source,validator:st.validator,renderer:st.renderer,xite:st.renderer,grade:st.grade||"S",files:[],fields:st.rule?[st.rule]:[],heavy:false,eq:defEq,text:null,needs:[],
      status:"known",value:undefined,ok:null,ms:null,at:null,runs:0,why:st.why||null},spec);
    if(c.expected===undefined)c.status="pending";map.set(id,c);emit(id,"define");return c},
  get:id=>map.get(id),list:()=>[...map.values()],
  status:id=>{const c=map.get(id);return c?c.status:null},
  on(id,fn){if(!listeners.has(id))listeners.set(id,[]);listeners.get(id).push(fn)},
  earn(id){const c=map.get(id);if(!c||c.status==="bad")return;c.status=c.expected===undefined?"pending":"earned";emit(id,"earn")},
  ready(c){return !c.needs||c.needs.every(n=>self.DATA&&DATA.loaded(n))},
  async run(id){const c=map.get(id);if(!c)throw new Error("no claim "+id);if(!c.compute)return{id,value:c.expected,expected:c.expected,ok:null,ms:0,at:Date.now()};
    if(!CLAIMS.ready(c))return{id,value:undefined,expected:c.expected,ok:null,ms:0,at:Date.now(),waiting:c.needs.filter(n=>!DATA.loaded(n))};
    const t=performance.now();let v;try{v=await c.compute()}catch(e){c.status="bad";c.err=String(e);c.value=undefined;emit(id,"run");return{id,error:c.err,expected:c.expected}}
    c.ms=performance.now()-t;c.at=Date.now();c.runs++;c.value=v;c.ok=c.expected===undefined?null:c.eq(v,c.expected);c.status=c.ok===false?"bad":"earned";if(c.ok===false)console.warn("claim mismatch",id,"computed",v,"expected",c.expected);emit(id,"run");return{id,value:v,expected:c.expected,ok:c.ok,ms:c.ms,at:c.at}},
  async runAll(filter){const out=[];for(const c of map.values()){if(filter&&!filter(c))continue;if(c.compute&&CLAIMS.ready(c))out.push(await CLAIMS.run(c.id))}return out},
  runReady(){CLAIMS.list().forEach(c=>{if(c.compute&&CLAIMS.ready(c)&&c.value===undefined)LOOP.idle(()=>CLAIMS.run(c.id))})}
};
function paint(b,c){const ok=c.status;b.className="claim "+ok+(b.dataset.size?" "+b.dataset.size:"");const v=b.querySelector(".v");
  if(ok==="bad")txt(v,`computed ${face(Object.assign({},c,{text:c.text}))} · expected ${face(Object.assign({},c,{value:undefined}))}`);else txt(v,face(c));
  b.title=`${c.label}${c.unit?" · "+c.unit:""} · ${ok==="known"?"known from the record":ok==="earned"?"recomputed in this view":ok==="bad"?"MISMATCH: computed differs from the record":"not yet computed"} · grade ${c.grade}`}
function claimChip(id,opts){opts=opts||{};const c=map.get(id)||CLAIMS.define(id,{});const b=el("button",{class:"claim "+c.status+(opts.size?" "+opts.size:""),type:"button",data:{claim:id,size:opts.size||""}});
  b.appendChild(el("b",{class:"v",text:face(c)}));const u=opts.label!==undefined?opts.label:(c.unit||c.label);if(u)b.appendChild(el("small",{class:"u",text:u}));
  b.addEventListener("click",()=>proofDrawer(id));CLAIMS.on(id,()=>paint(b,map.get(id)));paint(b,c);return b}
let proofId=null;
function proofDrawer(id){const c=map.get(id),box=$("proof");if(!c||!box)return;proofId=id;box.hidden=false;box.textContent="";
  const close=el("button",{text:"close",onclick:()=>{box.hidden=true;proofId=null}});
  const rerun=el("button",{class:"primary",text:`RE-RUN${c.runs?" ("+c.runs+")":""}`,onclick:async()=>{rerun.disabled=true;rerun.textContent="running…";await CLAIMS.run(id);proofDrawer(id)}});
  if(!c.compute)rerun.disabled=true;
  box.appendChild(el("div",{class:"row"},[el("h3",{text:c.label}),el("span",{class:"pill "+(c.status==="bad"?"p-bad":c.status==="earned"?"p-ok":"p-mute"),text:c.status}),gradeChip(c.grade),close]));
  const dl=el("dl");const add=(k,v)=>{dl.appendChild(el("dt",{text:k}));dl.appendChild(el("dd",{text:v==null?"—":typeof v==="string"?v:JSON.stringify(v)}))};
  add("unit",c.unit);add("computed",c.value===undefined?(CLAIMS.ready(c)?"not yet run":"waiting for parts: "+(c.needs||[]).join(", ")):c.value);add("expected (baked)",c.expected);add("agree",c.ok===null?"—":c.ok?"yes":"NO");
  add("source",c.source);add("validator",c.validator);add("X_ITE",c.renderer||c.xite);add("grade",{C:"C · Confirmed for these scenes",L:"L · list price / estimate",S:"S · Suspected (one sample)"}[c.grade]||c.grade);if(c.why)add("why this grade",c.why);
  add("files",(c.files||[]).join(", ")||"inline STATS + parts");add("rule",(c.fields||[]).join(" · "));add("last run",c.at?new Date(c.at).toISOString()+" · "+c.ms.toFixed(1)+" ms":"never in this view");box.appendChild(dl);
  box.appendChild(el("pre",{text:c.compute?String(c.compute):"(no compute: this number is quoted, not re-measured here)"}));
  box.appendChild(el("div",{class:"row"},[rerun,el("span",{class:"note",text:"RE-RUN recomputes from the loaded parts in this browser; a mismatch turns the chip red and prints both values."})]))}
/* ---------- the headline claims (stats.json ids), computed with the same rules the build used ---------- */
const fin=i=>i.A[i.A.length-1],med=a=>UTIL.median(a);
const paidLanes=()=>(self.LM||STATS.meta).models.filter(m=>m.prov!=="nvidia");
CLAIMS.define("c.rates",{label:"% valid, first try → end of loop",unit:"three paid lanes",needs:["live.core"],text:v=>v.map(x=>`${x.firstPct} → ${x.validPct}`).join(" · "),
  compute(){return paidLanes().map(m=>{const s=LIVE.filter(i=>i.m===m.id),first=s.filter(i=>i.A[0].ok).length,valid=s.filter(i=>fin(i).ok).length;return{id:m.id,n:s.length,first,valid,firstPct:Math.round(100*first/s.length),validPct:Math.round(100*valid/s.length)}})}});
CLAIMS.define("c.seven",{label:"valid on the fork, nothing drawn",unit:"of 178 valid finals · X_ITE 16.5.0 and 16.5.1",needs:["live.core","renders.151"],text:v=>v+" of "+(STATS.claims["c.seven"].of||178),
  compute(){return LIVE.filter(i=>{const f=fin(i);if(!f.ok||f.r.err)return false;const r1=R151.live[keyOf(i.m,i.p,i.A.length)];return (f.r.nb||0)<.005&&r1&&!r1.err&&(r1.nb||0)<.005}).length}});
CLAIMS.define("c.ratio",{label:"validator median vs model-call median",unit:"358 calls",needs:["live.core"],text:v=>`${fmt.ms(v.vmed)} vs ${fmt.ms(v.mmed)}`,
  compute(){const vmed=med(LIVE.flatMap(i=>i.A.map(a=>a.vms))),mmed=med(LIVE.flatMap(i=>i.A.map(a=>a.ms)));return{vmed,mmed,x:Math.round(mmed/Math.max(1,vmed))}}});
CLAIMS.define("c.calls",{label:"calls on the page",unit:"sum of A[].length",needs:["live.core"],compute(){return LIVE.reduce((n,i)=>n+i.A.length,0)}});
CLAIMS.define("c.failed",{label:"failed calls",unit:"events.jsonl rows with an error",needs:["events"],compute(){return EVENTS.failed.length}});
CLAIMS.define("c.cut",{label:"cut chains",unit:"cap or time box stopped the lane",needs:["events"],compute(){return EVENTS.cut.length}});
CLAIMS.define("c.canary",{label:"canary: bodies · flips",unit:"fork@8dd0d3e vs recorded verdicts",needs:["drift"],text:v=>`${v.bodies} bodies · ${v.flips} flips`,
  compute(){const V=DRIFT.v8dd0d3e.verdicts,ids=Object.keys(V);let flips=0;
    /* recorded eb4b4b4 verdicts for the live bodies live in LIVE[].A[].ok; the replay's in REAL[].f2; the ledger is XSD-valid by construction (29 steps verified at build) */
    if(self.LIVE&&LIVE.length&&self.REAL&&REAL.length){ids.forEach(k=>{const v=V[k];let rec=null;const m=/x3d\/(.+?)\/([\w-]+)_a(\d+)\.x3d$/.exec(k);
      if(m){const it=LIVE.find(i=>i.m.replace("/","_")===m[1]&&i.p===m[2]);if(it&&it.A[+m[3]-1])rec=!!it.A[+m[3]-1].ok}else{const it=REAL.find(i=>k.endsWith(i.k));if(it)rec=!!it.f2[0]}
      if(rec!=null&&rec!==!!v.valid)flips++})}
    return{bodies:ids.length,flips}}});
CLAIMS.define("c.truncated",{label:"outputs cut at the token limit",unit:"finish reason length / max_tokens",needs:["live.core"],compute(){return LIVE.reduce((n,i)=>n+i.A.filter(a=>/length|max_tokens/i.test(a.fin||"")).length,0)}});
CLAIMS.define("c.replay17",{label:"valid on the 11 Oct service, nothing drawn",unit:"of 91 · X_ITE 16.5.0",needs:["replay"],text:v=>v+" of "+(STATS.claims["c.replay17"].of||91),compute(){return REAL.filter(i=>i.x&&i.s&&!i.r.err&&(i.r.nb||0)<.005).length}});
CLAIMS.define("c.lockstep",{label:"C14N lockstep",unit:"page hash vs repo C14N over 175 stamped heads",compute:null});
if(self.DATA)DATA.on("*",()=>CLAIMS.runReady());
Object.assign(self,{CLAIMS,claimChip,proofDrawer,__claims:map});
})();
