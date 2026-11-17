'use strict';
// Exercise the actual atlas script with a small DOM adapter; no browser-pixel claim.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'Integration-Atlas.html'),'utf8');
const data=source.match(/<script id="atlas-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=source.match(/<script>([\s\S]*?)<\/script>/)[1];
const ids=[...source.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
assert.equal(new Set(ids).size,ids.length,'Document IDs must be unique');
function node(tag='div'){return {tag,children:[],dataset:{},attrs:{},handlers:{},value:'',textContent:'',hidden:false,
 append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;},
 setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,fn){this.handlers[k]=fn;},click(){this.onclick?.();}};}
const elements=new Map(),panels=['bridges','findings','review','corrections','kits','ontology'].map(id=>Object.assign(node(),{id}));
const buttons=panels.map(p=>Object.assign(node('button'),{dataset:{panel:p.id}}));
function $(id){if(!elements.has(id))elements.set(id,node());return elements.get(id);}
$('atlas-data').textContent=data;
for(const id of ['package','status','slice'])$(id).value='all';
const document={getElementById:$,createElement:node,addEventListener(){},
 querySelectorAll(q){return q==='[data-panel]'?buttons:q==='main>section'?panels:[];},
 querySelector(){return buttons.find(b=>b.dataset.panel==='review');}};
const context={document,window:{},Map,JSON,String};vm.runInNewContext(script,context,{timeout:5000});
assert.equal($('bridgeGrid').children.length,27);assert.equal($('kitList').children.length,439);
assert.equal($('correctionGrid').children.length,21);
$('package').value='WP7';$('package').handlers.input();assert.equal($('bridgeGrid').children.length,1);
$('status').value='Planned';$('status').handlers.input();assert.equal($('bridgeGrid').children.length,0);
$('slice').value='splat-trailer';$('slice').handlers.input();assert.equal($('kitList').children.length,22);
buttons.find(b=>b.dataset.panel==='review').click();
assert.equal(panels.find(p=>p.id==='review').hidden,false);
assert.equal(panels.find(p=>p.id==='bridges').hidden,true);
assert.equal(context.window.AtlasChecks.bridgeCount,27);
assert.equal(context.window.AtlasChecks.kitCount,439);
console.log('PASS actual atlas script: 27 bridges,21 corrections,439 files,filters,tabs,unique IDs; native pixels not tested');
