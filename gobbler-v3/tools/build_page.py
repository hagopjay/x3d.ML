"""Gobbler 3 page: the stage (poc harness), the explorer (search, filters, loops, evidence), graph-v3.json and graph-v3.jsonld.
Usage: python3 -I build_page.py --graph graph.json --scene gobbler3.x3d --poc /home/user/x3d.poc --out DIR [--public]
--public drops every node whose visibility is not 'public' (and every edge that touches one) and writes no private paths."""
import argparse, html, importlib.util, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('bg3', os.path.join(HERE, 'build_gobbler_v3.py'))
bg3 = importlib.util.module_from_spec(spec); sys.modules['bg3'] = bg3; spec.loader.exec_module(bg3)
esc = html.escape

def hexcol(rgb): return '#%02x%02x%02x' % tuple(int(round(255 * c)) for c in rgb)

CLS_HEX = {c: hexcol(rgb) for c, rgb in bg3.CLASS_COLOUR.items()}
FAM_OF = {c: f for f, (_, cs) in bg3.FAMILY.items() for c in cs}
FAM_LABEL = {'spec': 'Standards and nodes', 'tool': 'Tools, validators, repos', 'people': 'People, orgs, events', 'work': 'Workstreams, documents, scenes',
             'learn': 'Experiments, findings, metrics', 'rule': 'Rules and decisions', 'loop': 'Flywheel loops'}
FAM_HEX = {f: hexcol(rgb) for f, (rgb, _) in bg3.FAMILY.items()}


def filter_public(g):
    keep = [i for i, n in enumerate(g['nodes']) if n.get('vis', 'public') == 'public']
    remap = {o: k for k, o in enumerate(keep)}
    nodes = [dict(g['nodes'][o]) for o in keep]
    edges = []
    for e in g['edges']:
        if e['s'] in remap and e['t'] in remap:
            e = dict(e); e['s'] = remap[e['s']]; e['t'] = remap[e['t']]; edges.append(e)
    loops = []
    for L in g['loops']:
        if all(s in remap for s in L['steps']) and L['centre'] in remap:
            L = dict(L); L['steps'] = [remap[s] for s in L['steps']]; L['centre'] = remap[L['centre']]; loops.append(L)
    # remap loop indices on nodes and edges
    old_loops = g['loops']; lmap = {}
    for k, L in enumerate(loops):
        for oi, ol in enumerate(old_loops):
            if ol['name'] == L['name'] and ol['ev'] == L['ev']: lmap[oi] = k
    for n in nodes: n['loops'] = [lmap[x] for x in n.get('loops', []) if x in lmap]
    for e in edges: e['loop'] = lmap.get(e['loop'], -1) if e['loop'] >= 0 else e['loop']
    out = dict(g); out.update(nodes=nodes, edges=edges, loops=loops)
    return out


def slim(g, public):
    """What the page needs: no evidence text beyond one line per edge, no private paths in public builds."""
    nodes = []
    for n in g['nodes']:
        d = {'id': n['id'], 'label': n['label'], 'cls': n['cls'], 'prov': n['prov'], 'grade': n['grade'], 'xyz': n['xyz'], 'deg': n['deg'], 'w': n['w'],
             'loops': n.get('loops', []), 'metrics': [({'name': x['name'], 'value': x['value']} if public else x) for x in n.get('metrics', [])[:3]], 'notes': n.get('notes', [])[:1], 'props': {k: v for k, v in (n.get('props') or {}).items() if v not in (None, '')}}
        if not public: d['docs'] = n.get('docs', [])
        nodes.append(d)
    edges = [{'s': e['s'], 't': e['t'], 'p': e['p'], 'grade': e['grade'], 'prov': e['prov'], 'loop': e['loop'], 'ev': (e.get('ev') or [])[:1], **({} if public else {'docs': e.get('docs', [])})}
             for e in g['edges'] if e.get('loop', -1) != -3 or True]
    loops = [{'name': L['name'], 'steps': L['steps'], 'centre': L['centre'], 'gain': L['gain'], 'prov': L['prov'], 'grade': L['grade'], 'votes': L['votes'], 'ev': L['ev'],
              'ring': {'center': L['ring']['center'], 'normal': L['ring']['normal'], 'radius': L['ring']['radius']}} for L in g['loops']]
    return {'nodes': nodes, 'edges': edges, 'loops': loops, 'meta': g['meta']}


def jsonld(s):
    ctx = {'@vocab': 'https://polyxandria.example/kg#', 'name': 'http://schema.org/name', 'prov': 'px:provenance', 'grade': 'px:grade', 'px': 'https://polyxandria.example/kg#'}
    gr = []
    for i, n in enumerate(s['nodes']):
        gr.append({'@id': 'px:n%d' % i, '@type': 'px:' + n['cls'], 'name': n['label'], 'prov': n['prov'], 'grade': n['grade'], 'px:position': n['xyz']})
    for k, e in enumerate(s['edges']):
        gr.append({'@id': 'px:s%d' % k, '@type': 'px:Statement', 'px:subject': {'@id': 'px:n%d' % e['s']}, 'px:predicate': e['p'], 'px:object': {'@id': 'px:n%d' % e['t']},
                   'prov': e['prov'], 'grade': e['grade'], **({'px:evidence': e['ev'][0]} if e.get('ev') else {}), **({'px:loop': e['loop']} if e['loop'] >= 0 else {})})
    for k, L in enumerate(s['loops']):
        gr.append({'@id': 'px:loop%d' % k, '@type': 'px:FlywheelLoop', 'name': L['name'], 'prov': L['prov'], 'grade': L['grade'], 'px:steps': {'@list': [{'@id': 'px:n%d' % x} for x in L['steps']]}, **({'px:gain': L['gain']} if L.get('gain') else {})})
    return {'@context': ctx, '@graph': gr}


CSS = """
.ex{display:grid;grid-template-columns:minmax(260px,330px) 1fr minmax(260px,360px);gap:22px;align-items:start}
@media(max-width:980px){.ex{grid-template-columns:1fr}}
.ex h3{font-size:15px;margin:0 0 8px;color:var(--gold)}
.ex input[type=search]{width:100%;padding:10px 12px;background:var(--bg2);border:1px solid var(--rule);border-radius:8px;color:var(--ink);font:15px var(--sans)}
.ex .grp{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.ex .chip{cursor:pointer}
.sw{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:baseline}
.list{max-height:560px;overflow:auto;border:1px solid var(--rule);border-radius:8px;background:var(--bg2)}
.list button{display:grid;grid-template-columns:14px 1fr auto;gap:8px;align-items:center;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--rule);color:var(--ink);padding:8px 10px;font:14px var(--sans);cursor:pointer}
.list button:hover,.list button.on{background:#1a1620}
.list small{color:var(--ink3);font:11px var(--mono)}
.card{border:1px solid var(--rule);border-radius:10px;background:var(--bg2);padding:16px;position:sticky;top:12px}
.card h4{font:500 20px var(--font);margin:0 0 4px}
.card .meta{font:12px var(--mono);color:var(--ink3);margin-bottom:10px}
.card blockquote{margin:10px 0;padding:8px 12px;border-left:2px solid var(--gold2);color:var(--ink2);font:14px/1.45 var(--font)}
.card ul{margin:6px 0 0;padding:0;list-style:none}
.card li{padding:3px 0;font-size:13.5px;color:var(--ink2)}
.card li a{cursor:pointer}
.tag{font:11px var(--mono);border:1px solid var(--rule);border-radius:5px;padding:2px 6px;margin-right:4px;color:var(--ink2)}
.tag.sim{border-color:#7a5b24;color:#e0b66a}.tag.dat{border-color:#3f6b4f;color:#9fd1af}.tag.rec{border-color:#59508a;color:#b7aef0}
.loops{display:grid;gap:10px}
.loop{border:1px solid var(--rule);border-radius:10px;padding:12px 14px;background:var(--bg2)}
.loop b{font:500 16px var(--font)}
.loop ol{margin:6px 0 8px;padding-left:20px;color:var(--ink2);font-size:13.5px}
.fid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:14px}
.fid div{border:1px solid var(--rule);border-radius:8px;padding:10px 12px}
.fid b{display:block;font:500 24px var(--font);color:var(--gold)}.fid span{font-size:12.5px;color:var(--ink3)}
"""


def build(args):
    g = json.load(open(args.graph))
    if args.public: g = filter_public(g)
    s = slim(g, args.public)
    os.makedirs(args.out, exist_ok=True)
    for f in ('common.js', 'common.css'): shutil.copy(os.path.join(args.poc, 'src', f), os.path.join(args.out, f))
    os.makedirs(os.path.join(args.out, 'vendor/x_ite'), exist_ok=True)
    for f in ('x_ite.min.js', 'x_ite.css'):
        shutil.copy(os.path.join(args.vendor, f), os.path.join(args.out, 'vendor/x_ite', f))
    ad = os.path.join(args.vendor, 'assets')
    if os.path.isdir(ad) and not os.path.isdir(os.path.join(args.out, 'vendor/x_ite/assets')): shutil.copytree(ad, os.path.join(args.out, 'vendor/x_ite/assets'))
    shutil.copy(args.scene, os.path.join(args.out, 'gobbler3.x3d'))
    json.dump(s, open(os.path.join(args.out, 'graph-v3.json'), 'w'), separators=(',', ':'))
    json.dump(jsonld(s), open(os.path.join(args.out, 'graph-v3.jsonld'), 'w'), separators=(',', ':'))
    m = g['meta']; N = len(s['nodes']); E = len(s['edges']); Lc = len(s['loops'])
    prov = {}
    for n in s['nodes']: prov[n['prov']] = prov.get(n['prov'], 0) + 1
    gr = {}
    for n in s['nodes']: gr[n['grade']] = gr.get(n['grade'], 0) + 1
    st = m.get('stats', {})
    fid = [(N, 'entities drawn'), (E, 'relations'), (Lc, 'flywheel loops'), (prov.get('data', 0), 'from live data'), (prov.get('doc', 0), 'quoted from documents'),
           (prov.get('model_recall', 0) + prov.get('simulated', 0), 'tagged recalled or simulated')]
    pal = {c: CLS_HEX[c] for c in CLS_HEX}
    cfg = dict(scene='gobbler3.x3d', look=dict(toneMapping='KHR_PBR_NEUTRAL', exposure=1.0), darkDefault=False, autoClean=0,
               viewpoints=[['Wide', 'Wide'], ['Colossus', 'Colossus'], ['EyeToEye', 'Eye'], ['Inside', 'Inside'], ['Flywheel', 'Flywheel'], ['Crown', 'Crown']],
               tour=dict(vp='Wide', center=[5.2, -2.2, 0], r0=26, r1=9.5, e0=34, e1=6, duration=44, spin=0.05, loop='pingpong', fov=0.95, delay=900))
    nav = '<a class="chip" href="index.html">All demos</a><a class="chip" href="gobbler.html">Gobbler</a><a class="chip on" href="gobbler3.html">Gobbler 3</a>'
    head = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Gobbler 3 · PolyXandria</title><meta name="description" content="A knowledge graph of the X3D community and its flywheel loops, growing out of the gobbler\'s neck.">'
            '<link rel="stylesheet" href="vendor/x_ite/x_ite.css"><link rel="stylesheet" href="common.css"><style>' + CSS + '</style>'
            '<script src="vendor/x_ite/x_ite.min.js"></script><script src="common.js"></script></head><body>')
    stage = ('<header class="stage" id="stage"><div class="shade"></div><div class="fog"></div><div class="dark"></div><div class="grain"></div><div class="flash"></div><div class="vignette"></div>'
             '<div class="ui"><div class="top"><div class="brand"><a href="index.html">PolyXandria</a></div><nav class="nav">' + nav + '</nav></div>'
             '<div class="titleblock"><div class="kicker">Demo · Gobbler 3 · scriptless X3D 4.0 knowledge graph</div><h1>The <em>Gobbler</em> thinks</h1>'
             '<p>Everything we know about the X3D community, as a graph the bird is swallowing. The flywheel loops turn as wheels; the lights wander.</p></div>'
             '<div class="bar"><div class="btns" id="vps"><button class="chip" id="btn-tour">Pause tour</button><button class="chip" id="btn-dark">Lights out</button>'
             '<button class="chip" id="btn-clean">Hide text</button><button class="chip" id="btn-full">Full screen</button></div><div class="hud" id="hud">starting</div></div></div>'
             '<div class="busy" id="busy">Starting the viewer</div><div class="hint" id="hint">Drag to orbit · scroll to zoom · pick a star in the explorer below to fly to it</div></header>')
    legend = ''.join('<button class="chip fam on" data-fam="%s"><span class="sw" style="background:%s"></span>%s</button>' % (f, FAM_HEX[f], esc(FAM_LABEL[f])) for f in FAM_LABEL)
    provb = ''.join('<button class="chip pv on" data-pv="%s">%s</button>' % (k, esc(v)) for k, v in (('data', 'live data'), ('doc', 'quoted'), ('model_recall', 'recalled'), ('simulated', 'simulated')))
    gradeb = ''.join('<button class="chip gd on" data-gd="%s">%s</button>' % (k, k) for k in ('Confirmed', 'Likely', 'Suspected'))
    body = ('<main><section class="band"><div class="wrap"><h2>Explore the graph</h2>'
            '<p class="lead">The 3D scene is one scriptless file. This panel is the index to it: search a name, filter by kind, provenance or grade, and the camera flies to the star. '
            'Simulated and recalled entities are tagged, and real ones carry the sentence they came from.</p>'
            '<div class="fid">' + ''.join('<div><b>%s</b><span>%s</span></div>' % (n, esc(l)) for n, l in fid) + '</div><br>'
            '<div class="ex"><div><h3>Find</h3><input type="search" id="q" placeholder="validator, Blender, glTF, X_ITE..." autocomplete="off">'
            '<div class="grp">' + legend + '</div><div class="grp">' + provb + '</div><div class="grp">' + gradeb + '</div></div>'
            '<div><h3 id="lh">Entities</h3><div class="list" id="list"></div></div>'
            '<div><div class="card" id="card"><h4>Pick a star</h4><div class="meta">entity card</div><p style="color:var(--ink3);font-size:14px">Every entity shows its kind, how we know it (live data, a quoted document, recalled or simulated), '
            'its grade, the sentence that supports it and its neighbours.</p></div></div></div></div></section>'
            '<section class="band"><div class="wrap"><h2>The flywheel loops</h2><p class="lead">The virtuous circle and the knowledge graph are the same thing. Each loop is a ring of the graph; ride one to watch the camera follow its steps.</p>'
            '<div class="loops" id="loops"></div></div></section>'
            '<section class="band"><div class="wrap"><h2>Take it with you</h2><p class="lead">The graph as data, for tools: <a href="graph-v3.json">graph-v3.json</a> (what this page reads) and <a href="graph-v3.jsonld">graph-v3.jsonld</a> '
            '(JSON-LD, every relation a statement with provenance, grade and evidence). The scene is <a href="gobbler3.x3d">gobbler3.x3d</a>, X3D 4.0, checked with the fork validator.</p></div></section>'
            '<footer><div class="wrap"><p>Real core, tagged fill. Counts are from the build that made this page. Evidence lines are quoted from the sources they came from.</p><p><a href="index.html">All demos</a></p></div></footer></main>')
    js = PAGE_JS % {'pal': json.dumps(pal), 'fam': json.dumps(FAM_OF), 'famhex': json.dumps(FAM_HEX)}
    page = head + stage + body + '<script>PX.boot(%s);</script><script>%s</script></body></html>' % (json.dumps(cfg), js)
    open(os.path.join(args.out, 'gobbler3.html'), 'w', encoding='utf-8').write(page)
    print('page', args.out, N, 'nodes', E, 'edges', Lc, 'loops', os.path.getsize(os.path.join(args.out, 'graph-v3.json')) // 1024, 'KB json')


PAGE_JS = r"""
(function(){
  var PAL=%(pal)s, FAM=%(fam)s, FAMHEX=%(famhex)s, G=null, sel=-1, flyRaf=0, ride=0;
  var $=function(s){return document.querySelector(s)}, $$=function(s){return Array.prototype.slice.call(document.querySelectorAll(s))};
  var on={fam:{},pv:{},gd:{}}; $$('.fam').forEach(function(b){on.fam[b.dataset.fam]=1}); $$('.pv').forEach(function(b){on.pv[b.dataset.pv]=1}); $$('.gd').forEach(function(b){on.gd[b.dataset.gd]=1});
  function e(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  fetch('graph-v3.json').then(function(r){return r.json()}).then(function(g){G=g;G.adj=g.nodes.map(function(){return[]});g.edges.forEach(function(x,i){G.adj[x.s].push(i);G.adj[x.t].push(i)});render();loops()});
  function pvTag(p){return'<span class="tag '+(p==='data'?'dat':p==='simulated'?'sim':p==='model_recall'?'rec':'')+'">'+({data:'live data',doc:'quoted',model_recall:'recalled',simulated:'simulated'}[p]||p)+'</span>'}
  function render(){
    var q=$('#q').value.trim().toLowerCase(), out=[];
    G.nodes.forEach(function(n,i){ if(!on.fam[FAM[n.cls]]||!on.pv[n.prov]||!on.gd[n.grade])return; if(q&&n.label.toLowerCase().indexOf(q)<0&&n.cls.toLowerCase().indexOf(q)<0)return; out.push(i)});
    out.sort(function(a,b){return G.nodes[b].deg-G.nodes[a].deg});
    $('#lh').textContent=out.length+' of '+G.nodes.length+' entities';
    $('#list').innerHTML=out.slice(0,250).map(function(i){var n=G.nodes[i];return'<button data-i="'+i+'" class="'+(i===sel?'on':'')+'"><span class="sw" style="background:'+PAL[n.cls]+'"></span><span>'+e(n.label)+'</span><small>'+e(n.cls)+'</small></button>'}).join('');
  }
  $('#list').addEventListener('click',function(ev){var b=ev.target.closest('button');if(b)select(+b.dataset.i,true)});
  $('#q').addEventListener('input',render);
  [['fam','fam'],['pv','pv'],['gd','gd']].forEach(function(k){$$('.'+k[0]).forEach(function(b){b.addEventListener('click',function(){var key=b.dataset[k[1]];if(on[k[0]][key]){delete on[k[0]][key];b.classList.remove('on')}else{on[k[0]][key]=1;b.classList.add('on')}render()})})});
  function select(i,fly){
    sel=i;var n=G.nodes[i];render();
    var nb=G.adj[i].slice().sort(function(a,b){return rank(G.edges[b])-rank(G.edges[a])}).slice(0,10);
    var h='<h4>'+e(n.label)+'</h4><div class="meta"><span class="sw" style="background:'+PAL[n.cls]+'"></span>'+e(n.cls)+' · '+pvTag(n.prov)+'<span class="tag">'+n.grade+'</span></div>';
    var ev=null;G.adj[i].forEach(function(k){if(!ev&&G.edges[k].ev&&G.edges[k].ev[0])ev=G.edges[k].ev[0]});
    if(n.notes&&n.notes[0])h+='<p style="font-size:14px;color:var(--ink2)">'+e(n.notes[0])+'</p>';
    if(ev)h+='<blockquote>'+e(ev)+'</blockquote>';
    if(n.metrics&&n.metrics.length)h+='<ul>'+n.metrics.map(function(m){return'<li><b style="color:var(--ink)">'+e(m.value)+'</b> '+e(m.name)+'</li>'}).join('')+'</ul>';
    var pk=Object.keys(n.props||{}).slice(0,5);if(pk.length)h+='<ul>'+pk.map(function(k){return'<li>'+e(k)+': '+e(n.props[k])+'</li>'}).join('')+'</ul>';
    if(nb.length){h+='<div class="meta" style="margin-top:12px">connected to</div><ul>'+nb.map(function(k){var x=G.edges[k],o=x.s===i?x.t:x.s,on_=G.nodes[o];return'<li><a data-go="'+o+'">'+e(on_.label)+'</a> <span style="color:var(--ink3);font:11px var(--mono)">'+(x.s===i?'':'← ')+e(x.p.replace(/_/g,' '))+(x.s===i?' →':'')+' · '+x.grade+'</span></li>'}).join('')+'</ul>'}
    if(n.docs&&n.docs.length)h+='<div class="meta" style="margin-top:12px">'+e(n.docs.join(' · '))+'</div>';
    $('#card').innerHTML=h;
    if(fly)flyTo(n.xyz);
    mark(n.xyz);
  }
  function rank(x){return({Confirmed:3,Likely:2,Suspected:1}[x.grade]||0)*10+(x.prov==='data'?5:0)}
  $('#card').addEventListener('click',function(ev){var a=ev.target.closest('a[data-go]');if(a)select(+a.dataset.go,true)});
  function mark(p){try{var m=PX.el.browser.currentScene.getNamedNode('PickMarker');m.translation=new X3D.SFVec3f(p[0],p[1],p[2])}catch(x){}}
  function probe(){var sc=PX.el.browser.currentScene;return sc.getNamedNode('Probe')}
  function flyTo(p,from,fov){
    if(!window.X3D||!PX.el||!PX.el.browser)return; if(PX.tourStop)PX.tourStop();
    var v;try{v=probe()}catch(x){return}
    var cur=v.position, cp=[cur.x,cur.y,cur.z]; var d=0.0;
    var tgt=p, pos=from||[p[0]+0.35,p[1]+0.4,p[2]+2.6];
    var a=cp, b=pos, t0=performance.now(), D=1500;
    try{v.set_bind=true;if(fov)v.fieldOfView=fov}catch(x){}
    var oa=null; cancelAnimationFrame(flyRaf);
    (function step(){var k=Math.min(1,(performance.now()-t0)/D);k=k*k*(3-2*k);
      var q=[a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k,a[2]+(b[2]-a[2])*k], o=PX.lookAt(q,tgt);
      try{v.position=new X3D.SFVec3f(q[0],q[1],q[2]);v.orientation=new X3D.SFRotation(o[0],o[1],o[2],o[3])}catch(x){}
      if(k<1)flyRaf=requestAnimationFrame(step)})();
    $$('.vp').forEach(function(b){b.classList.remove('on')});
    $('#stage').scrollIntoView({behavior:'smooth',block:'start'});
  }
  function loops(){
    $('#loops').innerHTML=G.loops.map(function(L,i){
      return'<div class="loop"><b>'+e(L.name)+'</b> '+pvTag(L.prov)+'<span class="tag">'+L.grade+'</span>'+(L.gain?'<span class="tag">'+e(L.gain)+'</span>':'')+'<ol>'+L.steps.map(function(s){return'<li>'+e(G.nodes[s].label)+'</li>'}).join('')+'</ol>'+
        '<button class="chip" data-wheel="'+i+'">Fly to the wheel</button> <button class="chip" data-ride="'+i+'">Ride the loop</button></div>'}).join('')||'<p class="lead">No loops in this build.</p>';
  }
  $('#loops').addEventListener('click',function(ev){
    var w=ev.target.closest('[data-wheel]'),r=ev.target.closest('[data-ride]');
    if(w){var L=G.loops[+w.dataset.wheel],rg=L.ring,n=rg.normal,s=n[2]>=0?1:-1,c=rg.center;flyTo(c,[c[0]+s*n[0]*rg.radius*2.6,c[1]+s*n[1]*rg.radius*2.6+0.3,c[2]+s*n[2]*rg.radius*2.6],0.95);mark(c)}
    if(r){var L2=G.loops[+r.dataset.ride],k=0;clearInterval(ride);var stepf=function(){var n=G.nodes[L2.steps[k%%L2.steps.length]];select(L2.steps[k%%L2.steps.length],true);k++;if(k>L2.steps.length+1)clearInterval(ride)};stepf();ride=setInterval(stepf,3200)}
  });
  document.addEventListener('pointerdown',function(ev){if(ev.target.closest&&ev.target.closest('x3d-canvas'))clearInterval(ride)});
})();
"""

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', required=True); ap.add_argument('--scene', required=True); ap.add_argument('--poc', default='/home/user/x3d.poc')
    ap.add_argument('--out', required=True); ap.add_argument('--vendor', default=os.path.join(HERE, '..', 'site')); ap.add_argument('--public', action='store_true')
    build(ap.parse_args())
