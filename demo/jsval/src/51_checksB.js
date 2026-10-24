/* js-port-of-8dd0d3e -- semantic checks, group B (field / ROUTE typing).
 * Line-by-line port of semantic.py (commit 8dd0d3e):
 *   _resolve_route_field (236-257), _script_fields (263-273), _proto_interfaces (276-297),
 *   _endpoint_fields (300-312), _check_route_validity (315-416)
 *   _type_ancestry (422-437), _node_field_map (440-441), _field_accepts (444-452),
 *   _check_containerfield (455-516)
 *   _check_dead_boolean_routes (636-672)
 * Each check receives ctx = {root, scene, version, uom, py, t, emit(level, check, message)} and
 * emits in exactly the order Python appends diagnostics. Field tables come from
 * X3DVAL._m.uom (nodeFieldMap keeps X3DUOM field order, which drives candidate order;
 * typeAncestry follows baseType + additionalBaseTypes through nodes and abstracts).
 * Helpers are exported as X3DVAL._m.routeHelpers for other groups / tests.
 */
(function (X3DVAL) {
  var checks = X3DVAL._m.checks;

  var NODE_FIELD_TYPES = new Set(['SFNode', 'MFNode']);                    // _NODE_FIELD_TYPES
  // _DECLARED_FIELD_NODES: interface extended by user-declared <field> children.
  var DECLARED_FIELD_NODES = new Set(['Script', 'ComposedShader', 'PackagedShader', 'ShaderProgram']);
  var ALWAYS_FALSE_SRC = 'BooleanFilter', ALWAYS_FALSE_FIELD = 'inputFalse';   // _ALWAYS_FALSE
  var TRUE_ONLY_NODES = new Set(['IntegerTrigger', 'TimeTrigger', 'BooleanToggle']); // _TRUE_ONLY (field set_boolean)

  // Python str(None) -> 'None' (a UOM field value may be None in the Python tables).
  function pyStr(v) { return v === null || v === undefined ? 'None' : String(v); }
  // dict.get(key, "") on a field-info dict: the key may exist with value None (-> None, falsy).
  function fget(f, key) { var v = f[key]; return v === undefined ? '' : v; }

  function nodeFieldMap(tag) { return X3DVAL._m.uom.nodeFieldMap(tag); }   // _node_field_map (cached Map; never mutate)
  function typeAncestry(tag) { return X3DVAL._m.uom.typeAncestry(tag); }   // _type_ancestry (cached Set)

  // _resolve_route_field: honour set_X (in) / X_changed (out) aliases of inputOutput fields.
  function resolveRouteField(fields, fieldName, direction) {
    var info = fields.get(fieldName);
    if (info !== undefined) return info;
    if (direction === 'in' && fieldName.startsWith('set_')) {
      var b1 = fields.get(fieldName.slice('set_'.length));
      if (b1 !== undefined && fget(b1, 'accessType') === 'inputOutput') return b1;
    }
    if (direction === 'out' && fieldName.endsWith('_changed')) {
      var b2 = fields.get(fieldName.slice(0, fieldName.length - '_changed'.length));
      if (b2 !== undefined && fget(b2, 'accessType') === 'inputOutput') return b2;
    }
    return null;
  }

  function declaredField(t, f) {
    var name = t.get(f, 'name');
    return { name: name, type: t.get(f, 'type', ''), accessType: t.get(f, 'accessType', '') };
  }
  // _script_fields: <field> children (any namespace, local tag) with a truthy name; later duplicates overwrite.
  function scriptFields(t, el) {
    var out = new Map();
    var ch = t.children(el);
    for (var i = 0; i < ch.length; i++) {
      var child = ch[i];
      if (child.tag === 'field' && t.get(child, 'name')) out.set(t.get(child, 'name'), declaredField(t, child));
    }
    return out;
  }
  // _proto_interfaces: {protoName: Map(field -> info)} from ProtoDeclare/ProtoInterface/field and ExternProtoDeclare/field.
  function protoInterfaces(t, scene) {
    var out = new Map();
    for (var el of t.iter(scene)) {
      var tag = el.tag, name = t.get(el, 'name');
      if (!name) continue;
      if (tag === 'ProtoDeclare') {
        var fields = new Map();
        var subs = t.children(el);
        for (var i = 0; i < subs.length; i++) {
          var sub = subs[i];
          if (sub.tag !== 'ProtoInterface') continue;
          var fs = t.children(sub);
          for (var j = 0; j < fs.length; j++) {
            var f = fs[j];
            if (f.tag === 'field' && t.get(f, 'name')) fields.set(t.get(f, 'name'), declaredField(t, f));
          }
        }
        out.set(name, fields);
      } else if (tag === 'ExternProtoDeclare') {
        var ef = new Map();
        var efs = t.children(el);
        for (var k = 0; k < efs.length; k++) {
          var g = efs[k];
          if (g.tag === 'field' && t.get(g, 'name')) ef.set(t.get(g, 'name'), declaredField(t, g));
        }
        out.set(name, ef);
      }
    }
    return out;
  }
  // _endpoint_fields: UOM fields of tag, augmented by declared <field>s (Script/shaders) or by a proto interface.
  function endpointFields(t, el, tag, protos) {
    var fields = new Map(nodeFieldMap(tag));                 // fresh dict like Python ({} when tag unknown)
    if (DECLARED_FIELD_NODES.has(tag)) {
      for (var kv of scriptFields(t, el)) fields.set(kv[0], kv[1]);   // declared fields augment the built-ins
    } else {
      // <ProtoInstance name="P"> exposes ProtoDeclare P's interface; the shorthand <P .../> form too.
      var pname = tag === 'ProtoInstance' ? t.get(el, 'name') : tag;
      if (pname !== null && protos.has(pname)) {
        var merged = new Map(protos.get(pname));             // {**protos[pname], **fields}
        for (var kv2 of fields) merged.set(kv2[0], kv2[1]);
        fields = merged;
      }
    }
    return fields;
  }

  // ---- ROUTE validity (315-416) -------------------------------------------------------
  checks.check_route_validity = function (ctx) {
    var t = ctx.t, py = ctx.py;
    var protoIfaces = protoInterfaces(t, ctx.scene);

    var defMap = new Map();                                 // LAST DEF wins -> [el, tag]
    for (var el of t.iter(ctx.scene)) {
      var defName = t.get(el, 'DEF');
      if (defName) defMap.set(defName, [el, el.tag]);
    }

    for (var route of t.iterTag(ctx.scene, 'ROUTE')) {     // scene.iter("ROUTE"): non-namespaced only
      var fromNode = t.get(route, 'fromNode', '');
      var fromField = t.get(route, 'fromField', '');
      var toNode = t.get(route, 'toNode', '');
      var toField = t.get(route, 'toField', '');

      if (!defMap.has(fromNode)) {
        var avail1 = py.pySorted(defMap.keys()).join(', ') || '(none)';
        ctx.emit('error', 'route-missing-from-node',
          "ROUTE fromNode='" + fromNode + "' not found. Available DEFs: " + avail1 + '.');
        continue;
      }
      if (!defMap.has(toNode)) {
        var avail2 = py.pySorted(defMap.keys()).join(', ') || '(none)';
        ctx.emit('error', 'route-missing-to-node',
          "ROUTE toNode='" + toNode + "' not found. Available DEFs: " + avail2 + '.');
        continue;
      }

      var fromEl = defMap.get(fromNode)[0], fromType = defMap.get(fromNode)[1];
      var toEl = defMap.get(toNode)[0], toType = defMap.get(toNode)[1];

      // A ProtoInstance whose ProtoDeclare/ExternProtoDeclare is not in this file: interface unknown, skip.
      if ((fromType === 'ProtoInstance' && !protoIfaces.has(t.get(fromEl, 'name'))) ||
          (toType === 'ProtoInstance' && !protoIfaces.has(t.get(toEl, 'name')))) continue;

      var fromFields = endpointFields(t, fromEl, fromType, protoIfaces);
      var toFields = endpointFields(t, toEl, toType, protoIfaces);

      var fromInfo = resolveRouteField(fromFields, fromField, 'out');
      if (fromInfo === null) {
        ctx.emit('error', 'route-invalid-from-field',
          "ROUTE fromField='" + fromField + "' does not exist on " + fromType + " (DEF='" + fromNode + "').");
        continue;
      }
      var toInfo = resolveRouteField(toFields, toField, 'in');
      if (toInfo === null) {
        ctx.emit('error', 'route-invalid-to-field',
          "ROUTE toField='" + toField + "' does not exist on " + toType + " (DEF='" + toNode + "').");
        continue;
      }

      var fromAccess = fget(fromInfo, 'accessType');
      if (fromAccess !== 'outputOnly' && fromAccess !== 'inputOutput') {
        ctx.emit('error', 'route-wrong-access-type',
          "ROUTE fromField='" + fromField + "' on " + fromType + " has accessType='" + pyStr(fromAccess) +
          "' -- must be 'outputOnly' or 'inputOutput' to be a ROUTE source.");
      }
      var toAccess = fget(toInfo, 'accessType');
      if (toAccess !== 'inputOnly' && toAccess !== 'inputOutput') {
        ctx.emit('error', 'route-wrong-access-type',
          "ROUTE toField='" + toField + "' on " + toType + " has accessType='" + pyStr(toAccess) +
          "' -- must be 'inputOnly' or 'inputOutput' to be a ROUTE destination.");
      }

      var fromTypeName = fget(fromInfo, 'type'), toTypeName = fget(toInfo, 'type');
      if (fromTypeName && toTypeName && fromTypeName !== toTypeName) {
        ctx.emit('error', 'route-type-mismatch',
          'ROUTE type mismatch: ' + fromNode + '.' + fromField + ' is ' + fromTypeName +
          ' but ' + toNode + '.' + toField + ' is ' + toTypeName + '. ROUTE requires matching field types.');
      }
    }
  };

  // ---- containerField (419-516) -------------------------------------------------------
  var RE_ACC_SPLIT = null;
  // _field_accepts: node-typed field whose acceptableNodeTypes ('|' or whitespace separated) meets the ancestry.
  function fieldAccepts(field, ancestry) {
    if (!NODE_FIELD_TYPES.has(field.type)) return false;
    var acc = field.acceptableNodeTypes;
    if (!acc) return true;                                   // unspecified -> be lenient
    if (!RE_ACC_SPLIT) RE_ACC_SPLIT = new RegExp('[|' + X3DVAL._m.py.PY_WS + ']+');
    var toks = X3DVAL._m.py.pyStrip(acc).split(RE_ACC_SPLIT);
    for (var i = 0; i < toks.length; i++) if (ancestry.has(toks[i])) return true;
    return false;
  }

  checks.check_containerfield = function (ctx) {
    var t = ctx.t, uom = ctx.uom;
    for (var parent of t.iter(ctx.scene)) {
      var ptag = parent.tag;
      if (uom.nodeInfo(ptag) === null) continue;
      var pfields = uom.nodeFieldMap(ptag);
      var ch = t.children(parent);
      for (var i = 0; i < ch.length; i++) {
        var child = ch[i], ctag = child.tag;
        var cinfo = uom.nodeInfo(ctag);
        if (cinfo === null) continue;                        // skip ROUTE/field/IS/meta/comments
        if (ctag === 'ProtoInstance') continue;              // a prototype instance stands in for any node type
        var cfAttr = t.get(child, 'containerField');
        var cf = cfAttr || cinfo.containerField;
        if (!cf) continue;
        var anc = uom.typeAncestry(ctag);
        var explicit = cfAttr !== null;
        var candidates = [];
        for (var kv of pfields) if (fieldAccepts(kv[1], anc)) candidates.push(kv[0]);
        var suggest = '';
        if (candidates.length) {
          var head = "containerField='" + candidates[0] + "'";
          var more = candidates.length > 1 ? ' (or ' + candidates.slice(1).join(', ') + ')' : '';
          suggest = ' Use ' + head + more + ' to place a ' + ctag + ' here.';
        }
        var field = pfields.get(cf);
        var hint = explicit ? '' :
          ' ' + ctag + "'s default containerField is '" + cf + "', which does not fit a " + ptag +
          ' -- an explicit containerField is required here.';
        if (field === undefined) {
          ctx.emit('error', 'containerfield-unknown',
            ctag + " containerField='" + cf + "' but " + ptag + " has no field named '" + cf + "'." + hint + suggest);
        } else if (!NODE_FIELD_TYPES.has(field.type)) {
          ctx.emit('error', 'containerfield-not-node',
            ctag + " containerField='" + cf + "' targets " + ptag + '.' + cf + ', which is a ' + pyStr(field.type) +
            ' value field, not a node container.' + suggest);
        } else if (!fieldAccepts(field, anc)) {
          var acc = fget(field, 'acceptableNodeTypes');
          var alt = candidates.filter(function (c) { return c !== cf; });
          var s2 = alt.length ? " Use containerField='" + alt[0] + "'." : '';
          ctx.emit('error', 'containerfield-type-mismatch',
            ptag + '.' + cf + ' does not accept a ' + ctag + ' (accepts: ' + pyStr(acc) + ').' + s2);
        }
      }
    }
  };

  // ---- dead boolean ROUTEs (636-672) --------------------------------------------------
  checks.check_dead_boolean_routes = function (ctx) {
    var t = ctx.t, py = ctx.py;
    var version = t.get(ctx.root, 'version', '');           // scene.getroottree().getroot().get("version", "")
    var legacy;
    try { legacy = py.pyFloat(version) <= 3.3; } catch (e) { legacy = false; }   // ValueError -> False
    var defs = new Map();                                    // LAST DEF wins; elements only
    for (var el of t.iter(ctx.scene)) {
      if (el.kind !== 'element') continue;
      var d = t.get(el, 'DEF');
      if (d) defs.set(d, el.tag);
    }
    for (var route of t.iterTag(ctx.scene, 'ROUTE', true)) {   // scene.iter("ROUTE", "{*}ROUTE")
      var fromNode = t.get(route, 'fromNode'), toNode = t.get(route, 'toNode');
      var srcType = fromNode === null ? undefined : defs.get(fromNode);
      var dstType = toNode === null ? undefined : defs.get(toNode);
      if (!(srcType === ALWAYS_FALSE_SRC && t.get(route, 'fromField') === ALWAYS_FALSE_FIELD)) continue;
      if (!(dstType !== undefined && TRUE_ONLY_NODES.has(dstType) && t.get(route, 'toField') === 'set_boolean')) continue;
      if (legacy && dstType !== 'BooleanToggle') continue;
      ctx.emit('warning', 'route-never-fires',
        'ROUTE ' + fromNode + '.inputFalse -> ' + toNode + '.set_boolean never fires: inputFalse only sends FALSE and ' +
        dstType + ' acts only on TRUE' + (dstType !== 'BooleanToggle' ? ' in X3D 4.0' : '') +
        '. To react when the input turns FALSE, route inputNegate instead.');
    }
  };

  X3DVAL._m.routeHelpers = {
    NODE_FIELD_TYPES: NODE_FIELD_TYPES, DECLARED_FIELD_NODES: DECLARED_FIELD_NODES, TRUE_ONLY_NODES: TRUE_ONLY_NODES,
    scriptFields: scriptFields, protoInterfaces: protoInterfaces, endpointFields: endpointFields,
    resolveRouteField: resolveRouteField, fieldAccepts: fieldAccepts,
    nodeFieldMap: nodeFieldMap, typeAncestry: typeAncestry
  };
  X3DVAL._m.checksB = {
    ids: ['containerfield-unknown', 'containerfield-not-node', 'containerfield-type-mismatch',
      'route-missing-from-node', 'route-missing-to-node', 'route-invalid-from-field', 'route-invalid-to-field',
      'route-wrong-access-type', 'route-type-mismatch', 'route-never-fires'],
    functions: ['check_containerfield', 'check_route_validity', 'check_dead_boolean_routes']
  };
})((typeof self !== 'undefined' ? self : globalThis).X3DVAL);
