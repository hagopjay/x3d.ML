import sys, rdflib, pyshacl, json, time
ONT='/mnt/project-files/research/ontology-lentz-polys-2026-10-17/sources/uploads-17oct/X3dOntology4.1.ttl'
def run(ttl, label=''):
    data=rdflib.Graph(); data.parse(ttl,format='turtle')
    data.parse('xb-hanim.ttl',format='turtle')           # vocabulary joined into the data graph
    shapes=rdflib.Graph(); shapes.parse('xb-shapes.ttl',format='turtle')
    t=time.time()
    conforms, rgraph, rtext = pyshacl.validate(data, shacl_graph=shapes, inference='none', advanced=True, allow_warnings=False)
    SH=rdflib.Namespace('http://www.w3.org/ns/shacl#')
    rows=[]
    for r in rgraph.subjects(rdflib.RDF.type, SH.ValidationResult):
        rows.append((str(rgraph.value(r,SH.sourceShape)).split('#')[-1], str(rgraph.value(r,SH.resultSeverity)).split('#')[-1],
                     str(rgraph.value(r,SH.focusNode)).split('#')[-1], str(rgraph.value(r,SH.resultMessage))))
    rows.sort()
    print(label, 'conforms', conforms, 'results', len(rows), f'{time.time()-t:.2f}s')
    for x in rows: print('  ', x[0], x[1], x[2], '|', x[3][:170])
    return rows
if __name__=='__main__': run(sys.argv[1], sys.argv[1])
