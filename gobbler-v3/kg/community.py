"""Pass 3a: the wider global X3D community, recalled by the model (provenance model_recall). 8 facets x 3 runs, vote.
Nothing here is Confirmed: it is the model's memory of public facts, graded Likely only when all 3 runs agree."""
import json, os, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gem, schema
G3 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = 'gemini-3.1-pro-preview'
FACETS = {
 'standards': 'Standards bodies, working groups and specifications around X3D: Web3D Consortium and its working groups, ISO/IEC 19775/19776/19777, X3D 3.x/4.0/4.1 milestones, H-Anim (ISO/IEC 19774), VRML97, related encodings (XML, ClassicVRML, JSON, Compressed Binary).',
 'runtimes': 'Runtimes, browsers and libraries that play X3D: X_ITE, X3DOM, Castle Game Engine, FreeWRL, InstantReality, Cobweb, Xj3D, BS Contact, Octaga and similar, with what each implements and who maintains it.',
 'authoring': 'Authoring, export, import, conversion and validation tools for X3D: X3D-Edit, Blender X3D add-ons, X3DJSONLD, x3d-tidy, Aopt, X3D Schematron/XSD validators, MeshLab, converters to glTF/USD, X3DUOM, Python/Java/JS language bindings (X3DPSAIL, X3DJSAIL, X3DOM...).',
 'people_orgs': 'Well-known public organisations and public professional roles in the X3D community (labs, universities, companies, consortium officers). Only include a person if you are certain of the name and public role; omit anything uncertain.',
 'events': 'Recurring conferences, birds-of-a-feather sessions, hackathons and releases where X3D work is presented (Web3D Conference, SIGGRAPH Web3D BOF, Khronos/AOUSD cross-talk, WebXR events).',
 'adjacent': 'Adjacent 3D ecosystems that X3D interoperates or competes with: glTF/Khronos, OpenUSD/AOUSD, OpenXR, WebXR, WebGPU, three.js, Babylon.js, A-Frame, Cesium and 3D Tiles/OGC, IFC/buildingSMART, PlayCanvas, Unreal, Unity, Blender, NVIDIA Omniverse.',
 'splats_ai': 'AI-era 3D: Gaussian splatting (INRIA 3DGS, SPZ, KHR_gaussian_splatting, X3D 4.1 GaussianSplats), MCP servers for 3D (Blender MCP, X3D MCP), text/image-to-3D models, LLM scene generation research, agentic 3D pipelines, relation to X3D.',
 'domains': 'Application domains where X3D is used: medical/molecular visualisation, CAD/PLM, geospatial/digital twins, cultural heritage, education, simulation (DIS, IEEE 1278), automotive/AEC, with notable projects.',
}
SYS = "You are an expert on the global X3D / Web3D community. Output only facts you are highly confident are true as of your knowledge; omit anything you would have to guess. Never invent people, versions or dates."
def prompt(facet, desc):
    cls = ', '.join(schema.CLASSES); pr = ', '.join(p for p in schema.PREDICATES if p not in ('step_of', 'feeds', 'co_used_with'))
    return f"""Facet "{facet}": {desc}

Return JSON {{"entities":[{{"name":"short canonical name","type":"<one of: {cls}>","note":"one factual sentence","confidence":0.0-1.0}}],
"triples":[{{"s":"entity name","p":"<one of: {pr}>","o":"entity name","confidence":0.0-1.0}}]}}
Give 25-45 entities and 40-80 triples. Prefer well-known, checkable facts. Reuse identical names across triples. Include the umbrella entities the facet hangs from (e.g. Web3D Consortium, X3D 4.0)."""

def run(a):
    facet, k = a
    fn = '%s/runs_community/%s_%d.json' % (G3, facet, k)
    if os.path.exists(fn): return fn
    for att in range(3):
        try:
            r = gem.jcall(MODEL, prompt(facet, FACETS[facet]), system=SYS, temperature=0.5, max_out=14000, tag='community:%s:%d' % (facet, k), cap=15.0)
            json.dump({'facet': facet, 'run': k, 'result': r}, open(fn, 'w')); return fn
        except Exception as e:
            err = str(e)[:80]
    return 'ERR %s %s' % (facet, err)
if __name__ == '__main__':
    os.makedirs(G3 + '/runs_community', exist_ok=True)
    jobs = [(f, k) for f in FACETS for k in range(3)]
    with cf.ThreadPoolExecutor(3) as ex:
        for r in ex.map(run, jobs): print(r[-70:], 'spent $%.3f' % gem.spent(), flush=True)
