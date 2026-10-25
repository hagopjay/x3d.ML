/* 32-inspector.js — S9 inspector (SPEC S9, rules 4, 10, 11). Globals: INSPECTOR, renderInspector, insCtl, setTab, tab (window getter, the v3 hook).
   Ported from v3 demo/tether-firehose-v3.template.html: OPCOL, stepDesc, realExtra, tabChain (574–592), tabTrace (593–601), tagLines/LCSdiff/diffHtml
   (603–616; local copies, the diff worker of 14-morph is not a dependency here), tabTether (621–633), tabVerify (634–638), show3d's reading of a measured frame
   and the #v3msg / #v3none vocabulary (651–672), renderInspector + insSig (674–694), inject (475–484: local fallback used only when 36-wall's global is absent),
   setTab / insBody / insCtl handlers (901–904).
   Changes: 11 tabs Chain · Report · Trace · Verify · Tether · Stage · Receipt · Head XML · PROV · OpenLineage · OTLP; Trace uses 04-prov spansOf (real run_s,
   nothing modeled: dashed spans never appear here); Verify re-hashes the head through HASH (worker) and prints the page-normalised hash on every row, saying
   plainly that no repo C14N hash is stamped on these scenes; Stage loads the body on the hero stage (STAGE.show.load) and measures it in the hidden canvas
   (STAGE.measure.show), no second X_ITE; Report = every attempt's full report with line links into the Bench and the agrees | differs chip from the js-port
   (VAL.compare; "not loaded" said honestly); Receipt = the scene's claim rows (value, source field, stamp, grade, RE-RUN). Event rows selected in the firehose
   (ids F-nnn / C-nnn) show the ledger row. When nothing is pinned the inspector previews the newest scene (no select emitted; switches at most every 3 s).
   One LOOP panel "inspector" (SELECT|VERIFY|SCENE|MODE|VAL|DATA|THEME, 4 Hz); innerHTML only when the signature changes, never on a timer.
   Test hooks: #insSub, #insBody, #tabs button[data-t] (11), #v3msg, #v3none, #insCtl button[data-t], renderInspector(force | id | sc), INSPECTOR.{tab,target(),
   renders,measureMemo,portMemo,stageShow}, window.tab, __panels.inspector.renders. */
(function(){
"use strict";
const TABS=[["chain","Chain"],["report","Report"],["trace","Trace"],["verify","Verify"],["tether","Tether"],["stage","Stage"],["receipt","Receipt"],["xml","Head XML"],["prov","PROV"],["ol","OpenLineage"],["otlp","OTLP"]];
const CH={verified:["p-ok","VERIFIED"],stale:["p-warn","STALE"],broken:["p-bad","BROKEN"],"seal-fail":["p-bad","SEAL FAIL"],"no-record":["p-mute","NO RECORD"],"?":["p-mute","?"]};
const OPCOL={generate:"p-info",validate:"p-ok",repair:"p-warn",render:"p-mute",transform:"p-info",ingest:"p-mute",measure:"p-acc",judge:"p-ok",summary:"p-mute"};
const DRAWTXT={"unparseable":"X_ITE could not parse the file","nothing drawable":"X_ITE accepted the file, dropped what it could not read and was left with nothing to draw: a few blank frames, then idle","blank frame":"frames were drawn but under 0.5% of pixels ever differ from the background","draws":"draws"};
const LABEL={edit:"coordinate edit",del:"step deletion",flipmid:"interior verdict flip",fliplast:"last-step verdict flip"};
const disp=m=>String(m==null?"":m);
const money=v=>v==null?"—":fmt.usd(+v);
const pct=x=>x==null?"—":(x*100).toFixed(1)+"%";
const cur={tab:"chain",sig:"",renders:0,preview:null,previewAt:0,v3Token:0,user:false,ledger:null};
const measureMemo=new Map(),portMemo=new Map(),rehashMemo=new Map();
let body,sub,tabsEl,ctl,view3d,v3msg,v3none,v3img,v3frame,pinBtn,section;
/* ---------- diff (one tag per line; local copy of v3 603–616) ---------- */
const tagLines=x=>x.replace(/\r/g,"").replace(/>\s*</g,">\n<").split("\n");
function LCSdiff(a,b){const n=a.length,m=b.length,w=m+1;if(n*w>4e6){return a.map(l=>["-",l]).concat(b.map(l=>["+",l]))}const t=new Uint16Array((n+1)*w);
  for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)t[i*w+j]=a[i]===b[j]?t[(i+1)*w+j+1]+1:Math.max(t[(i+1)*w+j],t[i*w+j+1]);
  const o=[];let i=0,j=0;while(i<n&&j<m){if(a[i]===b[j]){o.push([" ",a[i]]);i++;j++}else if(t[(i+1)*w+j]>=t[i*w+j+1])o.push(["-",a[i++]]);else o.push(["+",b[j++]])}
  while(i<n)o.push(["-",a[i++]]);while(j<m)o.push(["+",b[j++]]);return o}
function diffHtml(a,b){const d=LCSdiff(tagLines(a),tagLines(b)),keep=new Array(d.length).fill(false),add=d.filter(r=>r[0]==="+").length,del=d.filter(r=>r[0]==="-").length;
  d.forEach((r,i)=>{if(r[0]!==" ")for(let k=Math.max(0,i-2);k<=Math.min(d.length-1,i+2);k++)keep[k]=true});
  const o=[];let gap=false,shown=0,seen=0;
  for(let i=0;i<d.length;i++){if(!keep[i]){gap=true;continue}
    if(shown>=100){o.push(`<span class="g">… ${add+del-seen} more changed lines not shown</span>`);break}
    if(gap&&o.length)o.push('<span class="g">  …</span>');gap=false;shown++;if(d[i][0]!==" ")seen++;
    o.push(`<span class="${d[i][0]==="+"?"a":d[i][0]==="-"?"d":"c"}">${d[i][0]} ${esc(d[i][1].slice(0,220))}</span>`)}
  return{html:o.join("\n"),add,del,base:tagLines(a).length}}
const fmtRep=l=>esc(String(l).replace(/^-\s*/,"").slice(0,300)).replace(/\*\*\[([\w-]+)\]\*\*/g,(m,c)=>"<b>"+c+"</b>");
const lineLink=(l,k)=>String(l).replace(/^Line (\d+):/,(m,n)=>`<a data-bench="${n}" data-att="${k}" title="open attempt ${k+1} in the Bench at line ${n}">Line ${n}</a>:`);
/* ---------- target: the pinned scene or event, else a preview of the newest scene ---------- */
function target(){if(!self.S)return{};
  if(cur.ledger&&!S.sel)return{ev:cur.ledger,pinned:true};
  if(S.sel){const sc=S.byId.get(S.sel);if(sc)return{sc,pinned:true};const ev=self.FH&&FH.eventOf(S.sel);if(ev)return{ev,pinned:true}}
  if(cur.preview&&!S.byId.has(cur.preview.id))cur.preview=null;
  const now=performance.now(),n=S.scenes[S.scenes.length-1];
  if(n&&(!cur.preview||(cur.preview!==n&&now-cur.previewAt>3000))){cur.preview=n;cur.previewAt=now}
  return cur.preview?{sc:cur.preview,pinned:false}:{}}
/* ---------- Chain ---------- */
function stepDesc(r){
  if(r.op==="generate")return`<em>${esc(disp(r.model))}</em> ${esc(r.condition||"")} · ${fmt.int(r.tokens_in)}→${fmt.int(r.tokens_out)} tok · ${fmt.int(r.latency_ms)} ms · ${r.cost_usd_est!==undefined?money(r.cost_usd_est)+" list price":r.cost_apportioned_usd!==undefined?money(r.cost_apportioned_usd)+" apportioned":"—"}${r.attempts_total>1?` · ${r.attempts_total} attempts`:""}${r.finish?` · finish ${esc(r.finish)}`:""} · prompt ${esc(String(r.prompt_sha256||""))}`;
  if(r.op==="validate")return`<em>${esc(r.validator||"")}</em> <i>@</i> ${esc(r.validator_ref||"")} → <b class="${r.verdict==="valid"?"okc":"badc"}">${esc(r.verdict||"")}</b>${r.codes&&r.codes.length?" · "+esc(r.codes.join(", ")):""}${r.finding?` · <i>${esc(String(r.finding).slice(0,120))}</i>`:""}${r.ms!=null?` · ${fmt.ms(r.ms)} <i>${esc(r.ms_src||"")}</i>`:""}${r.recorded?" · <i>recorded 11 Oct</i>":""}`;
  if(r.op==="repair")return`<em>${esc(disp(r.agent||r.model))}</em> round ${r.round} · ${r.kind==="deterministic"?"deterministic fix":"report shown"} · fixes ${esc((r.fixes||[]).join(", ")||"none named")}${r.cost_usd_est!==undefined?" · "+money(r.cost_usd_est):""}${r.report_sha256?` · report ${esc(String(r.report_sha256).slice(0,12))}`:""}`;
  if(r.op==="render")return`${esc(r.renderer||"")} · ${r.load_ok?"parsed":'<b class="badc">NOT PARSED</b>'}${r.nodes!==undefined&&r.load_ok?" · "+r.nodes+" root nodes":""}${r.unknown_nodes?` · <b class="warnc">${r.unknown_nodes} unknown nodes dropped</b>`:""} · nonblank <b class="${r.nonblank_ratio<.005?"warnc":"okc"}">${pct(r.nonblank_ratio)}</b>${r.no_frame?` · <b class="warnc">no frame: nothing drawable</b>`:""}${r.frames_watched?` · ${r.frames_watched} frames`:""}`;
  return esc(Object.entries(r).filter(([k])=>!/^(op|input_sha256|output_sha256|prev)$/.test(k)).map(([k,v])=>`${k} ${typeof v==="object"?JSON.stringify(v):v}`).join(" · ").slice(0,300))}
function realExtra(sc){const it=sc.item;if(!it)return"";
  if(sc.src==="live"){const f=it.A[it.A.length-1],tin=it.A.reduce((a,b)=>a+b.ti,0),tout=it.A.reduce((a,b)=>a+b.to,0),r=f.r||{};
    return`<div class="note" style="margin-top:8px"><b>prompt</b> ${esc(it.p)} · ${esc(it.c)}: ${esc(it.pt)}<br><b>calls</b> ${it.A.length} · ${fmt.int(tin)} tokens in, ${fmt.int(tout)} out · ${money(it.A.reduce((a,b)=>a+b.u,0))} at list price (L) · finished at run time ${fmt.clock(it.T)}<br><b>X_ITE said</b> in the offline pass: ${r.msgs&&r.msgs.length?r.msgs.map(esc).join(" · "):"nothing"}<br><b>draw outcome</b> ${esc(DRAWTXT[sc.drawKind]||sc.drawKind||"-")}${!r.err&&r.frames?` · ${r.frames} frame${r.frames===1?"":"s"} watched, the last at ${r.last} ms; best frame ${pct(r.cb)}, screenshot ${pct(r.shot)}`:""}${it.A.length>1?` · <a data-go="tether">see the repair loop</a>`:""}</div>`}
  if(sc.src==="real"){const r=it.r||{};
    return`<div class="note" style="margin-top:8px"><b>prompt</b> ${esc(it.p)} · ${esc(it.c)}: ${esc(it.pt)}<br><b>run</b> ${esc(it.rid||"")} · ${esc(it.hw||"")} · ${it.at} attempt${it.at===1?"":"s"} recorded as flags<br><b>X_ITE said</b> in the offline pass: ${r.msgs&&r.msgs.length?r.msgs.map(esc).join(" · "):"nothing"}<br><b>draw outcome</b> ${esc(DRAWTXT[sc.drawKind]||sc.drawKind||"-")}${!r.err&&r.frames?` · ${r.frames} frame${r.frames===1?"":"s"} watched, the last at ${r.last} ms; best frame ${pct(r.cb)}, screenshot ${pct(r.shot)}`:""}${sc.drawKind==="unparseable"&&!it.wf?" · the file is not well-formed XML":""}</div>`}
  return`<div class="note" style="margin-top:8px"><b>source</b> ${esc(sc.src)} · a scene written in this view (${sc.src==="bench"?"the Bench":"the live lane"}); excluded from every aggregate${S.flags.includeMine?" unless 'include my runs' is on (it is)":""}</div>`}
function tabChain(sc,steps,vr){
  const h='<div class="chain">'+steps.map(([n,cx])=>{let r;try{r=JSON.parse(cx)}catch(e){return`<div class="step"><div class="op pill p-bad">${n} ?</div><div class="b">step is not JSON</div></div>`}
    return`<div class="step"><div class="op pill ${OPCOL[r.op]||"p-mute"}">${n} ${esc(String(r.op||"?").toUpperCase())}</div><div class="b">${stepDesc(r)}<br><i>in</i> ${esc(String(r.input_sha256||"").slice(0,12))} <i>→ out</i> ${esc(String(r.output_sha256||"").slice(0,12))} <i>prev</i> ${esc(String(r.prev||"").slice(0,12))}</div></div>`}).join("")+"</div>";
  return h+realExtra(sc)+`<div style="margin-top:8px" class="m">${vr.ok?`<span class="okc">verify(): chain intact, head output hash equals current content hash ${contentHash(sc.xml).slice(0,16)} (page-normalised)</span>`:`<span class="badc">verify(): ${esc(vr.problems.join(" · "))}</span>`}</div>`}
/* ---------- Report ---------- */
function tabReport(sc){const it=sc.item;
  if((sc.src==="bench"||sc.src==="viewer")&&sc.port&&self.reportHtml){  /* 34-bench hand-off: sc.port is the js-port result computed in this browser; its own report, verbatim */
    return`<div class="note" style="margin:0 0 8px"><b>your browser's work</b> · ${esc(sc.id)} was validated here by <b>js-port-of-8dd0d3e</b>${sc.port.ms!=null?" in "+fmt.ms(sc.port.ms):""}; nothing below was recorded on 17 Oct and this scene is in no rate or count on the page${it&&it.p?` · source item: ${esc(it.p)}${it.m?" · "+esc(disp(it.m)):""}`:" · pasted text"}</div>${reportHtml(sc.port)}`}
  if(sc.src==="live"&&it&&it.A){const A=it.A,n=A.length;let h=`<div class="note" style="margin:0 0 8px"><b>prompt</b> ${esc(it.p)} · ${esc(it.c)}: ${esc(it.pt)}<br>${n} report${n===1?"":"s"} from <b>${esc(self.LM?LM.validator:"fork@eb4b4b4")}</b>, recorded in process on 17 Oct; every line is the validator's own text. Line numbers open the attempt in the Bench.</div><div class="repList">`;
    A.forEach((a,k)=>{const xe=a.xe||[],se=a.se||[],fx=a.fx||[];
      h+=`<div class="rep"><h4>ATTEMPT ${k+1} OF ${n} · <span class="pill ${a.ok?"p-ok":"p-bad"}">${a.ok?"VALID":"INVALID"}</span> on ${esc(self.LM?LM.validator:"fork@eb4b4b4")} in ${fmt.ms(a.vms)} · ${a.ok?"no findings":`XSD ${xe.length?`<b>${xe.length} error${xe.length===1?"":"s"}</b>`:"valid"} · semantic <b>${se.length}</b> · ${fx.length} exact fix${fx.length===1?"":"es"}`}${k<n-1?` · report of ${fmt.int(a.rl||0)} characters sent back to the model`:""}</h4>`;
      h+=xe.map(l=>`<div><b>xsd</b> ${lineLink(esc(String(l).slice(0,400)),k)}</div>`).join("")+se.map(l=>`<div>${lineLink(fmtRep(l),k)}</div>`).join("")+fx.map(l=>`<div><i>fix</i> ${fmtRep(l).replace(/^<b>[\w-]+<\/b>\s*/,"")}</div>`).join("")+"</div>"});
    h+="</div>"+portLine(sc);return h}
  if(sc.src==="real"&&it){const f=(v,c)=>`<span class="pill ${v?"p-ok":"p-bad"}">${v?"valid":"invalid"}</span>${c&&c.length?" · "+esc(c.join(", ")):""}`;
    return`<div class="note" style="margin:0 0 8px"><b>prompt</b> ${esc(it.p)} · ${esc(it.c)}: ${esc(it.pt)}<br>The 11 Oct run kept verdict flags, not report text: what follows is every recorded verdict for this body.</div><div class="repList">`+
      `<div class="rep"><h4>svc@11Oct (the service that was live)</h4>xsd ${it.x?"valid":"<b>invalid</b>"} · semantic ${it.s?"valid":"<b>invalid</b>"} · constraints ${it.cn?"ok":"<b>not ok</b>"}${it.at>1?`<br>earlier attempts: ${(it.earlier||[]).map((e,i)=>`#${i+1} xsd ${e[0]?"✓":"✗"} semantic ${e[1]?"✓":"✗"}`).join(" · ")}`:""}</div>`+
      `<div class="rep"><h4>fork@8c0a457 recorded</h4>${f(it.f1[0],it.f1[1])}</div><div class="rep"><h4>fork@eb4b4b4 recorded</h4>${f(it.f2[0],it.f2[1])}</div>${driftLine(sc)}</div>`+portLine(sc)}
  return`<p class="note" style="margin:0">A scene written in this view carries its report in its own x3dprov steps (see Chain)${sc.port?`; the js-port said <span class="pill ${sc.port.valid?"p-ok":"p-bad"}">${sc.port.valid?"VALID":"INVALID"}</span>`:""}.</p>`+portLine(sc)}
function driftLine(sc){if(!self.DRIFT||!DRIFT.v8dd0d3e)return"";const it=sc.item,key=sc.src==="live"?"live-2026-10-17/x3d/"+keyOf(it.m,it.p,it.A.length):"replay/"+it.k,v=DRIFT.v8dd0d3e.verdicts[key];if(!v)return"";
  return`<div class="rep"><h4>fork@8dd0d3e recorded (drift part, per commit)</h4><span class="pill ${v.valid?"p-ok":"p-bad"}">${v.valid?"valid":"invalid"}</span>${v.xsd?"":" · xsd"}${v.sem&&v.sem.length?" · "+esc(v.sem.join(", ")):""}</div>`}
function portLine(sc){const k=sc.id+"|"+sc.xml.length,m=portMemo.get(k);let inner;
  if(m&&m.res)inner=`<span class="pill ${m.cmp==="agrees"?"p-ok":"p-warn"}">${m.cmp}</span> js-port-of-8dd0d3e in this browser: <b class="${m.res.valid?"okc":"badc"}">${m.res.valid?"VALID":"INVALID"}</b>${m.codes.length?" · "+esc(m.codes.join(", ")):""} · ${fmt.ms(m.res.ms)}${m.cmp==="differs"?" · recorded: "+esc(m.rec):""}`;
  else if(m&&m.err)inner=`<span class="pill p-mute">port: error</span> ${esc(m.err)}`;
  else if(self.VAL&&(VAL.mode==="full"||VAL.mode==="semantic-only"))inner=`<span class="pill p-mute">port: validating…</span> js-port-of-8dd0d3e${VAL.mode==="semantic-only"?" (semantic only: wasm refused)":""}`;
  else if(sc.port&&sc.port.valid!=null)inner=`<span class="pill ${sc.port.valid?"p-ok":"p-bad"}">${sc.port.valid?"VALID":"INVALID"}</span> js-port-of-8dd0d3e in this browser (set by ${sc.src==="bench"?"the bench":"the wall"})${self.codesOfRes&&codesOfRes(sc.port).length?" · "+esc(codesOfRes(sc.port).join(", ")):""}${sc.port.ms!=null?" · "+fmt.ms(sc.port.ms):""}`;
  else inner=`<span class="pill p-mute">port: not loaded</span> ${esc(self.VAL?VAL.reason||VAL.mode:"VAL absent")} · recorded verdicts shown; nothing is re-judged here`;
  if(sc.portNote)inner+=` · <i>${esc(String(sc.portNote))}</i>`;  /* 36-wall: its note after an injection */
  return`<div class="port" data-k="port">${inner}</div>`}
function portCheck(sc){if(!self.VAL||!(VAL.mode==="full"||VAL.mode==="semantic-only"))return;const k=sc.id+"|"+sc.xml.length;if(portMemo.has(k))return;
  const it=sc.item;let recOk,recCodes,xml;
  if(sc.src==="live"&&it&&it.A){const a=it.A[it.A.length-1];recOk=!!a.ok;recCodes=codesOf(a);xml=it.B[it.B.length-1]}else if(sc.src==="real"&&it){recOk=!!it.f2[0];recCodes=it.f2[1]||[];xml=it.b}else{recOk=sc.verdict==="valid";recCodes=[];xml=stripProv(sc.xml)}
  portMemo.set(k,{pending:true});
  VAL.validate(xml).then(res=>{const cmp=VAL.compare(res,recOk,recCodes);portMemo.set(k,{res,cmp,codes:codesOfRes(res),rec:(recOk?"valid":"invalid")+(recCodes.length?" "+recCodes.join(", "):"")});if(!sc.port)sc.port=res;if(self.LOOP)LOOP.dirty(LOOP.bits.VAL)})
    .catch(e=>{portMemo.set(k,{err:String(e&&e.message||e).slice(0,160)});if(self.LOOP)LOOP.dirty(LOOP.bits.VAL)}).finally(()=>{cur.sig="";if(self.LOOP)LOOP.dirty(LOOP.bits.SELECT)})}
/* ---------- Trace ---------- */
function tabTrace(sc){const sp=spansOf(sc);if(!sp.length)return'<p class="note">no steps</p>';
  const tmin=Math.min(...sp.map(p=>p.t0)),tmax=Math.max(...sp.map(p=>p.t0+p.ms)),tot=Math.max(1,tmax-tmin),W=620,L=170,bw=W-L-70,rowH=24,abs=sp.some(p=>p.r.run_s!=null);
  const colr={generate:"var(--info)",validate:"var(--ok)",repair:"var(--warn)",render:"var(--acc)",transform:"var(--info)",measure:"var(--acc)"};
  let s=`<div class="trace"><svg viewBox="0 0 ${W} ${sp.length*rowH+34}" role="img" aria-label="trace">`;
  sp.forEach((p,i)=>{const y=8+i*rowH,x=L+bw*(p.t0-tmin)/tot,w=Math.max(2,bw*p.ms/tot),hatch=p.src==="modeled"||p.src==="simulated";
    s+=`<text x="2" y="${y+13}" style="fill:var(--fg)">${p.n} ${esc(p.r.op)}</text><text x="70" y="${y+13}">${esc(String(p.r.validator_ref||p.r.agent_ref||disp(p.r.model||"")||"").slice(0,14))}</text>`+
       `<rect x="${x.toFixed(1)}" y="${y}" width="${w.toFixed(1)}" height="15" fill="${colr[p.r.op]||"var(--dim)"}" opacity="${hatch?.45:.9}"${hatch?' stroke="var(--fg)" stroke-dasharray="3 2" stroke-width=".6"':""}/>`+
       `<text x="${Math.min(x+w+4,W-62).toFixed(1)}" y="${y+12}" style="fill:var(--fg)">${p.ms?fmt.ms(p.ms):"—"}${p.src==="missing"?" (no duration recorded)":""}</text>`});
  s+=`<text x="${L}" y="${sp.length*rowH+24}">${abs?"run time "+fmt.clock(tmin/1000):"0"}</text><text x="${L+bw-40}" y="${sp.length*rowH+24}">+${(tot/1000).toFixed(1)} s</text></svg>`;
  s+=`<div class="legend"><span style="--c:var(--info)">generate · recorded call time (provider-reported)</span><span style="--c:var(--ok)">validate · measured in process</span><span style="--c:var(--warn)">repair · recorded</span><span style="--c:var(--acc)">render · measured in the offline pass, drawn after the last call</span></div>`+
     `<p class="note" style="margin:6px 0 0">Spans are the chain steps in order; starts come from the recorded run_s of each call${abs?" (absolute on the run clock)":""} and every duration is the one in the step's own JSON. Nothing here is modeled; a dashed span would mean a modeled duration and none is drawn on this page.</p></div>`;return s}
/* ---------- Verify ---------- */
function tabVerify(sc){const vr=verify(sc.xml,true),t0=performance.now();for(let i=0;i<20;i++)verify(sc.xml);const us=Math.round((performance.now()-t0)*1000/20),c=CH[vr.status]||CH["?"],ch=contentHash(sc.xml);
  let h=`<div class="m" style="margin-bottom:6px">verify() on ${esc(sc.id)}: <span class="pill ${c[0]}">${c[1]}</span> in ${us} µs · ${vr.rows?vr.rows.length:0} checks · continuity ${vr.ok?'<span class="okc">intact</span>':`<span class="badc">${esc(vr.problems.join(" · "))}</span>`}</div><table class="vtab"><thead><tr><th>step</th><th>check</th><th>expected</th><th>found</th><th></th><th>hash</th></tr></thead><tbody>`;
  h+=(vr.rows||[]).map(r=>`<tr><td>${r.n}</td><td>${esc(r.chk)}</td><td>${esc(String(r.exp).slice(0,14))}</td><td class="${r.ok?"mutec":"badc"}">${esc(String(r.got).slice(0,14))}</td><td><span class="pill ${r.ok?"p-ok":"p-bad"}">${r.ok?"OK":"FAIL"}</span></td><td class="mutec">page-normalised</td></tr>`).join("")+"</tbody></table>";
  h+=`<div class="note" style="margin-top:8px"><b>page-normalised hash</b> ${ch} = SHA-256( text-normalised scene minus x3dprov.* ) · <b>repo C14N</b>: not stamped for this scene — the repo-stamped files (the 174 gpu-phase heads under runs/, the physics ledger, the suite steps) carry lxml-C14N hashes; byte equality with a repo file is never claimed here (rule 10).</div>`;
  h+=`<div class="note m" data-k="rehash" style="margin-top:6px">${rehashLine(sc)}</div>`;
  h+=`<p class="note" style="margin:6px 0 0">The checks stop at the first broken link, so a deleted or edited step is named before the content hash is compared. Without a seal the last step's own text is not checked against anything: that is the open gap the seal closes (HMAC stand-in; the key is in the page source and the page says so).</p>`;return h}
function rehashLine(sc){const k=sc.id+"|"+sc.xml.length,m=rehashMemo.get(k);
  if(!m)return"re-hash through HASH: queued…";if(m.err)return"re-hash through HASH: "+esc(m.err);if(m.pending)return"re-hash through HASH ("+esc(HASH.mode)+"): running…";
  return`re-hash through HASH (${esc(m.mode)}): content hash ${esc(m.hash.slice(0,16))} ${m.same?"equals":"<b class=\"badc\">DIFFERS from</b>"} the main thread · chain <span class="pill ${(CH[m.status]||CH["?"])[0]}">${(CH[m.status]||CH["?"])[1]}</span> · continuity verdict ${m.ok?'<span class="okc">intact</span>':'<span class="badc">broken</span>'}`}
function rehash(sc){const k=sc.id+"|"+sc.xml.length;if(rehashMemo.has(k)||!self.HASH)return;rehashMemo.set(k,{pending:true});const xml=sc.xml;
  Promise.all([HASH.hashMany([xml]),HASH.batch([sc.id],[xml])]).then(([hs,st])=>{rehashMemo.set(k,{hash:hs[0],same:hs[0]===contentHash(xml),status:st[0].status,ok:st[0].ok,mode:HASH.mode})}).catch(e=>rehashMemo.set(k,{err:String(e&&e.message||e).slice(0,120)}))
    .finally(()=>{const d=body&&body.querySelector("[data-k=rehash]");if(d&&cur.tab==="verify"){const t=target();if(t.sc&&t.sc.id===sc.id)d.innerHTML=rehashLine(sc)}})}
/* ---------- Tether ---------- */
function tabTether(sc){const it=sc.item;
  if(sc.src==="real"&&it)return`<p class="note" style="margin:0">The Tether loop (generate, validate on the fork, send the model its own report, repair, validate again) was recorded step for step only in <b>17 OCT</b>. The 11 Oct run kept ${it.at} attempt${it.at===1?"":"s"} as flags${it.at>1?": "+(it.earlier||[]).map((e,i)=>`#${i+1} xsd ${e[0]?"✓":"✗"} semantic ${e[1]?"✓":"✗"}`).join(" · ")+` · final xsd ${it.x?"✓":"✗"} semantic ${it.s?"✓":"✗"}`:""}; the earlier bodies were not kept, so no diff can be drawn. Switch to 17 OCT in the mast for the loop.</p>`;
  if(sc.src!=="live"||!it||!it.A)return`<p class="note" style="margin:0">A scene written in this view keeps its attempt cards in the panel that wrote it (${sc.src==="bench"?"the Bench":"the live lane"}); its steps are in the Chain tab.</p>`;
  const A=it.A,n=A.length,B=it.B||[];
  let h=`<div class="note" style="margin:0 0 8px"><b>prompt</b> ${esc(it.p)} · ${esc(it.c)}: ${esc(it.pt)}<br>${n===1?"One call; the scene "+(A[0].ok?"passed the validator on the first try, so the loop never ran.":"failed and the loop ended (no repair was recorded: the lane was cut)."):n+" calls. Each step below is in this scene's provenance record: the repair's input hash is the previous attempt's content hash."}</div><div class="tt">`;
  A.forEach((a,k)=>{const bod=B[k]||"",df=k&&B[k-1]?diffHtml(B[k-1],bod):null,r=a.r||{},xe=a.xe||[],se=a.se||[],fx=a.fx||[];
    const shot=r.jpg&&(r.nb||0)>=.005?`<img class="th2" alt="measured frame, attempt ${k+1}" src="data:image/jpeg;base64,${r.jpg}">`:`<div class="th2">${r.err?"PARSE FAIL":r.jpg===undefined&&!r.rendered?"NOT RENDERED":"NOTHING TO DRAW"}</div>`;
    h+=`<div class="att"><h4>ATTEMPT ${k+1} OF ${n} · ${esc(disp(it.m))} · ${(a.ms/1000).toFixed(1)} s · ${fmt.int(a.ti)}→${fmt.int(a.to)} tok · ${money(a.u)} · ${(bod.length/1024).toFixed(1)} KB · hash ${bod?contentHash(bod).slice(0,12):"—"}</h4>${shot}`+
      `<div class="rep"><span class="pill ${a.ok?"p-ok":"p-bad"}">${a.ok?"VALID":"INVALID"}</span> on ${esc(self.LM?LM.validator:"fork@eb4b4b4")} in ${fmt.ms(a.vms)}${a.ok?"":` · XSD ${xe.length?`<b>${xe.length} error${xe.length===1?"":"s"}</b>`:"valid"} · semantic <b>${se.length}</b>`}`+
      xe.slice(0,4).map(l=>`<br><b>xsd</b> ${esc(String(l).slice(0,260))}`).join("")+se.slice(0,5).map(l=>`<br>${fmtRep(l)}`).join("")+fx.slice(0,4).map(l=>`<br><i>fix</i> ${fmtRep(l).replace(/^<b>[\w-]+<\/b>\s*/,"")}`).join("")+
      `<br>X_ITE 16.5.0 offline: ${r.err?"cannot parse the file":(r.nb||0)>=.005?"draws, "+pct(r.nb)+" of pixels differ":"draws nothing"}</div>`+
      (df?`<div class="df"><span class="g">Δ against attempt ${k}: +${df.add} −${df.del} tag lines (the scene has ${df.base})</span>\n${df.html}</div>`:"")+`</div>`;
    if(k<n-1)h+=`<div class="arrow">▼ the model is sent its own report: ${xe.length+se.length} error${xe.length+se.length===1?"":"s"}, ${fx.length} exact fix${fx.length===1?"":"es"}, ${fmt.int(a.rl||0)} characters · repair call ${k+2} ▼</div>`});
  return h+"</div>"}
/* ---------- Receipt ---------- */
function receiptRows(sc){const it=sc.item||{},rows=[],R=(label,value,src,st,grade,rr)=>rows.push({label,value,src,st,grade,rr});
  const chain=verify(sc.xml);
  if(sc.src==="live"&&it.A){const A=it.A,f=A[A.length-1],r=f.r||{},k=self.renderOf?renderOf(it,A.length):{r151:null},r1=k.r151,v=self.LM?LM.validator:"fork@eb4b4b4";
    R("verdict",`${f.ok?"valid":"invalid"} on ${v}${A.length>1?" after "+(A.length-1)+" repair"+(A.length>2?"s":""):" first try"}`,`live.core A[${A.length}].ok`,["RECORDED 17 Oct","fork@eb4b4b4 recorded"],"C","port");
    R("codes",codesOf(f).join(", ")||"none",`A[${A.length}].xe / se`,["RECORDED 17 Oct","fork@eb4b4b4 recorded"],"C");
    R("validator time",fmt.ms(f.vms),`A[${A.length}].vms · measured in process`,["RECORDED 17 Oct","fork@eb4b4b4 recorded"],"C");
    R("model call time",A.map(a=>fmt.ms(a.ms)).join(" · "),"A[].ms · provider-reported",["RECORDED 17 Oct"],"C");
    R("tokens",A.map(a=>fmt.int(a.ti)+"→"+fmt.int(a.to)).join(" · "),"A[].ti / to · provider-reported",["RECORDED 17 Oct"],"C");
    R("spend",money(A.reduce((s,a)=>s+a.u,0))+" at list price","A[].u · list price, not an invoice",["RECORDED 17 Oct"],"L");
    R("nonblank 16.5.0",r.err?"unparseable":`${pct(r.nb)} · ${r.frames||0} frames · last ${r.last||0} ms`,`A[${A.length}].r.nb · 192×144 swiftshader offline`,["RECORDED 17 Oct",null,"X_ITE 16.5.0 offline"],"C","measure");
    R("nonblank 16.5.1",r1?(r1.err?"unparseable":pct(r1.nb)):"not in the 16.5.1 pass",`renders.151 live[${keyOf(it.m,it.p,A.length)}]`,["RECORDED 17 Oct",null,"X_ITE 16.5.1 offline"],"C");
    R("draw kind",sc.drawKind||"—","kindOf(item): err → unparseable; nb ≥ 0.5% → draws; no frame or dropped nodes → nothing drawable; else blank frame",["RECORDED 17 Oct",null,"X_ITE 16.5.0 offline"],"C");
    const dv=self.DRIFT&&DRIFT.v8dd0d3e&&DRIFT.v8dd0d3e.verdicts["live-2026-10-17/x3d/"+keyOf(it.m,it.p,A.length)];if(dv)R("fork@8dd0d3e",dv.valid?"valid":"invalid"+(dv.xsd?"":" · xsd")+(dv.sem&&dv.sem.length?" · "+dv.sem.join(", "):""),"drift v8dd0d3e.verdicts",["RECORDED per commit","fork@8dd0d3e recorded"],"C")}
  else if(sc.src==="real"&&it.r){const r=it.r;
    R("verdict svc@11Oct",`${it.x&&it.s?"valid":"invalid"} · xsd ${it.x?"✓":"✗"} semantic ${it.s?"✓":"✗"} constraints ${it.cn?"✓":"✗"}`,"replay x / s / cn",["RECORDED 11 Oct","svc@11Oct recorded"],"C","port");
    R("fork@8c0a457",(it.f1[0]?"valid":"invalid")+(it.f1[1]&&it.f1[1].length?" · "+it.f1[1].join(", "):""),"replay f1",["RECORDED 11 Oct","fork@8c0a457 recorded"],"C");
    R("fork@eb4b4b4",(it.f2[0]?"valid":"invalid")+(it.f2[1]&&it.f2[1].length?" · "+it.f2[1].join(", "):""),"replay f2",["RECORDED 11 Oct","fork@eb4b4b4 recorded"],"C");
    R("model call time",fmt.ms(it.lat),"replay lat · vLLM log",["RECORDED 11 Oct"],"C");R("tokens",fmt.int(it.ti)+"→"+fmt.int(it.to),"replay ti / to",["RECORDED 11 Oct"],"C");
    R("cost",money(it.rc/it.nrun)+" apportioned",`run cost ${money(it.rc)} / ${it.nrun} scenes`,["RECORDED 11 Oct"],"L");
    R("nonblank 16.5.0",r.err?"unparseable":`${pct(r.nb)} · ${r.frames||0} frames · last ${r.last||0} ms`,"replay r.nb",["RECORDED 11 Oct",null,"X_ITE 16.5.0 offline"],"C","measure");
    if(r.nb151!==undefined)R("nonblank 16.5.1",r.err151?"unparseable":pct(r.nb151),"renders.151 replay["+it.k+"]",["RECORDED 11 Oct",null,"X_ITE 16.5.1 offline"],"C");
    if(r.nb164!==undefined)R("nonblank 16.4.1",r.err164?"unparseable":pct(r.nb164),"replay r.nb164",["RECORDED 11 Oct",null,"X_ITE 16.4.1 offline"],"C");
    R("draw kind",sc.drawKind||"—","kindOf(item)",["RECORDED 11 Oct",null,"X_ITE 16.5.0 offline"],"C");
    const dv=self.DRIFT&&DRIFT.v8dd0d3e&&DRIFT.v8dd0d3e.verdicts["replay/"+it.k];if(dv)R("fork@8dd0d3e",dv.valid?"valid":"invalid","drift v8dd0d3e.verdicts",["RECORDED per commit","fork@8dd0d3e recorded"],"C")}
  else{R("verdict",sc.verdict||"—",sc.port?"js-port-of-8dd0d3e in this view":"the step that wrote it",["RE-RUN HERE","js-port-of-8dd0d3e here"],"C","port");if(sc.nb!=null)R("nonblank here",pct(sc.nb),"STAGE.measure in this browser",["RE-RUN HERE",null,"X_ITE 16.5.0 in this browser · "+(self.ENV&&ENV.gl==="gpu"?"gpu":"software")],"C","measure")}
  R("steps in the head",String(readSteps(sc.xml).length)+(sc.sealed?" · sealed":" · unsealed"),"readSteps(xml) · x3dprov.step.N metas",["RE-RUN HERE"],"C");
  R("content hash",contentHash(sc.xml).slice(0,16)+"… page-normalised","contentHash(xml) in this browser",["RE-RUN HERE"],"C","hash");
  R("chain",(CH[chain.status]||CH["?"])[1].toLowerCase()+(chain.problems.length?" · "+chain.problems[0]:""),"verify(xml) in this browser",["RE-RUN HERE"],"C","verify");
  return rows}
function tabReceipt(sc){const rows=receiptRows(sc);
  let h=`<div class="note" style="margin:0 0 6px">What this page asserts about <b>${esc(sc.id)}</b>, each with the field it was read from, its stamps and a grade (C confirmed for this scene · L list price · S suspected). RE-RUN recomputes in this browser and prints both values.</div><table class="receipt"><thead><tr><th>claim</th><th>value</th><th>source</th><th>stamps</th><th></th></tr></thead><tbody>`;
  rows.forEach((r,i)=>{const st=r.st||[];h+=`<tr data-i="${i}"><td>${esc(r.label)}</td><td data-k="val">${esc(r.value)}</td><td><span class="src">${esc(r.src)}</span></td><td>${st[0]?stamp("source",st[0]).outerHTML:""} ${st[1]?stamp("validator",st[1]).outerHTML:""} ${st[2]?stamp("renderer",st[2]).outerHTML:""} ${gradeChip(r.grade).outerHTML}</td><td>${r.rr?`<button type="button" data-rr="${r.rr}" data-i="${i}">RE-RUN</button>`:'<span class="src">quoted from the record</span>'}</td></tr>`});
  return h+"</tbody></table>"}
async function rerun(kind,sc,cell,btn){btn.disabled=true;btn.textContent="running…";let out="";const it=sc.item||{};
  try{
    if(kind==="hash"){const steps=readSteps(sc.xml),head=steps.length?JSON.parse(steps[steps.length-1][1]).output_sha256:null,h=contentHash(sc.xml),w=self.HASH?(await HASH.hashMany([sc.xml]))[0]:h;out=`computed ${h.slice(0,16)}… · worker ${w.slice(0,16)}… ${w===h?"equal":"DIFFER"} · head output ${head?head.slice(0,16)+"…":"none"} ${head===h?"agrees":"differs"}`}
    else if(kind==="verify"){const v=verify(sc.xml),st=self.HASH?(await HASH.batch([sc.id],[sc.xml]))[0]:{status:v.status};out=`computed ${v.status}${v.problems.length?" · "+v.problems[0]:""} · worker ${st.status} ${st.status===v.status?"agrees":"differs"}`}
    else if(kind==="measure"){if(!self.STAGE||!STAGE.measure||!STAGE.measure.ok)throw new Error("X_ITE measure canvas not available in this viewer");const R=await STAGE.measure.show(sc.xml,{expectNone:sc.drawKind==="nothing drawable",timeoutMs:12000});
      if(R.cancelled)out="measure superseded by a newer load; press again";else{const rec=sc.src==="live"&&it.A?it.A[it.A.length-1].r:sc.src==="real"?it.r:{nb:sc.nb};const recB=rec&&!rec.err?(rec.nb||0)<.005:null;const here=R.err?null:R.noFrame?true:(R.nb||0)<.005;
        out=`computed here: ${R.err?"X_ITE refused: "+R.err:R.noFrame?(R.slow?"no frame yet (slow renderer)":"no frame: nothing drawable"):pct(R.nb)+" · "+R.frames+" frames"} · recorded ${rec?rec.err?"unparseable":pct(rec.nb):"—"} · ${here===null||recB===null?"not comparable":here===recB?"agrees on the 0.5% line":"DIFFERS on the 0.5% line"} · X_ITE 16.5.0 in this browser · ${self.ENV&&ENV.renderer||"?"}`}}
    else if(kind==="port"){if(!self.VAL||!(VAL.mode==="full"||VAL.mode==="semantic-only"))throw new Error("js-port not loaded: "+(self.VAL?VAL.reason:"VAL absent"));
      let recOk,recCodes,xml;if(sc.src==="live"&&it.A){const a=it.A[it.A.length-1];recOk=!!a.ok;recCodes=codesOf(a);xml=it.B[it.B.length-1]}else if(sc.src==="real"){recOk=!!(it.x&&it.s);recCodes=[];xml=it.b}else{recOk=sc.verdict==="valid";recCodes=[];xml=stripProv(sc.xml)}
      const res=await VAL.validate(xml);out=`js-port-of-8dd0d3e: ${res.valid?"valid":"invalid"}${codesOfRes(res).length?" · "+codesOfRes(res).join(", "):""} in ${fmt.ms(res.ms)} · recorded ${recOk?"valid":"invalid"} · ${VAL.compare(res,recOk,recCodes)}`;if(!sc.port)sc.port=res}
  }catch(e){out="re-run failed: "+String(e&&e.message||e).slice(0,160)}
  cell.textContent=out;btn.disabled=false;btn.textContent="RE-RUN";if(self.LOOP)LOOP.dirty(LOOP.bits.VAL|LOOP.bits.SELECT)}
/* ---------- Stage (the hero stage + the hidden measure canvas; the v3 #v3msg / #v3none hooks keep their vocabulary) ---------- */
function validatorsLine(sc){if(!self.VALS)return"";if(sc.src==="live")return`${self.LM?LM.validator:"fork@eb4b4b4"}: ${sc.verdict}`;return VALS.filter(V=>V.id!=="port"||sc.port).map(V=>`${V.ref.replace("fork@","f@")}: ${judge(sc,V).verdict}`).join(" · ")}
function offlineLine(sc){const it=sc.item;if(sc.src==="live"&&it&&it.A){const r=it.A[it.A.length-1].r||{},k=self.renderOf?renderOf(it,it.A.length):{r151:null};return`offline: 16.5.0 ${r.err?"unparseable":pct(r.nb)} · 16.5.1 ${k.r151?(k.r151.err?"unparseable":pct(k.r151.nb)):"—"}`}
  if(sc.src==="real"&&it&&it.r){const r=it.r;return`offline: 16.5.0 ${r.err?"unparseable":pct(r.nb)} · 16.5.1 ${r.nb151!==undefined?(r.err151?"unparseable":pct(r.nb151)):"—"}`}return"offline: not recorded (written in this view)"}
function stageFrame(sc){const it=sc.item;let jpg=null;if(sc.src==="live"&&it&&it.A){const r=it.A[it.A.length-1].r;jpg=r&&r.jpg||null}else if(sc.src==="real"&&it&&it.r)jpg=it.r.jpg||null;
  if(jpg){v3img.src="data:image/jpeg;base64,"+jpg;v3img.hidden=false;v3img.alt="measured frame of "+sc.id+" (offline pass)"}else{v3img.hidden=true;v3img.removeAttribute("src")}}
function renderMeasure(sc,R){const said=(R.msgs||[]).slice(0,4),nf=R.noFrame,vs=validatorsLine(sc);
  if(R.err){v3none.hidden=false;v3none.innerHTML=`<b>COULD NOT PARSE</b><i>X_ITE refused this file: ${esc(String(R.err).slice(0,150))}</i>`;v3msg.innerHTML=`X_ITE refused this scene: <b>${esc(String(R.err).slice(0,150))}</b><br>${esc(offlineLine(sc))}<br>validators: ${esc(vs)}`;return}
  if(nf&&R.slow){v3none.hidden=false;v3none.innerHTML=`<b>NO FRAME YET</b><i>X_ITE gave no frame in 12 s on this device and printed nothing about dropped content. The offline pass recorded this scene as <b>${esc(sc.drawKind||"?")}</b>, so a slow or software renderer is the likeliest cause.</i>`}
  else if(nf||((R.nb||0)<.005&&R.dropped)){v3none.hidden=false;v3none.innerHTML=`<b>NOTHING TO DRAW</b><i>X_ITE accepted the file, dropped what it could not read, and ${nf?"had nothing left to render, so it never scheduled a frame":"drew only blank frames"}.${said.length?"<br>It said: "+said.map(esc).join(" · "):""}</i>`}
  else v3none.hidden=true;
  const rec=sc.src==="live"&&sc.item?sc.item.A[sc.item.A.length-1].r:sc.src==="real"&&sc.item?sc.item.r:null,recBlank=rec&&!rec.err?(rec.nb||0)<.005:null,hereBlank=nf?true:(R.nb||0)<.005;
  v3msg.innerHTML=`X_ITE loaded ${R.nodes!=null?R.nodes:"?"} root nodes in ${R.ms} ms · `+(nf?`<b>no frame in ${R.slow?12:2.5} s</b>`:`${R.frames} frame${R.frames===1?"":"s"} watched · pixels differing from background: <b class="accc">${pct(R.nb)}</b> (best frame)${(R.nb||0)<.005?" · <b>BLANK</b>":""}`)+
    (said.length&&!nf?`<br>X_ITE said: ${said.map(esc).join(" · ")}`:"")+`<br>${esc(offlineLine(sc))} · this browser: ${recBlank===null?"not comparable":hereBlank===recBlank?'<span class="okc">agrees with the offline record on the 0.5% line</span>':'<span class="warnc">differs from the offline record on the 0.5% line</span>'}`+
    `<br>validators: ${esc(vs)}<br><span class="mutec">measured in the hidden 192×144 canvas · X_ITE 16.5.0 in this browser · ${esc(self.ENV&&ENV.renderer||"?")} · the stage above shows the same bytes${self.__stage&&__stage.show.staged?" staged (lights added at render time, nothing written)":" unstaged"}</span>`}
async function stageShow(sc,opts){opts=opts||{};const tk=++cur.v3Token;if(!sc)return;stageFrame(sc);v3none.hidden=true;
  if(!self.STAGE||!STAGE.show||!STAGE.measure){v3msg.textContent="X_ITE is not available in this viewer (xite/x_ite.min.js); the measured JPEG is the counted frame. "+offlineLine(sc)+" · validators: "+validatorsLine(sc);return}
  const key=sc.id+"|"+sc.xml.length,memo=measureMemo.get(key);
  v3msg.textContent="loading "+sc.id+" on the stage…";
  if(STAGE.show.ok||STAGE.show.ready){try{const r=await STAGE.show.load(sc.xml,{scene:sc,staged:!!(self.FX&&FX.level>0)});if(tk!==cur.v3Token)return;if(!r.ok&&!r.cancelled&&r.err)v3msg.textContent="the stage refused this scene: "+r.err}catch(e){}}
  if(opts.scroll){const st=$("stage");if(st)st.scrollIntoView({behavior:self.FX&&FX.level>0?"smooth":"auto",block:"start"})}
  if(memo){renderMeasure(sc,memo);return}
  if(!STAGE.measure.ok&&!STAGE.measure.ready){v3msg.textContent="the measure canvas is not up in this viewer; "+offlineLine(sc)+" · validators: "+validatorsLine(sc);return}
  v3msg.textContent="measuring "+sc.id+" in the hidden 192×144 canvas…";
  const R=await STAGE.measure.show(sc.xml,{expectNone:sc.drawKind==="nothing drawable",timeoutMs:12000});if(tk!==cur.v3Token)return;
  if(!R.cancelled)measureMemo.set(key,R);  /* 08-stage queues every caller and resolves each promise with its own R: no retry, no give-up; an uncached R is simply shown */
  renderMeasure(sc,R)}
/* ---------- events (ledger rows from the firehose: F-nnn failed calls, C-nnn cut chains) ---------- */
function renderEvent(ev){const e=ev.ev,link=self.FH?FH.sceneOfEvent(ev):null;
  sub.innerHTML=`${esc(ev.id)} · <span class="pill ${ev.kind==="failed"?"p-bad":"p-warn"}">${ev.kind==="failed"?"FAILED CALL":"CUT CHAIN"}</span> · ${esc(disp(ev.m))} · ${esc(ev.p)}`;
  const rows=ev.kind==="failed"?[["what","a model call that failed: the provider answered "+esc(ev.code==="credit"?"insufficient credit (the account ran out)":ev.code)+"; no body came back, so there is no scene, no validator run and no chain"],["model",esc(disp(ev.m))],["prompt",esc(ev.p)],["attempt",String(ev.k)],["run clock",`${fmt.clock(e.t0)} → ${fmt.clock(e.t1)}`],["kind",esc(ev.code)],["source",ev.n==null?"runs/live-2026-10-17/events.jsonl, as the waterfall reported it (the kind only; raw provider text never ships)":`runs/live-2026-10-17/events.jsonl → EVENTS.failed[${ev.n-1}] (the kind only; raw provider text never ships)`],["counted as","one of the failed calls in the run strip (claim c.failed); never a scene, never in a rate"]]
    :[["what",`the lane stopped this chain: ${esc(ev.reason)} · ${ev.calls} call${ev.calls===1?"":"s"} were made and the chain ended neither valid nor at the third attempt`],["model",esc(disp(ev.m))],["prompt",esc(ev.p)],["last attempt",String(ev.k)],["run clock",fmt.clock(e.t1)],["reason",esc(ev.reason)+(self.LM&&LM.lanes&&LM.lanes[ev.m]?" · lane: "+esc(LM.lanes[ev.m]):"")],["its scene",link?`<a data-sel="${esc(link.id)}">${esc(link.id)}</a> · its last recorded attempt is on the page as that scene`:"not released yet on the run clock (or not on the page)"],["source",ev.n==null?"runs/live-2026-10-17/events.jsonl, as the waterfall reported it":`runs/live-2026-10-17/events.jsonl → EVENTS.cut[${ev.n-1}]`],["counted as","one of the cut chains in the run strip (claim c.cut)"]];
  body.hidden=false;view3d.hidden=true;body.innerHTML=`<dl class="ledgerRow">${rows.map(([k,v])=>`<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl><p class="note" style="margin:8px 0 0">${cur.tab==="chain"?"":"The "+esc(TABS.find(t=>t[0]===cur.tab)[1])+" tab has nothing to show for a ledger row: "}there is no chain here, only the record that a call happened and how it ended.</p>`;
  ctl.hidden=true}
/* ---------- render ---------- */
function render(force){if(!body||!self.S)return;const t=target(),sc=t.sc;
  const sig=sc?[sc.id,cur.tab,sc.status,sc.nsteps,sc.xml.length,S.vi,self.VAL?VAL.mode:"",t.pinned?1:0,sc.detected?1:0,sc.port?1:0,sc.injured?1:0,sc.tampered?1:0,sc.portNote?1:0].join("|"):t.ev?["ev",t.ev.id,cur.tab].join("|"):"none|"+cur.tab;
  if(!force&&sig===cur.sig)return;const tabChanged=cur.sig.split("|")[1]!==cur.tab,sceneChanged=!cur.sig.startsWith((sc?sc.id:t.ev?"ev":"none")+"|");cur.sig=sig;cur.renders++;if(INSPECTOR.panel)INSPECTOR.panel.renders=cur.renders;
  pinBtn.hidden=!t.pinned;
  if(t.ev){renderEvent(t.ev);return}
  if(!sc){body.hidden=false;view3d.hidden=true;body.innerHTML='<span class="note">Select a scene in the firehose, the waterfall, the wall, the hero rail or the contact sheet to see its chain, verify it, render it on the stage, and tamper with it.</span>';ctl.hidden=true;sub.textContent="click a row, a bar, a thumbnail or a wall cell";return}
  const vr=verify(sc.xml),c=CH[vr.status]||CH["?"],steps=readSteps(sc.xml);
  sub.innerHTML=`${esc(sc.id)} · <span class="pill ${c[0]}">${c[1]}</span>${sc.sealed?' <span class="pill p-info">SEALED</span>':' <span class="pill p-mute">UNSEALED</span>'}${sc.src==="bench"||sc.src==="viewer"?' <span class="pill p-you" title="made in this browser; in no rate or count">YOUR BROWSER</span>':""}${sc.tampered?' <span class="pill p-bad" title="36-wall injection 5 or 6: the text was changed in this browser">TAMPERED</span>':""} · ${esc(disp(sc.model))}${sc.item&&sc.item.p?" · "+esc(sc.item.p):""} · <span class="${t.pinned?"accc":"mutec"}">${t.pinned?"pinned":"newest · click a row to pin"}</span>`;
  const is3d=cur.tab==="stage";body.hidden=is3d;view3d.hidden=!is3d;let h="";
  if(cur.tab==="chain")h=tabChain(sc,steps,vr);
  else if(cur.tab==="report"){h=tabReport(sc);portCheck(sc)}
  else if(cur.tab==="trace")h=tabTrace(sc);
  else if(cur.tab==="verify"){h=tabVerify(sc);rehash(sc)}
  else if(cur.tab==="tether")h=tabTether(sc);
  else if(cur.tab==="receipt")h=tabReceipt(sc);
  else if(cur.tab==="xml"){const x=sc.xml,hd=/<head>[\s\S]*?<\/head>/.exec(x),head=hd?hd[0]:x.slice(0,2000);h=`<div class="note" style="margin:0 0 6px"><b>the file's head</b>: every step the page added is an x3dprov.step.N meta of this copy; no side JSON is the record (rule 11). page-normalised hash ${contentHash(x).slice(0,16)}… · ${fmt.bytes(x.length)} in all · repo C14N: not stamped for this scene.</div><pre>${esc(head.replace(/<meta /g,m=>"\n  "+m).slice(0,8000))}${head.length>8000?"\n… ("+head.length+" bytes of head)":""}</pre>`}
  else if(cur.tab==="prov")h="<pre>"+esc(JSON.stringify(provJson(sc,steps),null,1))+"</pre>";
  else if(cur.tab==="ol")h="<pre>"+esc(JSON.stringify(olJson(sc,steps),null,1))+"</pre>";
  else if(cur.tab==="otlp")h="<pre>"+esc(JSON.stringify(otlpJson(sc),null,1))+"</pre>";
  if(!is3d)body.innerHTML=h;
  else if(!t.pinned){cur.v3Token++;stageFrame(sc);v3none.hidden=true;v3msg.textContent=`preview of ${sc.id}: pin a scene (click its row) to load it on the stage and measure it here · ${offlineLine(sc)}`}
  else if(sceneChanged||tabChanged||(force===true&&cur.user)){stageShow(sc,{scroll:cur.user&&tabChanged});cur.user=false}
  ctl.hidden=false;ctl.querySelectorAll("button").forEach(b=>{b.disabled=false})}
/* SIM "open" (film group contract): {id, tab, from} after a SIM.select(id) on a waterfall bar, or {ledger:{kind,m,p,k,t0,t1,reason}, from} on a failed tick / cut stub.
   An id opens that tab (Tether by default); a ledger is matched to its EVENTS row (F-nnn / C-nnn, so the firehose highlights it) or shown as a ledger row of its own. */
function ledgerRow(l){const isCut=l.kind==="cut"||l.calls!=null||(l.kind!=="failed"&&/time box|cap/.test(String(l.reason||"")));const t=l.t1!=null?l.t1:l.t0;
  return isCut?{id:"ledger",kind:"cut",m:l.m,p:l.p,k:l.k,t,ev:{t0:l.t0,t1:t},calls:l.calls!=null?l.calls:l.k,reason:String(l.reason||"cut"),n:null}
    :{id:"ledger",kind:"failed",m:l.m,p:l.p,k:l.k,t,ev:{t0:l.t0!=null?l.t0:t,t1:t},code:String(l.code||(l.kind&&l.kind!=="failed"?l.kind:l.reason)||"failed"),n:null}}
function openFrom(e){if(!e||!self.S)return;
  if(e.ledger){const l=e.ledger,row=ledgerRow(l),near=(a,b)=>a!=null&&b!=null&&Math.abs(a-b)<0.05;
    const hit=self.FH?FH.events().find(x=>x.kind===row.kind&&x.m===l.m&&x.p===l.p&&(row.kind==="cut"?near(x.t,l.t1):(near(x.t,l.t1)||near(x.ev.t0,l.t0)))):null;
    if(hit){cur.ledger=null;if(S.sel!==hit.id)SIM.select(hit.id)}else{if(S.sel!==null)SIM.select(null);cur.ledger=row}  /* after the select: its listener clears the ledger */cur.sig="";render(true)}
  else if(e.id){cur.ledger=null;if(S.sel!==e.id){S.sel=e.id;if(self.LOOP)LOOP.dirty(LOOP.bits.SELECT)}setTab(e.tab||"tether",false)}
  if(e.from&&section){const ins=$("inspector");if(ins)ins.scrollIntoView({behavior:self.FX&&FX.level>0?"smooth":"auto",block:"nearest"})}}
function renderInspector(a,b){let force=true;if(typeof a==="boolean")force=a;else if(a&&typeof a==="object"&&a.id){S.sel=a.id;if(self.LOOP)LOOP.dirty(LOOP.bits.SELECT)}else if(typeof a==="string"){S.sel=a;if(self.LOOP)LOOP.dirty(LOOP.bits.SELECT)}if(typeof b==="boolean")force=b;render(force)}
function setTab(t,user){if(t==="v3d")t="stage";if(!TABS.some(x=>x[0]===t))return;cur.tab=t;cur.user=!!user;[...tabsEl.children].forEach(x=>x.classList.toggle("on",x.dataset.t===t));render(true)}
/* ---------- tamper (36-wall owns the global inject; this is the v3 fallback used only when it is absent) ---------- */
function injectLocal(type,sc){let x=sc.xml;const all=readSteps(x);
  if(type==="edit"){const m=/(translation|size|radius|height|diffuseColor|point)="([^"]*)"/.exec(stripProv(x));if(m)x=x.replace(m[0],`${m[1]}="${m[2]} 9"`);else x=x.replace(/<Scene\b[^>]*>/,m0=>m0+"<!"+"--edited--"+">")}
  else if(type==="del"){const n=all.length>2?2:1;x=x.replace(new RegExp(`<meta name="x3dprov\\.step\\.${n}" content="[^"]*"/>`),"")}
  else if(type==="flipmid"){const st=all.find(([n,c])=>n>=2&&n<all.length&&JSON.parse(c).verdict)||all[1];if(st){const j=JSON.parse(st[1]);if(j.verdict)j.verdict=j.verdict==="valid"?"invalid":"valid";else j.note="edited";x=setStepJson(x,st[0],j)}}
  else if(type==="fliplast"){const st=all[all.length-1],j=JSON.parse(st[1]);if(j.verdict)j.verdict=j.verdict==="valid"?"invalid":"valid";else if(j.model)j.model=j.model+"-x";else j.note="edited";x=setStepJson(x,st[0],j)}
  sc.xml=x;sc.injured={t:performance.now(),type};sc.detected=false;sc.status="verified";S.inj++;
  if(self.logEv)logEv("inj",`${sc.id}: injected ${LABEL[type]} (${sc.sealed?"sealed":"unsealed"} chain)`);if(self.LOOP)LOOP.dirty(LOOP.bits.SCENE|LOOP.bits.VERIFY|LOOP.bits.SELECT)}
function insCtl(type){const t=target(),sc=t.sc;if(!sc)return null;const before=sc.xml;let done=false;
  if(typeof self.inject==="function"){try{const r=self.inject(type,sc,{stage:false});done=!!(r&&(sc.injured||sc.tampered||sc.xml!==before))}catch(e){console.warn("inject (36-wall) failed, local edit instead:",e)}}  /* 36-wall inject(type,target,opts) sets sc.injured (edit/del/flipmid/fliplast) or sc.tampered */
  if(!done)injectLocal(type,sc);
  cur.sig="";if(self.FH)FH.update(sc.id);render(true);if(self.LOOP)LOOP.dirty(LOOP.bits.VERIFY|LOOP.bits.SELECT);return sc}
/* ---------- mount ---------- */
function mount(sec){section=sec;const sb=sec.querySelector(".sb");if($("inspector"))return;
  sub=el("span",{class:"sub",id:"insSub",text:"click a row, a bar, a thumbnail or a wall cell"});pinBtn=el("button",{type:"button",id:"insPin",text:"unpin",title:"follow the newest scene again",onclick:()=>{if(self.SIM)SIM.select(null);else{S.sel=null;render(true)}}});pinBtn.hidden=true;
  tabsEl=el("div",{class:"tabs",id:"tabs"});TABS.forEach(([k,l],i)=>tabsEl.appendChild(el("button",{type:"button",class:i?"":"on",data:{t:k},text:l})));
  body=el("div",{id:"insBody",class:"scroll insBody"});
  v3img=el("img",{alt:""});v3img.hidden=true;v3none=el("div",{id:"v3none"});v3none.hidden=true;v3frame=el("div",{class:"frame"},[v3img,v3none]);v3msg=el("div",{id:"v3msg"});
  view3d=el("div",{id:"view3d"},[v3frame,v3msg,el("div",{class:"v3ctl"},[el("button",{type:"button",text:"SHOW ON THE STAGE ↑",title:"load this scene on the hero stage and scroll to it",onclick:()=>{const t=target();if(t.sc){cur.user=true;stageShow(t.sc,{scroll:true})}}}),
    el("button",{type:"button",text:"MEASURE AGAIN",title:"measure the raw bytes again in the hidden 192×144 canvas",onclick:()=>{const t=target();if(t.sc){measureMemo.delete(t.sc.id+"|"+t.sc.xml.length);stageShow(t.sc,{})}}}),
    el("span",{text:"the measured frame on the left is the counted one (offline pass); the stage above shows the same bytes; nothing is sampled from the stage"})])]);view3d.hidden=true;
  ctl=el("div",{class:"ctl",id:"insCtl"},[el("b",{text:"TAMPER THIS SCENE"})].concat(Object.keys(LABEL).map(k=>el("button",{type:"button",class:"bad",data:{t:k},text:LABEL[k]}))));
  const ins=el("div",{class:"ins",id:"inspector"},[el("header",null,[el("h3",{text:"Inspector"}),sub,el("span",{class:"insR"},[pinBtn])]),tabsEl,body,view3d,ctl]);
  const after=$("fh")?($("fh").nextElementSibling&&$("fh").nextElementSibling.classList.contains("fhStat")?$("fh").nextElementSibling.nextSibling:$("fh").nextSibling):null;sb.insertBefore(ins,after);
  tabsEl.addEventListener("click",e=>{const b=e.target.closest("button[data-t]");if(b)setTab(b.dataset.t,true)});
  body.addEventListener("click",e=>{const go=e.target.closest("a[data-go]");if(go){e.preventDefault();setTab(go.dataset.go,true);return}
    const sl=e.target.closest("a[data-sel]");if(sl){e.preventDefault();if(self.SIM)SIM.select(sl.dataset.sel);return}
    const bl=e.target.closest("a[data-bench]");if(bl){e.preventDefault();const t=target(),sc=t.sc;if(!sc)return;const k=+bl.dataset.att||0,xml=sc.item&&sc.item.B&&sc.item.B[k]||sc.xml;
      if(self.BENCH&&typeof BENCH.load==="function"){try{BENCH.load(xml,`${sc.id} attempt ${k+1}`,{line:+bl.dataset.bench})}catch(err){console.warn("BENCH.load",err)}}const bs=$("bench");if(bs)bs.scrollIntoView({behavior:self.FX&&FX.level>0?"smooth":"auto",block:"start"});return}
    const rr=e.target.closest("button[data-rr]");if(rr){const t=target(),sc=t.sc;if(!sc)return;const tr=rr.closest("tr"),cell=tr&&tr.querySelector("[data-k=val]");if(cell)rerun(rr.dataset.rr,sc,cell,rr)}});
  ctl.addEventListener("click",e=>{const b=e.target.closest("button[data-t]");if(b)insCtl(b.dataset.t)});
  INSPECTOR.panel=LOOP.register({name:"inspector",bit:LOOP.bits.SELECT|LOOP.bits.VERIFY|LOOP.bits.SCENE|LOOP.bits.MODE|LOOP.bits.VAL|LOOP.bits.DATA|LOOP.bits.THEME,rateHz:4,budgetMs:4,draw(){render(false)}});INSPECTOR.panel.renders=0;
  if(self.SIM){SIM.on("select",()=>{cur.user=false;cur.ledger=null;LOOP.onFrame(()=>render(false))});SIM.on("open",openFrom);SIM.on("reset",()=>{cur.preview=null;cur.sig="";measureMemo.clear();portMemo.clear();rehashMemo.clear();LOOP.onFrame(()=>render(true))})}
  if(self.VAL&&VAL.on)VAL.on(()=>{cur.sig="";LOOP.dirty(LOOP.bits.VAL)});
  render(true)}
const INSPECTOR={get tab(){return cur.tab},set tab(t){setTab(t)},target,render,setTab,openFrom,ledgerRow,stageShow,measureMemo,portMemo,rehashMemo,receiptRows,diffHtml,LCSdiff,panel:null,get renders(){return cur.renders}};
if(self.FH&&FH.onMount)FH.onMount(mount);else SECTIONS.register({id:"stream",header:{title:"Firehose + inspector",unit:"inspector (30-firehose absent in this build)",stamps:{source:"RECORDED 17 Oct",validator:"fork@eb4b4b4 recorded",renderer:"X_ITE 16.5.0 offline"},grade:"C",honesty:"inspector only: the firehose module is not in this build"},part:"live.bodies",mount});
try{Object.defineProperty(self,"tab",{get:()=>cur.tab,set:t=>setTab(t),configurable:true})}catch(e){}
Object.assign(self,{INSPECTOR,renderInspector,insCtl,setTab});
})();
