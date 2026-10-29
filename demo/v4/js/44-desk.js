/* 44-desk.js — S15 MEMBERS' DESK (SPEC-v4 S15, §3 tiers, rule 9; WORKPLAN 44-desk). Owns #desk .sb. Private build, members and owner only:
   the section carries data-tier="member" (07-tier removes it below that tier) and this module also removes it when TIER.caps.files is null.
   CONNECT is the consent moment: the first files.list({path: ROOT, recursive: true}) runs on that click and never at load (__desk.listCalls is 0 until then).
   The tree lists every entry with size and createdAt; LOAD on a .json run file reads it through files.read in 25 MiB chunks, parses the live-run schema
   ({items:[{m, p, T, A:[…], B:[…]}], meta}), registers MODES "files:<name>" with a generator mirroring 20-sim genLive (generate → validate → repair → … →
   render, every step's ms_src as the file records it), adds a mast run-segment button and switches to the mode: waterfall, scope, firehose, matrix, wall
   and morph replay it without a republish (the waterfall's generic source reads the released scenes' items; a FILM source is registered here with the
   file's own stamps when FILM is present). Scenes carry src "files", ids D-00n; the baked aggregates (LIVE, LIVESTATS, CLAIMS) are never touched.
   Flywheel: flywheel/<id>/{chain.json, r0.x3d, r1.x3d} entries → RE-VALIDATE reads the r1 (else r0) bodies, VAL.validateMany on js-port-of-8dd0d3e,
   and lights the XLAD flywheel row (42-suite XLAD.light). Owner: BAKE THIS RUN INTO V4.1 prints the republish recipe as text (the page never republishes itself).
   Globals: DESK {connect, load(path), flywheel, root, mode}. Test hooks: __desk {listCalls, readCalls, entries, runs, flywheelDirs, loaded, mode, flywheel, err, revision},
   #deskConnect, #deskTree li[data-path], #deskTree button.load, #deskFly, #deskFlyNote, #deskBake, #deskStatus, #runseg button[data-m^="files:"].
   v3 port: none (new in v4). Stamps: RECORDED <date> (from the file's meta.date when it is 17 or 24 Oct) · the file's validator when it is in the closed vocabulary. */
(function(){
"use strict";
const ROOT="research/traceability-2026-10-17/firehose4",CHUNK=25*1024*1024;
const __desk={listCalls:0,readCalls:0,entries:[],runs:[],flywheelDirs:[],loaded:{},mode:null,flywheel:null,err:null,revision:null,connected:false};
self.__desk=__desk;
const E={};let sec=null,files=null;
const VSTAMP={"fork@8c0a457":"fork@8c0a457 recorded","fork@eb4b4b4":"fork@eb4b4b4 recorded","fork@8dd0d3e":"fork@8dd0d3e recorded","fork@fa0b389":"fork@fa0b389 recorded"};
function status(t){if(E.status)txt(E.status,t||"")}
function base(p){return String(p).split("/").pop()}
function rel(p){return String(p).startsWith(ROOT+"/")?String(p).slice(ROOT.length+1):String(p)}
function dateStamp(meta){const d=String(meta&&meta.date||"");if(d.endsWith("10-17"))return"RECORDED 17 Oct";if(d.endsWith("10-24"))return"RECORDED 24 Oct";if(d.endsWith("10-11"))return"RECORDED 11 Oct";return"RECORDED 24 Oct"}
/* ---------- files ---------- */
async function listAll(path){const out=[];let cursor;do{__desk.listCalls++;const r=await files.list(Object.assign({path,recursive:true},cursor?{cursor}:{}));(r&&r.entries||[]).forEach(e=>out.push(e));cursor=r&&r.cursor}while(cursor&&out.length<20000);return out}
async function readAll(path){const parts=[];let off=0,size=null,rev=null;
  for(let i=0;i<4096;i++){__desk.readCalls++;const r=await files.read(path,{offset:off,length:CHUNK});const b=r&&r.bytes?r.bytes:new Uint8Array(0);parts.push(b);size=r&&r.size!=null?r.size:off+b.length;rev=r&&r.revision||rev;off+=b.length;if(!b.length||off>=size)break}
  const all=new Uint8Array(parts.reduce((a,b)=>a+b.length,0));let p=0;parts.forEach(b=>{all.set(b,p);p+=b.length});return{bytes:all,size,revision:rev}}
async function connect(){if(!files)return null;status("listing "+ROOT+"…");E.connect.disabled=true;
  try{const entries=await listAll(ROOT);__desk.entries=entries;__desk.connected=true;tree(entries);status(`${entries.length} entries under ${ROOT} · read as you`);return entries}
  catch(e){__desk.err=e&&e.code||String(e);status(`files.list failed (${__desk.err})${e&&e.code==="rate_limited"&&e.retryAfterMs?" · retry after "+fmt.ms(e.retryAfterMs):""}`);E.connect.disabled=false;return null}}
/* ---------- tree ---------- */
function tree(entries){if(!E.tree)return;E.tree.textContent="";const sorted=entries.slice().sort((a,b)=>String(a.path).localeCompare(String(b.path)));__desk.runs=[];const fly=new Set();
  const dirs=new Set();sorted.forEach(e=>{const r=rel(e.path),d=r.includes("/")?r.split("/").slice(0,-1).join("/"):"";if(d)dirs.add(d)});
  const seen=new Set();sorted.forEach(e=>{if(e.isDirectory)return;const r=rel(e.path),d=r.includes("/")?r.split("/").slice(0,-1).join("/"):"";
    if(d&&!seen.has(d)){seen.add(d);E.tree.appendChild(el("li",{class:"dir",text:d+"/"}))}
    const li=el("li",{data:{path:e.path}});li.appendChild(el("span",{class:"nm",text:base(e.path),title:e.path}));li.appendChild(el("span",{class:"sz",text:fmt.bytes(e.size||0)}));if(e.createdAt)li.appendChild(el("span",{class:"at",text:String(e.createdAt).slice(0,10)}));
    const m=r.match(/^flywheel\/([^/]+)\//);if(m)fly.add(m[1]);
    if(/\.json$/.test(r)&&(/^(data|runs)\//.test(r))&&!/renders|replay|manifest|stats|hero|rigok|events|staged/.test(base(r))){__desk.runs.push(e.path);const b=el("button",{class:"load",type:"button",text:"LOAD",title:"files.read in 25 MiB chunks → a run mode on the mast"});b.addEventListener("click",()=>load(e.path,b));li.appendChild(b)}
    E.tree.appendChild(li)});
  __desk.flywheelDirs=[...fly];if(E.fly){E.fly.disabled=!fly.size;txt(E.flyNote,fly.size?`${fly.size} flywheel chain${fly.size===1?"":"s"} in the files · RE-VALIDATE runs their final bodies on js-port-of-8dd0d3e here`:"no flywheel/ chains in the files")}}
/* ---------- a run file becomes a mode ---------- */
function parseRun(text){let j;try{j=JSON.parse(text)}catch(e){throw new Error("not JSON: "+String(e&&e.message||e).slice(0,80))}
  const items=Array.isArray(j)?j:j&&Array.isArray(j.items)?j.items:null;if(!items||!items.length)throw new Error("not a live-run file (no items[])");
  const bad=items.find(it=>!it||!Array.isArray(it.A)||!it.A.length);if(bad)throw new Error("not a live-run file (an item has no A[] calls)");
  if(!items.some(it=>Array.isArray(it.B)&&it.B.length))throw new Error("the run file carries no bodies (B[]): nothing to chain");
  return{items,meta:(j&&j.meta)||{}}}
function genFor(run){return function genFiles(){const idx=S.order[S.ri];if(idx===undefined)return null;const it=run.items[idx];if(!it||(it.T||0)>S.clk)return null;S.ri++;
  const id="D-"+String(S.ri).padStart(3,"0"),f=it.A[it.A.length-1],mm=((run.meta.models)||[]).find(q=>q.id===it.m)||{prov:"files"};S.seq=S.ri;
  const sc={id,src:"files",item:it,model:it.m,mode:it.A.length>1?"repair x"+(it.A.length-1):"oneshot",born:S.clk,sealed:false,status:"?",nsteps:0,vref:"",verdict:"",xml:"",nb:null,blank:false,T:it.T||0,promptId:it.p};
  const M=S.mod[it.m]||(S.mod[it.m]={n:0,first:0,rep:0,repOk:0,cost:0,valid:0}),usd=it.A.reduce((a,b)=>a+(+b.u||0),0);M.n++;M.cost+=usd;S.cost+=usd;S.stage.gen++;
  const psha=it.psha?String(it.psha).slice(0,16):sha(String(it.pt||it.p||"")).slice(0,16),vref=run.meta.validator||"as recorded in the file";let x=it.B&&it.B[0]||"<X3D version='4.0' profile='Interchange'><Scene/></X3D>";
  it.A.forEach((a,k)=>{const body=(it.B&&it.B[k])||x;const b={model:it.m,provider:mm.prov,prompt_id:it.p,prompt_sha256:psha,tokens_in:a.ti??null,tokens_out:a.to??null,latency_ms:a.ms??null,cost_usd_est:a.u??null,finish:a.fin||"stop",run_s:a.t0??null,ms:a.ms||0,ms_src:a.ms?"recorded":"missing"};
    if(k===0)x=addStep(body,{op:"generate",condition:"oneshot",...b,input_sha256:"none"},body,false);
    else{x=addStep(x,{op:"repair",kind:a.agent==="autofix"?"deterministic":"model",round:k,report_shown:a.agent!=="autofix",report_sha256:it.A[k-1].rsha||"",fixes:self.codesOf?codesOf(it.A[k-1]):[],...b},body,false);S.stage.rep++;M.rep++}
    x=addStep(x,{op:"validate",validator:"fork",validator_ref:vref,verdict:a.ok?"valid":"invalid",codes:self.codesOf?codesOf(a):[],xsd_valid:!!a.x,n_errors:(a.xe||[]).length+(a.se||[]).length,ms:a.vms||0,ms_src:a.vms?"measured":"missing"},x,false)});
  if(it.A[0].ok){M.first++;S.stage.v1p++}else S.stage.v1f++;if(!it.A[0].ok&&f.ok){S.stage.v2p++;M.repOk++}
  const r=f.r||null,nb=r?(r.nb??0):null;sc.nb=nb;sc.blank=nb!=null&&nb<.005;sc.drawKind=r&&self.kindOf?kindOf(it):"not rendered";
  x=addStep(x,{op:"render",renderer:r?"x_ite@"+(run.meta.xite||"16.5.0")+" (offline, as the file records it)":"none (no renders in the file)",load_ok:r?!r.err:null,nodes:r?(r.nodes??0):null,nonblank_ratio:nb??0,frames_watched:r?(r.frames||0):0,no_frame:r&&r.nf?1:0,ms:r?(r.ms||0):0,ms_src:r?"measured":"none"},x,false);
  if(r&&!sc.blank)S.stage.ren++;if(f.ok){M.valid++;S.stage.ok++}else S.stage.drop++;sc.vref=vref;finish(sc,x,f.ok?"valid":"invalid");return sc}}
async function load(path,btn){if(!files)return null;const name=base(path).replace(/\.json$/,""),mode="files:"+name;if(btn)btn.disabled=true;status(`reading ${rel(path)}…`);
  try{const r=await readAll(path);const text=new TextDecoder().decode(r.bytes);const run=parseRun(text);__desk.revision=r.revision;
    const lanes=[...new Set(run.items.map(it=>it.m+(it.arm?" · "+it.arm:"")))],label=(run.meta.date?String(run.meta.date).slice(5).replace("-"," ").replace(/^(\d\d) (\d\d)$/,(s,a,b)=>`${+b} ${["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"][+a-1]||a}`):name.toUpperCase())+" · files";
    const tmax=()=>Math.max(+run.meta.t_total||0,...run.items.map(i=>+i.T||0));
    MODES.register(mode,{label,gen:genFor(run),tmax,order:()=>run.items.map((_,i)=>i).sort((a,b)=>(run.items[a].T||0)-(run.items[b].T||0)),ready:()=>true,lanes:()=>lanes,meta:()=>run.meta,
      honesty:`from the project's files · ${rel(path)} · revision ${r.revision||"?"} · ${run.items.length} chains · validator ${run.meta.validator||"as recorded per row"} · not rendered offline unless the file carries renders`});
    if(self.FILM&&FILM.register)FILM.register(mode,{chains:()=>self.S&&S.mode===mode?S.scenes.map(s=>s.item).filter(it=>it&&Array.isArray(it.A)):[],lanes:()=>lanes.map((k,i)=>({key:k,model:k.split(" · ")[0],arm:k.split(" · ")[1]||null,prov:null,why:(run.meta.lanes||{})[k]||null,i})),tmax,meta:()=>run.meta,
      stamps:{source:dateStamp(run.meta),validator:VSTAMP[run.meta.validator]||"none"},honesty:()=>MODES.get(mode).honesty,clockNote:"run clock from the file"});
    const rs=$("runseg");if(rs&&!rs.querySelector(`button[data-m="${mode}"]`))rs.appendChild(el("button",{data:{m:mode},text:label,title:rel(path)}));
    __desk.loaded[mode]={path,items:run.items.length,bytes:r.bytes.length,revision:r.revision,lanes};__desk.mode=mode;MODES.set(mode);
    const hl=sec&&sec.querySelector(".hl");if(hl)txt(hl,`read as you, from the project's files, revision ${r.revision||"?"} · verdicts in these files were recorded by the run (validator named per row) · not rendered offline unless a renders file exists for the run`);
    status(`${rel(path)} mounted as ${label}: ${run.items.length} chains, ${lanes.length} lanes, ${fmt.bytes(r.bytes.length)} read in ${__desk.readCalls} chunk${__desk.readCalls===1?"":"s"} · the baked tables above are untouched`);
    if(E.bake){E.bake.hidden=false;txt(E.bake,recipe(path,run,r.revision))}return mode}
  catch(e){__desk.err=e&&(e.code||e.message)||String(e);status(`LOAD failed for ${rel(path)}: ${__desk.err}`);if(btn)btn.disabled=false;return null}}
function recipe(path,run,rev){return`BAKE THIS RUN INTO V4.1 — owner recipe (text only; the page never republishes itself)
1. copy the file from the project: ${path} (revision ${rev||"?"}, ${run.items.length} chains, ${run.meta.date||"date in meta"})
2. python3 demo/v4/build/build_parts.py --run2 <that file>        # part run24 (or the next run's part), HAS_RUN2 true
3. python3 demo/v4/build/claims.py && python3 demo/v4/build_v4.py demo/build/v4 --files-map
4. python3 demo/tests/check_v4.py && python3 demo/tests/check_v4_lane.py
5. publish demo/build/v4/index.html with files.json to the v4 artifact URL (same URL, new version); add the row to BUILD.versions`}
/* ---------- flywheel ---------- */
async function flywheel(){if(!files||!__desk.flywheelDirs.length)return null;E.fly.disabled=true;const dirs=__desk.flywheelDirs,items=[];txt(E.flyNote,"reading flywheel bodies…");
  try{for(const d of dirs){const pick=__desk.entries.find(e=>rel(e.path)===`flywheel/${d}/r1.x3d`)||__desk.entries.find(e=>rel(e.path)===`flywheel/${d}/r0.x3d`);if(!pick)continue;const r=await readAll(pick.path);items.push({id:d,xml:new TextDecoder().decode(r.bytes),file:rel(pick.path)})}
    if(!items.length)throw new Error("no r0/r1 bodies");txt(E.flyNote,`validating ${items.length} bodies on js-port-of-8dd0d3e…`);await VAL.need();if(VAL.mode!=="full")throw new Error("validator not full: "+VAL.reason);
    const res=await VAL.validateMany(items.map(i=>({id:i.id,xml:i.xml})),(i,n)=>txt(E.flyNote,`validating ${i}/${n}…`));let valid=0;const rows=items.map(i=>{const v=res.get(i.id);if(v&&v.valid)valid++;return{id:i.id,file:i.file,valid:!!(v&&v.valid),codes:v?codesOfRes(v):["no result"]}});
    __desk.flywheel={n:items.length,valid,rows};const text=`${valid} of ${items.length} flywheel chains valid on js-port-of-8dd0d3e here · from the project's files`;txt(E.flyNote,text+" · "+rows.map(r=>`${r.id} ${r.valid?"valid":"invalid"}`).join(", "));
    if(self.XLAD&&XLAD.light)XLAD.light("flywheel",text);return __desk.flywheel}
  catch(e){__desk.err=String(e&&(e.code||e.message)||e);txt(E.flyNote,"flywheel re-validation failed: "+__desk.err);E.fly.disabled=false;return null}}
/* ---------- DOM ---------- */
function build(sb){sb.textContent="";const bar=el("div",{class:"deskBar"});sb.appendChild(bar);
  E.connect=el("button",{id:"deskConnect",class:"primary",type:"button",text:"CONNECT",title:"the first files.list runs on this click, never at load"});E.connect.addEventListener("click",connect);bar.appendChild(E.connect);
  bar.appendChild(el("span",{class:"m",text:ROOT}));E.status=el("span",{class:"deskStatus",id:"deskStatus",text:"nothing read yet: CONNECT lists the project's files (consent moment)"});bar.appendChild(E.status);
  const grid=el("div",{class:"deskGrid"});sb.appendChild(grid);E.tree=el("ul",{class:"deskTree",id:"deskTree"});grid.appendChild(E.tree);
  const right=el("div",{class:"deskRight"});grid.appendChild(right);
  const fly=el("div",{class:"card deskFly"});right.appendChild(fly);E.fly=el("button",{id:"deskFly",type:"button",text:"RE-VALIDATE FLYWHEEL CHAINS",disabled:""});E.fly.addEventListener("click",flywheel);fly.appendChild(E.fly);E.flyNote=el("div",{class:"note",id:"deskFlyNote",text:"flywheel/*/chain.json + r0/r1.x3d, re-validated on the port for the S14 strip"});fly.appendChild(E.flyNote);
  right.appendChild(el("div",{class:"note",text:"LOAD mounts a run file as a mode on the mast (waterfall, scope, firehose, matrix, wall, morph replay it); the baked tables never change. JSON, JSONL and X3D only live here (demo/v4/build/mirror_to_project.py)."}));
  E.bake=el("pre",{class:"deskRecipe",id:"deskBake",hidden:""});right.appendChild(E.bake);}
function mount(section){sec=section;const sb=sec.querySelector(".sb");if(!sb)return;
  const start=()=>{files=self.TIER&&TIER.caps.files;if(!files||typeof files.list!=="function"||(typeof BUILD!=="undefined"&&BUILD&&BUILD.share)){sec.remove();return}
    build(sb);if(!TIER.is("owner")&&E.bake)E.bake.remove();};
  if(self.TIER){if(TIER.tier)start();else TIER.on(start)}else sec.remove()}
SECTIONS.register({id:"desk",tier:"member",header:{title:"Members' desk",unit:"the project's files, read as you · a run mounts as a mode without a republish",stamps:{source:"RECORDED 24 Oct",validator:"fork@8dd0d3e recorded",renderer:"none"},grade:"S",
  honesty:"read as you, from the project's files · nothing is read before CONNECT · verdicts in these files were recorded by the run (validator named per row) · not rendered offline unless a renders file exists for the run"},mount});
Object.assign(self,{DESK:{connect,load,flywheel,root:ROOT,mode:()=>__desk.mode}});
})();
