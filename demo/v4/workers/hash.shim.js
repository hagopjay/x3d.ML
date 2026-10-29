/* hash.shim.js — appended to js/04-prov.js by build_v4.py to make workers/hash.worker.js (never edit the built file).
   Protocol (ARCHITECTURE §4 / 04): {id, type:'ping'} → {id, pong:true}; {id, type:'verify', ids, xmls} → {id, statuses:[{id, status, ok}]};
   {id, type:'hash', xmls} → {id, hashes}; {id, type:'sha256', bytes} → {id, hex}; {id, type:'build', x0, steps:[{step, after, seal}]} → {id, xml}; errors → {id, error}. */
(function(){
"use strict";
const hex=b=>Array.from(new Uint8Array(b),x=>x.toString(16).padStart(2,"0")).join("");
self.onmessage=async function(ev){const d=ev.data||{},id=d.id;try{
  if(d.type==="ping")return self.postMessage({id,pong:true});
  if(d.type==="verify")return self.postMessage({id,statuses:d.ids.map((sid,i)=>{const v=self.verify(d.xmls[i]);return{id:sid,status:v.status,ok:v.ok}})});
  if(d.type==="hash")return self.postMessage({id,hashes:d.xmls.map(x=>self.contentHash(x))});
  if(d.type==="sha256"){let h=null;if(self.crypto&&crypto.subtle){try{h=hex(await crypto.subtle.digest("SHA-256",d.bytes))}catch(e){}}return self.postMessage({id,hex:h||self.sha256b(d.bytes instanceof Uint8Array?d.bytes:new Uint8Array(d.bytes))})}
  if(d.type==="build"){let x=d.x0;d.steps.forEach(s=>{x=self.addStep(x,s.step,s.after??x,s.seal)});return self.postMessage({id,xml:x})}
  self.postMessage({id,error:"unknown type "+d.type})}catch(e){self.postMessage({id,error:String(e&&e.message||e)})}};
})();
