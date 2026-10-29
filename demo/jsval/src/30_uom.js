/* js-port-of-8dd0d3e -- X3DUOM tables (X3DVAL._m.uom).
 * Data comes from data/uom-4.1.json (extracted from X3dUnifiedObjectModel-4.1.xml by
 * tools/extract_uom.py; shape in PLAN.md section 3) and data/nodes-4.0.json. Python's
 * get_x3duom() always reads the 4.1 UOM regardless of the document version; so do we.
 */
(function (X3DVAL) {
  var raw = null;
  var nodes = null, abstracts = null, fieldTypes = null, profiles = null;
  var fieldMapCache = null, ancestryCache = null, geometry = null;
  var concreteNamesByVersion = {};

  function setData(uomJson, nodes40, nodes41) {
    raw = uomJson;
    nodes = Object.create(null); abstracts = Object.create(null); fieldTypes = Object.create(null); profiles = Object.create(null);
    fieldMapCache = new Map(); ancestryCache = new Map(); geometry = null;
    for (var name in uomJson.nodes) {
      var n = uomJson.nodes[name];
      nodes[name] = {
        component: n.c === undefined ? null : n.c,
        level: n.l === undefined ? null : n.l,
        baseType: n.b === undefined ? null : n.b,
        additionalBaseTypes: n.ab || [],
        containerField: n.cf === undefined ? null : n.cf,
        fields: (n.f || []).map(function (f) {
          var o = { name: f[0], type: f[1], accessType: f[2] };
          if (f.length > 3 && f[3]) o.acceptableNodeTypes = f[3];
          return o;
        })
      };
    }
    for (var an in uomJson.abstracts) {
      var a = uomJson.abstracts[an];
      abstracts[an] = { baseType: a.b === undefined ? null : a.b, additionalBaseTypes: a.ab || [] };
    }
    for (var ft in uomJson.fieldTypes) {
      var t = uomJson.fieldTypes[ft];
      fieldTypes[ft] = { isArray: !!t[0], tupleSize: t[1] };
    }
    for (var p in uomJson.profiles) {
      var lst = uomJson.profiles[p];
      profiles[p] = lst === null ? null : new Set(lst);     // null = Full: everything allowed
    }
    concreteNamesByVersion = {};
    if (nodes40) concreteNamesByVersion['4.0'] = new Set(nodes40);
    concreteNamesByVersion['4.1'] = new Set(nodes41 || Object.keys(uomJson.nodes));
  }

  function nodeInfo(tag) { return nodes && Object.prototype.hasOwnProperty.call(nodes, tag) ? nodes[tag] : null; }
  function abstractInfo(name) { return abstracts && Object.prototype.hasOwnProperty.call(abstracts, name) ? abstracts[name] : null; }
  // _node_field_map: {name: field} in UOM order (later duplicates overwrite, as in a dict comprehension).
  function nodeFieldMap(tag) {
    var m = fieldMapCache.get(tag);
    if (m) return m;
    m = new Map();
    var info = nodeInfo(tag);
    if (info) for (var i = 0; i < info.fields.length; i++) m.set(info.fields[i].name, info.fields[i]);
    fieldMapCache.set(tag, m);
    return m;
  }
  // _type_ancestry: {typename} + every base reachable via baseType and additionalBaseTypes.
  function typeAncestry(typename) {
    var c = ancestryCache.get(typename);
    if (c) return c;
    var chain = new Set([typename]);
    var todo = [typename];
    while (todo.length) {
      var name = todo.pop();
      var info = nodeInfo(name) || abstractInfo(name);
      if (!info) continue;
      var bases = [info.baseType].concat(info.additionalBaseTypes || []);
      for (var i = 0; i < bases.length; i++) {
        var b = bases[i];
        if (b && !chain.has(b)) { chain.add(b); todo.push(b); }
      }
    }
    ancestryCache.set(typename, chain);
    return chain;
  }
  // semantic.py _inherits_from: baseType chain only, abstracts looked up before nodes.
  function inheritsFrom(info, target, visited) {
    if (!visited) visited = new Set();
    var base = info.baseType;
    if (!base || visited.has(base)) return false;
    visited.add(base);
    if (base === target) return true;
    var parent = abstractInfo(base) || nodeInfo(base);
    if (!parent) return false;
    return inheritsFrom(parent, target, visited);
  }
  // semantic.py _get_geometry_nodes
  function geometryNodes() {
    if (geometry) return geometry;
    var s = new Set();
    for (var name in nodes) if (inheritsFrom(nodes[name], 'X3DGeometryNode')) s.add(name);
    ['Box', 'Sphere', 'Cylinder', 'Cone', 'Text', 'IndexedFaceSet', 'IndexedLineSet', 'IndexedTriangleSet',
      'PointSet', 'LineSet', 'TriangleSet', 'ElevationGrid', 'Extrusion'].forEach(function (n) { s.add(n); });
    geometry = s;
    return s;
  }
  // profile.py profile_nodes: {profile: Set|null}
  function profileNodes() { return profiles; }

  X3DVAL._m.uom = {
    setData: setData,
    get raw() { return raw; },
    get nodes() { return nodes; },
    get abstracts() { return abstracts; },
    get fieldTypes() { return fieldTypes; },
    get profiles() { return profiles; },
    get concreteNamesByVersion() { return concreteNamesByVersion; },
    nodeInfo: nodeInfo, abstractInfo: abstractInfo, nodeFieldMap: nodeFieldMap, typeAncestry: typeAncestry,
    inheritsFrom: inheritsFrom, geometryNodes: geometryNodes, profileNodes: profileNodes
  };
})((typeof self !== 'undefined' ? self : globalThis).X3DVAL);
