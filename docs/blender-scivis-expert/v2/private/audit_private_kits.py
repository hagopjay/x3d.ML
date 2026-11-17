#!/usr/bin/env python3
"""Read-only, standard-library archive audit. Never imports or runs archived kits."""
from __future__ import annotations
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

BASE=Path(__file__).resolve().parents[1]
REPO=BASE/'source/x3d.ml'
REL='docs/blender-scivis-expert'
ROOT=REPO/REL
HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
OUT=BASE/'private'
OUT.mkdir(exist_ok=True)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def dump(name,value):(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def name(node):
    if isinstance(node,ast.Name):return node.id
    if isinstance(node,ast.Attribute):return name(node.value)+'.'+node.attr
    return '<expression>'

class Scan(ast.NodeVisitor):
    def __init__(self):self.depth=0;self.findings=[];self.imports=set();self.paths=set()
    def visit_Import(self,node):self.imports.update(a.name.split('.')[0] for a in node.names)
    def visit_ImportFrom(self,node):
        if node.module:self.imports.add(node.module.split('.')[0])
    def visit_FunctionDef(self,node):
        # Decorators/defaults execute at definition; body only executes when called.
        for d in node.decorator_list:self.visit(d)
        for d in (*node.args.defaults,*node.args.kw_defaults):
            if d is not None:self.visit(d)
        self.depth+=1
        for child in node.body:self.visit(child)
        self.depth-=1
    visit_AsyncFunctionDef=visit_FunctionDef
    def visit_Lambda(self,node):
        self.depth+=1;self.visit(node.body);self.depth-=1
    def visit_Constant(self,node):
        if isinstance(node.value,str) and (node.value.startswith(('/mnt/','/tmp/','/workspace/','/home/','~/')) or '/mnt/project-files/' in node.value):
            self.paths.add(node.value[:1000])
    def visit_Call(self,node):
        callee=name(node.func);cats=[]
        if callee in ('exec','eval','compile') or callee.endswith(('.exec_module','.load_module')):cats.append('dynamic-code-candidate')
        if callee.startswith(('subprocess.','os.system','os.popen')):cats.append('process-launch-candidate')
        if callee.startswith(('requests.','httpx.','urllib.request.','socket.')) or callee.endswith(('.urlopen','.urlretrieve')):cats.append('network-candidate')
        if callee.endswith(('.parse_args','.parse_known_args')):cats.append('cli-parse')
        if callee.endswith(('.write_text','.write_bytes','.mkdir','.makedirs','.save','.save_as_mainfile','.save_mainfile','.export_x3d','.write_image','.render','.unlink','.remove','.rmtree')):cats.append('write-or-render-candidate')
        if callee in ('open','io.open') or callee.endswith('.open'):
            mode=None
            if len(node.args)>1 and isinstance(node.args[1],ast.Constant):mode=node.args[1].value
            for kw in node.keywords:
                if kw.arg=='mode' and isinstance(kw.value,ast.Constant):mode=kw.value.value
            if isinstance(mode,str) and any(c in mode for c in 'wax+'):cats.append('file-write-candidate')
        if callee.startswith('bpy.ops.') and any(x in callee for x in ('read_factory_settings','open_mainfile','import_','export_','delete')):cats.append('blender-state-mutation-candidate')
        if cats:
            self.findings.append({'line':node.lineno,'callee':callee,'categories':cats,'syntactic_module_scope':self.depth==0,
                'expression':ast.get_source_segment(self.text,node)[:350] if ast.get_source_segment(self.text,node) else callee})
        self.generic_visit(node)

git_entries={}
raw=subprocess.check_output(['git','ls-tree','-r','-l','-z','HEAD','--',REL],cwd=REPO).decode()
for row in raw.split('\0'):
    if not row:continue
    info,p=row.split('\t',1);mode,kind,oid,size=info.split()
    git_entries[p]={'git_blob':oid,'git_mode':mode,'git_bytes':int(size)}
records=[];slice_counts=Counter();imports=Counter();hazards=Counter();module_hazards=Counter();absolute_paths=defaultdict(set);json_files=[]
for repo_path,meta in sorted(git_entries.items()):
    p=REPO/repo_path;raw=p.read_bytes();rel=p.relative_to(ROOT).as_posix();parts=Path(rel).parts
    git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if git_blob!=meta['git_blob']:raise RuntimeError('Working tree differs from pinned Git blob: '+repo_path)
    sl=parts[1] if parts[0]=='kits' and len(parts)>1 else 'knowledge-and-workflow'
    row={'path':rel,'repository_path':repo_path,'slice':sl,'bytes':len(raw),'sha256':sha(raw),'extension':p.suffix,**meta}
    if p.suffix in ('.x3d','.ply'):row['salvage_action']='reuse-as-bounded-fixture-after-current-validation'
    elif p.suffix=='.json':row['salvage_action']='preserve-as-historical-report-or-manifest-not-fresh-execution'
    elif p.suffix=='.patch':row['salvage_action']='review-and-rebase-existing-proposal-avoid-parallel-reimplementation'
    elif '/patched_src/' in rel:row['salvage_action']='reference-prototype-diff-against-exact-current-addon-before-adoption'
    elif p.suffix in ('.py','.sh'):row['salvage_action']='adapt-paths-pins-cli-and-output-receipt-before-executing'
    else:row['salvage_action']='archive-source-context-and-corrections'
    if len(raw)!=meta['git_bytes']:raise RuntimeError('Working tree byte count differs: '+repo_path)
    slice_counts[sl]+=1
    if p.suffix=='.py':
        text=raw.decode('utf-8');scan=Scan();scan.text=text
        try:
            scan.visit(ast.parse(text,filename=repo_path));row['python_parse']='pass'
            row['imports']=sorted(scan.imports);row['static_candidates']=scan.findings;row['absolute_path_literals']=sorted(scan.paths)
            imports.update(scan.imports)
            for f in scan.findings:
                hazards.update(f['categories'])
                if f['syntactic_module_scope']:module_hazards.update(f['categories'])
            for path in scan.paths:absolute_paths[path].add(rel)
        except SyntaxError as error:row['python_parse']={'status':'fail','line':error.lineno,'message':error.msg}
    if p.suffix=='.json':
        try:
            value=json.loads(raw);summary={'path':rel,'sha256':sha(raw),'bytes':len(raw),'root_type':type(value).__name__,'root_length':len(value)}
            if isinstance(value,dict):summary['keys']=list(value)
            row['json_parse']='pass';json_files.append(summary)
        except (ValueError,TypeError) as error:row['json_parse']={'status':'fail','message':str(error)}
    records.append(row)

doc_only=[]
for readme in sorted((ROOT/'kits').rglob('README.md')):
    parent=readme.parent;files=[p for p in parent.rglob('*') if p.is_file()]
    if files and all(p.name in ('README.md','CONTRIBUTING.md','release_notes.md','CODE_OF_CONDUCT.md','LICENSE','LICENSE.md') for p in files):
        doc_only.append({'directory':parent.relative_to(ROOT).as_posix(),'files':[p.relative_to(parent).as_posix() for p in files],
                         'status':'documentation-only snapshot; executable dependency source absent'})

names=defaultdict(list)
for row in records:names[Path(row['path']).name].append(row['path'])
critical={
 'splat-reference-source':['ref_render.py','cmp_png.py','rt_test.py','rt_test_lib.py','fixture_gen_sh3.py','rt_2000.json'],
 'science-rules':['sci-semantic-checks.patch','sci_checks.py','run_probes_sci.py'],
 'guard-prototype':['guard.sh','bl_phase.py','gate.py','blender_guard.py','blender_lane_probe.py'],
 'look-fixtures':['chart2.x3d','alpha.x3d','pl_1.x3d','pl_4.x3d','pl_16.x3d','pl_64.x3d','sort_hazard.x3d','sort_ok.x3d'],
 'missing-corpus-and-images':['snapshot_v1.jsonl','rt_summary.json','repro_bl.json','real_sphinx_mesh.json','D8B.stats.json','pix_0.exr','pix_1.exr','fig.blend','fig.png','E1-results.md'],
}
critical_records=[]
for group,values in critical.items():
    for value in values:critical_records.append({'group':group,'referenced_basename':value,'archived_candidates':names.get(value,[]),'status':'present-by-basename' if value in names else 'absent-from-this-folder','note':'Basename presence alone does not establish source/run identity.'})

comparison=[]
upload=BASE.parent/'upload'
for branch,attached in [('KNOWLEDGE-BASE-v1.md','KNOWLEDGE-BASE-v1 (2).md'),('KNOWLEDGE-BASE-v1.1-addendum.md','KNOWLEDGE-BASE-v1.1-addendum (2).md'),('FLYWHEEL-SYNERGY-v1.md','FLYWHEEL-SYNERGY-v1 (2).md')]:
    a=(ROOT/branch).read_bytes();b=(upload/attached).read_bytes()
    comparison.append({'branch_path':REL+'/'+branch,'attachment':attached,'branch_bytes':len(a),'attachment_bytes':len(b),'branch_sha256':sha(a),'attachment_sha256':sha(b),'byte_identical':a==b})

workflow_path=ROOT/'workflow-result-wf_6a9e68d8.json';wr=workflow_path.read_bytes();w=json.loads(wr)
grades={'Suspected':1,'Likely':2,'Confirmed':3};grade_names={v:k for k,v in grades.items()}
verifications=[]
for entry in w['verified']:
    bridge=entry['bridge'];verdicts=entry['verdicts'];all_grades=[bridge.get('grade','Suspected')]+[v.get('corrected_grade','Suspected') for v in verdicts]
    row={'bridge_id':bridge['id'],'synthesizer_grade':bridge.get('grade'),'verifier_count':len(verdicts),'corrected_grades':[v.get('corrected_grade') for v in verdicts],
         'lower_grade':grade_names[min(grades.get(g,1) for g in all_grades)],'ok_flags':[v.get('ok') for v in verdicts],
         'problem_counts':[len(v.get('problems',[])) for v in verdicts]}
    verifications.append(row)
summary={'schema':'scivis.raw-workflow-audit/1','confidentiality':'private','source_commit':HEAD,'source_path':REL+'/workflow-result-wf_6a9e68d8.json','source_sha256':sha(wr),'source_bytes':len(wr),
 'structure':{'digests':len(w['digests']),'catalog_bridges':len(w['catalog']['bridges']),'verified_bridge_rows':len(w['verified']),'verifier_verdicts':sum(len(v['verdicts']) for v in w['verified']),'critic_missing':len(w['critic']['missing']),'critic_overclaims':len(w['critic']['overclaims']),'critic_suggested_entries':len(w['critic']['suggested_additional_bridges']),'additional_bridge_ids':re.findall(r'B(?:19|2[0-7])',json.dumps(w['critic']['suggested_additional_bridges']))},
 'agent_count_interpretation':{'reported':52,'arithmetic':'14 readers + 1 synthesizer + 36 verifier verdicts + 1 critic = 52','qualification':'JSON stores reports, not provider execution receipts or independent agent identities.'},
 'digest_slices':[d['slice'] for d in w['digests']],'grade_rows':verifications,'lower_grade_counts':dict(Counter(v['lower_grade'] for v in verifications)),
 'attachment_comparisons':comparison,'embedded_evidence_boundary':'The workflow embeds narrative digests, bridge proposals, verifier reports and critic text. It does not embed all cited files, images, external corpus rows, tool executables or run receipts. Reported numbers do not become newly reproduced by parsing this JSON.',
 'three_documents_unchanged':all(c['byte_identical'] for c in comparison),
 'grade_interpretation':'These are historical grades reported by the archived workflow. This audit inspects the report; it does not promote its claims to fresh executed or reproduced evidence.'}
dump('raw-workflow-summary.json',summary)
audit={'schema':'scivis.kit-inventory/1','confidentiality':'private','audit_utc':datetime.now(timezone.utc).isoformat(),'repository':'hagopjay/x3d.ml','branch':'claude/project-thread-0lc3kd','source_commit':HEAD,'source_prefix':REL,
 'method':'Read-only byte hashing, JSON parsing and static Python AST inspection. No archived kit was imported or executed. Static candidates are review leads, not proof of harmful behavior; syntactic module-scope includes statements under __main__ guards and conditional branches.',
 'counts':{'files':len(records),'bytes':sum(v['bytes'] for v in records),'extensions':dict(Counter(v['extension'] for v in records)),'slices':dict(slice_counts),'python_parsed':sum(v.get('python_parse')=='pass' for v in records),'python_parse_failures':[v['path'] for v in records if isinstance(v.get('python_parse'),dict)]},
 'static_candidate_counts':dict(hazards),'syntactic_module_scope_candidate_counts':dict(module_hazards),'imported_modules_by_file_count':dict(imports.most_common()),
 'absolute_path_literals':[{'literal':p,'referenced_by':sorted(fs)} for p,fs in sorted(absolute_paths.items())],
 'documentation_only_dependency_snapshots':doc_only,'json_documents':json_files,'critical_artifact_presence':critical_records,'attachment_comparisons':comparison,'files':records}
dump('kit-inventory.json',audit)
print(json.dumps({'files':len(records),'bytes':audit['counts']['bytes'],'slices':dict(slice_counts),'all_attachments_identical':summary['three_documents_unchanged'],'grades':summary['lower_grade_counts'],'documentation_only_dependencies':len(doc_only),'static':dict(hazards),'module_scope':dict(module_hazards),'python_parse_failures':audit['counts']['python_parse_failures']}))
