import sys,re,os,collections
for f in sys.argv[1:]:
    try:
        sz=os.path.getsize(f)
        with open(f,'rb') as fh: b=fh.read(min(sz,3_000_000))
        s=b.decode('utf8','replace')
        tags=collections.Counter(re.findall(r'<([A-Za-z][A-Za-z0-9]*)',s))
        prof=re.search(r'profile="([^"]*)"',s); ver=re.search(r'<X3D[^>]*version="([^"]*)"',s)
        comps=re.findall(r'<component name="(\w+)" level="(\d)"',s)
        interesting={k:v for k,v in tags.items() if k in ('VolumeData','IsoSurfaceVolumeData','ImageTexture3D','PointSet','ElevationGrid','GeoElevationGrid','HAnimHumanoid','MetadataString','MetadataFloat','MetadataSet','MetadataDouble','MetadataInteger','GaussianSplats','Inline','PhysicalMaterial','Material','UnlitMaterial','TimeSensor','CoordinateInterpolator','PositionInterpolator','OrientationInterpolator','ParticleSystem','Text','GeoLOD','GeoViewpoint','LOD','Switch','Script','ProximitySensor','IndexedFaceSet','IndexedTriangleSet','TriangleSet','Color','ColorRGBA','Normal','ImageTexture','Appearance','Shape','Transform','ROUTE','DirectionalLight','PointLight','SpotLight','Viewpoint','NavigationInfo','Background','Fog','LineSet','IndexedLineSet','Extrusion','NurbsCurve','NurbsPatchSurface','Billboard','WorldInfo','MultiTexture','TextureCoordinate','EnvironmentLight','Anchor','Collision','StaticGroup','CADLayer','Annotation','BoundaryEnhancementVolumeStyle')}
        print(f"{f} [{sz}] v={ver.group(1) if ver else '?'} p={prof.group(1) if prof else '?'} comps={comps} {dict(interesting)}")
    except Exception as e:
        print(f,'ERR',e)
