/* js-port-of-8dd0d3e -- semantic checks, group A (structure / identity).
 * Line-by-line port of semantic.py (commit 8dd0d3e):
 *   _check_profile_components (847-878) + profile.py check_profile/component_statements (21-135)
 *   _check_duplicate_defs (102-121), _check_def_use_consistency (124-169), _check_use_before_def (519-540)
 *   _check_shape_completeness (172-203), _check_empty_groups (206-233)
 *   _check_naming_conventions (773-833), _check_missing_viewpoint (836-844)
 * Each check receives ctx = {root, scene, version, uom, py, t, emit(level, check, message)} and
 * emits in exactly the order Python appends diagnostics.
 */
(function (X3DVAL) {
  var checks = X3DVAL._m.checks;

  // ---- profile / component ------------------------------------------------------------
  // profile.py _STATEMENTS: allowed in every profile.
  var STATEMENTS = new Set([
    'connect', 'ExternProtoDeclare', 'EXPORT', 'field', 'fieldValue', 'IMPORT',
    'IS', 'ProtoBody', 'ProtoDeclare', 'ProtoInterface', 'ProtoInstance',
    'ROUTE', 'X3D', 'Scene', 'head', 'meta', 'component', 'unit'
  ]);

  // profile.py declared_components: {component name: max level}; int(level|"1"), ValueError -> 1
  function declaredComponents(ctx, root) {
    var t = ctx.t, py = ctx.py;
    var comps = new Map();
    for (var el of t.iter(root)) {
      if (el.tag !== 'component') continue;
      var name = t.get(el, 'name');
      if (!name) continue;
      var level;
      try { level = py.pyInt(t.get(el, 'level', '1')); } catch (e) { level = 1; }
      comps.set(name, Math.max(level, comps.has(name) ? comps.get(name) : 0));
    }
    return comps;
  }

  // profile.py check_profile -> {profile, components, missing[], unknown[]}
  function checkProfile(ctx, root) {
    var t = ctx.t, uom = ctx.uom, py = ctx.py;
    var profile = t.get(root, 'profile');            // null when absent (Python None)
    var comps = declaredComponents(ctx, root);
    var report = { profile: profile, components: comps, missing: [], unknown: [] };

    var allowed;
    if (profile) {
      var pn = uom.profileNodes();
      allowed = Object.prototype.hasOwnProperty.call(pn, profile) ? pn[profile] : null;
    } else {
      allowed = new Set();                             // missing/empty profile attribute: nothing allowed
    }
    if (allowed === null) return report;               // Full profile, or an unknown profile name

    var scene = null;
    for (var el of t.iter(root)) { if (el.tag === 'Scene') { scene = el; break; } }
    if (scene === null) return report;

    var seen = new Set();
    for (var el2 of t.iter(scene)) {
      var tag = el2.tag;
      if (!tag || seen.has(tag) || STATEMENTS.has(tag)) continue;
      seen.add(tag);
      var info = uom.nodeInfo(tag);
      if (info === null) { report.unknown.push(tag); continue; }
      if (allowed.has(tag)) continue;
      var comp = info.component, level = info.level || 1;
      if (comp && (comps.has(comp) ? comps.get(comp) : 0) >= level) continue;
      report.missing.push({
        node: tag, component: comp, level: level,
        declared_level: comps.has(comp) ? comps.get(comp) : 0, line: el2.line
      });
    }
    report.missing.sort(function (a, b) {
      return py.cmpTuple([a.component || '', a.level, a.node], [b.component || '', b.level, b.node]);
    });
    return report;
  }

  // profile.py component_statements
  function componentStatements(ctx, report) {
    var needed = new Map();
    for (var i = 0; i < report.missing.length; i++) {
      var m = report.missing[i];
      if (m.component) needed.set(m.component, Math.max(needed.has(m.component) ? needed.get(m.component) : 0, m.level));
    }
    var names = ctx.py.pySorted(needed.keys());
    return names.map(function (c) { return "<component name='" + c + "' level='" + needed.get(c) + "'/>"; });
  }

  function pyStr(v) { return v === null || v === undefined ? 'None' : String(v); }

  checks.check_profile_components = function (ctx) {
    var report = checkProfile(ctx, ctx.root);
    if (report.missing.length === 0) return;
    var fixes = componentStatements(ctx, report).join(' ');
    for (var i = 0; i < report.missing.length; i++) {
      var m = report.missing[i];
      var have = m.declared_level ? 'declared at level ' + m.declared_level : 'not declared';
      ctx.emit('error', 'profile-component',
        m.node + ' (component ' + pyStr(m.component) + ' level ' + m.level + ', ' + have +
        ") is outside profile '" + pyStr(report.profile) + "'. Browsers that enforce the header (X_ITE, x3d-tidy) refuse to load it.");
    }
    ctx.emit('info', 'profile-component-fix',
      'Add to <head>: ' + fixes + ' -- or raise the profile (Immersive covers most content, Full covers everything).');
  };

  // ---- duplicate DEF ------------------------------------------------------------------
  checks.check_duplicate_defs = function (ctx) {
    var t = ctx.t;
    var seen = new Map();                              // first DEF wins
    for (var el of t.iter(ctx.scene)) {
      var defName = t.get(el, 'DEF');
      if (!defName) continue;
      var tag = el.tag;
      if (seen.has(defName)) {
        ctx.emit('error', 'duplicate-def',
          "Duplicate DEF name '" + defName + "': first used on " + seen.get(defName) +
          ', also used on ' + tag + '. DEF names must be unique within a scene.');
      } else {
        seen.set(defName, tag);
      }
    }
  };

  // ---- DEF / USE consistency ----------------------------------------------------------
  checks.check_def_use_consistency = function (ctx) {
    var t = ctx.t, py = ctx.py;
    var defs = new Map();                              // DEF -> tag of first definition
    var uses = new Set();
    var referenced = new Set();                        // DEFs named by ROUTE, IMPORT/EXPORT
    for (var el of t.iter(ctx.scene)) {
      var tag = el.tag;
      var defName = t.get(el, 'DEF');
      if (defName && !defs.has(defName)) defs.set(defName, tag);
      var useName = t.get(el, 'USE');
      if (useName) uses.add(useName);
      if (tag === 'ROUTE') {
        var fn = t.get(el, 'fromNode'), tn = t.get(el, 'toNode');
        if (fn) referenced.add(fn);
        if (tn) referenced.add(tn);
      } else if (tag === 'EXPORT') {
        if (t.get(el, 'localDEF')) referenced.add(t.get(el, 'localDEF'));
      } else if (tag === 'IMPORT') {
        if (t.get(el, 'inlineDEF')) referenced.add(t.get(el, 'inlineDEF'));
      }
    }

    var sortedUses = py.pySorted(uses);
    for (var i = 0; i < sortedUses.length; i++) {
      var u = sortedUses[i];
      if (!defs.has(u)) {
        var available = py.pySorted(defs.keys()).join(', ') || '(none)';
        ctx.emit('error', 'use-undefined-def',
          "USE='" + u + "' references a DEF that does not exist in this scene. Available DEF names: " + available + '.');
      }
    }

    var unused = [];
    for (var d of defs.keys()) if (!uses.has(d) && !referenced.has(d)) unused.push(d);
    unused = py.pySorted(unused);
    for (var j = 0; j < unused.length; j++) {
      var dn = unused[j];
      ctx.emit('info', 'unused-def',
        "DEF='" + dn + "' (" + defs.get(dn) + ") is defined but never USE'd and no ROUTE, IMPORT or EXPORT names it. " +
        'This is fine if you reference it externally (Script, SAI).');
    }
  };

  // ---- USE before DEF -----------------------------------------------------------------
  checks.check_use_before_def = function (ctx) {
    var t = ctx.t;
    var allDefs = new Set();
    for (var el of t.iter(ctx.scene)) { var d0 = t.get(el, 'DEF'); if (d0) allDefs.add(d0); }
    var seen = new Set();
    for (var el2 of t.iter(ctx.scene)) {
      var useName = t.get(el2, 'USE');
      if (useName && !seen.has(useName) && allDefs.has(useName)) {
        ctx.emit('error', 'use-before-def',
          "USE='" + useName + "' (" + el2.tag + ') appears before its DEF in document order. A USE must follow the DEF it references.');
      }
      var defName = t.get(el2, 'DEF');
      if (defName) seen.add(defName);
    }
  };

  // ---- Shape completeness -------------------------------------------------------------
  checks.check_shape_completeness = function (ctx) {
    var t = ctx.t, py = ctx.py;
    var geometryNodes = ctx.uom.geometryNodes();
    for (var shape of t.iterTag(ctx.scene, 'Shape')) {
      if (t.get(shape, 'USE')) continue;              // USE'd Shape is childless by definition
      var defName = t.get(shape, 'DEF', '');
      var childTags = new Set();
      var ch = t.children(shape);
      for (var i = 0; i < ch.length; i++) childTags.add(ch[i].tag);
      var hasGeometry = false;
      for (var ct of childTags) if (geometryNodes.has(ct)) { hasGeometry = true; break; }
      var hasAppearance = childTags.has('Appearance');
      var label = defName ? ' (DEF=' + py.pyRepr(defName) + ')' : '';
      if (!hasGeometry) {
        ctx.emit('warning', 'shape-no-geometry',
          'Shape' + label + ' has no geometry child. Add a geometry node like Box, Sphere, or IndexedFaceSet.');
      }
      if (!hasAppearance) {
        ctx.emit('info', 'shape-no-appearance',
          'Shape' + label + ' has no Appearance. The shape will render with a default white material.');
      }
    }
  };

  // ---- empty grouping nodes -----------------------------------------------------------
  // semantic.py _GROUPING_NODES is a Python set (hash-seed-dependent iteration order across tags);
  // we use source order. Within one tag, document order -- identical to Python.
  var GROUPING_NODES = [
    'Transform', 'Group', 'Switch', 'Collision', 'LOD', 'Anchor',
    'Billboard', 'StaticGroup', 'CADAssembly', 'CADLayer', 'CADPart',
    'GeoLOD', 'EspduTransform', 'ReceiverPdu', 'SignalPdu',
    'TransmitterPdu', 'HAnimJoint', 'HAnimSegment', 'HAnimSite',
    'LayoutGroup', 'ScreenGroup', 'Viewport'
  ];
  var EMPTY_GROUP_EXEMPT = new Set(['HAnimJoint', 'HAnimSegment', 'HAnimSite']);

  checks.check_empty_groups = function (ctx) {
    var t = ctx.t, py = ctx.py;
    for (var k = 0; k < GROUPING_NODES.length; k++) {
      var tag = GROUPING_NODES[k];
      if (EMPTY_GROUP_EXEMPT.has(tag)) continue;
      for (var el of t.iterTag(ctx.scene, tag)) {
        if (t.len(el) === 0) {                         // comments/PIs count as children, like lxml len(el)
          if (t.get(el, 'USE')) continue;
          var defName = t.get(el, 'DEF', '');
          var label = defName ? ' (DEF=' + py.pyRepr(defName) + ')' : '';
          ctx.emit('warning', 'empty-group', tag + label + ' has no children. Empty grouping nodes have no effect.');
        }
      }
    }
  };

  // ---- naming conventions -------------------------------------------------------------
  var NAMING_HINTS_URL = 'https://www.web3d.org/x3d/content/examples/X3dSceneAuthoringHints.html#NamingConventions';
  var NAMING_ATTRS = ['DEF', 'USE', 'name'];

  checks.check_naming_conventions = function (ctx) {
    var t = ctx.t, py = ctx.py;
    var seen = new Set();                              // (attr, value) pairs
    for (var el of t.iter(ctx.scene)) {
      var tag = el.tag;
      if (!tag) continue;
      for (var i = 0; i < NAMING_ATTRS.length; i++) {
        var attr = NAMING_ATTRS[i];
        var value = t.get(el, attr);
        if (!value) continue;
        var key = attr + '\u0000' + value;
        if (seen.has(key)) continue;
        seen.add(key);
        var problems = [];
        if (value.indexOf('.') >= 0) problems.push("'.' interferes with ClassicVRML ROUTE syntax");
        if (value.indexOf('-') >= 0) problems.push("'-' becomes a subtraction operator in generated class/variable names");
        if (problems.length) {
          ctx.emit('warning', 'naming-convention',
            attr + "='" + value + "' on " + tag + ': ' + problems.join('; ') + '. See ' + NAMING_HINTS_URL);
        }
        if (value !== py.pyStrip(value) || py.pyAnyIsSpace(value)) {
          ctx.emit('error', 'naming-convention',
            attr + "='" + value + "' on " + tag + ' contains whitespace, which is illegal in ID/NMTOKEN values.');
        } else if (py.pyIsDigit(py.pyFirstChar(value))) {
          ctx.emit('error', 'naming-convention',
            attr + "='" + value + "' on " + tag + ' starts with a digit, which is illegal for XML names.');
        }
      }
    }
  };

  // ---- missing Viewpoint --------------------------------------------------------------
  checks.check_missing_viewpoint = function (ctx) {
    for (var vp of ctx.t.iterTag(ctx.scene, 'Viewpoint')) { if (vp) return; }
    ctx.emit('info', 'no-viewpoint',
      'Scene has no Viewpoint node. The browser will use a default camera. Consider adding a Viewpoint for a defined initial view.');
  };

  X3DVAL._m.checksA = {
    ids: ['profile-component', 'profile-component-fix', 'duplicate-def', 'use-undefined-def', 'unused-def',
      'use-before-def', 'shape-no-geometry', 'shape-no-appearance', 'empty-group', 'naming-convention', 'no-viewpoint'],
    functions: ['check_profile_components', 'check_duplicate_defs', 'check_def_use_consistency', 'check_use_before_def',
      'check_shape_completeness', 'check_empty_groups', 'check_naming_conventions', 'check_missing_viewpoint'],
    STATEMENTS: STATEMENTS, GROUPING_NODES: GROUPING_NODES, EMPTY_GROUP_EXEMPT: EMPTY_GROUP_EXEMPT,
    checkProfile: checkProfile, declaredComponents: declaredComponents, componentStatements: componentStatements
  };
})((typeof self !== 'undefined' ? self : globalThis).X3DVAL);
