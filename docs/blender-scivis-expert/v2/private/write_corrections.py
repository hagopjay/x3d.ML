from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]
retrieved='2026-11-17'
sources={
 'S01':{'title':'Blender5.3release','url':'https://www.blender.org/releases/5-3/','access':'primary search result'},
 'S02':{'title':'Blender5.2LTSrelease','url':'https://www.blender.org/releases/5-2/','access':'primary search result; direct open403'},
 'S03':{'title':'Blender5.3rendering release notes','url':'https://developer.blender.org/docs/release_notes/5.3/rendering/','access':'primary search excerpt; direct open402'},
 'S04':{'title':'Official Web3D extension','url':'https://extensions.blender.org/add-ons/web3d-x3d-vrml2-format/','access':'primary search result'},
 'S05':{'title':'Reference3DGS PLY writer','url':'https://github.com/graphdeco-inria/gaussian-splatting/blob/main/scene/gaussian_model.py','access':'primary source code in search result'},
 'S06':{'title':'Python floating-point tutorial','url':'https://docs.python.org/3.13/tutorial/floatingpoint.html','access':'primary search result'},
 'S07':{'title':'NumPyfloat32scalar definition','url':'https://numpy.org/doc/stable/reference/arrays.scalars.html','access':'primary search result'},
 'S08':{'title':'Blender color management','url':'https://docs.blender.org/manual/en/4.5/render/color_management.html','access':'primary search excerpt; direct open402'},
 'S09':{'title':'X_ITE browser color controls','url':'https://create3000.github.io/x_ite/','access':'primary search excerpt'},
 'S10':{'title':'X3Dv4 programmable shaders','url':'https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/shaders.html','access':'primary search result'},
 'S11':{'title':'Web3D CML molecular visualization examples','url':'https://www.web3d.org/x3d/content/examples/Basic/ChemistryMarkupLanguage/','access':'primary search result'},
 'S12':{'title':'KHR_gaussian_splatting specification','url':'https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md','access':'primary page opened; currentmain rather than frozencommit'},
 'S13':{'title':'SPZ format and quantization','url':'https://github.com/nianticlabs/spz/blob/main/README.md','access':'primary search excerpt'},
 'S14':{'title':'AlphaFoldDBconfidence documentation','url':'https://alphafold.ebi.ac.uk/faq','access':'primary search result'},
 'S15':{'title':'OpenUSD26.03schema announcement','url':'https://aousd.org/blog/openusd-v26-03/','access':'primary projectalliance announcement'},
 'S16':{'title':'X3D Geospatial highprecision design','url':'https://www.web3d.org/specifications/X3Dv4Draft/ISO-IEC19775-1v4-IS.proof/Part01/components/geospatial.html','access':'primary specification proof search excerpt; finaleditioncheckrecommended'},
}
for source in sources.values():source['retrieved_utc_date']=retrieved

rows=[]
def add(key,topic,original,decision,replacement,mode,refs=(),action='',hooks=(),local=()):
 rows.append({'id':key,'topic':topic,'historical_claim':original,'assessment':decision,
              'replacement':replacement,'evidence_mode':mode,'sources':list(refs),
              'local_evidence':list(local),'next_action':action,'ontology_hooks':list(hooks)})

add('K01','runtime freshness','Blender5.3 is alpha; release due10Nov; daily hand-download needed.',
    'stale','Blender5.3.0 was released10November2026. Blender5.2.4 is the current5.2LTS patch on that date. Keep5.2LTS and5.3native-splat lanes separately pinned.',
    'primary_documentation_checked',('S01','S02'),
    'Replace the historical future-release task with a stable5.3CI/probe task. Do not infer PyPIwheel availability from executable release.',('SoftwareBuild','hasVersion','retrievedAt'))
add('K02','native splat attribute order','radiance:base is opacity plus basecolour.',
    'incorrect order','Blender documents radiance:base as base/DCradiance in xyz followed by opacity in w. SHattributes require an explicit coefficient ordering.',
    'primary_documentation_checked',('S03',),
    'Use asymmetric known-answer splats; separately test activation and SHbasis against actual imported attributes.',('AttributeSemantic','componentOrder','activation'))
add('K03','native support versus interchange','Blender5.3 native import/render means complete splat IO.',
    'overbroad if inferred','Official5.3notes document native PLY/SPZimport and rendering, with no nativeexport. They retain color-space and ApplyTransform caveats.',
    'primary_documentation_checked',('S03',),
    'Measure nativeattributes and forkexport as different routes; a native pointcloud or plausible still is not a roundtrip.',('ImportRoute','ExportRoute','KnownLimitation'))
add('K04','splat byte arithmetic','SH3 has59numbers and248bytes inPLY.',
    'incomplete accounting','SH3 uses59model scalars, or236bytes atfloat32. The common referencePLY adds3normal scalars, yielding62float32properties and248bytes pervertex, beforeheader.',
    'derived_from_primary_code',('S05',),
    'Name propertylist, scalarwidth, endianness andheader separately; preserve the68/104/164/248table only for this declaredlayout.',('StorageLayout','propertyCount','payloadBytes'))
add('K05','precision','32-bit versus64-bit means6vs15ordersofmagnitude.',
    'wrong quantity','The distinction concerns significant precision, not exponentrange. Reopened Blender5.2.4mesh coordinates matchedfloat32quantization in two metriccoordinatecontrols. Localorigin storage substantially reduced measured errors.',
    'executed_bounded_control',('S06','S07'),
    'Retain64-bit sourcecoordinates and reversibleorigin/units metadata; budget absoluteerror at the actualcoordinate magnitude.',('CoordinateFrame','origin','unit','maxAbsoluteError'),('probes/precision-control.json',))
add('K06','scientific color','Standard is universally value-correct and X_ITE is unmanagedsRGB-ish.',
    'overbroad','Standard avoids an additional creativeviewtransform, but displayconversion, materiallighting, exposure andalpha still affectpixels. X_ITE exposes colorSpace, displayColorSpace andtoneMapping controls.',
    'primary_documentation_checked',('S08','S09'),
    'Pin both colorpipelines; use unlitknown-color charts for quantitativecomparison and keep beautyrenders as a separateview.',('ColorEncoding','DisplayTransform','Exposure','LightingCondition'))
add('K07','data textures','Non-Color should be used for all scientific images.',
    'needs semantic distinction','Tag numeric data maps as Non-Color. An alreadyencodeddisplaycolormap is color data and requires its declaredencoding rather than automaticNon-Color tagging.',
    'primary_documentation_and_inference',('S08',),
    'Record scalar units andtransferfunction separately from RGBencodings; mark the second sentence as pipelineinterpretation.',('ScalarField','TransferFunction','ColorEncoding'))
add('K08','X3D attribute carrier','X3D has no equivalent to perpointattributes beyond Color/Metadata.',
    'too absolute','X3D has namedFloatVertexAttribute andmatrixvertexattributes for shaders, plus typedMetadata. Those carriers do not automatically provide scientificmeaning or aGeometryNodesgraph equivalent.',
    'primary_specification_checked',('S10',),
    'Define attributes withname, association, components, units, nullmask anddisplaymapping; check supported runtimeprofile.',('AttributeSemantic','DataAssociation','Unit','Missingness'))
add('K09','molecular semantics','X3D has no conceptof atoms,bonds orinteractions.',
    'requires core/application distinction','The core is not a molecularanalysisontology, but Web3D alreadyprovides CML-to-X3D molecularprototype examples. Preserve domainidentities via PROTO/Metadata and a molecularsidecar.',
    'primary_project_examples_checked',('S11',),
    'Reuse the establishedchemicalmapping direction before inventing newAtom/Bondcore nodes; retain sourcePDB/mmCIF/CML identifiers.',('MolecularEntity','Residue','Bond','wasDerivedFrom'))
add('K10','analysis ownership','Blender visualizes; it does notanalyze.',
    'useful policy stated as a false absolute','Treat independent scientificarrays/checks as authoritative. BlenderPython andGeometryNodes may computeanalysis; those computations still need units, validation andreproducibleoracles.',
    'architectural_recommendation',(),
    'Separate numericalauthority from presentationauthority by contract instead of by applicationname.',('ScientificComputation','PresentationTransform','AuthorityScope'))
add('K11','splat versus mesh','Splatsview; meshesmeasureandsimulate.',
    'heuristic not a theorem','A radiancefield is not automatically a validatedsurface; a mesh is not automatically a measurement. Analysissuitability depends on acquisition, reconstruction, calibration and uncertainty.',
    'architectural_recommendation',(),
    'Grade a representation against its intended task and retain reconstruction assumptions.',('Representation','MeasurementProcess','UncertaintyModel','FitForPurpose'))
add('K12','current extension routes','The stock extension and modernfork can be described as oneX3Dcapability.',
    'incorrect aggregation','The officialextension advertises3.3. Current local5.2.4fixture receipts test stockcommit a173dfb and forkcommit044bea3 separately; both execute, while their recorded preservationlosses differ.',
    'primary_documentation_and_existing_executed_receipts',('S04',),
    'Use current boundedloss tables; do not inherit one route\'s capabilities or losses into another.',('CapabilityObservation','Route','LossEvent','SoftwareBuild'),
    ('../../x3d.STEM/studies/research-loom/evidence/blender-stock-extension.json','../../x3d.STEM/studies/research-loom/evidence/blender-ecosystem-fork.json'))
add('K13','compression','PLYlossless; SPZ10x; SOG15–20x.',
    'format- andcorpus-dependent','PLYpropertytypes andwriter determineprecision. SPZdocumentsquantization; compressionratios andfidelity must be measured for the exactcodec settingsandcorpus.',
    'primary_documentation_and_inference',('S13',),
    'Reportdecodedposition, scale, angular andSHerrors alongside bytes; do not promote aZSTDcontainer to losslessmodelstorage.',('CodecProfile','Quantization','ErrorBudget','Corpus'))
add('K14','glTF splat standard','KHR_gaussian_splatting ratified3September2026, tradepressonly.',
    'status strengthened; exactdate unverified','The KhronosprimaryREADME currentlymarks thebaseextensionComplete/Ratified. That alone doesnotverify3September or ratifyeach dependentcompressionextension.',
    'primary_specification_checked',('S12',),
    'Pin acommittedspecificationrevision andtest quaternionorder, linear/logscale and opacityactivation on eachroute.',('SpecificationRevision','ExtensionStatus','Activation','QuaternionConvention'))
add('K15','molecular confidence','pLDDT lives in theBfactorcolumn.',
    'needs provenancecondition','AlphaFolddownloads storepLDDT inBfactorfields. Do not reinterpret arbitraryexperimentalPDBBfactors as pLDDT. Localconfidence doesnotestablish correctrelativechainplacement.',
    'primary_documentation_checked',('S14',),
    'Requireproducer/fieldsemanticmetadata; test confidencebandboundaryvalues explicitly.',('ConfidenceScore','Producer','FieldSemantic','Threshold'))
add('K16','render measurement','Saving AOVs turnsa render intoameasurement.',
    'overbroad','AOVs arenumericoutputs ofarenderingprocess. Scientificmeasurement requires definedunits, conventions, calibration andvalidation against the claimedquantity.',
    'architectural_recommendation',(),
    'Recordcamera, depthconvention, colorencoding, sample/seed, masks and displaymapping; keep rawbuffers with thefigure.',('RenderActivity','MeasurementClaim','Calibration','CameraModel'))
add('K17','float tolerance','Allpositions/scales/rotations/opacity/SHshould be within1e-6float32.',
    'universal absolutebound unjustified','Use quantity-specific absoluteandrelativetolerances. Compare quaternionrotations modulo q/-q, covariance underbasischange, andSHafter declaredbasisandrotationmapping.',
    'derived_numeric_recommendation',('S06','S07'),
    'Attachunits andtolerancerationale to each witness; distinguish serializationquantization from displayerror.',('Tolerance','EquivalenceRelation','Unit','ScientificWitness'))
add('K18','OpenUSD freshness','OpenUSD26.03 contains aGaussianSplat schema.',
    'supported atdocumentationlevel','AOUSD\'s26.03announcement identifies theParticleFieldschemafamily includingUsdVolParticleField3DGaussianSplat. Schemaavailability doesnotproveanyparticularBlenderIOpath.',
    'primary_project_documentation_checked',('S15',),
    'Preserve this positiveinteroplink but gateadaptercapability on an executedfixture.',('SchemaType','AdapterCapability','CapabilityObservation'))
add('K19','geospatial standards reuse','Localorigin is a newad-hocworkaroundneeded atallX3Dborders.',
    'existing standardhook','X3D\'sGeospatialdesign alreadyusesGeoCoordinate doubleprecisioncoordinates andlocalorigins. The newBlenderprobe supplies boundedmeasurements for theauthoringhub.',
    'primary_specification_and_executed_control',('S16',),
    'Map originalCRSandlocalframe tostandardswhereapplicable; neverinferCRSfromcoordinate magnitude.',('GeoCoordinate','CoordinateReferenceSystem','LocalOrigin'),('probes/precision-control.json',))
add('K20','evidence grading','Confirmedrequires a namedvalidatorandX_ITEpatch for everykindofclaim.',
    'singlegrade mixesindependent evidenceaxes','Record claimtype, sourcequality, executedscope, artifactidentity, falsificationcontrols andfreshness separately. A releasefactcanbe primarychecked withouta renderer; schema-validity cannotconfirmdomaintruth.',
    'methodology_recommendation',(),
    'Keep thehistoricalgrades unchanged; add structured evidencefacets instead of silentlyupgradingeverything from one newtest.',('Claim','EvidenceActivity','ArtifactIdentity','Freshness','Scope'))
add('K21','outcome/licensing claims','Drugdiscoveryoutcomes, productlicenses, quotas and addonversions arelivefacts.',
    'park for targetedreview','Retain thehistoricalclaims as datedresearchnotes. They are not refreshedby thistechnicalreview andmustnotbe promoted as currentmedical,legal orcommercialguidance.',
    'not_revalidated',(),
    'Create separate source-specificreviewtasks onlywhen thecorresponding molecular/licensedassetworkflow is selected.',('HistoricalClaim','ReviewTask','LicensePassport','ValidityInterval'))

polished={
 'K01':('Blender 5.3 is alpha; release due 10 November; daily hand-download needed.',
        'Blender 5.3.0 was released on 10 November 2026. Blender 5.2.4 is the current 5.2 LTS patch on that date. Keep the 5.2 LTS and 5.3 native-splat lanes separately pinned.',
        'Replace the historical future-release task with a stable 5.3 CI/probe task. Do not infer PyPI wheel availability from the executable release.'),
 'K02':('radiance:base is opacity followed by base color.',
        'Blender stores raw SH degree-zero coefficients in radiance:base.xyz, followed by activated opacity in w. The new four-splat native 5.3 test reproduces this mapping and all 15 higher-degree RGB coefficient slots.',
        'Keep asymmetric known-answer splats. Treat SH basis, channel order, opacity activation and scale activation as separate declared mappings.'),
 'K03':('Blender 5.3 native import/render implies complete splat interchange.',
        'Native import and rendering are available in Blender 5.3; the official notes state that native export is absent. The new structural test reproduces native PLY import, a fork X3D 4.1 round trip and a loss of covariance under Apply Transform.',
        'Keep native import, fork export, rendering and transform preservation as separate capabilities. This four-splat structural test does not complete the B01 renderer or scale ladder.'),
 'K04':('SH degree 3 has 59 numbers and occupies 248 bytes in PLY.',
        'SH degree 3 uses 59 model scalars, or 236 bytes at float32. The common reference PLY adds three normal scalars, yielding 62 float32 properties and 248 bytes per vertex, before the header.',
        'Name the property list, scalar width, endianness and header separately. Preserve the 68/104/164/248-byte table only for this declared layout.'),
 'K05':('32-bit versus 64-bit means six versus fifteen orders of magnitude.',
        'This distinction concerns significant precision, not exponent range. Reopened Blender 5.2.4 mesh coordinates matched float32 quantization in two metric coordinate controls. Local-origin storage substantially reduced the measured errors.',
        'Retain 64-bit source coordinates and reversible origin/units metadata. Budget absolute error at the actual coordinate magnitude.'),
 'K06':('Standard is universally value-correct and X_ITE is unmanaged sRGB-ish.',
        'Standard avoids an additional creative view transform, but display conversion, material lighting, exposure and alpha still affect pixels. X_ITE exposes colorSpace, displayColorSpace and toneMapping controls.',
        'Pin both color pipelines. Use unlit known-color charts for quantitative comparison and retain beauty renders as a separate view.'),
 'K07':('Non-Color should be used for every scientific image.',
        'Tag numeric data maps as Non-Color. An already encoded display colormap is color data and needs its declared encoding rather than automatic Non-Color tagging.',
        'Record scalar units and the transfer function separately from RGB encodings. The second sentence is an interpretation of the documented color pipeline.'),
 'K08':('X3D has no carrier for per-point attributes beyond Color and Metadata.',
        'X3D has named FloatVertexAttribute and matrix vertex attributes for shaders, plus typed Metadata. These carriers do not automatically provide scientific meaning or an equivalent of a Geometry Nodes graph.',
        'Define attributes with a name, data association, component count, units, missing-value mask and display mapping. Check the supported runtime profile.'),
 'K09':('X3D has no concept of atoms, bonds or interactions.',
        'The core is not a molecular analysis ontology, but Web3D already supplies CML-to-X3D molecular prototype examples. Preserve domain identities through PROTO/Metadata and a molecular sidecar.',
        'Reuse the established chemical mapping direction before proposing new Atom/Bond core nodes. Retain source PDB, mmCIF or CML identifiers.'),
 'K10':('Blender visualizes; it does not analyze.',
        'Treat independently checked scientific arrays as authoritative. Blender Python and Geometry Nodes can perform analysis; those computations still need units, validation and reproducible reference checks.',
        'Separate numerical authority from presentation authority by contract rather than by application name.'),
 'K11':('Splats are for viewing; meshes are for measuring and simulation.',
        'A radiance field is not automatically a validated surface, and a mesh is not automatically a measurement. Analytical suitability depends on acquisition, reconstruction, calibration and uncertainty.',
        'Grade each representation against its intended task and retain its reconstruction assumptions.'),
 'K12':('The stock extension and modern fork can be aggregated as one X3D capability.',
        'The official extension advertises X3D 3.3. Current local Blender 5.2.4 fixtures test stock commit a173dfb and fork commit 044bea3 separately. Both execute, while their recorded preservation losses differ.',
        'Use the current bounded loss tables. Do not transfer one route\'s capabilities or losses to another route.'),
 'K13':('PLY is lossless; SPZ is 10× smaller; SOG is 15–20× smaller.',
        'PLY property types and the writer determine precision. SPZ documents quantization. Compression ratios and fidelity must be measured for the exact codec settings and corpus.',
        'Report decoded position, scale, angular and SH errors alongside bytes. A ZSTD container does not imply lossless model storage.'),
 'K14':('KHR_gaussian_splatting was ratified on 3 September 2026, based only on trade press.',
        'The current Khronos primary README marks the base extension Complete/Ratified. This does not verify the 3 September date or ratify every dependent compression extension.',
        'Pin a committed specification revision. Test quaternion order, linear/log scale and opacity activation on each route.'),
 'K15':('pLDDT lives in the B-factor column.',
        'AlphaFold downloads store pLDDT in B-factor fields. Do not reinterpret arbitrary experimental PDB B-factors as pLDDT. Local confidence does not establish correct relative chain placement.',
        'Require producer and field-semantic metadata. Test the confidence-band boundary values explicitly.'),
 'K16':('Saving AOVs turns a render into a measurement.',
        'AOVs are numeric outputs of a rendering process. Scientific measurement requires defined units, conventions, calibration and validation against the claimed quantity.',
        'Record the camera, depth convention, color encoding, sample count/seed, masks and display mapping. Keep raw buffers with the figure.'),
 'K17':('Every position, scale, rotation, opacity and SH value should round-trip within an absolute 1e-6 float32 tolerance.',
        'Use quantity-specific absolute and relative tolerances. Compare quaternion rotations modulo q/−q, covariance under basis changes, and SH after the declared basis and rotation mapping.',
        'Attach units and a tolerance rationale to each witness. Distinguish serialization quantization from display error.'),
 'K18':('OpenUSD 26.03 contains a Gaussian splat schema.',
        'AOUSD\'s 26.03 announcement identifies the ParticleField schema family, including UsdVolParticleField3DGaussianSplat. Schema availability does not prove any particular Blender import/export path.',
        'Preserve this positive interoperability link, but require an executed fixture before claiming adapter capability.'),
 'K19':('Local-origin handling is a new ad hoc workaround required at every X3D border.',
        'X3D\'s Geospatial design already uses GeoCoordinate double-precision coordinates and local origins. The new Blender probe supplies bounded storage measurements for the authoring hub.',
        'Map the original CRS and local frame to established standards where applicable. Never infer a CRS from coordinate magnitude.'),
 'K20':('Every kind of Confirmed claim requires both a named validator and an X_ITE patch.',
        'Record claim type, source quality, executed scope, artifact identity, falsification controls and freshness separately. A release fact can be primary-checked without a renderer; schema validity cannot confirm domain truth.',
        'Keep the historical grades unchanged. Add structured evidence facets rather than silently upgrading every claim after one new test.'),
 'K21':('Drug-discovery outcomes, product licenses, quotas and add-on versions are live facts.',
        'Retain these historical claims as dated research notes. They are not refreshed by this technical review and must not be promoted as current medical, legal or commercial guidance.',
        'Create separate source-specific review tasks when the corresponding molecular or licensed-asset workflow is selected.'),
}
assessment_polish={
 'K02':'incorrect component order', 'K04':'incomplete storage accounting',
 'K09':'requires a core/application distinction', 'K12':'incorrect aggregation of separate routes',
 'K13':'depends on the storage profile and corpus',
 'K14':'status strengthened; exact historical date unverified',
 'K15':'requires a provenance condition',
 'K17':'universal absolute bound unjustified',
 'K18':'supported at the documentation level',
 'K19':'existing standard hook', 'K20':'one grade mixes independent evidence axes',
 'K21':'park for targeted review'}
source_titles={
 'S01':'Blender 5.3 release', 'S02':'Blender 5.2 LTS release',
 'S03':'Blender 5.3 rendering release notes', 'S04':'Official Web3D extension',
 'S05':'Reference 3DGS PLY writer', 'S06':'Python floating-point tutorial',
 'S07':'NumPy float32 scalar definition', 'S08':'Blender color management',
 'S09':'X_ITE browser color controls', 'S10':'X3D v4 programmable shaders',
 'S11':'Web3D CML molecular visualization examples', 'S12':'KHR_gaussian_splatting specification',
 'S13':'SPZ format and quantization', 'S14':'AlphaFold DB confidence documentation',
 'S15':'OpenUSD 26.03 schema announcement', 'S16':'X3D Geospatial high-precision design'}
for key,title in source_titles.items():sources[key]['title']=title
sources['S15']['access']='primary project-alliance announcement'
sources['S16']['access']='primary specification proof search excerpt; checking the final edition is recommended'
for row in rows:
 row['historical_claim'],row['replacement'],row['next_action']=polished[row['id']]
 if row['id'] in assessment_polish:row['assessment']=assessment_polish[row['id']]
 if row['id'] in ('K02','K03'):
  row['evidence_mode']='primary_documentation_and_executed_native53_control'
  row['local_evidence'].append('native53/results/native53-result.json')

inputs={}
for name in ('KNOWLEDGE-BASE-v1 (2).md','KNOWLEDGE-BASE-v1.1-addendum (2).md'):
 p=WORK/'upload'/name
 inputs[name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
packing=[]
for degree in range(4):
 meaningful=11+3*(degree+1)**2
 packing.append({'sh_degree':degree,'meaningful_scalar_count':meaningful,'meaningful_float32_bytes':4*meaningful,
                 'reference_ply_normal_scalars':3,'reference_ply_float32_payload_bytes_per_vertex':4*(meaningful+3)})
payload={'schema':'scivis.knowledge-corrections/1','created_utc':datetime.now(timezone.utc).isoformat(),
         'visibility':'private','source_documents_unchanged':True,'input_identity':inputs,
         'sources':sources,'corrections':rows,'derived_reference_ply_layout':packing,
         'scope':'Review of the supplied KB notes, primary documentation, existing Research Loom receipts, a new Blender 5.2.4 precision probe and a four-splat native Blender 5.3 structural/data probe.'}
(ROOT/'knowledge-corrections.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
lines=['# Knowledge base v1.2: corrections and evidence facets','',
       'Private additive review · 17 November 2026. The supplied v1 and v1.1 files remain unchanged.',
       '', 'The strongest change is to make every assertion name its subject and scope. A current product release, a supported format, an executed import and a scientifically faithful round trip are different claims. Preserve the historical grading while recording these additional facets.',
       '', '| ID | Topic | Assessment |', '|---|---|---|']
for r in rows:lines.append('| '+r['id']+' | '+r['topic']+' | '+r['assessment']+' |')
for r in rows:
 lines+=['', '## '+r['id']+' · '+r['topic'],'',r['replacement'],'',
          '**Evidence:** `'+r['evidence_mode']+'`. '+', '.join('['+s+']('+sources[s]['url']+')' for s in r['sources']),
          '', '**Next action:** '+r['next_action'],'',
          '**Ontology hooks:** '+', '.join('`'+v+'`' for v in r['ontology_hooks'])+'.']
 if r['local_evidence']:lines+=['','Local evidence: '+', '.join('`'+v+'`' for v in r['local_evidence'])+'.']
lines+=['','## Reproduced precision control','',
        'Blender 5.2.4 LTS, build `cd5dc428cce1`, saved and reopened real mesh data. Readback matched an independent binary32 packing reference. Source coordinates and a decimal origin remained in the saved source text. Deliberate actual-vertex changes were detected with the source metadata left unchanged.',
        '', '| Synthetic metric frame | Direct global maximum error | Restored local-origin maximum error |',
        '|---|---:|---:|']
precision=json.loads((ROOT/'probes/precision-control.json').read_text())
for r in precision['cases']:
 lines.append(f"| {r['case_id']} | {r['direct_world_max_abs_error_m']:.9g} m | {r['restored_world_max_abs_error_m']:.9g} m |")
lines+=['','Restoration happens in Python binary64 outside Blender world transforms. Translating an object back to a large float32 world position can reintroduce the loss. This is a bounded storage result, not a GPU, X3D or general geospatial-accuracy certification.',
        '', '## Reference PLY size arithmetic','',
        'The formula below is independently derived from the reference writer\'s declared property list. Header bytes are extra. PLY writers with different types or omitted normals have different sizes.',
        '', '| Maximum SH degree | Model scalars | Model float32 bytes | Reference PLY bytes including normals |',
        '|---:|---:|---:|---:|']
for p in packing:lines.append(f"| {p['sh_degree']} | {p['meaningful_scalar_count']} | {p['meaningful_float32_bytes']} | {p['reference_ply_float32_payload_bytes_per_vertex']} |")
lines+=['','## Retrieval boundaries','',
        'All online sources were checked on 17 November 2026. Some official pages refused a direct fetch while their primary-domain search excerpts remained available; the JSON source register records that distinction. Current `main` documents are observations, not reproducible commit pins. Exact historical release dates and all addon/version claims not expressly corrected above remain unverified. No new medical-outcome or license guidance is inferred.',
        '', 'The official stock extension, the ecosystem fork, the owned scientific adapter and Blender\'s native splat importer are separate routes. Preserve their independent source pins and fixtures; combining their feature lists into one virtual application would overstate what any one executable path can do.']
lines+=['','## Executed native Blender 5.3 update','',
        'The [seven-answer native report](native53/NATIVE53-RESULTS.md) records the new four-splat SH3 test, independent X3D scalar checks, fork save/import behavior and the Apply Transform covariance failure. Its receipts and reproducible probe are in `native53/results/`. This is structural and attribute evidence; it does not complete the B01 renderer or scale ladder.']
(ROOT/'KB-v1.2-CORRECTIONS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'status':'pass','corrections':len(rows),'source_urls':len(sources),'input_documents':len(inputs)}))
