from pathlib import Path
import hashlib
import json

BASE=Path('/workspace/scratch/aee90170662d')
REPO=BASE/'x3d.STEM'
STUDY=REPO/'studies/research-loom'
OUT=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(rel):return json.loads((STUDY/rel).read_text())
bank=read('web/bank/index.json')
packets={row['id']:json.loads((STUDY/'web/bank'/row['packet']).read_text()) for row in bank['cases']}
paths=[
 'CONTRACT.md','README.md','docs/BLENDER-HUB.md','docs/EXCHANGE-CONTRACT.md',
 'docs/FOLDBACK.md','docs/VALIDATION.md','evidence/build.json','evidence/release.json',
 'evidence/verification.json','evidence/x3d-validation.json','web/bank/index.json',
 'evidence/blender-stock-extension.json','evidence/blender-ecosystem-fork.json','evidence/blender-runtime.json',
 'stemloom/core.py','stemloom/exchange.py','stemloom/blender_io.py','tools/build.py',
 'tools/check.py','tools/validate_x3d.py','tools/verify.py','tools/export_glb.py',
 'serve.py','tests/test_server.py','tests/test_pipeline.py','tests/test_exchange.py',
 'tests/test_blender_contract.py','tests/scene.test.cjs']
for kind in ('flow','tensor','modes'):
 for action in ('transfer','render','glb'):paths.append(f'evidence/blender-{action}-{kind}.json')
evidence={f'E{i+1:02}':{'path':'studies/research-loom/'+p,'sha256':sha(STUDY/p),'bytes':(STUDY/p).stat().st_size} for i,p in enumerate(paths)}
by_path={v['path'].removeprefix('studies/research-loom/'):k for k,v in evidence.items()}
def refs(*names):return [by_path[n] for n in names]

# This is a fresh byte-identity audit only, not rerunning Blender or science.
checks=[]
for row in bank['cases']:
 raw=(STUDY/'web/bank'/row['packet']).read_bytes()
 checks.append({'scope':'packet','id':row['id'],'pass':len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']})
for rel,digest in bank['source_sha256'].items():
 checks.append({'scope':'bank_producer','id':rel,'pass':sha(STUDY/rel)==digest})
release=read('evidence/release.json')
for rel,digest in release['source_sha256'].items():
 checks.append({'scope':'release_source','id':rel,'pass':sha(STUDY/rel)==digest})
for kind in ('flow','tensor','modes'):
 render=read(f'evidence/blender-render-{kind}.json')
 image=STUDY/f'docs/assets/{kind}.png'
 checks.append({'scope':'render_png','id':kind,'pass':sha(image)==render['image_sha256'] and image.stat().st_size==render['image_bytes']})
 glb=read(f'evidence/blender-glb-{kind}.json')
 checks.append({'scope':'glb','id':kind,'pass':sha(STUDY/f'exports/blender/{kind}.glb')==glb['glb_sha256']})
 checks.append({'scope':'scientific_blend','id':kind,'pass':sha(STUDY/'exports/blender'/glb['source_blend_name'])==glb['source_blend_sha256']})
if not all(c['pass'] for c in checks):raise RuntimeError('Current byte identity audit failed')

rows=[]
def bridge(id,title,status,priority,implemented,gap,adopt,evidence_refs,ontology):
 rows.append({'id':id,'title':title,'original_scope_status':status,'priority':priority,
  'current_implemented_elements':implemented,'remaining_acceptance_gap':gap,
  'integration_action':adopt,'evidence_refs':evidence_refs,'ontology_hooks':ontology,
  'evidence_level':'inspected_current_source_and_executed_receipts; artifact_identity_rechecked; no application rerun'})
bridge('B01','Splat round-trip ladder','not_addressed','P1',
 'Research Loom has durable deterministic case packets, manifest hashes, explicit geometric tolerances and negative controls for meshes/lines/points.',
 'No GaussianSplats, SH0–SH3 fields, opacity/logit clamp fixtures, real splat datasets or X_ITE-vs-splat-oracle PSNR are in this study.',
 'Reuse manifest, source binding and expected-loss patterns for a separate splat fixture suite; preserve historical splat numbers as reported until their exact bytes and pins are recovered.',
 refs('web/bank/index.json','tools/build.py','evidence/release.json'),['Fixture','FieldEncoding','ExpectedLoss','RoundTripObservation'])
bridge('B02','Validator large-attribute verdict','partially_closes','P0',
 'The pinned adapter has an explicit 2 MiB input cap and records an input refusal separately from pass/fail of XSD/semantic checks.',
 'No large-attribute ladder, huge_tree patch or XSD engine ceiling was executed by Research Loom. Bounded small scenes cannot substantiate a large-splat fix.',
 'Adopt its honest scoped refusal vocabulary, then recover or rebuild the historical large-attribute fixtures under the selected validator pin and explicit parser budgets.',
 refs('tools/validate_x3d.py','evidence/x3d-validation.json'),['Instrument','InputBudget','Refusal','ValidationObservation'])
bridge('B03','Splat export slabs','not_addressed','P2',
 'The Blender source text block is compressed and line-chunked to avoid a real long-line performance pathology.',
 'That source-text envelope is not GaussianSplats spatial/depth slabbing, and no render-order or per-attribute size claims follow from it.',
 'Keep the text-envelope performance fix separate; specify slabbing against measured attribute bytes, scientific field retention and compositing order.',
 refs('stemloom/blender_io.py','docs/BLENDER-HUB.md'),['RepresentationEncoding','PartitionStrategy','OrderingConstraint','PerformanceObservation'])
bridge('B04','Importer value correctness','partially_closes','P0',
 'An owned adapter uses proper Y-up/Z-up rotation, explicit sRGB/linear conversion, actual vertex/glyph/tube readback and scalar-appearance comparisons. External stock and fork routes have separate executed mixed-fixture loss receipts.',
 'No broad fork material/default/Unlit/light-energy regression pack is delivered; the owned adapter is not a repair of the external fork.',
 'Promote the asymmetric fixture and actual-coordinate mutation control into a handoff pack for x3d-blender-io; add field-specific tolerances and material/default controls without broadening current success claims.',
 refs('stemloom/blender_io.py','evidence/blender-stock-extension.json','evidence/blender-ecosystem-fork.json','evidence/blender-transfer-flow.json','evidence/blender-transfer-tensor.json','evidence/blender-transfer-modes.json'),['CoordinateConvention','ColorEncoding','AdapterVersion','RetentionObservation','MutationControl'])
bridge('B05','Blender agent guard','partially_closes','P0',
 'Study publication is gated before index replacement; canonical packet/frame bytes, producer hashes and declared witness inequalities are checked. Imports are bound to exact canonical packet bytes and stale producer processes refuse requests.',
 'This is not a sandbox for arbitrary bpy scripts, a Blender MCP preflight, an agent repair loop or a complete feature-loss audit.',
 'Wrap existing deterministic gates with a thin script-lane runner whose contracts distinguish eligibility, unsupported data and execution failure. Add pre-export loss rules rather than inferring completeness from XSD success.',
 refs('stemloom/core.py','tools/build.py','serve.py','tests/test_server.py','tests/test_pipeline.py','evidence/release.json'),['Candidate','EligibilityDecision','ProducerSnapshot','ExecutionAttempt','LossFinding'])
bridge('B06','Look parity chart','partially_closes','P1',
 'Data colors are declared sRGB; explicit piecewise conversion is measured, studio Blender renders use Standard display transform, and GLB serialization is compared separately from BYTE_COLOR reimport.',
 'No cross-renderer numeric chart, ΔE/PSNR gate, alpha sorting chart or native X_ITE pixels were executed here. A beautiful Blender render is not a look-parity result.',
 'Reuse color fixtures but run paired unlit/value-preserving chart measurements with common camera/exposure/background before judging scene appearance.',
 refs('docs/BLENDER-HUB.md','evidence/blender-render-tensor.json','evidence/blender-glb-tensor.json','evidence/release.json'),['ColorEncoding','ViewTransform','RenderConfiguration','ImageMetric','ComparisonProtocol'])
bridge('B07','Importer must-not-raise corpus suite','partially_closes','P1',
 'The owned bounded X3D reader rejects unsupported/static-subset violations and unsafe/malformed inputs; unit tests exercise actual coordinate edits and invalid topology. Actual Blender-coordinate tampering is caught.',
 'No 585-scene corpus or 3,649 mutant set was inspected or executed in this map, and no general external-importer crash result is established.',
 'Use source-hashed failure fixtures and expected refusals in a corpus manifest; retain crashes, unsupported features and preflight-invalid inputs as distinct outcomes.',
 refs('stemloom/exchange.py','tests/test_exchange.py','tests/test_pipeline.py','tests/test_blender_contract.py'),['CorpusMember','MutantOf','UnsupportedFeature','Crash','ExpectedRefusal'])
bridge('B08','Splat oracle ordering','not_addressed','P2',
 'Saved frame identity and temporal selection are explicit; no frontend interpolation invents model states.',
 'No splat software oracle, overlapping-splat ordering ladder, camera-view PSNR or transparency ordering experiment exists in this study.',
 'Implement with the splat ladder after the coordinate/SH/color contracts are fixed; retain known-answer images and renderer identity per pose.',
 refs('docs/EXCHANGE-CONTRACT.md','evidence/release.json'),['RenderPose','CompositingOrder','KnownAnswerImage','ImageMetric'])
bridge('B09','Scientific semantic checks','partially_closes','P0',
 '63 application-level witnesses separately check ABC field identities/integration, covariance/eigenbasis/quadratic forms and membrane boundaries/energy/spectrum. Generic XSD and implemented semantic checks are recorded separately.',
 'The historical 12-id sci-semantic patch was not recovered or adopted, and new local model tests are not generic units/legend/pLDDT validator rules.',
 'Map recurring scientific failures to a namespaced finding catalog with machine-readable variable, units, model assumption, evidence and remediation; keep advisory generic lints distinct from mathematical acceptance gates.',
 refs('CONTRACT.md','stemloom/core.py','evidence/verification.json','evidence/x3d-validation.json'),['ScientificClaim','Assumption','Witness','ComparisonRule','Finding','Remediation'])
bridge('B10','Scientific fixture factory','partially_closes','P0',
 'Nine reproducible Python-authored research cases generate 78 static frames, raw datasets and metadata-bearing exports; all candidates must pass before publication. VTP carries named scientific arrays, units and explicit validity masks; VTI checks actual lattice ordering.',
 'The factory is not Blender-first and does not cover molecular pLDDT/PAE, volumes, splats or arbitrary Blender attributes. X3D raw-array reconstruction is explicitly outside its subset.',
 'Adopt one canonical fixture schema with analytic/raw arrays distinct from geometry and appearance. Expand by data topology only after preserving current measured contracts.',
 refs('tools/build.py','web/bank/index.json','docs/EXCHANGE-CONTRACT.md','evidence/verification.json'),['ScientificCase','Dataset','DataTopology','Variable','UnitLabel','ValidityMask','VisualEncoding'])
bridge('B11','Corpus tiers and loss ledger','partially_closes','P1',
 'Current case inventory and per-route expected/observed losses are durable. External route status=pass means executed; retention_status=lossy records omission separately.',
 'No PolyXandria spine A–D reclassification, 585-scene rerun or generalized per-object loss ledger was executed here.',
 'Generalize the case/route evidence into per-feature ledger rows; do not count an object as retained merely because the exporter completed.',
 refs('docs/EXCHANGE-CONTRACT.md','evidence/blender-stock-extension.json','evidence/blender-ecosystem-fork.json','web/bank/index.json'),['CorpusTier','FeatureRequirement','ExpectedLoss','ObservedLoss','ExecutionStatus','RetentionStatus'])
bridge('B12','Figure provenance chain','partially_closes','P0',
 'Packets, producers, selected frames, adapters, tools, native scientific blends, GLBs and PNGs have cross-bound hashes. Current release runner checks actual retained artifacts and frame/tool binding; server imports prevent stale source/packet labeling.',
 'These unsigned local receipts do not implement the historical x3dprov chain, renderer-stamped chain heads, authentication, signatures or Library lineage ingestion.',
 'Adopt existing exact-byte identities as entities and existing transformations as activities, then define canonical payload/chain hash rules before integrating x3dprov. Preserve source claim vs edited geometry history.',
 refs('tools/check.py','evidence/release.json','serve.py','evidence/blender-render-flow.json','evidence/blender-glb-flow.json'),['Artifact','ContentDigest','TransformActivity','GeneratedFrom','HistoricalClaim','AuthenticationBoundary'])
bridge('B13','Blender 5.3 native readiness','not_addressed','P1',
 'Actual executed runtime is Blender5.2.4 LTS with recorded official archive identity.',
 'No Blender5.3/native GaussianSplats execution or current capability refresh is supplied by Research Loom. Old daily-build/PyPI statements from October must not be carried forward as current facts.',
 'Treat 5.2.4 as a proven baseline; establish a separate 5.3 feature probe and CI dimension from newly verified primary sources and an actual runtime.',
 refs('evidence/blender-runtime.json','docs/BLENDER-HUB.md'),['RuntimeBuild','CapabilityProbe','CompatibilityMatrix','ObservedAt'])
bridge('B14','Flywheel orchestration graph','not_addressed','P1',
 'tools/check.py provides a deterministic release sequence and source-drift checks; it is a useful node boundary.',
 'No LangGraph checkpointed graph, writer/repair loop, human-gate node or automated rule promotion is present in Research Loom.',
 'Begin with a dependency-light state machine wrapping current tools and typed outcomes; add orchestration framework bindings only after resume/idempotency/identity semantics are exercised.',
 refs('tools/check.py','tools/build.py','evidence/release.json'),['Run','Activity','Attempt','Checkpoint','Transition','RetryPolicy'])
bridge('B15','Three-way/data-fidelity attacker metric','partially_closes','P1',
 'Separate scientific, structural, geometry-transfer and offline-render evidence exists, with known-bad controls; actual VTK readers and Blender save/reopen provide independent representation checks.',
 'There is no native X_ITE visibility arm, DSPy metric, red-team search, calibrated judge panel or agent-generated held-out set in this study.',
 'Expose an evidence vector rather than a multiplied binary score. Preserve not_run/unsupported/refused separately; promote minimal failures to fixtures before any learned judge optimization.',
 refs('evidence/verification.json','evidence/release.json','docs/FOLDBACK.md','tools/check.py'),['EvidenceVector','OracleObservation','Coverage','Abstention','FailureClass','HeldOutFixture'])
bridge('B16','SPZ compact sidecar','not_addressed','P2',
 'A lossless compressed source-packet envelope exists inside Blender Text.',
 'This is neither SPZ decode/encode nor a scientific compressed-geometry sidecar, and conveys no SPZ/SOG compatibility.',
 'Keep container/source compression and splat field compression separate in the taxonomy; recover the historical decoder and define axis/SH/quantization tests before integrating.',
 refs('stemloom/blender_io.py','docs/BLENDER-HUB.md'),['ContainerEncoding','FieldQuantization','CodecVersion','CoordinateConvention','DecoderObservation'])
bridge('B17','Licence passport','partially_closes','P1',
 'Vendored X_ITE and validator source include license and origin manifests, with hashes checked by the release tooling. Case sources are preserved as source references.',
 'Source citations and vendor licenses are not a per-input/per-derived-artifact licence passport or redistribution decision; no spine classifier was audited here.',
 'Add explicit license assertions with source artifact, actor, assertion date, scope and unknown status; keep legal constraints out of the scientific validity predicate.',
 refs('tools/check.py','tools/validate_x3d.py','web/bank/index.json'),['LicenseAssertion','SourceArtifact','Derivation','PermissionScope','UnknownLicense'])
bridge('B18','Agent lane A/B benchmark','not_addressed','P2',
 'The three analytic families and measured counterexamples can supply a small deterministic benchmark seed.',
 'No 115-prompt benchmark, Blender agent arm, x3d_mcp writer arm, API spend, randomization or judge calibration was run by Research Loom.',
 'Design matched prompts and equal tool budgets only after guard, data-fidelity oracles and held-out fixtures are stable; use cached/manual baselines before paid runs.',
 refs('docs/FOLDBACK.md','web/bank/index.json','evidence/release.json'),['BenchmarkTask','WriterLane','Budget','Randomization','OutcomeVector','CalibrationSet'])

summary={'cases':len(bank['cases']),'saved_frames':sum(c['frames'] for c in bank['cases']),
 'declared_scientific_witnesses':sum(len(p['witnesses']) for p in packets.values()),
 'release_status':release['status'],'source_drift':release['source_drift'],
 'recorded_python_test_counts':[c['tests_run'] for c in release['commands'] if 'tests_run' in c],
 'recorded_blender_gate_count':len(release['blender']),'native_xite_browser_status':release['browser']['status'],
 'validator':{'commit':read('evidence/x3d-validation.json')['instrument']['commit'],'xsd':'4.0','semantic_vocabulary':'4.1'},
 'owned_adapter_coordinate_map':'(x,y,z) -> (x,-z,y); determinant +1',
 'fresh_audit_scope':'Read source and existing executed receipts; recomputed only artifact/source SHA identities. Did not rerun Blender, scientific models, native browser, or original private kits.'}
report={'schema':'scivis.current-evidence-map/1','visibility':'private','as_of':'2026-11-17',
 'source_root':str(REPO),'historical_source':'upload/FLYWHEEL-SYNERGY-v1 (2).md',
 'status_semantics':{'implemented':'Original bridge acceptance contract is fully exercised; no bridge is assigned this status merely by analogy.',
 'partially_closes':'Current source/receipts implement a directly reusable subset; remaining original acceptance gaps are explicit.',
 'not_addressed':'Original bridge-specific behavior is absent; adjacent reusable infrastructure may exist.'},
 'summary':summary,'fresh_artifact_identity_audit':{'status':'pass','checks':checks},'evidence':evidence,'bridges':rows,
 'candidate_bridge_updates':[
 {'id':'B26','status':'partially_closes','current':'Three science-only GLBs actually export/reimport in Blender5.2.4; actual expanded geometry and identity extras are measured. Serialized FLOAT colors are exact in selected fixtures; reimport BYTE_COLOR is quantized within recorded bound.',
  'gap':'No USD arm, external second glTF runtime, Khronos Neutral cross-renderer comparison or material-transmission/IOR/volume suite.', 'evidence_refs':refs('tools/export_glb.py','evidence/blender-glb-flow.json','evidence/blender-glb-tensor.json','evidence/blender-glb-modes.json')},
 {'id':'B27','status':'partially_closes','current':'The owned subset preserves points/lines/colors and actual geometry readback. The ordinary PointSet omission in the modern fork is now directly recorded for its mixed fixture.',
  'gap':'No broad PointCloud exporter repair, PointSet ColorRGBA alpha chart, pixel point-size calibration or native X_ITE/Cycles equivalence.', 'evidence_refs':refs('stemloom/exchange.py','evidence/blender-ecosystem-fork.json','tests/test_exchange.py')}
 ]}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'current-evidence-map.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
lines=['# Current Research Loom evidence mapped to the historical flywheel','',
 'Private working analysis. Inspected on 17 November 2026. This review reads current source and executed receipts and rechecks byte identities. It does not rerun Blender, science, browser rendering or the private historical kits.','',
 '## The material advance','',
 'Research Loom now supplies a durable fixture and evidence spine: **9 cases, 78 saved frames and 63 declared scientific witnesses**, three owned Blender save/reopen transfers, three actual CPU renders, and three science-geometry GLB exports/reimports. The release receipt records **59 study tests and 14 shared tests, each normally and under `-O`**. Its nine Blender gates bind current packet/frame/tool identities and actual retained files.','',
 'The fresh identity audit in the JSON companion rehashed all nine packet bytes, bank producers, release source identities, three PNGs, three GLBs and three scientific `.blend` sources. Every inspected identity matched. These checks are repeatable identity observations, not authentication and not a fresh scientific or renderer execution.','',
 'No original bridge is automatically complete because the new work resembles it. The original corpus, splat and agent acceptance scopes remain separate.','',
 '| Bridge | Current relation | Priority | Directly reusable contribution | Remaining boundary |','|---|---|---|---|---|']
for r in rows:lines.append('| '+r['id']+' | '+r['original_scope_status'].replace('_',' ')+' | '+r['priority']+' | '+r['current_implemented_elements']+' | '+r['remaining_acceptance_gap']+' |')
lines += ['', '## Corrections that matter for integration','',
 '1. **Execution and retention are different outcomes.** The official stock extension2.5.2 executed on Blender5.2.4 but wrote X3D3.0 and omitted fixture lines, points, vertex colors and metadata. The modern fork at `044bea3ae33a991f816de15a307826b6d7f576ec` wrote4.0 and retained the mesh, line, colors, PBR material and metadata, while omitting its ordinary PointSet. These are bounded fixture findings; neither supports a blanket conformance verdict.',
 '2. **The owned adapter does not repair the fork.** It preserves this case schema’s editable meshes and glyph-expanded lines/points through a proper rotation. Its measured coordinate maxima are approximately1.48e-7,1.20e-7 and9.54e-8. Actual vertex-mutation controls were caught. Arbitrary modifiers, topology edits, material graphs and animations are outside its contract.',
 '3. **Scientific arrays and display geometry have different carriers.** Raw packet data and VTP/VTI retain numerical variables and units. The bounded X3D subset carries geometry and provenance; it does not recover raw `point_data`. VTP missing arrays have explicit validity masks. Membrane geometry is magnified while displacement arrays remain unexaggerated.',
 '4. **Hashes are identities.** The new packet/frame/producer/source binding is a sound base for B12, but it is neither the original x3dprov chain nor publisher authentication. Historical solver claims remain historical after geometry edits.',
 '5. **Color must be measured at the right stage.** Explicit sRGB/linear conversion and exact GLB FLOAT serialization coexist with approximately0.00360–0.00430 linear color differences after Blender BYTE_COLOR reimport, within a recorded0.004555 bound. Render lighting/view transforms are a separate pixel-level comparison.',
 '6. **Native X_ITE is not a completed oracle arm here.** The current release explicitly records browser `not_run`; existing Node tests cover actual adapter functions and projection geometry. XSD4.0 plus semantic vocabulary4.1 cannot establish visibility, material parity or physical correctness.',
 '7. **Compression has several unrelated meanings.** The chunked zlib/base85 Blender Text envelope solves source retention/performance. It supplies no evidence for SPZ, SOG, splat quantization or render-order-preserving spatial slabs. Keep these as different representation transformations.','',
 '## Recommended next adoption order','',
 '- **P0: evidence contract and loss ledger.** Reuse packet/frame/tool binding; normalize execution/retention/refusal/not-run outcomes and per-field loss observations. Promote the PointSet omission and asymmetric/color controls to owner-ready external-fork fixtures.',
 '- **P0: typed semantic layer.** Keep generic structural findings, scientific model witnesses and visual encodings separate. Treat units labels, coordinate transforms, data topology, display magnification and historical claims as explicit graph entities.',
 '- **P1: recover and rerun original kits.** Reconcile validator pins and raw result identities before using old corpus/splat/PSNR numbers. Rebuild the smallest splat ladder and Blender5.3 native probe against current runtime evidence.',
 '- **P1: renderer and graph integration.** Add native-browser visibility/color checks and a resumable thin-wrapper state machine after deterministic acceptance boundaries are fixed. Maintain outcome vectors rather than collapsing missing arms into scalar pass scores.',
 '- **P2: costlier breadth.** Scale corpus, splat partition/order tests, SPZ, USD, and matched agent A/B only when earlier gates and rights assertions are usable.','',
 '## Proposed ontology hooks','',
 'Use the terms in each JSON bridge row as candidate local concepts, not assertions that a public ontology already defines them. The useful joins are `ScientificCase → Dataset → Variable → VisualEncoding → Representation`, `TransformActivity → AdapterVersion → Artifact`, and `Witness/RetentionObservation → Instrument → RuntimeBuild`. A `ScientificClaim` must identify its assumption and measurement scope; a `HistoricalClaim` must remain distinguishable after an edit. A `ContentDigest` identifies an artifact while a `LicenseAssertion` and an authentication assertion make different claims.','',
 '## Evidence index','', '| Ref | Path | SHA-256 |', '|---|---|---|']
for k,v in evidence.items():lines.append(f"| {k} | `{v['path']}` | `{v['sha256']}` |")
(OUT/'current-evidence-map.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'status':'pass','bridges':len(rows),'evidence_files':len(evidence),'identity_checks':len(checks),'original_scopes_fully_closed':0}))
