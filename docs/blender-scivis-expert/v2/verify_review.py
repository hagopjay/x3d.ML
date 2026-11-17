#!/usr/bin/env python3
"""Reproduce scoped software/metadata checks; does not rerun Blender or old kits."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
if (ROOT/'test-deps').exists():sys.path.insert(0,str(ROOT/'test-deps'))
sys.path.insert(0,str(ROOT/'integration'))
import inventory


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study',type=Path,required=True)
    p.add_argument('--private-repo',type=Path)
    p.add_argument('--python313',type=Path)
    a=p.parse_args()
    result={'schema':'scivis.integration-release/1','started_utc':datetime.now(timezone.utc).isoformat(),
            'status':'fail','commands':[],'scope':'Software, shape, current-file and scoped-support checks. Blender execution remains in its own receipts.'}
    commands=[([sys.executable,'-m','unittest','discover','-s','integration/tests','-q'],ROOT),
              ([sys.executable,'-O','-m','unittest','discover','-s','integration/tests','-q'],ROOT),
              ([sys.executable,'-m','unittest','discover','-s','adapters/tests','-q'],ROOT),
              ([sys.executable,'-O','-m','unittest','discover','-s','adapters/tests','-q'],ROOT),
              (['node','docs/check_atlas.cjs'],ROOT)]
    if a.private_repo:
        for flags in ([],['-O']):
            commands.append(([sys.executable,*flags,'-m','unittest','discover','-s','tests','-p','test_x3dprov_escapes.py','-q'],a.private_repo.resolve()))
    if a.python313:
        for flags in ([],['-O']):
            commands.append(([str(a.python313.resolve()),*flags,'-m','unittest','discover','-s','integration/tests','-q'],ROOT))
    for command,cwd in commands:
        r=subprocess.run(command,cwd=cwd,capture_output=True,text=True,timeout=60)
        row={'command':command,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
        match=re.search(r'Ran (\d+) tests',r.stderr)
        if match:row['tests_run']=int(match.group(1))
        result['commands'].append(row)
        if r.returncode:raise RuntimeError(r.stderr or r.stdout)
    graph=inventory.read_json(ROOT/'integration/examples/research-loom-inventory.jsonld')
    import jsonschema
    schema=inventory.read_json(ROOT/'integration/inventory.schema.json')
    jsonschema.Draft202012Validator(schema).validate(graph)
    inspection=inventory.verify(graph,{'stem_repo':a.study.resolve().parents[1],
        'review_inputs':ROOT/'inputs','private_workspace':ROOT})
    inventory.write_json(ROOT/'integration/examples/current-bindings.json',inspection)
    if inspection['status']!='pass':raise RuntimeError('Live bindings differ')
    outcomes=[]
    for n in graph['@graph']:
        if inventory.entity_type(n)!='Claim':continue
        r=inventory.support(graph,n['@id'],inspection);outcomes.append(r)
        negative=any(x in n['@id'] for x in (':browser-',':post-edit-',':historical-corpus-counts-current'))
        expected='unsupported' if negative else 'supported_within_declared_scope'
        if r['status']!=expected:raise RuntimeError('Claim support control differs: '+n['@id'])
    counts=dict(Counter(x['status'] for x in outcomes))
    controls={'status':'pass','json_schema':'draft2020-12','claims':counts,'claim_results':outcomes,
              'scope':'Current recorded-support queries; no scientific pipeline is re-executed by this check.'}
    inventory.write_json(ROOT/'integration/examples/claim-query-controls.json',controls)
    result['bindings']={'status':'pass','artifacts':inspection['artifact_count']}
    result['claim_queries']=counts
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('integration','adapters','ontology','docs') for p in (ROOT/folder).rglob('*')
        if p.is_file() and p.suffix in ('.py','.cjs') and '__pycache__' not in p.parts}
    result['core_regression_before_fix']={'source_sha256':'74746444c0093a72636686fa325da5950802d860861e61a859ed1c0ba78cedae',
        'observed_tests':5,'observed_errors':4,'state':'recorded earlier in this pass; not rerun by this check'}
    result['preexisting_ingest_suite']={'passed':15,'skipped':2,'skip_reason':'Original external real-data directories absent',
        'state':'Executed earlier in this pass with pytest9.2.0; not rerun by this check'}
    result['native_browser']={'status':'not_run','scope':'Atlas logic checked in Node; no native X_ITE or atlas browser pixels claimed.'}
    result['status']='pass';result['finished_utc']=datetime.now(timezone.utc).isoformat()
    inventory.write_json(ROOT/'private/integration-release.json',result)
    print(json.dumps({'status':'pass','commands':len(commands),'bindings':inspection['artifact_count'],'claim_queries':counts}))


if __name__=='__main__':main()
