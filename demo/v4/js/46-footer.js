/* 46-footer.js — S16 footer deck (wave 1 plain: Under the hood, Step 0 table, Versions strip, licences, credit line; wave 2 adds What is real, owner console, Ask).
   Globals: FOOTER, fillUnder. Ported from v3 fillUnder (697–708: the hash line; the render-budget readout is new and reads LOOP.stats).
   DOM: #under (.parts table, .budget, .hashline, .errors), #env, #versionsDeck, #licences, #credit. Test hooks: #under table tr[data-part], #versions a (mast), #under .errors .errline. */
(function(){
"use strict";
function partsTable(host){let tb=host.querySelector("table.parts");if(!tb){tb=el("table",{class:"parts"},[el("thead",null,el("tr",null,["part","published","raw","rows","sha256","state","ms"].map(h=>el("th",{text:h})))),el("tbody")]);host.appendChild(tb)}
  const body=tb.querySelector("tbody"),names=Object.keys((MANIFEST&&MANIFEST.parts)||{});while(body.children.length<names.length)body.appendChild(el("tr",{data:{part:""}},[0,1,2,3,4,5,6].map(()=>el("td"))));
  names.forEach((n,i)=>{const tr=body.children[i],m=MANIFEST.parts[n],st=(self.DATA&&DATA.status[n])||{state:"idle"};tr.dataset.part=n;tr.dataset.state=st.state;
    txt(tr.children[0],n);txt(tr.children[1],fmt.bytes(m.bytes_b64));txt(tr.children[2],fmt.bytes(m.bytes_raw));txt(tr.children[3],m.rows==null?"—":fmt.int(m.rows));txt(tr.children[4],m.sha256.slice(0,8)+(st.sha&&st.sha!==m.sha256?" ≠ "+st.sha.slice(0,8):""));
    txt(tr.children[5],st.state==="loading"?`loading ${st.bytes?Math.round(100*st.got/st.bytes)+"%":fmt.bytes(st.got)}`:st.state==="loaded"?"ok · hash matches":st.state==="refused"?"REFUSED · "+(st.err||""):st.state);tr.children[5].style.color=st.state==="refused"||st.state==="missing"?"var(--bad)":st.state==="loaded"?"var(--ok)":"var(--mute)";txt(tr.children[6],st.ms?Math.round(st.ms):"")})}
function fillUnder(){const host=$("under");if(!host)return;
  if(!host.querySelector(".parts"))host.append(el("div",{class:"note m",data:{k:"lead"}}),el("div",{class:"budget note m"}),el("div",{class:"hashline note m"}),el("div",{class:"errors"}));
  partsTable(host);
  const loaded=Object.values((self.DATA&&DATA.status)||{}).filter(s=>s.state==="loaded").length,total=Object.keys((MANIFEST&&MANIFEST.parts)||{}).length;
  txt(host.querySelector("[data-k=lead]"),`parts ${loaded} of ${total} loaded · published ${fmt.bytes(Object.values(MANIFEST.parts).reduce((a,p)=>a+p.bytes_b64,0))} → decoded ${fmt.bytes(Object.values(MANIFEST.parts).reduce((a,p)=>a+p.bytes_raw,0))} · each checked against manifest sha256 of the decoded bytes · hash ${self.HASH?HASH.mode:"?"} (queue ${self.HASH?HASH.queue:0}, memo ${self.HASH?HASH.memo.size:0}) · build ${BUILD.sha||"?"} ${BUILD.date||""}`);
  const st=self.LOOP?LOOP.stats:null;if(st){const pan=Object.entries(st.panel).filter(([,v])=>v.n).sort((a,b)=>b[1].p95-a[1].p95).slice(0,8).map(([k,v])=>`${k} ${v.last.toFixed(1)}/${v.p95.toFixed(1)} ms`).join(" · ");
    txt(host.querySelector(".budget"),`render budget: ${st.fps} fps · frame p95 ${st.frame.p95.toFixed(1)} ms mean ${st.frame.mean.toFixed(1)} ms · panels (last/p95): ${pan||"none yet"}${self.S?" · scenes "+S.scenes.length+" · clk "+fmt.clock(S.clk)+" ×"+S.rate:""}`)}
  const sc=self.S&&S.byId.get(S.sel),steps=sc?readSteps(sc.xml):[];
  txt(host.querySelector(".hashline"),`page hash = SHA-256( text-normalised scene minus x3dprov.* )${sc?" = "+contentHash(sc.xml).slice(0,16)+"…":""} · step n = { op, …facts, input, output = h(x after), prev = SHA-256(step n−1) } · chain head = SHA-256(step ${steps.length||"n"}) · seal (optional) = HMAC(key, head : n), an HMAC stand-in with the key in the page source · repo hash = SHA-256(C14N(...)), shown side by side where both exist; byte equality not claimed`);
  const errs=host.querySelector(".errors");const msgs=((self.DATA&&DATA.messages)||[]).concat((self.BOOT&&BOOT.log)||[]);while(errs.children.length<msgs.length)errs.appendChild(el("div",{class:"errline"}));msgs.forEach((m,i)=>txt(errs.children[i],m))}
function versionsDeck(){const h=$("versionsDeck");if(!h||!BUILD)return;h.textContent="";const ul=el("div",{class:"note m"});(BUILD.versions||[]).forEach(x=>{const row=el("div");
  if(x.id&&!BUILD.share&&!x.this)row.appendChild(el("a",{href:"https://claude.ai/artifact/"+x.id,target:"_blank",rel:"noopener",text:x.v+" · "+x.id}));else row.appendChild(el("span",{text:x.v+(x.this?" · this page":x.id&&BUILD.share?"":" · "+(x.id||"planned"))}));
  row.appendChild(el("span",{text:" — "+(x.title||"")}));ul.appendChild(row)});
  ul.appendChild(el("div",{text:`build ${BUILD.sha||"?"} · ${BUILD.date||""} · X_ITE ${BUILD.xite} as own files (passes ${(BUILD.passes||[]).join(", ")}) · validator recorded ${(BUILD.validator_recorded||[]).join(", ")} · port ${BUILD.port} · parts sha256 in manifest.json${BUILD.has_run24?" · 24 OCT run included":""}${BUILD.has_cycles?" · Cycles turntables baked":""}`}));h.appendChild(ul);
  const lic=$("licences");if(lic){lic.textContent="";lic.appendChild(el("div",{class:"note m",text:"Licences: X_ITE (MIT, Holger Seelig) · libxml2 and libxml2-wasm (MIT) · the js-port of x3d_mcp (same licence as the fork) · fonts: Barlow Condensed, IBM Plex (OFL via Google Fonts)."}))}
  const cr=$("credit");if(cr)txt(cr,BUILD.share?"Thesis and pipeline: x3d.io.":"Thesis and pipeline: HagopJay (x3d.io). Validator: x3d_mcp fork. Renderer: X_ITE. Blender bridge: x3d-blender-io.")}
const FOOTER={init(){sectionHeader("deck",{title:"Footer deck",unit:"under the hood · Step 0 · versions · licences",stamps:{source:"RE-RUN HERE",validator:"none",renderer:"none"},grade:"C",honesty:"everything in this deck is measured in this browser or read from the manifest; nothing here is a claim about the runs"});
  fillUnder();if(self.envTable)envTable("env");versionsDeck();
  LOOP.register({name:"under",bit:LOOP.bits.DATA|LOOP.bits.SELECT|LOOP.bits.CLOCK,rateHz:1,draw(){fillUnder();if(self.envTable)envTable("env")}});
  if(self.ENV)ENV.onChange(()=>envTable("env"))}};
SECTIONS.register({id:"deck",mount(){FOOTER.init()}});
Object.assign(self,{FOOTER,fillUnder});
})();
