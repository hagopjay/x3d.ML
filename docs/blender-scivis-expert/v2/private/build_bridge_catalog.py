"""Collate the supplied historical bridge proposals without promoting claims."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path('/workspace/scratch/aee90170662d')
OUT=ROOT/'blender-scivis-integration/private'
SOURCE=ROOT/'upload/FLYWHEEL-SYNERGY-v1 (2).md'
text=SOURCE.read_text()
lines=text.splitlines()

# New editorial review. These fields are proposals, not executed results.
reviews={
'B01':('WP1','P1',[],[],[], 'Reconstruct the SH0–SH3 ladder from retained kits; keep N=2000 and N=3125 runs separate and create independent per-field expected-loss rows.', ['splat_field_fidelity','quaternion_sign_equivalence','opacity_space','codec_profile'], 'Alpha-space <=1e-6 is unmeasured; measured historical logit differences and clamp losses cannot be called exact. Distinct fixture counts and missing renderer pins prevent promotion.'),
'B02':('WP1','P1',[],[],[], 'Locate and evaluate existing BUG-2 patch before writing another. Expose resource-limited/validator-error outcomes separately from scientific invalidity.', ['validation_attempt','resource_budget','parser_configuration'], 'Already tracked BUG-2; conflicting pins and parser/XSD limits require a current minimal reproducer. huge_tree alone is neither a complete bound policy nor an XSD-engine fix.'),
'B03':('WP1','P2',['B01'],['B02'],[], 'Specify byte budgets per field/node and preserve field alignment. Separate fixed-camera depth slabs from view-independent cells and measure each.', ['partition','view_dependency','bounding_volume','ordering_policy'], 'Depth-slab PSNR does not establish spatial-cell fidelity. A single-node baseline must use a count that actually fits. Reuse Sphinx files rather than retrain.'),
'B04':('WP2','P1',['B24'],[],[], 'Freeze before-fix readbacks, then target color/default fixtures against an exact add-on commit. Keep energy/look tuning optional and separate from data conversion.', ['color_encoding','default_value','appearance_contract','conversion_policy'], 'PR25 ordering is spurious; importer vs extractor touch different files. The owned bridge color conversion is evidence for that adapter only, not a fork fix.'),
'B05':('WP5','P1',[],['B24'],['B02'], 'Add declarative source-scene loss findings to the existing owning runner; report refusal, warning and failure independently. Inspect the source before export.', ['source_loss_audit','finding','severity','validation_attempt'], 'Guard and loss audit were separate prototypes; --data-colour was required for the recorded fail. Counts of three caught mistakes mixed errors with warnings.'),
'B06':('WP2','P2',[],['B04','B24'],[], 'Parameterize chart capture/comparison and freeze each camera, tone-map pair, patch mask and metric before claiming parity.', ['render_configuration','color_comparison','measurement_window','tolerance'], 'Neutral/Neutral and NONE/Standard results are mixed in the source. Unlit <=1 is conditional on an unfinished change; authored stills do not close cross-engine parity.'),
'B07':('WP2','P1',[],['B24'],[], 'Reconstruct crash controls, require an atomic refusal or complete import, and build an independently held-out mutant set beyond the tuned v2 coverage.', ['failure_family','mutant','held_out_partition','import_transaction'], '293/293 is coverage of mutants used to write checks, not generalization. Returning FINISHED after silently skipping corrupt data is not a suitable universal success criterion.'),
'B08':('WP1','P2',['B01'],['B24'],[], 'Recreate the oracle/ordering scenes with exact camera and renderer identities; store the table rather than relying on directory names.', ['reference_oracle','ordering_policy','camera_pose','render_comparison'], 'Historical headline PSNR values conflict across fixture directories. The premise that each wrong case is validator-clean also needs an executed record.'),
'B09':('WP3','P1',[],['B02','B24'],[], 'Recover the existing patch and list emitted rule IDs programmatically. Separate hard constraints from domain assumptions and heuristics before rebasing.', ['semantic_rule','scientific_witness','heuristic','finding'], 'The document disagrees over 11 vs12 IDs, including provenance-meta-missing; 496 passed is inferred without a complete log. Large-tree support is conditional, not a blocker for small probes.'),
'B10':('WP3','P1',[],['B04','B24'],[], 'Use one fixture profile and one expected-loss schema. Add genuine known-answer heatmap, pLDDT, volume and unit cases after preserving historical controls.', ['scientific_case','quantity','fixture','expected_loss'], '26 vs27 files and absent nanometre/heatmap/volume fixtures show a plan was conflated with implementation. Fixture authoring can proceed before importer fixes; repaired expectations cannot.'),
'B11':('WP2','P2',[],['B04','B07','B24'],[], 'Supply corpus manifests to the existing loss-ledger owner. Define stable per geometry, route tuple and attribute field, rather than by tag counts.', ['corpus_partition','retention_measurement','route_binding','expected_loss'], 'TierA111 refers to coarse mesh stats; only11 retained identical tag bags. TierB44 has no retained manifest. 91/167 scenes with any ROUTE is not route retention.'),
'B12':('WP4','P1',[],['B24'],[], 'Extend the owning x3dprov implementation with named byte/semantic/pixel hash methods and figure derivation, without creating a competing chain.', ['prov:Entity','prov:Activity','prov:wasGeneratedBy','hash_method','figure'], 'Current content hashes and render receipts establish useful bindings but are not an x3dprov chain or a signature. Repeated pixel identity needs its own recorded experiment.'),
'B13':('WP7','P1',[],['B01'],[], 'Refresh dated compatibility claims, then run seven explicit native-splat layout probes on a named supported binary. Reuse the existing ecosystem watcher.', ['software_build','capability_probe','compatibility_assertion','valid_time'], 'The 25Oct daily-build plan and alpha status are stale. Layout probe can run standalone; only full native parity depends on B01. SPZ/SOG and KHR ratification claims conflict and need primary sources.'),
'B14':('WP5','P2',[],['B05','B10'],[], 'Define pure wrappers and durable checkpoints around the owning workflow. First demonstrate interruption/resume using deterministic local fixtures and zero model calls.', ['workflow_run','checkpoint','transition','budget_policy'], 'Do not import the historical agent_loop.py: it reportedly had argparse and gcloud side effects plus remote endpoints. In-memory MemorySaver does not prove process-kill recovery.'),
'B15':('WP6','P2',['B05','B10'],[],[], 'Provide the existing scorekeeper with a vector of validation, runtime, Blender and data-fidelity outcomes plus explicit oracle disagreements.', ['oracle_result','oracle_disagreement','data_fidelity','evaluation_partition'], 'The source corrects15 exports to16 from17inputs. Headlight emulation makes the Blender probe conditional; independent rendering does not imply independent semantics. No D rung was retained.'),
'B16':('WP1','P2',['B01'],['B13'],[], 'Keep codec-version/axis/antialias flags in a sidecar and compare a recovered decoder against an independent reference implementation.', ['codec_profile','quantization','sidecar_asset','antialiasing_convention'], 'Marble SH0 files cannot validate SH3 budgets. A from-memory SPZ-like encoder is not an SPZ conformance oracle; published twins from the same decoder are not independent evidence.'),
'B17':('WP4','P1',[],[],[], 'Repair lexical classifier false positives and record explicit rights status separately from validity and training eligibility; keep policy decisions explicit.', ['dct:license','rights_assertion','derivative_policy','training_eligibility'], 'Historical Confirmed applies to a mismatch finding, not a shipped passport. Only7 of11were forkexports; absent licence data cannot be created by classification, and a passport does not repair six invalid files.'),
'B18':('WP6','P3',['B05','B11','B15'],[],[], 'Pre-register a reproducible feasible-prompt selector and per-arm funnel, then implement an offline stub run before authorizing a budgeted experiment.', ['experiment','experimental_arm','prompt_partition','confidence_interval'], 'The115subset does not exist in the supplied description; baseline percentages are first-try validity, not fidelity. The harness and cost estimate are proposals, and paired judges need order-bias calibration.'),
'B19':('WP3','P2',['B10'],[],[], 'Build an analytic phantom with anisotropic spacing and independent array/isosurface checks before comparing any volume-rendered pixels.', ['volume','voxel_spacing','transfer_function','coordinate_frame'], 'One-voxel radius agreement is a proposed bound, not a current result. Pixel PSNR depends on matching transfer, sampling, camera and extinction assumptions.'),
'B20':('WP3','P2',['B10'],[],[], 'Create a small explicitly attributed molecular fixture with stable atom/residue/bond identities and known coordinate-derived distances; test instancing separately.', ['molecule','atom','residue','bond','prediction_confidence'], 'pLDDT belongs to prediction confidence, not binding affinity. Generic PDB B factors must not automatically be interpreted as pLDDT; domain provenance controls decoding.'),
'B21':('WP3','P1',['B10'],[],[], 'Add local-origin plus CRS/units mapping, and compare world reconstruction against high-precision coordinates at multiple offsets/scales.', ['coordinate_reference_system','local_origin','quantity','precision_budget'], 'A CoordinateDouble declaration does not prove the downstream host retains double precision. Named ULP/spacing and reconstruction error are better criteria than a blanket float32 tolerance.'),
'B22':('WP3','P2',[],['B10'],[], 'Record semantic ROUTE tuples and animation values at fixed normalized fractions; test rotations using orientation equivalence rather than raw quaternion components.', ['temporal_state','route_binding','interpolator','time_mapping'], 'Saved independent checkpoints in ResearchLoom are not an X3DROUTE-to-BlenderActions roundtrip. Equal key counts do not establish animation parity.'),
'B23':('WP3','P3',[],['B10'],[], 'Generate parent/hierarchy and weight fixtures from the ontology; distinguish valid HAnim hierarchy, skin deformation and Blender armature representation.', ['humanoid','joint','segment','site','skinning_weight','legal_parent'], 'Legal parent lookup and LOA metadata alone do not establish correct centers, bind pose or skin deformation. Reuse existing HAnim fixtures before adding another suite.'),
'B24':('WP0','P0',[],[],[], 'Inventory the private repository kits and raw workflow first; hash recoverable assets and freeze a before-fix baseline without fabricating missing scratch.', ['evidence_artifact','availability','historical_claim','baseline'], 'An attachment describing scratch is not the scratch. Mark unavailable kits as unresolved rather than reconstructing outputs and presenting them as recovered history.'),
'B25':('WP1','P2',[],['B10','B24'],[], 'Separate byte determinism, semantic equivalence, pixel reproducibility and measured scalability. Run bounded increasing scales with explicit stop/refusal outcomes.', ['determinism_profile','performance_measurement','resource_budget','semantic_hash'], 'Roundtrip equality and source identity do not establish repeated-export determinism; 1Mgeometry is beyond currentResearchLoom budgets. Do not infer a general splat wall from old hardware/library pins.'),
'B26':('WP2','P1',[],['B01','B04','B06'],[], 'Reuse current science GLBs as the first cross-format cases, then add PBR/texture/alpha and USD comparisons under separate contracts.', ['exchange_projection','material_mapping','third_path_comparison','expected_loss'], 'ResearchLoom has realGLBexport/reimport evidence but noUSD, nativeX_ITE parity, spline/point topology preservation or full KHRmaterial comparison.'),
'B27':('WP2','P1',[],['B10','B04'],[], 'Promote the current mesh/line/point fixture into a shared add-on regression and expand to ColorRGBA, LineSet variants and native non-splat PointCloud.', ['point_observation','line_sample','color_encoding','glyph_mapping'], 'Current owned bridge expands points and lines to glyph/tube meshes. That preserves selected observation coordinates, not nativePointSet/LineSet topology in Blender or glTF.'),
}

source_info=[]
for name in ('KNOWLEDGE-BASE-v1 (2).md','KNOWLEDGE-BASE-v1.1-addendum (2).md','FLYWHEEL-SYNERGY-v1 (2).md'):
 p=ROOT/'upload'/name
 source_info.append({'filename':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'inspection':'entire attachment read; references to other files are historical reports until separately recovered'})

rank={}
for line in lines:
 if re.match(r'\| \d+ \| B\d\d-',line):
  cells=[c.strip() for c in line.strip('|').split('|')]
  key=re.search(r'B\d\d',cells[1]).group()
  rank[key]={'rank':int(cells[0]),'direction':cells[2],'effort':cells[3],'cost_as_reported':cells[4], 'grade_as_reported':cells[5].replace('**',''),'owner_as_reported':cells[6]}

headers=list(re.finditer(r'^#### \d+\. (B\d\d)-([^:]+): (.+?)  \(([^)]+)\)$',text,re.M))
bridges=[]
for n,h in enumerate(headers):
 end=headers[n+1].start() if n+1<len(headers) else text.index('\n## 8. Missing links',h.end())
 section=text[h.end():end]
 key=h.group(1)
 raw={}
 for field,pattern in [('what','What'),('inputs','Inputs'),('deliverable','Deliverable'),('pass_criteria','Test / pass criteria'),('pins','Pins'),('dependencies','Depends on'),('visual_fidelity','Visual fidelity')]:
  m=re.search(r'^- \*\*'+re.escape(pattern)+r':\*\* (.+)$',section,re.M)
  raw[field]=m.group(1) if m else None
 notes=re.findall(r'^- \*Verifier:\* (.+)$',section,re.M)
 bridges.append({'id':key,'slug':h.group(2),'title':h.group(3),'historical_grade':h.group(4),'source_lines':[text[:h.start()].count('\n')+1,text[:end].count('\n')], 'historical_catalog':rank[key], 'historical_proposal':raw, 'historical_verifier_notes':notes})
for i,line in enumerate(lines):
 m=re.match(r'- (B(?:19|2[0-7])) ([A-Z-]+): (.+)',line)
 if m:
  bridges.append({'id':m.group(1),'slug':m.group(2),'title':m.group(2).replace('-',' ').title(),'historical_grade':'proposed by completeness critic; ungraded','source_lines':[i+1,i+1], 'historical_proposal':{'what':m.group(3)},'historical_verifier_notes':[]})

for b in bridges:
 wp,priority,hard,conditional,removed,action,hooks,caveat=reviews[b['id']]
 b['review']={'work_package':wp,'priority':priority,'hard_dependencies':hard,'conditional_dependencies':conditional,'removed_dependencies':removed,'next_action':action,'ontology_hooks_proposed':hooks,'critical_scope_correction':caveat,'status':'historical proposal reviewed; no claim of original-kit execution in this subtask','newly_implemented_in_this_subtask':False,'public_action':'none; private catalog only','planned_kit':b['id'].lower()+'-'+b['slug'].lower()}
 b['review']['privacy']='private; sanitize before any optional public code/fixture handoff'
 b['review']['evidence_requirement']='input hashes, fixture cardinalities, quantity/space, instrument/tool identities, observed/limit/rule, status and output hashes'

work_packages=[
 {'id':'WP0','name':'Evidence recovery and baseline','bridges':['B24'],'product':'Hashed recovery manifest, exact version register, claim registry, frozen before-fix records'},
 {'id':'WP1','name':'Representation, splats, compression and scale','bridges':['B01','B02','B03','B08','B16','B25'],'product':'One parameterized ladder plus parser/resource-budget and codec adapters'},
 {'id':'WP2','name':'Exchange retention and rendering contracts','bridges':['B04','B06','B07','B11','B26','B27'],'product':'One per-field expected-loss ledger and consumer-specific comparison profiles'},
 {'id':'WP3','name':'Scientific quantities and domain fixtures','bridges':['B09','B10','B19','B20','B21','B22','B23'],'product':'Known-answer cases, semantic rule data and domain-specific witness functions'},
 {'id':'WP4','name':'Provenance and rights','bridges':['B12','B17'],'product':'Extend existing provenance chain; separate rights facts from eligibility policy'},
 {'id':'WP5','name':'Guarded workflow and orchestration','bridges':['B05','B14'],'product':'Source audit adapter, no-side-effect wrappers, durable checkpoints'},
 {'id':'WP6','name':'Oracle evaluation and controlled experiments','bridges':['B15','B18'],'product':'Vector outcomes and pre-registered held-out paired evaluation'},
 {'id':'WP7','name':'Compatibility and capability watch','bridges':['B13'],'product':'Dated capability assertions backed by native probes and exact software builds'},
]
questions=[
 {'id':'Q01','question':'Which exact validator commits/profile are authoritative for each scene class?','resolution':'Use a per-run instrument identity; compare legacy integration behavior before selecting an ecosystem-wide default. Do not choose an uninspected old branch label.'},
 {'id':'Q02','question':'Which original kits/raw workflow can be recovered from the private branch?','resolution':'Root agent owns private access; attachments alone do not establish file availability. Preserve recovered bytes and hashes; record absent artifacts separately.'},
 {'id':'Q03','question':'What must survive each hub, and in what coordinate/color/numeric space?','resolution':'Define a per-projection contract for analytical arrays, display geometry and authored appearance; losses may be expected while scientific arrays remain authoritative.'},
 {'id':'Q04','question':'What is the canonical provenance/hash method?','resolution':'Keep byte hash, semantic hash, pixel hash and signature distinct; record algorithm/version and asset graph. Extend the existing x3dprov owner.'},
 {'id':'Q05','question':'Should color parity be an explicit profile independent of appearance rendering?','resolution':'Provide named profiles with recorded transforms; choose neither AgX nor Standard as a universal scientific truth. Compare actual data-to-color mapping separately.'},
 {'id':'Q06','question':'How are rights, derivative permission and training eligibility decided?','resolution':'Store explicit rights facts, provenance and uncertainty; make eligibility a versioned policy. Missing licences remain unknown; no classifier should infer a grant.'},
 {'id':'Q07','question':'What constitutes atomic importer success on a malformed scene?','resolution':'Either complete the declared supported subset or refuse with typed findings. FINISHED plus silently dropped scientific data is not equivalent to successful retention.'},
 {'id':'Q08','question':'How are model-based assumptions represented?','resolution':'Gaussian coverage, prediction confidence, volume transfer and physical display magnification need distinct semantic properties and assumption witnesses.'},
 {'id':'Q09','question':'What counts as a blind evaluation?','resolution':'Keep rule-development mutants and held-out generators separate, freeze them by hash, and report coverage separately from generalization.'},
 {'id':'Q10','question':'What is the supported native-splat layout today?','resolution':'Refresh primary sources and execute seven probes: base/DC, opacity, scale encoding, quaternion order, SH order, axis and color space.'},
 {'id':'Q11','question':'What is the budget for real model arms and remote corpus reads?','resolution':'Complete local stub/read-only integration first; any later billable/model/cloud experiment is a separately scoped decision. Do not inherit an old estimated budget as approval.'},
]
loops=[]
for i,line in enumerate(lines):
 if re.match(r'- L[1-6] ',line):loops.append({'id':re.match(r'- (L\d)',line).group(1),'historical_text':line[2:],'source_line':i+1})
edges=[]
for i,line in enumerate(lines):
 if re.match(r'- E\d\d ',line):edges.append({'id':re.match(r'- (E\d\d)',line).group(1),'historical_text':line[2:],'source_line':i+1,'current_status':'not promoted by this catalog; consult current-evidence-map.json'})
data={'schema':'scivis.private-bridge-catalog/2','review_date':'2026-11-17','privacy':'private','scope':'Full supplied KBv1, KBv1.1 and FlywheelSynergyv1 attachments; original private repository and raw workflow are not inspected by this subtask. Current ResearchLoom mapping is separately byte-pinned.','sources':source_info,'evidence_policy':{'historical_reported':'Original grade retained without promotion; no original kit was executed here.','document_inspected':'The complete attached text was read and source locations retained.','artifact_inspected':'Named bytes/receipts can support only their stated scope.','current_executed':'Only a new run with inputs/instruments/output identities may establish a new result.','no_transitive_confirmation':'A bridge does not become confirmed because a related adapter passes a narrower fixture.'},'work_packages':work_packages,'bridges':bridges,'workflow_edges_as_reported':edges,'loops_as_reported':loops,'open_questions':questions,'counts':{'original_bridges':18,'critic_candidates':9,'total':len(bridges),'work_packages':len(work_packages),'workflow_edges':len(edges),'loops':len(loops)}}
kb=(ROOT/'upload/KNOWLEDGE-BASE-v1 (2).md').read_text()
master=kb.split('## 10. Master hands-on test list',1)[1].split('## 11.',1)[0]
data['kb_master_tests_as_reported']=[{'number':int(m.group(1)),'text':m.group(2),'status':'historical candidate; execution not inferred'} for m in re.finditer(r'^(\d+)\. (.+)$',master,re.M)]
data['native_splat_probe_questions']=[{'id':'NS'+str(i+1),'meaning':meaning,'status':'requires current named native build and input encoding'} for i,meaning in enumerate(('radiance base: SH DC versus RGB','opacity: raw versus sigmoid/logit','scale: linear versus exponentiated','rotation: quaternion component order and normalization','SH: coefficient and channel slot order','axis: source/host/world convention','color: encoded versus linear convention'))]
data['kit_slices_to_reconcile']=[{'slice':name,'candidate_references':refs,'status':'named historical/repository slice; actual private kit availability is not inspected by this subtask'} for name,refs in [
 ('spine',['snapshot_v1.jsonl','manifest_clean_ondisk.json','fixtures_candidate_tierA.json','mutate.py','mutate_v2.py','sweep_rt.jsonl','sweep_mut2.jsonl']),
 ('splat-trailer',['rt_test.py','fixture_gen_sh3.py','real_rt.py','ref_render.py','cmp_png.py','fx3','fx4','fx5','probe_blender53_splat.py']),
 ('blender-io',['fixtures/','gen_splat_x3d.py','defaults','source/splat_native.py','importer crash-site list']),
 ('agentics',['blender_lane_probe.py','loss_audit source function','out/result.json']),
 ('x3d-mcp-fork',['guard.sh','bl_phase.py','gate.py','sci-semantic-checks.patch','probe_scenes','probes_patched.jsonl','pytest_main_rerun.txt']),
 ('ontology',['build_scene.py','bridge_fixture.x3d','defaults_probe2.x3d','defaults_audit.py','xb-shapes.ttl','xb-hanim.ttl']),
 ('compression',['spz_to_ply.py','splat_table_v2.md','fid.py','fid_rows.json','abl.out']),
 ('DSPy red-team',['bl_probe.py','repro_bl.json','x3d_metric.py','attacker.py','reproducers/r00-r08']),
 ('hall-build',['chart2/','alpha/','plight/','sorthaz/','make_chart2.py','measure_chart.py','chart_compare.py']),
 ('demos',['color.x3d','coltest.py','coltest_patched.py','look targets']),
 ('x3d-ml',['x3dprov.py','t2_roundtrip.py','t4_render_stamp.py','t4b_repro.py','t9_meta_places.py','out_t4/t4_result.json'])]]
data['historical_user_questions']=[{'source_line':i+1,'text':line[2:],'status':'historical question, not current blocking approval'} for i,line in enumerate(lines) if i>=586 and i<593 and line.startswith('- ')]
current_path=OUT/'current-evidence-map.json'
if current_path.is_file():
 current=json.loads(current_path.read_text())
 current_rows={row['id']:row for row in current['bridges']+current['candidate_bridge_updates']}
 for b in bridges:
  b['current_research_loom_mapping']=current_rows.get(b['id'],{'status':'not_mapped_in_current_evidence_subtask','reason':'Domain candidate or recovery/scale task outside the current18-plus-B26/B27 mapping.'})
 data['current_evidence_map']={'file':current_path.name,'sha256':hashlib.sha256(current_path.read_bytes()).hexdigest(),'summary':current['summary'],'fresh_artifact_identity_audit':current['fresh_artifact_identity_audit'],'evidence':current['evidence']}
assert len(bridges)==27 and len({b['id'] for b in bridges})==27
(OUT/'bridge-catalog.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(data['counts']))
