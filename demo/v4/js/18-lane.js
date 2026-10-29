/* 18-lane.js — S5 LIVE TETHER LANE "write one yourself" (SPEC-v4 S5, §4.1–4.6, rules 6 and 9; WORKPLAN 18-lane). Owns #lane .sb.
   The viewer's own Claude (capability `sample`, resolved by 07-tier as TIER.caps.sample; never called at load) writes a scene into the same loop the
   recorded run used: SYS.SYSTEM + the prompt → the body (longest fenced block holding <X3D, else the first <X3D…</X3D>, ≤ 60 KB) → VAL.validate on
   js-port-of-8dd0d3e → STAGE.measure.show (the counted frame) → on INVALID the recorder's exact repair template (repairText) goes back as the next user
   turn; at most 3 sample calls per run (write, repair, repair), one run at a time, no page-side retry from code. The chain is stamped with addStep
   (generate | repair{model, report_shown} + validate{js-port} per attempt, one render step for the final body: comparable step for step with the 358
   recorded chains, which rendered only the final) and lands through SIM.addViewerScene as src "viewer", id V-00n: excluded from every aggregate unless
   S.flags.includeMine (LANE.includeMine). The waterfall draws the run as the lane `you · live` (WF.addViewer/WF.touch), the oscilloscope gets one sample
   per call (SCOPE.add), the firehose row V-00n shows while selected or when include-mine is on, the matrix's viewer column reads sc.promptId.
   The one rule: the lane runs only when VAL.mode === "full"; otherwise the card body is one line and the lane is absent from waterfall and matrix.
   No window.claude / sample null → one line "this viewer did not grant a model to the page". Failure table §4.4 by e.code (fail()). Terminal, verdict and
   every message are written through textContent (reportHtml / DIFF.diffHtml are the two escaped-HTML helpers of 05-val / 14-morph).
   Save (§4.6): LANE.save() → a stored (uncompressed) zip written here (zipStore) with scene.x3d, prov.json, report.txt through TIER.caps.downloads.save;
   a rejected extension falls back to a .json bundle {xml, steps, report}; downloads null → the bundle to the clipboard.
   Globals: LANE {init, preflight, run(promptId, text), stop, retry, reset, includeMine(bool), save, state(), RATE_WAIT_MS}, liveTether, longestX3DBlock, zipStore.
   Test hooks: __lane {calls, state, attempts, steps, sc, err, reason, saved, failedRows, prompts}, #lanePre, #laneGo, #laneStop, #laneTerm, #laneVerdict,
   #laneLamps .lamp[data-l], #laneAtts .att, #laneMsg, #laneSave, #laneRetry, #laneInclude, #lanePick, #laneText.
   v3 port: none (v3 had no live lane; WORKPLAN §A assigns no v3 function here). Stamps: LIVE: your Claude · js-port-of-8dd0d3e here · X_ITE 16.5.0 in this browser. */
(function(){
"use strict";
const MAX_ATTEMPTS=3,MAX_BODY=60*1024,MAX_PROMPT=400,TURN_CAP=256*1024,TRIM_TO=20*1024;
const __lane={calls:0,state:"idle",attempts:[],steps:0,sc:null,err:null,reason:null,saved:null,failedRows:0,prompts:0,limits:null,tier:null};
self.__lane=__lane;
const B=self.LOOP?LOOP.bits:{LANE:128,SCENE:1,CLOCK:32};
const SHARE=!!(typeof BUILD!=="undefined"&&BUILD&&BUILD.share);
const WHO=SHARE?"your assistant":"your own Claude";
const E={};let sec=null,sample=null,ctl=null,running=false,firstCallEver=true,origin=0,row=null,lastV=null,lastReport=null,lastX=null,lastSc=null,waitT0=0,firstText=null,bar=0,panel=null,lanesOff=false;
const OFF_CODES=["not_granted","sampling_disabled","not_declared","capability_disabled","capability_removed"];
const BUG_CODES=["prompt_too_large","invalid_request","transform_error","queue_overflow","invalid_json","images_unavailable","tools_unavailable","image_rejected","session_expired"];
/* ---------- helpers ---------- */
function setState(s){__lane.state=s;if(sec)sec.dataset.state=s;dirty()}
function dirty(){if(self.LOOP)LOOP.dirty(B.LANE)}
function msg(t,tone){if(!E.msg)return;txt(E.msg,t||"");E.msg.dataset.tone=tone||"";E.msg.hidden=!t}
function lamp(name){if(!E.lamps)return;let past=true;E.lamps.querySelectorAll(".lamp").forEach(l=>{const me=l.dataset.l===name;l.classList.toggle("on",me);if(me)past=false;l.classList.toggle("done",past&&!!name)})}
function lampsOff(){if(E.lamps)E.lamps.querySelectorAll(".lamp").forEach(l=>{l.classList.remove("on");l.classList.remove("done")})}
function term(text){if(!E.term)return;E.term.textContent=text||"";E.term.scrollTop=E.term.scrollHeight}
function sha16(s){return sha(s).slice(0,16)}
function rendererStamp(){const gl=self.ENV&&ENV.gl;return gl==="none"||!gl?"none":"X_ITE 16.5.0 in this browser · "+(gl==="gpu"?"gpu":"software")}
function honestyLine(){const tier=__lane.tier||"default",r=(self.ENV&&ENV.renderer)||"renderer unknown";
  return`LIVE · ${WHO} (tier ${tier}; model id not reported) · validated js-port-of-8dd0d3e in this browser · rendered X_ITE 16.5.0 in this browser (${r}) · unsealed chain · not part of any recorded table above · one sample · Suspected as a rate`}
function headerSpec(){return{title:"Live tether lane",unit:"write one yourself · "+WHO+" writes a scene into the same loop",stamps:{source:"LIVE: your Claude",validator:"js-port-of-8dd0d3e here",renderer:rendererStamp()},grade:"S",honesty:honestyLine()}}
/* the body: the longest fenced block containing <X3D; else the first <X3D…</X3D>; cap 60 KB (SPEC §4.2) */
function longestX3DBlock(text){if(!text)return null;let best=null;const re=/```[a-zA-Z0-9_-]*\s*\n([\s\S]*?)```/g;let m;
  while((m=re.exec(text))){const b=m[1].trim();if(b.includes("<X3D")&&(!best||b.length>best.length))best=b}
  if(!best){const i=text.indexOf("<X3D");if(i<0)return null;const j=text.indexOf("</X3D>",i);best=j<0?text.slice(i):text.slice(i,j+6);best=best.trim()}
  if(!best.includes("<X3D"))return null;return best.length>MAX_BODY?{tooLong:true,body:best.slice(0,MAX_BODY),len:best.length}:best}
function turnBytes(turns){let n=0;turns.forEach(t=>{n+=new TextEncoder().encode(t.content||"").length});return n}
/* ---------- prompt picker: 50 recorded prompts grouped by category, each with the recorded lanes' first-try / at-end pills ---------- */
function lanePills(pid){const L=self.LIVE||[];const its=L.filter(i=>i.p===pid);if(!its.length)return"";const f=its.filter(i=>i.A&&i.A[0]&&i.A[0].ok).length,e=its.filter(i=>i.ok).length;return` · ${f}/${its.length} first try · ${e}/${its.length} at end`}
function fillPicker(){if(!E.pick)return;const cur=E.pick.value;E.pick.textContent="";const P=self.PROMPTS||[];__lane.prompts=P.length;const groups=new Map();
  P.forEach(p=>{const c=p.category||"other";if(!groups.has(c))groups.set(c,[]);groups.get(c).push(p)});
  groups.forEach((list,c)=>{const g=el("optgroup",{label:c});list.forEach(p=>g.appendChild(el("option",{value:p.prompt_id,text:p.prompt_id+lanePills(p.prompt_id)})));E.pick.appendChild(g)});
  E.pick.appendChild(el("option",{value:"",text:"free text (≤ 400 chars)"}));if(cur&&[...E.pick.options].some(o=>o.value===cur))E.pick.value=cur;onPick()}
function onPick(){if(!E.text||!E.pick)return;const free=E.pick.value==="";E.text.hidden=!free;E.pshow.hidden=free;if(!free){const p=(self.PROMPTS||[]).find(q=>q.prompt_id===E.pick.value);txt(E.pshow,p?p.prompt:"")}}
function pickedPrompt(){const id=E.pick?E.pick.value:"";if(id){const p=(self.PROMPTS||[]).find(q=>q.prompt_id===id);return{id,text:p?p.prompt:id}}const t=(E.text?E.text.value:"").slice(0,MAX_PROMPT).trim();return{id:null,text:t}}
/* ---------- the loop (SPEC §4.2) ---------- */
async function liveTether(promptId,promptText){
  if(running)return null;if(!sample)throw new Error("sample not granted");running=true;__lane.attempts=[];__lane.err=null;__lane.steps=0;lastX=null;lastV=null;lastReport=null;lastSc=null;
  if(E.atts)E.atts.textContent="";if(E.verdict)E.verdict.textContent="";msg("");setState("running");if(E.go)E.go.disabled=true;if(E.stop)E.stop.disabled=false;if(E.save)E.save.disabled=true;if(E.retry)E.retry.hidden=true;
  const turns=[{role:"user",content:SYS.SYSTEM+"\n\nPROMPT: "+promptText}];
  let x=null,t0=performance.now(),trimmed=false,aborted=false,note=null,finishHow="stop",nb=null,measured=null;
  const t0rel=()=>(performance.now()-origin)/1000;
  for(let k=0;k<MAX_ATTEMPTS;k++){
    ctl=new AbortController();lamp("WRITE");firstText=null;waitT0=performance.now();bar=0;t0=performance.now();
    row=WF_add({k,n:k+1,t0:t0rel(),inflight:true,ok:false,p:promptId||"viewer-text"});
    let r;__lane.calls++;
    try{r=await sample(turns,{signal:ctl.signal,modelTier:"default",cache:false,onText:u=>{if(!u||typeof u.text!=="string")return;if(firstText==null)firstText=performance.now()-t0;term(u.text);bar=Math.min(1,bar+.02);dirty()}})}
    catch(e){const out=fail(k,e,x);running=false;return out}
    firstCallEver=false;
    const ms=Math.round(performance.now()-t0),tft=firstText==null?null:Math.round(firstText);__lane.tier=r&&r.modelTierApplied||"default";
    const text=r&&typeof r.text==="string"?r.text:"";term(text);
    const got=longestX3DBlock(text);let body=got&&got.body!==undefined?got.body:got;const tooLong=!!(got&&got.tooLong);finishHow=r&&r.truncated?"length":tooLong?"length":"stop";
    const att={k,ms,tft,chars:body?body.length:0,truncated:!!(r&&r.truncated),tooLong,hash:body?contentHash(body).slice(0,16):null,verdict:null,nb:null,text};__lane.attempts.push(att);
    const gen={op:k===0?"generate":"repair",model:"claude (viewer)",model_tier:__lane.tier,provider:"artifact sample",prompt_id:promptId||"viewer-text",prompt_sha256:sha16(promptText),tokens_in:null,tokens_out:null,tokens_src:"not reported by the sample capability",chars:body?body.length:0,latency_ms:ms,tft_ms:tft,ms_src:"measured",cost_usd_est:null,finish:finishHow};
    if(k===0)gen.condition="oneshot";else Object.assign(gen,{kind:"model",round:k,report_shown:true,report_sha256:sha16(lastReport||""),fixes:codesOfRes(lastV)});if(trimmed){gen.turn_trimmed=true;trimmed=false}
    if(!body){msg("no X3D document in the answer","bad");const carrier=x||"<X3D version='4.0' profile='Interchange'><Scene/></X3D>";x=addStep(carrier,gen,carrier,false);
      x=addStep(x,{op:"validate",validator:"js-port",validator_ref:"js-port-of-8dd0d3e",verdict:"invalid",codes:["no-x3d-document"],n_errors:1,ms:0,ms_src:"none"},x,false);att.verdict="no-x3d-document";
      attCard(att,null,null);rowDone(false,ms,null);__lane.failedRows++;break}
    x=addStep(k===0?body:x,gen,body,false);
    lamp("VALIDATE");let v;try{v=await VAL.validate(body)}catch(e){note="validator error: "+String(e&&e.message||e).slice(0,160);msg("validator error · treated as unavailable for this attempt, never as a verdict","bad");att.verdict="validator error";attCard(att,null,null);rowDone(false,ms,null);break}
    lastV=v;att.verdict=v.valid?"valid":"invalid";att.vms=v.ms;
    x=addStep(x,{op:"validate",validator:"js-port",validator_ref:"js-port-of-8dd0d3e",verdict:v.valid?"valid":"invalid",codes:codesOfRes(v),xsd_valid:!!(v.xsd&&v.xsd.valid),n_errors:((v.xsd&&v.xsd.errors)||[]).length+((v.semantic&&v.semantic.errors)||[]).length,ms:v.ms||0,ms_src:"measured"},x,false);
    verdictCard(v);rowDone(!!v.valid,ms,v.ms||0);if(self.SCOPE&&SCOPE.add)SCOPE.add({ms,vms:v.ms||0,ok:!!v.valid,lane:"you"});
    lamp("RENDER");let px=null;try{px=await STAGE.measure.show(body,{timeoutMs:12000})}catch(e){px={err:String(e&&e.message||e),nb:null,frames:0,series:[],msgs:[],noFrame:true,ms:0}}
    if(px&&px.noFrame&&!px.err)msg("NO FRAME YET · X_ITE drew nothing in 12 s","warn");
    att.nb=px?px.nb:null;att.noFrame=!!(px&&px.noFrame);att.renderErr=px&&px.err||null;measured=px;nb=px?px.nb:null;
    attCard(att,v,px);if(self.RASTER&&RASTER.live)try{RASTER.live("you/"+(promptId||"viewer-text"),px,"live lane")}catch(e){}
    if(v.valid){if(self.STAGE&&STAGE.show&&STAGE.show.ok&&STAGE.show.load)STAGE.show.load(body,{scene:"lane"}).catch(()=>{});break}
    if(k===MAX_ATTEMPTS-1)break;
    lamp("REPORT SHOWN");lastReport=repairText(v);turns.push({role:"assistant",content:text},{role:"user",content:lastReport});
    const cap=Math.min(TURN_CAP,(__lane.limits&&__lane.limits.maxPromptBytes)||TURN_CAP);
    while(turnBytes(turns)>cap){const a=turns.find(t=>t.role==="assistant"&&t.content.length>TRIM_TO);if(!a)break;a.content=a.content.slice(0,TRIM_TO);trimmed=true}
  }
  if(x){const px=measured||{};x=addStep(x,{op:"render",renderer:"x_ite@16.5.0 in this browser · "+((self.ENV&&ENV.renderer)||"renderer unknown"),gpu:(self.ENV&&ENV.gl)||"unknown",load_ok:!px.err,nonblank_ratio:px.nb??0,frames_watched:px.frames??0,no_frame:px.noFrame?1:0,slow:!!px.noFrame,parser_msgs:(px.msgs||[]).slice(0,4),ms:px.ms||0,ms_src:"measured",...(note?{note}:{})},x,false);
    finishLive(x,{verdict:lastV&&lastV.valid?"valid":"invalid",nb,note,finish:finishHow,aborted})}
  running=false;lamp("");setState(x?"done":"error");if(E.go)E.go.disabled=false;if(E.stop)E.stop.disabled=true;return lastSc}
/* ---------- §4.4 failure table ---------- */
function fail(k,e,x){const code=e&&e.code||"upstream_error";__lane.err={code,message:String(e&&e.message||e).slice(0,200),k};const keep=e&&typeof e.text==="string"?e.text:null;
  if(code==="cancelled"){lampsOff();if(keep!=null)term(keep);rowDone(false,null,null,"stopped by viewer");msg("stopped by viewer","mute");if(x)finishLive(x,{verdict:"aborted",aborted:true,finish:"aborted"});setState("stopped");enable();return lastSc}
  if(OFF_CODES.includes(code)){collapse("live lane off (not allowed in this view) — the recorded run is unaffected");if(self.WF&&WF.clearViewer)WF.clearViewer();lanesOff=true;setState("off");return null}
  if(code==="rate_limited"){lampsOff();rowDone(false,null,null,"rate limited");msg("your Claude is busy or at its limit; try again later","warn");if(sec)sec.dataset.bar="amber";if(x)finishLive(x,{verdict:"partial",finish:"rate_limited"});setState("rate_limited");
    if(E.go)E.go.disabled=true;later(()=>{if(E.go)E.go.disabled=false;if(sec)sec.dataset.bar="";if(__lane.state==="rate_limited")setState("idle")},LANE.RATE_WAIT_MS);if(E.stop)E.stop.disabled=true;return null}
  if(code==="refused"){lampsOff();term("");rowDone(false,null,null,"declined");msg("declined for this prompt; pick another","warn");setState("idle");enable();return null}
  if(code==="empty_completion"){lampsOff();rowDone(false,null,null,"empty");msg("no text came back; pick another prompt","warn");setState("idle");enable();return null}
  if(BUG_CODES.includes(code)){lampsOff();rowDone(false,null,null,code);msg(`lane error (${code})`,"bad");console.warn("lane error",code,e&&e.message);setState("idle");enable();return null}
  /* upstream_error and anything unknown (the contract maps unknown codes to upstream_error) */
  lampsOff();if(keep!=null)term(keep);if(E.termTag){txt(E.termTag,"INTERRUPTED");E.termTag.hidden=false}rowDone(false,null,null,"failed",true);__lane.failedRows++;msg("the call was interrupted upstream · one manual Retry, never automatic","bad");
  if(E.retry)E.retry.hidden=false;setState("interrupted");enable();return null}
function enable(){if(E.go)E.go.disabled=false;if(E.stop)E.stop.disabled=true;running=false}
function collapse(line){if(!E.body)return;E.body.textContent="";E.body.appendChild(el("div",{class:"laneOne note",text:line}));if(sec){const hl=sec.querySelector(".hl");if(hl)txt(hl,line)}}
/* ---------- waterfall row (22-waterfall WF.addViewer) ---------- */
function WF_add(r){if(!self.WF||!WF.addViewer)return null;if(!origin)origin=performance.now();return WF.addViewer(r)}
function rowDone(ok,ms,vms,label,failed){if(!row)return;row.inflight=false;row.t1=(performance.now()-origin)/1000;row.ok=!!ok;if(ms!=null)row.ms=ms;row.vms=vms;if(label)row.label=label;if(failed)row.failed=true;if(self.WF&&WF.touch)WF.touch()}
/* ---------- cards ---------- */
function verdictCard(v){if(!E.verdict)return;E.verdict.textContent="";const head=el("div",{class:"row"},[el("span",{class:"pill "+(v.valid?"p-ok":"p-bad"),text:v.valid?"VALID":"INVALID"}),el("span",{class:"m",text:`on js-port-of-8dd0d3e in ${fmt.ms(v.ms||0)}`})]);
  E.verdict.appendChild(head);const rep=el("div",{class:"rep"});rep.innerHTML=reportHtml(v);E.verdict.appendChild(rep)}
function attCard(att,v,px){if(!E.atts)return;const c=el("div",{class:"att card you",data:{k:att.k+1}});
  const parts=[`ATTEMPT ${att.k+1}`,`${WHO} (tier ${__lane.tier||"default"})`,`${(att.ms/1000).toFixed(1)} s${att.tft!=null?` (first text ${(att.tft/1000).toFixed(1)} s)`:""}`,`${fmt.int(att.chars)} chars`,att.hash?`hash ${att.hash}…`:"no body"];
  c.appendChild(el("div",{class:"attHead m",text:parts.join(" · ")}));
  const tags=el("div",{class:"row"});if(att.truncated||att.tooLong)tags.appendChild(el("span",{class:"pill p-warn",text:att.tooLong?"TOO LONG FOR THE LANE":"CUT AT THE OUTPUT LIMIT"}));
  tags.appendChild(el("span",{class:"pill "+(att.verdict==="valid"?"p-ok":att.verdict==="invalid"?"p-bad":"p-mute"),text:(att.verdict||"no verdict").toUpperCase()}));
  if(px)tags.appendChild(el("span",{class:"pill "+(px.err?"p-bad":px.noFrame?"p-warn":(px.nb||0)>=.005?"p-ok":"p-warn"),text:px.err?"X_ITE REFUSED":px.noFrame?"NO FRAME YET":`measured ${fmt.pct(px.nb||0)} · ${px.frames||0} frames`}));
  c.appendChild(tags);
  if(px&&!px.err&&!px.noFrame&&self.STAGE&&STAGE.measure&&STAGE.measure.canvas){const cv=el("canvas",{class:"attShot",width:192,height:144,title:"the measured 192×144 frame, copied after the measure (numbers come from STAGE.measure, never from this copy)"});
    try{cv.getContext("2d").drawImage(STAGE.measure.canvas,0,0,192,144)}catch(e){}c.appendChild(el("div",{class:"th"},cv))}
  if(v){const rep=el("div",{class:"rep attRep"});rep.innerHTML=reportHtml(v);c.appendChild(rep)}
  const prev=__lane.attempts[att.k-1];if(prev&&self.DIFF&&DIFF.diffHtml&&att.text&&prev.text){const a=longestX3DBlock(prev.text),b=longestX3DBlock(att.text);const sa=a&&a.body||a,sb=b&&b.body||b;
    if(sa&&sb){const d=el("div",{class:"attDiff m"});try{d.innerHTML=DIFF.diffHtml(sa,sb)}catch(e){d.textContent="diff unavailable"}c.appendChild(el("details",{},[el("summary",{text:`diff vs attempt ${att.k}`}),d]))}}
  E.atts.appendChild(c)}
/* ---------- the scene enters the world ---------- */
function finishLive(x,o){o=o||{};if(!x||!self.SIM||!SIM.addViewerScene)return null;const n=__lane.attempts.length;const nb=o.nb;
  const sc={src:"viewer",item:null,promptId:(__lane.attempts[0]&&__lane.attempts[0].pid)||lastPromptId,model:"claude (viewer)",mode:n>1?"repair x"+(n-1):"oneshot",verdict:o.verdict||"invalid",xml:x,nb:nb==null?null:nb,blank:nb!=null&&nb<.005,drawKind:nb==null?"not measured":nb>=.005?"draws":"blank frame",port:lastV,vref:"js-port-of-8dd0d3e",sealed:false,nsteps:0,note:o.note||null,tier:__lane.tier,finish:o.finish||"stop",label:"live lane"};
  const out=SIM.addViewerScene(sc);lastSc=out;__lane.sc=out.id;__lane.steps=readSteps(out.xml).length;if(row){row.id=out.id;if(self.WF&&WF.touch)WF.touch()}
  if(SIM.select)SIM.select(out.id);if(E.save)E.save.disabled=false;if(E.stampNote)txt(E.stampNote,`${out.id} · ${__lane.steps} steps · head ${contentHash(out.xml).slice(0,16)}… · unsealed · src viewer · excluded from every aggregate${self.S&&S.flags.includeMine?" unless include my runs (on)":" (include my runs is off)"}`);
  return out}
let lastPromptId=null;
/* ---------- save (§4.6): stored zip, .json fallback, clipboard fallback ---------- */
const CRC=(()=>{const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c>>>0}return t})();
function crc32(b){let c=0xFFFFFFFF;for(let i=0;i<b.length;i++)c=CRC[(c^b[i])&255]^(c>>>8);return(c^0xFFFFFFFF)>>>0}
function zipStore(files){const enc=new TextEncoder(),locals=[],centrals=[];let off=0;
  const u16=(v)=>[v&255,(v>>>8)&255],u32=(v)=>[v&255,(v>>>8)&255,(v>>>16)&255,(v>>>24)&255];
  files.forEach(f=>{const name=enc.encode(f.name),data=f.bytes instanceof Uint8Array?f.bytes:enc.encode(String(f.bytes)),crc=crc32(data);
    const head=new Uint8Array([0x50,0x4b,3,4,20,0,0,0,0,0,0,0,0,0,...u32(crc),...u32(data.length),...u32(data.length),...u16(name.length),0,0]);
    locals.push(head,name,data);
    centrals.push(new Uint8Array([0x50,0x4b,1,2,20,0,20,0,0,0,0,0,0,0,0,0,...u32(crc),...u32(data.length),...u32(data.length),...u16(name.length),0,0,0,0,0,0,0,0,0,0,0,0,...u32(off)]),name);
    off+=head.length+name.length+data.length});
  const cdSize=centrals.reduce((a,b)=>a+b.length,0),end=new Uint8Array([0x50,0x4b,5,6,0,0,0,0,...u16(files.length),...u16(files.length),...u32(cdSize),...u32(off),0,0]);
  const all=locals.concat(centrals,[end]),out=new Uint8Array(all.reduce((a,b)=>a+b.length,0));let p=0;all.forEach(a=>{out.set(a,p);p+=a.length});return out}
async function save(){const sc=lastSc;if(!sc)return null;const steps=readSteps(sc.xml).map(([n,c])=>({n,rec:JSON.parse(c)})),report=lastV?repairText(lastV):"no report",h8=contentHash(sc.xml).slice(0,8),pid=sc.promptId||"viewer-text";
  const bundle=JSON.stringify({id:sc.id,xml:sc.xml,steps,report,validator:"js-port-of-8dd0d3e",renderer:"X_ITE 16.5.0 in this browser"},null,1);
  const dl=self.TIER&&TIER.caps&&TIER.caps.downloads;let out;
  if(dl&&typeof dl.save==="function"){const zip=zipStore([{name:"scene.x3d",bytes:sc.xml},{name:"prov.json",bytes:JSON.stringify(provJson(sc,readSteps(sc.xml)),null,1)},{name:"report.txt",bytes:report}]);
    try{const r=await dl.save({filename:`tether-lane-${pid}-${h8}.zip`,data:zip});out={how:"zip",filename:`tether-lane-${pid}-${h8}.zip`,status:r&&r.status,bytes:zip.length}}
    catch(e){try{const r=await dl.save({filename:`tether-lane-${pid}-${h8}.json`,data:bundle});out={how:"json",filename:`tether-lane-${pid}-${h8}.json`,status:r&&r.status,zipError:e&&e.code}}catch(e2){out={how:"failed",error:e2&&e2.code||String(e2)}}}}
  else{try{await navigator.clipboard.writeText(bundle);out={how:"clipboard",bytes:bundle.length}}catch(e){out={how:"failed",error:String(e&&e.message||e)}}}
  __lane.saved=out;if(E.saveNote)txt(E.saveNote,out.how==="zip"?`saved ${out.filename} (stored zip: scene.x3d, prov.json, report.txt)`:out.how==="json"?`zip refused (${out.zipError}); saved ${out.filename} as a .json bundle`:out.how==="clipboard"?"downloads not granted in this view: the .json bundle is on your clipboard":"save failed: "+out.error);return out}
/* ---------- run / gates ---------- */
async function run(promptId,promptText){if(running||lanesOff)return null;
  if(promptId===undefined){const p=pickedPrompt();promptId=p.id;promptText=p.text}if(!promptText){msg("type a prompt or pick a recorded one","warn");return null}
  lastPromptId=promptId||null;sample=self.TIER&&TIER.caps.sample;if(!sample){collapse("this viewer did not grant a model to the page");return null}
  setState("preparing");if(E.go)E.go.disabled=true;msg(firstCallEver?"waiting for your permission…":"preparing…","mute");
  if(self.VAL){try{if(VAL.mode==="unloaded")await VAL.need();else await VAL.ready}catch(e){}}
  if(!self.VAL||VAL.mode!=="full"){offLine();return null}
  if(self.STAGE&&STAGE.measure&&STAGE.measure.ready)await Promise.race([STAGE.measure.ready,later(15000)]);
  if(!self.STAGE||!STAGE.measure||!STAGE.measure.browser){collapse("live lane off: X_ITE is not running in this viewer — the counted frame cannot be measured");setState("off");return null}
  if(!__lane.limits&&typeof sample.limits==="function"){try{__lane.limits=await sample.limits()}catch(e){__lane.limits=null}}
  msg("");return liveTether(promptId,promptText)}
function offLine(){const why=(self.VAL&&VAL.reason)||"validator not available";collapse(`live lane off: the exact validator cannot run in this viewer (${why}) — a loop without it would not be a tether`);__lane.reason=why;lanesOff=true;if(self.WF&&WF.clearViewer)WF.clearViewer();setState("off")}
function stop(){if(ctl)ctl.abort()}
function retry(){if(running)return null;if(E.retry)E.retry.hidden=true;if(E.termTag)E.termTag.hidden=true;return run()}
function reset(){if(running)return;lastSc=null;lastV=null;__lane.attempts=[];if(E.atts)E.atts.textContent="";if(E.verdict)E.verdict.textContent="";term("");msg("");lampsOff();if(E.termTag)E.termTag.hidden=true;if(E.retry)E.retry.hidden=true;setState("idle");enable()}
function includeMine(b){if(!self.S)return false;S.flags.includeMine=!!b;if(E.include)E.include.checked=!!b;if(self.SIM&&SIM.emit)SIM.emit("flags",S.flags);if(self.LOOP)LOOP.dirtyAll();return S.flags.includeMine}
/* ---------- DOM ---------- */
function build(sb){sb.textContent="";E.body=sb;const grid=el("div",{class:"laneGrid"});sb.appendChild(grid);
  const left=el("div",{class:"laneLeft"}),right=el("div",{class:"laneRight"});grid.appendChild(left);grid.appendChild(right);
  /* right: pre-flight card, picker, buttons */
  E.pre=el("div",{class:"card you lanePre",id:"lanePre"});right.appendChild(E.pre);
  E.pre.appendChild(el("div",{class:"laneCardTitle",text:"PRE-FLIGHT"}));
  E.pre.appendChild(el("p",{class:"note",text:`Runs on your own Claude usage: 1 to 3 calls, usually 5 to 60 s to the first text each. Sent: one prompt (recorded or yours) and, on repair, the validator's report. Not sent: project files, recorded data, anything else. Nothing is stored unless you press Save.`}));
  E.valNote=el("div",{class:"m laneValNote",id:"laneValNote"});E.pre.appendChild(E.valNote);
  E.pick=el("select",{id:"lanePick","aria-label":"recorded prompt"});E.pick.addEventListener("change",onPick);E.pre.appendChild(E.pick);
  E.pshow=el("div",{class:"note lanePshow",id:"lanePshow"});E.pre.appendChild(E.pshow);
  E.text=el("textarea",{id:"laneText",maxlength:String(MAX_PROMPT),rows:"3",placeholder:"your prompt, ≤ 400 chars",hidden:""});E.pre.appendChild(E.text);
  const btns=el("div",{class:"row laneBtns"});E.pre.appendChild(btns);
  E.go=el("button",{id:"laneGo",class:"primary",text:"WRITE IT LIVE",type:"button"});E.go.addEventListener("click",()=>run());btns.appendChild(E.go);
  E.notNow=el("button",{id:"laneNotNow",text:"not now",type:"button"});E.notNow.addEventListener("click",()=>{setState("idle");msg("the recorded run is unaffected","mute")});btns.appendChild(E.notNow);
  E.stop=el("button",{id:"laneStop",class:"bad",text:"Stop",type:"button",disabled:""});E.stop.addEventListener("click",stop);btns.appendChild(E.stop);
  E.retry=el("button",{id:"laneRetry",class:"warn",text:"Retry",type:"button",hidden:""});E.retry.addEventListener("click",retry);btns.appendChild(E.retry);
  E.msg=el("div",{class:"laneMsg m",id:"laneMsg",hidden:""});E.pre.appendChild(E.msg);
  const inc=el("label",{class:"laneInc m"});E.include=el("input",{type:"checkbox",id:"laneInclude"});E.include.addEventListener("change",()=>includeMine(E.include.checked));inc.appendChild(E.include);inc.appendChild(document.createTextNode(" include my runs in the tiles (+ your N)"));right.appendChild(inc);
  const sv=el("div",{class:"card laneSaveCard"});right.appendChild(sv);E.save=el("button",{id:"laneSave",text:"Save stamped scene",type:"button",disabled:""});E.save.addEventListener("click",save);sv.appendChild(E.save);
  E.saveNote=el("div",{class:"note",id:"laneSaveNote",text:SHARE?"a stored zip (scene.x3d, prov.json, report.txt); nothing is written to project files":"zip through the downloads capability when granted; .json fallback; clipboard when downloads is null"});sv.appendChild(E.saveNote);
  E.stampNote=el("div",{class:"m laneStamp",id:"laneStampNote"});sv.appendChild(E.stampNote);
  if(!SHARE)right.appendChild(el("div",{class:"note",text:"Playground boundary: one prompt box, no defect injector, no judge here."}));
  /* left: lamps, terminal, verdict, attempts */
  E.lamps=el("div",{class:"laneLamps",id:"laneLamps"});["WRITE","VALIDATE","REPORT SHOWN","REPAIR","RENDER"].forEach(n=>E.lamps.appendChild(el("span",{class:"lamp",data:{l:n},text:n})));left.appendChild(E.lamps);
  const th=el("div",{class:"row laneTermHead m"});E.wait=el("span",{id:"laneWait",text:"idle"});E.termTag=el("span",{class:"pill p-bad",id:"laneTermTag",hidden:""});th.appendChild(E.wait);th.appendChild(E.termTag);left.appendChild(th);
  E.bar=el("div",{class:"laneBar"},el("i"));left.appendChild(E.bar);
  E.term=el("pre",{class:"laneTerm",id:"laneTerm","aria-live":"polite"});left.appendChild(E.term);
  E.verdict=el("div",{class:"laneVerdict",id:"laneVerdict"});left.appendChild(E.verdict);
  E.atts=el("div",{class:"laneAtts",id:"laneAtts"});left.appendChild(E.atts);
  fillPicker();if(self.DATA)DATA.on("live.core",fillPicker)}
function valNote(){if(!E.valNote||!self.VAL)return;const m=VAL.mode;txt(E.valNote,m==="full"?"validator ready: js-port-of-8dd0d3e in this browser":m==="unloaded"?"validator loads on first use (js-port-of-8dd0d3e)":"validator: "+(VAL.reason||m));if(m==="none"||m==="semantic-only")offLine()}
function mount(section){sec=section;const sb=sec.querySelector(".sb");if(!sb)return;E.body=sb;
  const start=()=>{if(!self.claude||!self.TIER||!TIER.caps.sample){collapse("this viewer did not grant a model to the page");setState("nocap");return}
    build(sb);setState("preflight");valNote();if(self.VAL&&VAL.on)VAL.on(valNote);
    IO.observe(sec,v=>{if(v&&self.VAL&&VAL.mode==="unloaded"&&self.FX&&FX.level>0)VAL.need()},{rootMargin:"600px"})};
  if(self.TIER){if(TIER.tier)start();else TIER.on(()=>{if(__lane.state==="idle")start()})}else start();
  if(self.ENV&&ENV.onChange){let stamped=false;ENV.onChange(()=>{if(stamped||!ENV.gl)return;stamped=true;sectionHeader(sec,headerSpec())})}
  /* a mode switch starts a fresh S (20-sim fresh): the lane's rows belong to the view they ran in, so the waterfall's viewer lane is cleared with it */
  if(self.SIM&&SIM.on)SIM.on("mode",()=>{if(running)return;if(self.WF&&WF.clearViewer)WF.clearViewer();row=null;origin=0;lastSc=null;if(E.save)E.save.disabled=true});
  panel=LOOP.register({name:"lane",bit:B.LANE|B.CLOCK,rateHz:10,draw(){if(!E.wait)return;const busy=running;panel.always=busy;
    if(busy&&__lane.state==="running"){const el_=(performance.now()-waitT0)/1000;txt(E.wait,firstText==null?(firstCallEver?"waiting for your permission…":`waiting ${el_.toFixed(1)} s`):`first text ${(firstText/1000).toFixed(1)} s · ${el_.toFixed(1)} s elapsed`);if(E.bar)E.bar.firstElementChild.style.width=Math.round(bar*100)+"%"}
    else if(!busy&&E.wait.textContent!=="idle"&&__lane.state!=="running"){txt(E.wait,__lane.state);if(E.bar)E.bar.firstElementChild.style.width="0%"}}})}
SECTIONS.register({id:"lane",header:headerSpec(),mount});
const LANE={init:()=>!!sec,preflight(){if(!E.pre)return false;setState("preflight");E.pre.scrollIntoView({block:"nearest"});return true},run,stop,retry,reset,includeMine,save,liveTether,longestX3DBlock,zipStore,state:()=>__lane.state,RATE_WAIT_MS:30000,finishLive};
Object.assign(self,{LANE,liveTether,longestX3DBlock,zipStore});
})();
