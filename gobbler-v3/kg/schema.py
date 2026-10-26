"""Gobbler v3 knowledge-graph schema (ontology v1). Closed lists: the extractor must use them."""
CLASSES = {
 'Standard':   'a specification or format (X3D 4.0, X3D 4.1, glTF, USD, VRML97, SVG, ISO/IEC 19775)',
 'Component':  'an X3D component (Shape, HAnim, Geospatial, ParticleSystems, GaussianSplats...)',
 'NodeType':   'a single X3D node or element type (Material, Transform, GaussianSplats...)',
 'Tool':       'software that reads, writes, renders, converts, validates or generates 3D/X3D (X_ITE, X3DOM, Blender, Castle Game Engine, three.js, DSPy, LangGraph, MCP server...)',
 'Validator':  'a specific validator or checker build and the check it runs (fork d5598c4, upstream 74da0ec, use-type check)',
 'Repo':       'a source repository',
 'Org':        'an organisation, consortium, university or company',
 'Person':     'a named person (use only names that appear in the text or are public roles of the community)',
 'Event':      'a conference, release, milestone or dated happening',
 'Workstream': 'a project thread / line of work inside PolyXandria (Shroud, Giza, University scale, Traceability...)',
 'Document':   'a report, doc, spec, page, handoff, paper',
 'Dataset':    'a corpus or table (x3d_spine, the archive, bench sets)',
 'Scene':      'a concrete X3D scene, twin or exhibit (Shroud, Giza, Burruss Hall, Gobbler)',
 'Experiment': 'an A/B comparison, benchmark run or evaluation',
 'Finding':    'a result, defect class, surprise or emergent feature that was measured or observed',
 'Rule':       'a prompt rule, repair hint, validator check, heuristic or policy that was derived from findings',
 'Metric':     'a measured quantity with a value (first-try valid rate, recall, SSIM, dB...)',
 'Loop':       'a closed feedback loop (flywheel / virtuous circle): ordered steps that return to the start',
 'Decision':   'a choice made or pending (owner decisions, trade-offs)',
}
PREDICATES = {
 # structure
 'part_of': 'X is a part of Y', 'contains': 'X contains Y', 'version_of': 'X is a version of Y', 'supersedes': 'X replaces Y',
 'forked_from': 'X is a fork of Y', 'depends_on': 'X needs Y to work',
 # technical
 'implements': 'tool/validator implements a standard/component/node', 'reads': 'tool reads format/standard', 'writes': 'tool writes format/standard',
 'converts_to': 'tool or standard converts X to Y', 'validates': 'validator checks standard/scene/rule target', 'renders': 'tool renders scene/standard',
 'uses': 'X uses Y', 'co_used_with': 'node types appearing together in scenes (weighted)',
 # social
 'authored_by': 'X was made by Y', 'maintained_by': 'X is maintained by Y', 'member_of': 'person/org belongs to org', 'works_with': 'person/org collaborates with person/org',
 'hosts': 'org/event hosts X', 'presented_at': 'X presented or announced at event',
 # knowledge / flywheel
 'cites': 'document cites document/source', 'evidences': 'X is evidence for Y', 'measured_by': 'finding/experiment is measured by metric', 'produces': 'X produces Y',
 'discovered_in': 'finding discovered in experiment/workstream', 'motivates': 'finding motivates rule/decision/tool change', 'improves': 'rule/tool improves metric (with before/after)',
 'regresses': 'X worsens metric', 'contradicts': 'X conflicts with Y', 'blocks': 'X blocks Y', 'depends_on_decision': 'X waits for decision Y',
 # loop
 'step_of': 'X is a step of Loop Y', 'feeds': 'X feeds the next step Y of a loop',
 # added for the data layers
 'appears_in': 'X appears in dataset Y (weight = scene count)', 'watches': 'a workstream or routine watches X',
}
GRADES = ('Confirmed', 'Likely', 'Suspected')
PROVENANCE = ('data', 'doc', 'model_recall', 'simulated')
