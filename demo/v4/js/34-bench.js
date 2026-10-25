/* 34-bench.js — S10 THE BENCH: edit a scene, get the exact report (SPEC S10; rules 1–2, 4, 11; §6). Globals: BENCH, __bench.
   Editor over any chain body (hero attempt 1 · the selected scene · paste) with a line-number gutter canvas painting a marker per finding line; the report
   from VAL (js-port-of-8dd0d3e, in this browser) as cards with the named deterministic fixes and APPLY buttons; DRAWS? measures the edited body through
   STAGE.measure (the frame the numbers count; the visible stage only mirrors on request); the commit slider shows the recorded verdicts of the loaded body
   per notch (svc@11Oct, 8c0a457 … d5598c4, 8dd0d3e canary) and the live js-port verdict; STAMP THIS EDIT appends repair{kind:"human"} + validate (+ render
   when measured) through HASH.build into a COPY of the chain and pushes it to the wall as src:"bench" (excluded from every aggregate), then shows the receipt.
   Named fixes are text-level ports of the fork's repair_x3d kinds (profile, version, component, xsi, containerField) plus drop-attribute, which follows the
   XSD's own words ("attribute 'x' is not allowed"); the fork names no fix for the rest and the card says so. Read-only when VAL.mode === "none".
   Shim: the commit slider is local (38-ladder's SLIDER is not in the contract yet; request filed). v3: new in v4 (report lines follow v3 628–634).
   Test hooks: __bench {loads, runs, last, fixes, applied, measured, stamped, slider:{notches, active}, readOnly, src}, BENCH.load/set/text/run/apply/applyAll/
   measure/stamp/loadHero/loadSelected/fixesFor/verdictAt, DOM #benchTa #benchGut #benchRep #benchStatus #benchNotches #benchSlider #benchSel #benchVerdict
   #benchMeasure #benchDrawOut #benchStamp #benchReceipt .repApply, panel __panels.benchGutter.marks. */
(function(){
"use strict";
const NOTCHES=[{id:"svc",ref:"svc@11Oct",label:"svc@11Oct"},{id:"8c0a457",ref:"fork@8c0a457"},{id:"c9c9788",ref:"fork@c9c9788"},{id:"688174f",ref:"fork@688174f"},{id:"76fc439",ref:"fork@76fc439"},{id:"d61d4de",ref:"fork@d61d4de"},{id:"eb4b4b4",ref:"fork@eb4b4b4"},{id:"d5598c4",ref:"fork@d5598c4"},{id:"8dd0d3e",ref:"fork@8dd0d3e",label:"8dd0d3e canary"},{id:"port",ref:"js-port-of-8dd0d3e",label:"js-port now"}];
const DEBOUNCE=700,GUT_W=46,HONESTY="RE-RUN HERE · js-port-of-8dd0d3e (agreement with fork@8dd0d3e on 558 recorded bodies measured in S12) · X_ITE 16.5.0 in this browser · nothing you type is sent or stored";
const B={src:null,res:null,fixes:[],applied:[],measured:null,notch:9,readOnly:false,runs:0,loads:0,stamped:[],pending:null,marks:[],ready:false,text:()=>E.ta?E.ta.value:""};
const __bench={loads:0,runs:0,last:null,fixes:[],applied:[],measured:null,stamped:[],slider:{notches:NOTCHES.map(n=>n.id),active:null},readOnly:false,src:null};
const E={};let sec=null,runDeb=null,gutter=null;
const rend=()=>"X_ITE 16.5.0 in this browser · "+(self.ENV&&ENV.gl==="gpu"?"gpu":"software");
const header=()=>({title:"The bench",unit:"edit a scene, get the exact report",stamps:{source:"RE-RUN HERE",validator:"js-port-of-8dd0d3e here",renderer:rend()},grade:"C",honesty:HONESTY});
/* ---------- a light tag scanner (text positions of elements, parents, lines) for fixes and gutter markers ---------- */
const TAG_RE=/<!-{2}[\s\S]*?-{2}>|<!\[CDATA\[[\s\S]*?\]\]>|<\?[\s\S]*?\?>|<!DOCTYPE[^>]*>|<\/([A-Za-z_][\w.:-]*)\s*>|<([A-Za-z_][\w.:-]*)((?:\s+[\w.:-]+\s*=\s*(?:'[^']*'|"[^"]*"))*)\s*(\/?)>/g;
function scan(text){const els=[],stack=[];let m,pos=0,ln=1;TAG_RE.lastIndex=0;const lineAt=i=>{for(;pos<i;pos++)if(text.charCodeAt(pos)===10)ln++;return ln};
  while((m=TAG_RE.exec(text))){if(m[1]){for(let i=stack.length-1;i>=0;i--)if(stack[i].tag===m[1]){stack.length=i;break}continue}if(!m[2])continue;
    const e={tag:m[2],start:m.index,end:m.index+m[0].length,attrs:m[3]||"",self:!!m[4],parent:stack.length?stack[stack.length-1]:null,line:lineAt(m.index)};els.push(e);if(!e.self)stack.push(e)}
  return els}
const attrOf=(e,name)=>{const r=new RegExp("\\s"+name.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+"\\s*=\\s*(?:'([^']*)'|\"([^\"]*)\")");const m=r.exec(e.attrs);return m?(m[1]!=null?m[1]:m[2]):null};
function setAttr(text,e,name,value){const r=new RegExp("(\\s"+name+"\\s*=\\s*)(?:'[^']*'|\"[^\"]*\")");const open=text.slice(e.start,e.end);let out;
  if(r.test(open))out=open.replace(r,(_,p)=>p+"'"+value+"'");else out=open.replace(/^(<[\w.:-]+)/,(_,p)=>p+" "+name+"='"+value+"'");return text.slice(0,e.start)+out+text.slice(e.end)}
function dropAttr(text,e,name){const r=new RegExp("\\s+"+name+"\\s*=\\s*(?:'[^']*'|\"[^\"]*\")");const open=text.slice(e.start,e.end);if(!r.test(open))return null;return text.slice(0,e.start)+open.replace(r,"")+text.slice(e.end)}
const lineStart=(text,line)=>{let i=0;for(let n=1;n<line&&i>=0;n++){i=text.indexOf("\n",i);if(i<0)return -1;i++}return i};
/* ---------- the named fixes ---------- */
function fixesFor(res,text){const out=[];if(!res||!text)return out;const els=scan(text),root=els.find(e=>e.tag==="X3D"),xe=(res.xsd&&res.xsd.errors)||[],notes=(res.xsd&&res.xsd.notes)||[],se=(res.semantic&&res.semantic.errors)||[],fx=(res.semantic&&res.semantic.fixes)||[];
  const push=f=>{out.push(f);return f};
  xe.forEach((l,i)=>{const key="xsd:"+i;let m=/^Line (\d+): Element '([\w.:-]+)', attribute '([\w.:-]+)': The attribute '[\w.:-]+' is not allowed\./.exec(l);
    if(m){const line=+m[1],tag=m[2],attr=m[3];const e=els.find(x=>x.tag===tag&&x.line===line&&attrOf(x,attr)!==null)||els.find(x=>x.tag===tag&&x.line>=line-1&&x.line<=line+1&&attrOf(x,attr)!==null);
      if(e)push({key,kind:"drop-attribute",label:`remove ${attr}='…' from <${tag}> at line ${line} (the XSD names the attribute; nothing else changes)`,line,apply:t=>{const es=scan(t);const q=es.find(x=>x.tag===tag&&x.line===line&&attrOf(x,attr)!==null)||es.find(x=>x.tag===tag&&attrOf(x,attr)!==null);return q?dropAttr(t,q,attr):null}});return}
    m=/^Line (\d+): Element 'X3D': The attribute '(profile|version)' is required but missing\./.exec(l);
    if(m&&root){const a=m[2],v=a==="profile"?"Immersive":versionFor(notes);push({key,kind:a,label:a==="profile"?"set profile='Immersive' on <X3D> (the fork's repair_x3d default; component statements cover the rest)":`set version='${v}' on <X3D> (the lowest bundled schema that has every node)`,line:+m[1],apply:t=>{const r=scan(t).find(x=>x.tag==="X3D");return r?setAttr(t,r,a,v):null}});return}
    if(/noNamespaceSchemaLocation|XMLSchema-instance/.test(l)&&root)push({key,kind:"xsi",label:"XMLSchema-instance namespace http (not https) and a schema location that follows the version",line:+(/^Line (\d+)/.exec(l)||[])[1]||null,apply:fixXsi})});
  notes.forEach((n,i)=>{const m=/^Node '([\w.:-]+)' is not in X3D ([\d.]+); it was added in X3D ([\d.]+)\. Declare version='([\d.]+)'/.exec(n);
    if(m&&root&&!out.some(f=>f.kind==="version"))push({key:"note:"+i,kind:"version",label:`raise version to ${m[4]} (${m[1]} was added there; the schema location and DOCTYPE follow)`,line:root.line,apply:t=>{const r=scan(t).find(x=>x.tag==="X3D");if(!r)return null;let u=setAttr(t,r,"version",m[4]);u=u.replace(/x3d-\d\.\d\.xsd/g,"x3d-"+m[4]+".xsd").replace(/X3D \d\.\d\/\/EN/g,"X3D "+m[4]+"//EN").replace(/x3d-\d\.\d\.dtd/g,"x3d-"+m[4]+".dtd");return u}})});
  fx.forEach((e,i)=>{const msg=e.msg||"";const comps=[...msg.matchAll(/<component name='([^']+)' level='(\d+)'\/>/g)].map(x=>({name:x[1],level:x[2]}));if(!comps.length||!root)return;
    push({key:"fix:"+i,kind:"component",label:`add to <head>: ${comps.map(c=>`<component name='${c.name}' level='${c.level}'/>`).join(" ")} (the fork's repair_x3d adds or raises them; existing statements are raised, never duplicated)`,line:root.line,apply:t=>applyComponents(t,comps)})});
  se.forEach((e,i)=>{const msg=e.msg||"";if(!/^containerfield-/.test(e.id||""))return;const key="sem:"+i;
    let m=/^([\w.:-]+) containerField='([^']*)' but ([\w.:-]+) has no field named/.exec(msg)||/^([\w.:-]+) containerField='([^']*)' targets ([\w.:-]+)\./.exec(msg);let ctag,cf,ptag;
    if(m){ctag=m[1];cf=m[2];ptag=m[3]}else{m=/^([\w.:-]+)\.([\w.:-]+) does not accept a ([\w.:-]+) /.exec(msg);if(m){ptag=m[1];cf=m[2];ctag=m[3]}}
    const use=/Use containerField='([^']+)'/.exec(msg);
    if(!ctag||!use){push({key,kind:"unfixable",label:`${e.id}: the fork's repair_x3d names no deterministic fix here (the node is in the wrong place, not just mis-labelled); a human or model repair is needed`,noApply:true});return}
    const find=t=>{const es=scan(t);return es.find(x=>x.tag===ctag&&x.parent&&x.parent.tag===ptag&&(attrOf(x,"containerField")||"")!==use[1]&&((attrOf(x,"containerField")||cf)===cf))||es.find(x=>x.tag===ctag&&x.parent&&x.parent.tag===ptag&&(attrOf(x,"containerField")||"")!==use[1])};
    const e0=find(text);push({key,kind:"containerField",label:`set containerField='${use[1]}' on the <${ctag}> inside <${ptag}>${e0?" at line "+e0.line:""} (the fork's repair_x3d picks the conventional slot)`,line:e0?e0.line:null,apply:t=>{const q=find(t);return q?setAttr(t,q,"containerField",use[1]):null}})});
  se.forEach((e,i)=>{if(/^containerfield-/.test(e.id||""))return;if(out.some(f=>f.key==="sem:"+i))return;
    const why={"use-before-def":"the fork reorders siblings only inside a RigidBodyCollection; elsewhere moving nodes is a design decision","duplicate-def":"renaming a DEF changes which node every USE and ROUTE means","use-undefined-def":"the fork cannot know which node was meant"}[e.id];
    push({key:"sem:"+i,kind:"unfixable",label:`${e.id}: the fork's repair_x3d names no deterministic fix${why?" ("+why+")":""}; a human or model repair is needed`,noApply:true})});
  return out}
const versionFor=notes=>{const m=notes.map(n=>/added in X3D ([\d.]+)/.exec(n)).find(Boolean);return m?m[1]:"4.0"};
function fixXsi(t){const r=scan(t).find(x=>x.tag==="X3D");if(!r)return null;const v=attrOf(r,"version")||"4.0";let open=t.slice(r.start,r.end);
  open=open.replace(/xmlns:(\w+)='https:\/\/www\.w3\.org\/2001\/XMLSchema-instance'/,(_,p)=>"xmlns:"+p+"='http://www.w3.org/2001/XMLSchema-instance'").replace(/noNamespaceSchemaLocation='[^']*'/,"noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-"+v+".xsd'");
  return t.slice(0,r.start)+open+t.slice(r.end)}
function applyComponents(t,comps){const es=scan(t),root=es.find(x=>x.tag==="X3D");if(!root)return null;let head=es.find(x=>x.tag==="head"&&x.parent===root);let out=t;
  if(!head){const indent=(/\n([ \t]*)<Scene/.exec(t)||[])[1]||"  ";out=t.slice(0,root.end)+"\n"+indent+"<head>\n"+indent+"</head>"+t.slice(root.end);head=scan(out).find(x=>x.tag==="head"&&x.parent&&x.parent.tag==="X3D")}
  comps.forEach(c=>{const es2=scan(out),h=es2.find(x=>x.tag==="head"&&x.parent&&x.parent.tag==="X3D");if(!h)return;const ex=es2.find(x=>x.tag==="component"&&x.parent===h&&attrOf(x,"name")===c.name);
    if(ex){if(+(attrOf(ex,"level")||0)<+c.level)out=setAttr(out,ex,"level",c.level);return}
    const lastComp=es2.filter(x=>x.tag==="component"&&x.parent===h).pop();const ins=lastComp?lastComp.end:h.end;const ind=(/\n([ \t]*)<(?:meta|component|unit)/.exec(out.slice(h.start,h.start+2000))||[])[1]||((/\n([ \t]*)<head/.exec(out)||[])[1]||"  ")+"  ";
    out=out.slice(0,ins)+"\n"+ind+`<component name='${c.name}' level='${c.level}'/>`+out.slice(ins)});
  return out}
/* where a finding points in the text (XSD "Line N"; a quoted DEF/USE name; a named node), for the gutter and the line buttons */
function lineOfFinding(text,code,msg,els){let m=/\bline (\d+)\b/i.exec(msg);if(m)return+m[1];
  const q=[...msg.matchAll(/'([^']+)'/g)].map(x=>x[1]);for(const name of q){const e=els.find(x=>attrOf(x,"DEF")===name||attrOf(x,"USE")===name);if(e)return e.line}
  if(/^route-/.test(code)){const fr=/fromNode='([^']+)'|from '([^']+)'/.exec(msg);const e=els.find(x=>x.tag==="ROUTE"&&(!fr||(attrOf(x,"fromNode")===(fr[1]||fr[2]))));if(e)return e.line}
  m=/^([A-Z][\w]*)/.exec(msg);if(m){const e=els.find(x=>x.tag===m[1]);if(e)return e.line}return null}
function marksFor(res,text){const out=[];if(!res)return out;const els=scan(text);((res.xsd&&res.xsd.errors)||[]).forEach(l=>{const m=/^Line (\d+)/.exec(l);if(m)out.push({line:+m[1],tone:"bad"})});
  const S=res.semantic||{};(S.errors||[]).forEach(e=>{const l=lineOfFinding(text,e.id||"",e.msg||"",els);if(l)out.push({line:l,tone:"bad"})});(S.warnings||[]).forEach(e=>{const l=lineOfFinding(text,e.id||"",e.msg||"",els);if(l)out.push({line:l,tone:"warn"})});
  (S.fixes||[]).forEach(()=>{const r=els.find(x=>x.tag==="head")||els.find(x=>x.tag==="X3D");if(r)out.push({line:r.line,tone:"ok"})});return out}
/* ---------- verdict per notch for the loaded body ---------- */
function verdictAt(id){const s=B.src,res=B.res,edited=s?B.text()!==s.xml0:true;
  if(id==="port"){if(B.readOnly)return{state:"grey",why:"exact validator not available in this viewer"};if(!res)return{state:"pending",why:"not validated yet"};return{state:"live",valid:!!res.valid,codes:codesOfRes(res),ms:res.ms,ref:"js-port-of-8dd0d3e here"}}
  if(edited||!s)return{state:"grey",why:"not recorded for this text"};
  const it=s.item;
  if(s.kind==="real"&&it){if(id==="svc"){const ok=!!(it.x&&it.s);return{state:"rec",valid:ok,codes:ok?[]:[it.x?"semantic":"xsd"],ref:"svc@11Oct recorded"}}
    if(id==="8dd0d3e"&&self.DRIFT){const v=DRIFT.v8dd0d3e.verdicts["replay/"+it.k];if(v)return{state:"rec",valid:!!v.valid,codes:(v.xsd?[]:["xsd"]).concat(v.sem||[]),ref:"fork@8dd0d3e recorded"}}
    if(id==="8c0a457"&&it.f1)return{state:"rec",valid:!!it.f1[0],codes:it.f1[1]||[],ref:"fork@8c0a457 recorded"};if(id==="eb4b4b4"&&it.f2)return{state:"rec",valid:!!it.f2[0],codes:it.f2[1]||[],ref:"fork@eb4b4b4 recorded"};
    if(self.DRIFT&&DRIFT.by_commit[id]){const v=DRIFT.by_commit[id][it.k];if(v)return{state:"rec",valid:!!v.valid,codes:v.codes||[],ref:"fork@"+id+" recorded"}}
    return{state:"grey",why:"not recorded for this body"}}
  if(s.kind==="live"&&it){const a=it.A[s.k];if(id==="eb4b4b4"&&a)return{state:"rec",valid:!!a.ok,codes:codesOf(a),ms:a.vms,ref:"fork@eb4b4b4 recorded"};
    if(id==="8dd0d3e"&&self.DRIFT){const v=DRIFT.v8dd0d3e.verdicts["live-2026-10-17/x3d/"+keyOf(it.m,it.p,s.k+1)];if(v)return{state:"rec",valid:!!v.valid,codes:(v.xsd?[]:["xsd"]).concat(v.sem||[]),ref:"fork@8dd0d3e recorded"}}
    return{state:"grey",why:"not recorded for this text"}}
  return{state:"grey",why:"not recorded for this text"}}
/* ---------- DOM ---------- */
function build(sb){sb.textContent="";
  E.bar=el("div",{class:"benchBar row"},[el("span",{class:"legend",text:"Load:"}),E.bHero=el("button",{id:"benchHero",text:"hero attempt 1",onclick:()=>BENCH.loadHero()}),E.bSel=el("button",{id:"benchSelScene",text:"selected scene",disabled:true,onclick:()=>BENCH.loadSelected()}),E.bPaste=el("button",{id:"benchPaste",text:"paste",onclick:()=>BENCH.paste()}),
    E.src=el("span",{id:"benchSrc",class:"note m"}),el("span",{class:"legend",text:"· Validator:"}),E.sliderWrap=el("span",{class:"benchSliderWrap"},[E.notches=el("span",{id:"benchNotches",class:"benchNotches"}),E.slider=el("input",{id:"benchSlider",type:"range",min:"0",max:String(NOTCHES.length-1),step:"1",value:String(B.notch),"aria-label":"validator commit"}),E.sel=el("select",{id:"benchSel","aria-label":"validator commit"})]),E.verdict=el("span",{id:"benchVerdict",class:"note m"})]);
  NOTCHES.forEach((n,i)=>{E.notches.appendChild(el("button",{type:"button",class:"notch",data:{i:String(i),id:n.id},text:n.label||n.id,title:n.ref,onclick:()=>setNotch(i)}));E.sel.appendChild(el("option",{value:String(i),text:n.label||n.id}))});
  E.slider.addEventListener("input",e=>setNotch(+e.target.value));E.sel.addEventListener("change",e=>setNotch(+e.target.value));
  E.status=el("div",{id:"benchStatus",class:"benchStatus m"});
  E.ta=el("textarea",{id:"benchTa",class:"m",spellcheck:"false",wrap:"off","aria-label":"scene source"});E.gut=el("canvas",{id:"benchGut",class:"benchGut","aria-hidden":"true"});
  E.edSub=el("span",{class:"sub",id:"benchEdSub"});E.fixList=el("div",{id:"benchFixes",class:"benchFixes"});
  const ed=el("div",{class:"panel benchEd"},[el("header",null,[el("h3",{text:"Scene"}),E.edSub]),el("div",{class:"benchEditor"},[E.gut,E.ta]),E.fixList]);
  E.rep=el("div",{id:"benchRep",class:"benchRep"});E.repSub=el("span",{class:"sub",id:"benchRepSub"});
  const rep=el("div",{class:"panel benchReport"},[el("header",null,[el("h3",{text:"Report"}),E.repSub]),E.rep]);
  E.bMeasure=el("button",{id:"benchMeasure",class:"primary",text:"DRAWS?",title:"measure the edited body on the hidden 192×144 X_ITE canvas (raw bytes, own/default viewpoint, headlight)",onclick:()=>BENCH.measure()});
  E.auto=el("input",{type:"checkbox",id:"benchAuto"});E.bShow=el("button",{id:"benchShow",text:"show on the stage",title:"load the edited body on the visible stage (a mirror; the measured frame is the number)",onclick:()=>BENCH.show()});
  E.series=el("canvas",{id:"benchSeries",class:"benchSeries"});E.drawOut=el("div",{id:"benchDrawOut",class:"note m"});
  E.bStamp=el("button",{id:"benchStamp",class:"primary",text:"STAMP THIS EDIT",onclick:()=>BENCH.stamp()});E.stampNote=el("span",{id:"benchStampNote",class:"note m"});E.receipt=el("div",{id:"benchReceipt",class:"benchReceipt m"});
  const draw=el("div",{class:"panel benchDraw"},[el("header",null,[el("h3",{text:"Draws?"}),el("span",{class:"sub",text:"STAGE.measure · 192×144 · MEASURED here"})]),el("div",{class:"row"},[E.bMeasure,el("label",null,[E.auto,"after edits"]),E.bShow]),E.series,E.drawOut,
    el("div",{class:"row benchStampRow"},[E.bStamp,E.stampNote]),E.receipt]);
  sb.append(E.bar,E.status,el("div",{class:"benchGrid"},[ed,rep,draw]));
  E.ta.addEventListener("input",onInput);E.ta.addEventListener("scroll",()=>{GL.top=E.ta.scrollTop;if(gutter)gutter.forceDraw=true},{passive:true});if(typeof ResizeObserver!=="undefined")new ResizeObserver(es=>{for(const e of es)GL.h=Math.round(e.contentRect.height);if(gutter)gutter.forceDraw=true}).observe(E.ta);E.ta.addEventListener("keydown",e=>{if(e.key==="Tab"&&!e.shiftKey&&!B.readOnly){e.preventDefault();const s=E.ta.selectionStart,t=E.ta.value;E.ta.value=t.slice(0,s)+"  "+t.slice(E.ta.selectionEnd);E.ta.selectionStart=E.ta.selectionEnd=s+2;onInput()}});
  E.rep.addEventListener("click",e=>{const a=e.target.closest(".repApply");if(a){BENCH.apply(a.dataset.fix);return}const l=e.target.closest("[data-line]");if(l)gotoLine(+l.dataset.line)});
  E.fixList.addEventListener("click",e=>{const a=e.target.closest("button[data-fix]");if(a)BENCH.apply(a.dataset.fix);const all=e.target.closest("#benchApplyAll");if(all)BENCH.applyAll()});
  E.auto.checked=!!(self.FX&&FX.level>0);
  gutter=LOOP.register({name:"benchGutter",bit:LOOP.bits.VAL|LOOP.bits.THEME|LOOP.bits.RESIZE,el:E.gut,rateHz:self.FX&&FX.level>0?30:15,budgetMs:3,draw:drawGutter,degrade(ms){if(gutter.rateHz>8)gutter.rateHz=Math.max(8,gutter.rateHz-5)}});gutter.marks=0;
  LOOP.register({name:"benchSeries",bit:LOOP.bits.VAL|LOOP.bits.THEME|LOOP.bits.RESIZE,el:E.series,rateHz:4,draw:drawSeries});
  setNotch(B.notch);paintStatus()}
function gotoLine(n){const t=E.ta.value;const i=lineStart(t,n);if(i<0)return;const lh=lineH();E.ta.focus();E.ta.setSelectionRange(i,i);E.ta.scrollTop=Math.max(0,(n-4)*lh);if(gutter)gutter.forceDraw=true}
const lineH=()=>{const v=parseFloat(getComputedStyle(E.ta).lineHeight);return isFinite(v)&&v>0?v:17};
/* gutter: a cached offscreen layer holding the WHOLE document's gutter (numbers + marks), repainted only when text, marks, dpr or theme change;
   a scroll or resize just blits the visible slice (one drawImage). An unchanged key draws nothing (the canvas keeps its pixels). Line metrics are
   read from computed style only on a layer repaint. Documents taller than LAYER_MAX css px fall back to a windowed repaint of the visible lines. */
const GL={lkey:"",bkey:"",off:null,text:null,textDirty:true,n:1,lh:17,pad:6,windowed:false,top:0,h:0},LAYER_MAX=12000;
function gutterLines(){if(!GL.textDirty&&GL.text!=null)return GL.n;GL.textDirty=false;const t=E.ta.value;if(t!==GL.text){GL.text=t;let n=1;for(let i=t.indexOf("\n");i>=0;i=t.indexOf("\n",i+1))n++;GL.n=n}return GL.n}
function paintGutterLines(ctx,w,first,last,yOf,lh,pad){ctx.font="500 10.5px "+cssv("--mono");ctx.textAlign="right";ctx.textBaseline="middle";const marks=new Map();B.marks.forEach(m=>{const t=marks.get(m.line);if(!t||t==="warn"&&m.tone==="bad"||t==="ok"&&m.tone!=="ok")marks.set(m.line,m.tone)});gutter.marks=B.marks.length;
  const bg={bad:cssv("--badbg"),warn:cssv("--warnbg"),ok:cssv("--okbg")},fgs={bad:cssv("--bad"),warn:cssv("--warn"),ok:cssv("--ok")},fg=cssv("--fg"),dim=cssv("--dim");
  for(let l=first;l<=last;l++){const y=yOf(l);const tone=marks.get(l);if(tone){ctx.fillStyle=bg[tone];ctx.fillRect(0,y-lh/2,w,lh);ctx.fillStyle=fgs[tone];ctx.beginPath();ctx.arc(w-6,y,2.5,0,Math.PI*2);ctx.fill()}
    ctx.fillStyle=tone?fg:dim;ctx.fillText(String(l),w-13,y)}}
function drawGutter(){if(!E.gut||!E.ta)return;if(!GL.h){GL.h=E.ta.clientHeight;GL.top=E.ta.scrollTop}const h=GL.h||200,top=GL.top,dpr=Math.min(3,window.devicePixelRatio||1),theme=cssv("--p0")+cssv("--fg"),n=gutterLines();
  const lkey=[GL.text.length,n,B.marks,dpr,theme].join("|"),bkey=lkey+"|"+top+"|"+h;if(bkey===GL.bkey)return;
  if(lkey!==GL.lkey){const cs=getComputedStyle(E.ta);const v=parseFloat(cs.lineHeight);GL.lh=isFinite(v)&&v>0?v:17;GL.pad=parseFloat(cs.paddingTop)||6;GL.lkey=lkey;GL.windowed=GL.pad*2+n*GL.lh>LAYER_MAX;
    if(!GL.windowed){if(!GL.off)GL.off=document.createElement("canvas");const H=Math.ceil(GL.pad*2+n*GL.lh),{ctx,w}=fitCanvas(GL.off,GUT_W,H);ctx.clearRect(0,0,w,H);ctx.fillStyle=cssv("--p0");ctx.fillRect(0,0,w,H);
      paintGutterLines(ctx,w,1,n,l=>GL.pad+(l-1)*GL.lh+GL.lh/2,GL.lh,GL.pad);ctx.fillStyle=cssv("--line");ctx.fillRect(w-1,0,1,H)}}
  GL.bkey=bkey;const lh=GL.lh,pad=GL.pad,o=fitCanvas(E.gut,GUT_W,h);o.ctx.clearRect(0,0,o.w,o.h);
  if(!GL.windowed){o.ctx.fillStyle=cssv("--p0");o.ctx.fillRect(0,0,o.w,o.h);const sy=Math.round(top*o.dpr),sh=Math.min(GL.off.height-sy,Math.round(h*o.dpr));if(sh>0)o.ctx.drawImage(GL.off,0,sy,GL.off.width,sh,0,0,o.w,sh/o.dpr);return}
  const ctx=o.ctx,w=o.w;ctx.fillStyle=cssv("--p0");ctx.fillRect(0,0,w,h);const first=Math.max(1,Math.floor((top-pad)/lh)+1),last=Math.min(n,first+Math.ceil(h/lh)+1);
  paintGutterLines(ctx,w,first,last,l=>pad+(l-1)*lh-top+lh/2,lh,pad);ctx.fillStyle=cssv("--line");ctx.fillRect(w-1,0,1,h)}
function drawSeries(){if(!E.series)return;const W=E.series.clientWidth||300,H=44,{ctx,w,h}=fitCanvas(E.series,W,H);ctx.clearRect(0,0,w,h);ctx.fillStyle=cssv("--p0");ctx.fillRect(0,0,w,h);const m=B.measured;
  ctx.font="500 10.5px "+cssv("--mono");ctx.fillStyle=cssv("--dim");ctx.textBaseline="top";
  if(!m||!m.series||!m.series.length){ctx.fillText(m&&m.err?"X_ITE refused: "+m.err.slice(0,60):m&&m.noFrame?"no frame yet":"nonblank per sampled frame · press DRAWS?",6,4);return}
  const s=m.series,n=s.length,mx=Math.max(.01,...s),bw=Math.max(2,Math.floor((w-12)/n)-2);s.forEach((v,i)=>{const bh=Math.max(1,Math.round((h-16)*v/mx));ctx.fillStyle=cssv(v<.005?"--warn":"--acc");ctx.fillRect(6+i*(bw+2),h-4-bh,bw,bh)});
  ctx.fillStyle=cssv("--mute");ctx.fillText(`${n} samples · best ${fmt.pct(m.nb)} · 0.5 % line`,6,2);ctx.fillStyle=cssv("--line2");const y=h-4-Math.round((h-16)*.005/mx);ctx.fillRect(6,y,w-12,1)}
/* ---------- state → DOM (DOM is patched on events, never on a timer; the two canvases are LOOP panels) ---------- */
function paintStatus(){if(!E.status)return;const mode=self.VAL?VAL.mode:"unloaded";B.readOnly=mode==="none";__bench.readOnly=B.readOnly;E.ta.readOnly=B.readOnly;E.bStamp.disabled=B.readOnly||!B.res;
  const st=self.VAL&&VAL.status;let t;if(mode==="full")t=`js-port-of-8dd0d3e ready in this browser (${st&&st.transport||"worker"}${st&&st.compileMs&&st.compileMs["4.0"]!=null?", XSD 4.0 compiled in "+fmt.ms(st.compileMs["4.0"]):""}) · every verdict below is measured here · nothing you type is sent or stored`;
  else if(mode==="none")t=`READ-ONLY · exact validator not available in this viewer: ${VAL.reason} · recorded reports shown where the body is recorded; the fixes cannot be applied`;
  else t=`validator loading in this browser (${st&&st.phase||"…"}${st&&st.note?": "+st.note:""}; the XSD compiles in a worker, about 3 s) · the editor is live, the report follows`;
  txt(E.status,t);E.status.dataset.mode=mode;E.status.classList.toggle("ro",B.readOnly)}
function paintSrc(){GL.textDirty=true;const s=B.src;txt(E.src,s?`loaded: ${s.label}${B.applied.length?" · "+B.applied.length+" fix"+(B.applied.length===1?"":"es")+" applied here":""}${B.text()!==s.xml0?" · EDITED":""}`:"nothing loaded");
  const n=E.ta.value.split("\n").length;txt(E.edSub,`${n} lines · ${fmt.int(E.ta.value.length)} chars${B.src&&B.text()!==B.src.xml0?" · edited in this browser":""}`);__bench.src=s?{label:s.label,kind:s.kind,k:s.k}:null}
function paintReport(){const res=B.res;if(!res){E.rep.textContent="";E.rep.appendChild(el("div",{class:"placeholder",text:B.readOnly?"no recorded report for this body in this viewer":"the report appears 700 ms after the last keystroke"}));txt(E.repSub,"");return}
  const fixes=new Map();B.fixes.forEach(f=>{if(!f.noApply)fixes.set(f.key,f)});E.rep.innerHTML=reportHtml(res,{fixes});   /* built from data through esc() on a user event, never on a timer */
  const xe=((res.xsd&&res.xsd.errors)||[]).length,se=((res.semantic&&res.semantic.errors)||[]).length,fx=B.fixes.filter(f=>!f.noApply).length;
  txt(E.repSub,res.recorded?`recorded · ${res.label}`:`${xe} XSD · ${se} semantic · ${fx} named fix${fx===1?"":"es"}`);
  E.fixList.textContent="";if(B.readOnly||!B.fixes.length){if(B.fixes.length)E.fixList.appendChild(el("span",{class:"note",text:"fixes are shown, not applied: read-only in this viewer"}));return}
  E.fixList.appendChild(el("b",{text:"Fix what the validator named: "}));const ap=B.fixes.filter(f=>!f.noApply);
  if(ap.length>1)E.fixList.appendChild(el("button",{id:"benchApplyAll",class:"primary",text:`APPLY ALL ${ap.length}`}));
  ap.forEach(f=>E.fixList.appendChild(el("button",{data:{fix:f.key},class:"benchFix",text:`${f.kind}${f.line?" · line "+f.line:""}`,title:f.label})));
  const un=B.fixes.filter(f=>f.noApply);if(un.length)E.fixList.appendChild(el("span",{class:"note",text:` · ${un.length} finding${un.length===1?"":"s"} without a deterministic fix (the fork names none)`}));
  if(!ap.length&&!un.length)E.fixList.appendChild(el("span",{class:"note",text:"nothing to fix"}))}
function paintNotches(){NOTCHES.forEach((n,i)=>{const v=verdictAt(n.id),b=E.notches.children[i];b.className="notch "+(v.state==="grey"?"grey":v.state==="pending"?"pending":v.valid?"v":"i")+(i===B.notch?" on":"")+(v.state==="live"?" live":"");b.title=v.state==="grey"?n.ref+" · "+v.why:v.state==="pending"?n.ref+" · "+v.why:`${v.ref} · ${v.valid?"VALID":"INVALID"}${v.codes&&v.codes.length?" · "+v.codes.join(", "):""}`});
  const n=NOTCHES[B.notch],v=verdictAt(n.id);__bench.slider.active={id:n.id,...v};
  txt(E.verdict,v.state==="grey"?`${n.ref}: ${v.why}`:v.state==="pending"?`${n.ref}: ${v.why}`:`${v.ref} · ${v.valid?"VALID":"INVALID"}${v.codes&&v.codes.length?" · "+v.codes.join(", "):""}${v.ms!=null?" · "+(v.ms<10?(+v.ms).toFixed(1)+" ms":fmt.ms(v.ms)):""}`)}
function setNotch(i){B.notch=UTIL.clamp(i|0,0,NOTCHES.length-1);E.slider.value=String(B.notch);E.sel.value=String(B.notch);paintNotches()}
function paintDraw(){const m=B.measured;if(!m){txt(E.drawOut,"not measured yet · DRAWS? loads the edited body on the hidden measure canvas and samples inside X_ITE's finishEvents callback");return}
  const stale=m.hash!==contentHash(E.ta.value);
  txt(E.drawOut,`MEASURED here · ${m.err?"X_ITE refused: "+m.err:m.noFrame?(m.kind||"no frame yet"):`${m.frames} frames · nonblank ${fmt.pct(m.nb)} · ${m.kind}`} · X_ITE 16.5.0 in this browser · ${self.ENV&&ENV.renderer||"renderer ?"} · ${fmt.ms(m.ms)}${m.msgs&&m.msgs.length?" · X_ITE said: "+m.msgs.slice(0,2).join(" · "):" · X_ITE said nothing"}${stale?" · (text changed since: measure again)":""}`);
  if(gutter)LOOP.dirty(LOOP.bits.VAL)}
/* ---------- editing and validation ---------- */
function onInput(){B.measuredStale=true;paintSrc();if(runDeb)runDeb();E.bStamp.disabled=true}
async function run(){if(!E.ta)return null;const text=E.ta.value;B.runs++;__bench.runs=B.runs;
  if(!self.VAL||VAL.mode!=="full"){if(VAL&&VAL.mode==="unloaded"){VAL.need();VAL.ready.then(()=>{paintStatus();if(VAL.mode==="full")run()})}
    B.res=recordedReport();B.fixes=B.res?fixesFor(B.res,text):[];B.marks=B.res?marksFor(B.res,text):[];__bench.last=B.res;__bench.fixes=B.fixes.map(f=>({key:f.key,kind:f.kind,label:f.label,line:f.line||null}));paintStatus();paintReport();paintNotches();if(gutter)gutter.forceDraw=true;return B.res}
  let res;try{res=await VAL.validate(text)}catch(e){res={valid:null,error:String(e&&e.message||e),xsd:{errors:[]},semantic:{errors:[],warnings:[],info:[],fixes:[]}}}
  if(E.ta.value!==text)return null;   /* a newer keystroke owns the next run */
  B.res=res;B.fixes=fixesFor(res,text);B.marks=marksFor(res,text);__bench.last=res;__bench.fixes=B.fixes.map(f=>({key:f.key,kind:f.kind,label:f.label,line:f.line||null}));
  paintStatus();paintReport();paintNotches();paintSrc();E.bStamp.disabled=!res||res.valid==null;if(gutter)gutter.forceDraw=true;LOOP.dirty(LOOP.bits.VAL);
  if(E.auto.checked&&!isParse(res)&&res.valid!=null&&self.STAGE&&STAGE.measure&&STAGE.measure.browser)BENCH.measure();
  if(B.pending){const p=B.pending;B.pending=null;p(res)}return res}
const isParse=res=>!!(res&&res.xsd&&res.xsd.errors&&res.xsd.errors.length===1&&/^XML parse error/.test(res.xsd.errors[0]));
/* read-only viewers: the recorded report of the loaded attempt (fork@eb4b4b4 lines as recorded on 17 Oct), nothing re-validated */
function recordedReport(){const s=B.src;if(!s||!s.item||B.text()!==s.xml0)return null;
  const parse=l=>{const m=/^-\s*\*\*\[([\w-]+)\]\*\*\s*(.*)$/.exec(l);return m?{id:m[1],msg:m[2]}:{id:"semantic",msg:l}};
  if(s.kind==="live"){const a=s.item.A[s.k];if(!a)return null;return{valid:!!a.ok,recorded:true,label:"fork@eb4b4b4 recorded",ms:a.vms,xsd:{valid:!!a.x,errors:a.xe||[]},semantic:{status:"recorded",errors:(a.se||[]).map(parse),warnings:[],info:[],fixes:(a.fx||[]).map(parse)}}}
  if(s.kind==="real"){const it=s.item,ok=!!it.f2[0];return{valid:ok,recorded:true,label:"fork@eb4b4b4 recorded",ms:null,xsd:{valid:!(it.f2[1]||[]).includes("xsd"),errors:[]},semantic:{status:"recorded",errors:(it.f2[1]||[]).filter(c=>c!=="xsd").map(c=>({id:c,msg:"recorded code (the 11 Oct replay kept codes, not lines)"})),warnings:[],info:[],fixes:[]}}}
  return null}
function measure(){if(!self.STAGE||!STAGE.measure)return Promise.resolve(null);const text=E.ta.value;if(!text.trim())return Promise.resolve(null);E.bMeasure.disabled=true;txt(E.drawOut,"measuring on the hidden canvas (SwiftShader can take seconds) …");
  return STAGE.measure.show(text,{timeoutMs:15000}).then(r=>{if(!r||r.cancelled)return r;B.measured=Object.assign({hash:contentHash(text)},r);__bench.measured=B.measured;paintDraw();LOOP.dirty(LOOP.bits.VAL);return r}).finally(()=>{E.bMeasure.disabled=false})}
async function stamp(){if(B.readOnly||!self.SIM||!self.S)return null;const text=E.ta.value;if(!B.res||B.resText!==text){B.resText=text;await run()}const res=B.res;if(!res||res.valid==null)return null;
  E.bStamp.disabled=true;txt(E.stampNote,"building the chain through HASH …");
  const s=B.src,base=s&&s.sc?s.sc.xml:(s?s.xml0:text),sealed=!!(self.HASH&&HASH.sealOn),verdict=res.valid?"valid":"invalid",m=B.measured&&B.measured.hash===contentHash(text)?B.measured:null;
  const steps=[{step:{op:"repair",kind:"human",agent:"viewer edit",agent_ref:"this browser",round:1,report_shown:true,fixes:B.applied.map(a=>a.kind),chars_before:(s?s.xml0:text).length,chars_after:text.length,source:s?s.label:"paste",ms:0,ms_src:"none"},after:text,seal:sealed},
    {step:{op:"validate",validator:"js-port",validator_ref:"js-port-of-8dd0d3e",verdict,codes:codesOfRes(res),xsd_valid:!!(res.xsd&&res.xsd.valid),n_errors:((res.xsd&&res.xsd.errors)||[]).length+((res.semantic&&res.semantic.errors)||[]).length,ms:res.ms||0,ms_src:"measured"},seal:sealed}];
  if(m)steps.push({step:{op:"render",renderer:`x_ite@16.5.0 in this browser (${self.ENV&&ENV.renderer||"unknown renderer"})`,load_ok:!m.err,nodes:m.nodes??0,nonblank_ratio:m.nb??0,frames_watched:m.frames||0,no_frame:m.noFrame?1:0,parser_msgs:(m.msgs||[]).length,unknown_nodes:0,ms:m.ms||0,ms_src:"measured"},seal:sealed});
  let xml;try{xml=await HASH.build(base,steps)}catch(e){txt(E.stampNote,"HASH refused: "+String(e&&e.message||e));E.bStamp.disabled=false;return null}
  const sc=SIM.addViewerScene({src:"bench",item:s&&s.item||null,model:"viewer edit",mode:"bench",verdict,xml,nb:m?m.nb:null,blank:m?(m.nb||0)<.005:false,drawKind:m?m.kind:"not measured",port:res,vref:"js-port-of-8dd0d3e",sealed,label:s?s.label:"paste",nsteps:0});
  B.stamped.push(sc.id);__bench.stamped=B.stamped.slice();receipt(sc);E.bStamp.disabled=false;
  if(self.SIM&&SIM.select)SIM.select(sc.id);if(typeof self.renderInspector==="function")try{renderInspector(sc)}catch(e){}
  return sc}
function receipt(sc){const steps=readSteps(sc.xml),vr=verify(sc.xml);E.receipt.textContent="";
  txt(E.stampNote,`${sc.id} on the wall · src bench · excluded from every aggregate${self.S&&S.flags.includeMine?"":" (include my runs is off)"}`);
  const head=el("div",{class:"row"},[el("span",{class:"pill "+(vr.ok?"p-ok":"p-bad"),text:vr.status}),el("span",{text:`${sc.id} · ${steps.length} steps · head ${contentHash(sc.xml).slice(0,16)}… · ${sc.sealed?"sealed (HMAC stand-in, key in the page)":"unsealed"} · a copy: the recorded chain is untouched`})]);
  const tb=el("table",{class:"benchSteps"},[el("thead",null,el("tr",null,["n","op","who / what","in → out","prev"].map(h=>el("th",{text:h})))),el("tbody",null,steps.map(([n,c])=>{const r=JSON.parse(c);
    const who=r.op==="validate"?`${r.validator_ref} → ${r.verdict}${r.codes&&r.codes.length?" · "+r.codes.join(", "):""}`:r.op==="repair"?`${r.agent||r.model||"model"}${r.kind?" · "+r.kind:""}${r.fixes&&r.fixes.length?" · fixes "+r.fixes.join(", "):""}`:r.op==="render"?`${r.renderer} · nonblank ${fmt.pct(r.nonblank_ratio||0)}`:r.op==="generate"?`${r.model||""} ${r.condition||""}`:r.op;
    return el("tr",{class:n>steps.length-3?"new":""},[el("td",{text:String(n)}),el("td",null,el("span",{class:"pill "+({generate:"p-info",validate:"p-ok",repair:"p-warn",render:"p-mute"}[r.op]||"p-mute"),text:r.op})),el("td",{text:who}),el("td",{text:`${String(r.input_sha256).slice(0,10)} → ${String(r.output_sha256).slice(0,10)}`}),el("td",{text:String(r.prev).slice(0,10)})])}))]);
  E.receipt.append(head,el("div",{class:"scroll benchScroll"},tb),el("div",{class:"note",text:"receipt: steps added here = repair {kind:\"human\", agent:\"viewer edit\", report_shown:true} + validate on js-port-of-8dd0d3e"+(steps.some(([,c])=>/in this browser/.test(c))?" + render measured here":"")+" · verify() = prev-hash chain, input/output continuity, content hash of the head · page-normalised SHA-256, not the repo's C14N"}))}
/* ---------- public ---------- */
const BENCH={
  load(xml,label,meta){if(!E.ta)return;meta=meta||{};B.src={label:label||"paste",kind:meta.kind||"paste",item:meta.item||null,k:meta.k||0,sc:meta.sc||null,xml0:String(xml)};B.applied=[];__bench.applied=[];B.measured=null;__bench.measured=null;B.res=null;B.fixes=[];B.marks=[];
    E.ta.value=String(xml);E.ta.scrollTop=0;B.loads++;__bench.loads=B.loads;paintSrc();paintReport();paintDraw();paintNotches();E.receipt.textContent="";txt(E.stampNote,"");if(gutter)gutter.forceDraw=true;if(runDeb)runDeb.cancel();return run()},
  set(text){if(!E.ta)return;E.ta.value=String(text);onInput();if(runDeb)runDeb.cancel();return run()},
  text(){return E.ta?E.ta.value:""},
  run(){if(runDeb)runDeb.cancel();return run()},
  loadHero(){const h=self.HERO&&HERO.items&&HERO.items[0];if(!h)return null;const it=self.LIVE&&LIVE[h.idx];if(!it||!it.B||!it.B[0])return null;   /* the mount's DATA.on("live.bodies") retries */
    return BENCH.load(it.B[0],`hero ${it.p} · ${it.m} · attempt 1 of ${it.A.length} · RECORDED 17 Oct`,{kind:"live",item:it,k:0})},
  loadAttempt(it,k){if(!it||!it.B||!it.B[k])return null;return BENCH.load(it.B[k],`${it.p} · ${it.m} · attempt ${k+1} of ${it.A.length} · RECORDED 17 Oct`,{kind:"live",item:it,k})},
  loadSelected(){const sc=self.S&&S.sel&&S.byId.get(S.sel);if(!sc)return null;const kind=sc.src==="live"?"live":sc.src==="real"?"real":"scene";const it=sc.item||null;const k=it&&it.A?it.A.length-1:0;
    return BENCH.load(stripProv(sc.xml),`${sc.id} · ${sc.model||sc.src}${kind==="live"?" · final attempt "+(k+1):kind==="real"?" · RECORDED 11 Oct":""}`,{kind,item:it,k,sc})},
  paste(){if(!E.ta)return;if(B.src&&B.src.kind==="paste"&&E.ta.value){return}const seed="<X3D profile='Interchange' version='4.0'>\n  <Scene>\n    <Viewpoint description='bench' position='0 0 6'/>\n    <Shape>\n      <Appearance><Material diffuseColor='0.9 0.5 0.2'/></Appearance>\n      <Box/>\n    </Shape>\n  </Scene>\n</X3D>\n";
    BENCH.load(seed,"paste · your own scene (nothing you type is sent or stored)",{kind:"paste"});E.ta.focus();E.ta.select()},
  apply(key){if(B.readOnly)return null;const f=B.fixes.find(x=>x.key===key&&!x.noApply);if(!f)return null;const t=E.ta.value,u=f.apply(t);if(u==null||u===t){txt(E.stampNote,`fix ${f.kind}: nothing matched in the current text`);return null}
    E.ta.value=u;B.applied.push({kind:f.kind,label:f.label});__bench.applied=B.applied.slice();onInput();if(runDeb)runDeb.cancel();return run()},
  applyAll(){if(B.readOnly)return null;let t=E.ta.value,n=0;B.fixes.filter(f=>!f.noApply).forEach(f=>{const u=f.apply(t);if(u!=null&&u!==t){t=u;n++;B.applied.push({kind:f.kind,label:f.label})}});if(!n)return null;__bench.applied=B.applied.slice();E.ta.value=t;onInput();if(runDeb)runDeb.cancel();return run()},
  measure,stamp,show(){if(!self.STAGE||!STAGE.show)return null;return STAGE.show.load(E.ta.value,{scene:{id:"bench"}})},
  fixesFor,verdictAt,setNotch,notches:NOTCHES,scan,
  get res(){return B.res},get src(){return B.src}};
SECTIONS.register({id:"bench",header:header(),part:"live.bodies",
  mount(section){sec=section;const sb=section.querySelector(".sb");build(sb);runDeb=debounce(run,DEBOUNCE);B.ready=true;
    if(self.VAL){VAL.on(()=>{paintStatus();if(VAL.mode==="full"&&E.ta.value)run();if(VAL.mode==="none")run()})}
    if(self.ENV)ENV.onChange(()=>{const s=sec.querySelector(".sh .stamp[data-k=renderer]");if(s&&s.textContent!==rend())sectionHeader(sec,header())});
    if(self.SIM){SIM.on("select",id=>{E.bSel.disabled=!id;E.bSel.textContent=id?"selected scene "+id:"selected scene"});SIM.on("reset",()=>{E.bSel.disabled=!(self.S&&S.sel)})}
    IO.observe(section,v=>{if(v&&self.VAL&&VAL.mode==="unloaded")VAL.need()},{rootMargin:"600px"});
    E.ta.addEventListener("focus",()=>{if(self.VAL&&VAL.mode==="unloaded")VAL.need()});
    if(self.DATA)DATA.on("live.bodies",()=>{if(!B.src)BENCH.loadHero()});
    E.ta.value="";txt(E.edSub,"waiting for the live bodies (part live.bodies) …");paintStatus()}});
Object.assign(self,{BENCH,__bench});
})();
