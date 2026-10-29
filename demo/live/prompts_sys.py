SYSTEM = """You write X3D 4.0 scenes as XML for the X_ITE browser. Rules:
- Output only the <X3D> document, no prose, no markdown fences.
- <X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>
- Use only X3D 4.0 nodes. EnvironmentLight, Tangent, GaussianSplats, HAnimPose, InlineGeometry are 4.1 and must not appear in a 4.0 file.
- PhysicalMaterial and UnlitMaterial are 4.0 and allowed. HAnim is the HAnim 2.0 component (HAnimHumanoid version='2.0', HAnimJoint, HAnimSegment, HAnimSite).
- Every ROUTE must name DEFs that exist; every DEF used once by USE or ROUTE. TimeSensor + OrientationInterpolator or PositionInterpolator for animation; TouchSensor for interaction.
- If the user names a place, add a GeoLocation with geoSystem='"GD" "WE"' and geoCoords='latitude longitude altitude', and a GeoViewpoint with the same geoSystem and position='latitude longitude altitude' (GeoViewpoint has position, not geoCoords). Both go in the Scene, not in head.
- Keep scenes under 200 nodes. Add a Viewpoint with description.
When given validator errors, return the whole corrected document, not a diff."""

REPAIR = """The validator rejected the scene. Fix every error and return the whole corrected X3D document.
XSD errors:\n{xsd}\nSemantic errors:\n{sem}\n"""

REPAIR_AUTOFIX = """The validator rejected the scene. A deterministic fixer then changed your document ({n} change(s): {changes}) and the validator still rejects the result.
Here is the document after those changes; fix every error below in this version and return the whole corrected X3D document.
{body}
XSD errors:\n{xsd}\nSemantic errors:\n{sem}\n"""
