"""check_v4_phone.py — the phone (390x844) and tablet (768x1024) pass (SPEC-v4 §11, ARCHITECTURE §8; css 20-mast + 90-phone).

At each size, after BOOT.phase ready and every part loaded:
  * document.scrollingElement.scrollWidth <= innerWidth after boot, after scrolling to every section (and waiting for its panels to draw), and with the inspector open
  * no element whose box passes the viewport's right edge by more than 1 px, unless a scrolling/clipping ancestor inside the viewport holds it (offenders listed)
  * every section becomes visible in turn (scrollIntoView, box intersects the viewport)
  * the mast is position:sticky, stays at top 0 while scrolled; 40 px at 390; at 768 it wraps to <= 3 rows (<= 120 px): the chips (.mastR) sit on a row below the clock
  * tap targets: every visible mast button and every inspector tab is >= 44x44 (a mast button's hit box is max(its box, its ::after box))
  * canvases: none is laid out at its 300x150 default aspect after its section was visited (a canvas with no data yet keeps the CSS height of 90-phone.css)
  * both themes (html[data-theme=dark|light]): text contrast >= 4.5:1 (WCAG large text, >= 24 px or >= 18.66 px bold: 3:1) for a sample of 40 body-text elements (>= 12 px, opacity 1) spread over every section
Screenshots: demo/tests/shots/v4_phone_<w>_<section>.png (dark) and v4_phone_<w>_light_<section>.png (a few).
Run: V4_BUILD=demo/build/v4-phone python3 demo/tests/check_v4_phone.py [--csp noeval]
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4fixture import Fixture

fx = Fixture()
SIZES = [(390, 844), (768, 1024)]
LIGHT_SHOTS = {"stage", "film", "stream", "wall", "sheet"}

OFFENDERS = r"""(()=>{const iw=innerWidth,out=[];
 const held=e=>{let p=e.parentElement;while(p&&p!==document.body){const s=getComputedStyle(p);if(/auto|scroll|hidden|clip/.test(s.overflowX)){const r=p.getBoundingClientRect();if(r.right<=iw+1&&r.left>=-1)return true}p=p.parentElement}return false};
 for(const e of document.querySelectorAll('body *')){if(e.closest('#measureMount,#curtain,#tour,#director,#proof,#lightbox'))continue;const r=e.getBoundingClientRect();if(r.width<1||r.height<1)continue;
  if((r.right>iw+1||r.left<-1)&&!held(e))out.push((e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+(typeof e.className==='string'&&e.className.trim()?'.'+e.className.trim().split(/\s+/).slice(0,2).join('.'):''))+'@'+((e.closest('section,header')||{}).id||'-')+' ['+Math.round(r.left)+','+Math.round(r.right)+']')}
 return out.slice(0,25)})()"""

TAPS = r"""(sel)=>[...document.querySelectorAll(sel)].filter(b=>{const r=b.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(b).visibility!=='hidden'}).map(b=>{const r=b.getBoundingClientRect(),a=getComputedStyle(b,'::after');
 let w=r.width,h=r.height;if(a.content&&a.content!=='none'&&a.position==='absolute'){w=Math.max(w,parseFloat(a.width)||0);h=Math.max(h,parseFloat(a.height)||0)}
 return [b.id||b.dataset.t||b.dataset.r||b.dataset.m||b.textContent.trim().slice(0,12),Math.round(w),Math.round(h)]})"""

CONTRAST = r"""(()=>{
 const P=s=>{const m=s.match(/rgba?\(([^)]+)\)/);if(!m)return null;const v=m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);return [v[0],v[1],v[2],v.length>3?v[3]:1]};
 const over=(f,b)=>[f[0]*f[3]+b[0]*(1-f[3]),f[1]*f[3]+b[1]*(1-f[3]),f[2]*f[3]+b[2]*(1-f[3]),1];
 const L=c=>{const k=c.slice(0,3).map(x=>{x/=255;return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4)});return .2126*k[0]+.7152*k[1]+.0722*k[2]};
 const bgOf=e=>{const st=[];let p=e;while(p){const s=getComputedStyle(p);if(s.backgroundImage&&s.backgroundImage!=='none'&&!/gradient/.test(s.backgroundImage))return null;const c=P(s.backgroundColor);if(c&&c[3]>0){st.push(c);if(c[3]>=1)break}p=p.parentElement}
  let b=[0,0,0,1];if(st.length&&st[st.length-1][3]>=1)b=st.pop();else b=P(getComputedStyle(document.body).backgroundColor)||b;while(st.length)b=over(st.pop(),b);return b};
 const opa=e=>{let o=1,p=e;while(p){o*=+getComputedStyle(p).opacity;p=p.parentElement}return o};
 const secs=[...document.querySelectorAll('main section[id]')];const per=[];
 for(const s of secs){const c=[];const w=document.createTreeWalker(s,NodeFilter.SHOW_TEXT);let n;while((n=w.nextNode())){const t=n.nodeValue.trim();if(t.length<3)continue;const e=n.parentElement;if(!e||c.includes(e))continue;
   const r=e.getBoundingClientRect();if(r.width<2||r.height<2)continue;const cs=getComputedStyle(e);if(cs.visibility==='hidden'||parseFloat(cs.fontSize)<12)continue;if(e.closest('canvas,svg,option,[hidden],details:not([open])>:not(summary)'))continue;if(opa(e)<1)continue;c.push(e)}
  per.push(c)}
 const pick=[];let k=0;while(pick.length<40&&per.some(c=>c.length)){const c=per[k%per.length];if(c.length){const i=Math.floor(c.length*((k*0.618)%1));pick.push(c.splice(i,1)[0])}k++}
 return pick.map(e=>{const f=P(getComputedStyle(e).color),b=bgOf(e);if(!f||!b)return null;const fe=f[3]<1?over(f,b):f;const a=L(fe),c=L(b),cr=(Math.max(a,c)+.05)/(Math.min(a,c)+.05);
  const fs=parseFloat(getComputedStyle(e).fontSize),fw=+getComputedStyle(e).fontWeight||400,large=fs>=24||(fs>=18.66&&fw>=700);
  return [(e.closest('section')||{}).id,e.tagName.toLowerCase()+(typeof e.className==='string'&&e.className?'.'+e.className.split(' ')[0]:''),e.textContent.trim().slice(0,24),Math.round(cr*100)/100,large?3:4.5]}).filter(Boolean)})()"""

async def sweep(pg, w, h):
    tag = f"{w}"
    secs = await pg.evaluate("[...document.querySelectorAll('main section[id]')].map(s=>s.id)")
    fx.ok(f"{tag}: sections present", len(secs) >= 14, secs)
    sw = await pg.evaluate("[document.scrollingElement.scrollWidth, innerWidth]")
    fx.ok(f"{tag}: no horizontal scroll after boot", sw[0] <= sw[1], sw)
    # mast
    m = await pg.evaluate("(()=>{const m=document.getElementById('mast'),r=m.getBoundingClientRect();return {pos:getComputedStyle(m).position,h:r.height,top:r.top}})()")
    fx.ok(f"{tag}: mast is sticky", m["pos"] == "sticky", m)
    if w <= 600:
        fx.ok(f"{tag}: mast is 40 px", abs(m["h"] - 40) <= 1, m)
        one = await pg.evaluate("(()=>{const ids=['clk','scrub','bPause'];const t=ids.map(i=>document.getElementById(i).getBoundingClientRect());return t.every(r=>r.width>0&&r.bottom<=41)})()")
        fx.ok(f"{tag}: transport collapsed to clock · scrub · Pause · x1/x30/x60 in one row", one and await pg.evaluate("[...document.querySelectorAll('#speed button')].filter(b=>b.offsetWidth).map(b=>b.dataset.r).join()") == "1,30,60",
              await pg.evaluate("[...document.querySelectorAll('#mast button,#mast input')].filter(b=>b.offsetWidth).map(b=>b.id||b.textContent)"))
    else:
        rows = await pg.evaluate("(()=>{const c=document.getElementById('clk').getBoundingClientRect(),r=[...document.querySelectorAll('.mastR>*')].filter(x=>x.offsetWidth).map(x=>x.getBoundingClientRect());return {clkTop:c.top,clkBottom:c.bottom,chipTops:[...new Set(r.map(x=>Math.round(x.top)))],mast:document.getElementById('mast').getBoundingClientRect().height,sw:document.getElementById('mast').scrollWidth,cw:document.getElementById('mast').clientWidth}})()")
        fx.ok(f"{tag}: chips wrap to a row below the clock", rows["chipTops"] and min(rows["chipTops"]) >= rows["clkBottom"] - 1, rows)
        fx.ok(f"{tag}: mast fits the width and stays compact (<= 120 px, three rows)", rows["sw"] <= rows["cw"] + 1 and rows["mast"] <= 120, rows)
    taps = await pg.evaluate(TAPS, "#mast button")
    small = [t for t in taps if t[1] < 44 or t[2] < 44]
    fx.ok(f"{tag}: mast tap targets >= 44 px ({len(taps)} visible buttons, #bSound included when mounted)", taps and not small, small or taps)
    # every section in turn
    for s in secs:
        await pg.evaluate(f"document.getElementById('{s}').scrollIntoView({{block:'start'}})")
        await pg.wait_for_timeout(900)
        await fx.wait(pg, "LOOP.frames>0", 2000)
        await pg.wait_for_timeout(600)
        vis = await pg.evaluate(f"(()=>{{const r=document.getElementById('{s}').getBoundingClientRect();return r.height>0&&r.top<innerHeight&&r.bottom>0}})()")
        sw = await pg.evaluate("[document.scrollingElement.scrollWidth, innerWidth]")
        off = await pg.evaluate(OFFENDERS)
        mt = await pg.evaluate("document.getElementById('mast').getBoundingClientRect().top")
        fx.ok(f"{tag} #{s}: visible, no horizontal scroll, no element past the viewport, mast stuck at top", vis and sw[0] <= sw[1] and not off and abs(mt) < 1, {"vis": vis, "sw": sw, "off": off, "mastTop": mt})
        await fx.shot(pg, f"v4_phone_{tag}_{s}.png")
    # canvases whose layout still follows the 300x150 default bitmap (no CSS height before the first draw): rendered height == width/2 for a width other than 300
    stale = await pg.evaluate("[...document.querySelectorAll('main canvas')].filter(c=>c.width===300&&c.height===150&&c.offsetWidth>0&&c.offsetWidth!==300&&Math.abs(c.offsetHeight-c.offsetWidth/2)<=1&&!c.classList.contains('mribbonCv')).map(c=>c.id||c.className)")
    fx.ok(f"{tag}: no panel canvas laid out at its 300x150 default aspect (CSS height before the first draw)", not stale, stale)
    undrawn = await pg.evaluate("[...document.querySelectorAll('main canvas')].filter(c=>c.width===300&&c.height===150&&c.offsetWidth>0).map(c=>c.id||c.className)")
    print("INFO", tag, "canvases not drawn yet (no data for them yet, layout held by CSS):", undrawn)
    heights = await pg.evaluate("[...document.querySelectorAll('main canvas')].filter(c=>c.offsetWidth>0&&c.offsetWidth>c.parentElement.clientWidth+1).map(c=>c.id||c.className)")
    fx.ok(f"{tag}: no canvas wider than its box", not heights, heights)
    # inspector open: click the first firehose row, tabs scroll inside their strip and are 44 px targets
    await pg.evaluate("document.getElementById('stream').scrollIntoView()")
    await pg.wait_for_timeout(600)
    await pg.evaluate("(()=>{const r=document.querySelector('#fh tr[data-id]');if(r)r.click()})()")
    await pg.wait_for_timeout(800)
    await pg.evaluate("document.getElementById('tabs')&&document.getElementById('tabs').scrollIntoView({block:'center'})")
    await pg.wait_for_timeout(400)
    tabs = await pg.evaluate(TAPS, "#tabs button")
    small = [t for t in tabs if t[1] < 44 or t[2] < 44]
    fx.ok(f"{tag}: inspector tabs >= 44 px ({len(tabs)})", len(tabs) == 11 and not small, small or tabs)
    strip = await pg.evaluate("(()=>{const t=document.getElementById('tabs');const s=getComputedStyle(t);return {wrap:s.flexWrap,ox:s.overflowX,sw:t.scrollWidth,cw:t.clientWidth,rows:new Set([...t.children].map(b=>Math.round(b.getBoundingClientRect().top))).size}})()")
    fx.ok(f"{tag}: inspector tabs are one horizontally scrolling strip", strip["wrap"] == "nowrap" and strip["ox"] in ("auto", "scroll") and strip["rows"] == 1, strip)
    sw = await pg.evaluate("[document.scrollingElement.scrollWidth, innerWidth]")
    off = await pg.evaluate(OFFENDERS)
    fx.ok(f"{tag}: inspector open: no horizontal scroll, no offenders", sw[0] <= sw[1] and not off, {"sw": sw, "off": off})
    await fx.shot(pg, f"v4_phone_{tag}_inspector.png")
    # both themes
    for theme in ("dark", "light"):
        await pg.evaluate(f"THEME.set('{theme}')")
        await pg.wait_for_timeout(500)
        ok_t = await pg.evaluate("document.documentElement.dataset.theme")
        sample = await pg.evaluate(CONTRAST)
        low = [x for x in sample if x[3] < x[4]]
        fx.ok(f"{tag} {theme}: text contrast >= 4.5:1 (3:1 for WCAG large text) on {len(sample)} sampled elements", ok_t == theme and len(sample) >= 30 and not low,
              {"low": low[:12], "min": min([x[3] for x in sample] or [0]), "sections": sorted({x[0] for x in sample})})
        if theme == "light" and w <= 600:
            for s in secs:
                if s in LIGHT_SHOTS:
                    await pg.evaluate(f"document.getElementById('{s}').scrollIntoView()")
                    await pg.wait_for_timeout(700)
                    await fx.shot(pg, f"v4_phone_{tag}_light_{s}.png")
    await pg.evaluate("THEME.set('dark')")

async def main():
    async with fx.browser() as b:
        for (w, h) in SIZES:
            pg = await fx.page(b, width=w, height=h)
            await fx.goto(pg)
            fx.ok(f"{w}: boot reaches BOOT.phase ready", await fx.wait(pg, 'BOOT.phase==="ready"', 180000), await pg.evaluate("[BOOT.phase,LOOP.frames]"))
            fx.ok(f"{w}: parts loaded (live.jpg deferred on phone: DATA.phone)", await fx.wait(pg, 'Object.entries(DATA.status).filter(([k])=>!k.startsWith("xsd")&&!(DATA.phone&&k==="live.jpg")).every(([,s])=>s.state==="loaded")', 150000))
            await pg.wait_for_timeout(1500)
            await fx.shot(pg, f"v4_phone_{w}_top.png")
            await sweep(pg, w, h)
            e = fx.errors(pg)
            fx.ok(f"{w}: no page errors", not e, e[:5])
            await pg.context.close()
    fx.summary()

fx.run(main)
