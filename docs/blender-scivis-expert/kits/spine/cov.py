import json, collections
rows=[json.loads(l) for l in open('/mnt/project-files/polyxandria/library/data/snapshot_v1.jsonl')]
GEOM={'IndexedFaceSet','IndexedTriangleSet','IndexedTriangleStripSet','IndexedTriangleFanSet','IndexedLineSet','TriangleSet','TriangleStripSet','TriangleFanSet','LineSet','ElevationGrid','Extrusion','PointSet','Sphere','Box','Cylinder','Cone','Rectangle2D','Disk2D','Text'}
SPLAT={'GaussianSplats'}
HANIM={'HAnimHumanoid'}
HAND=GEOM|SPLAT|{'Shape','Transform','Appearance','Material','PhysicalMaterial','UnlitMaterial','ImageTexture','PixelTexture','MovieTexture','TextureTransform','TextureCoordinate','Coordinate','Normal','Color','ColorRGBA','FontStyle','Switch','Inline','Viewpoint','Background','PointLight','DirectionalLight','SpotLight','Sound','AudioClip','HAnimHumanoid','HAnimJoint','HAnimSegment','HAnimSite','TimeSensor','PositionInterpolator','OrientationInterpolator','ScalarInterpolator','CoordinateInterpolator','ROUTE','MetadataString','MetadataSet','MetadataFloat','MetadataInteger','MetadataDouble','MetadataBoolean'}
FLAT={'Scene','Group','StaticGroup','Collision','LOD','Anchor','Billboard','WorldInfo','NavigationInfo','field','IS','connect','fieldValue','EXPORT','IMPORT','USE','DEF','Route','head','meta','component','unit'}
def cls(n):
    if n in HAND: return 'H'
    if n in FLAT: return 'F'
    return 'U'
def summarize(sub,label):
    n=len(sub)
    parsed=[r for r in sub if r['nodes'].get('Scene')]
    out={}
    strict=[r for r in parsed if all(cls(k)!='U' for k in r['nodes'])]
    geom=[r for r in parsed if any(k in GEOM|SPLAT|HANIM for k in r['nodes'])]
    geom_strict=[r for r in strict if any(k in GEOM|SPLAT|HANIM for k in r['nodes'])]
    inst_tot=sum(c for r in parsed for k,c in r['nodes'].items() if k not in ('Scene',))
    inst_H=sum(c for r in parsed for k,c in r['nodes'].items() if cls(k)=='H')
    inst_F=sum(c for r in parsed for k,c in r['nodes'].items() if cls(k)=='F' and k!='Scene')
    inst_U=sum(c for r in parsed for k,c in r['nodes'].items() if cls(k)=='U')
    print(f"{label}: n={n} parsed(Scene)={len(parsed)} strict_no_U={len(strict)} ({100*len(strict)/max(1,len(parsed)):.1f}% of parsed, {100*len(strict)/max(1,n):.1f}% of n) any_geom={len(geom)} ({100*len(geom)/max(1,len(parsed)):.1f}% parsed) geom&no_U={len(geom_strict)} inst H/F/U={inst_H}/{inst_F}/{inst_U} of {inst_tot}")
    # blockers
    B=collections.Counter()
    for r in parsed:
        for k in r['nodes']:
            if cls(k)=='U': B[k]+=1
    return B, parsed
if __name__=='__main__':
    allb,_=summarize(rows,'ALL')
    cl=[r for r in rows if r['clean']]
    clb,_=summarize(cl,'CLEAN')
    lit=[r for r in cl if r['fork']=='valid' and r['up']=='valid']
    litb,_=summarize(lit,'CLEAN&both-valid(lit)')
    forkv=[r for r in cl if r['fork']=='valid']
    summarize(forkv,'CLEAN&fork-valid')
    ondisk=[r for r in lit if r['origin'].startswith('project:')]
    ob,_=summarize(ondisk,'CLEAN&lit&ondisk(project)')
    print('top blockers clean', clb.most_common(30))
    print('top blockers lit', litb.most_common(30))
    print('top blockers ondisk lit', ob.most_common(30))
    # by kind
    for k in sorted(set(r['kind'] for r in rows)):
        summarize([r for r in cl if r['kind']==k],'CLEAN kind='+k)
