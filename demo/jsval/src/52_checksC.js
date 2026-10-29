/* js-port-of-8dd0d3e -- semantic checks, group C (numeric arrays).
 * Line-by-line port of semantic.py (commit 8dd0d3e):
 *   _check_interpolator_keys (543-601)  [interpolator-key-length]
 *   _check_tuple_counts      (604-633)  [tuple-count]
 *   _check_gaussian_splats   (675-770)  [tuple-count, splat-array-length, splat-sh-partial, splat-no-color,
 *                                        splat-scale-space, splat-opacity-space, splat-quaternion-norm,
 *                                        splat-quaternion-order]
 *   _check_rigid_body_physics (881-986) [physics-non-finite, physics-mass, physics-zero-axis,
 *                                        physics-not-in-collection, physics-joint-body,
 *                                        physics-joint-cross-collection]
 * Each check receives ctx = {root, scene, version, uom, py, t, emit(level, check, message)} and
 * emits in exactly the order Python appends diagnostics. Messages echo raw attribute strings
 * and integer counts only, so no Python float formatting is needed.
 */
(function (X3DVAL) {
  var checks = X3DVAL._m.checks;

  // f" (DEF={el.get('DEF')!r})" if el.get("DEF") else ""
  function defLabel(ctx, el) {
    var d = ctx.t.get(el, 'DEF');
    return d ? ' (DEF=' + ctx.py.pyRepr(d) + ')' : '';
  }
  // Python truthiness of a float: 0.0 and -0.0 are false, NaN is true.
  function truthy(x) { return x !== 0; }
  // Python min()/max() over a non-empty list of floats: keep the first element, replace only on
  // a strict < / > (so NaN wins only when it is the first element).
  function pyMin(a) { var m = a[0]; for (var i = 1; i < a.length; i++) if (a[i] < m) m = a[i]; return m; }
  function pyMax(a) { var m = a[0]; for (var i = 1; i < a.length; i++) if (a[i] > m) m = a[i]; return m; }
  function pySquare(x) {
    var y = x * x;
    if (y === Infinity && Number.isFinite(x)) throw new RangeError("OverflowError: (34, 'Numerical result out of range')");
    return y;
  }

  // ---- interpolator key / keyValue lengths ---------------------------------------------
  // _INTERP_ARITY (dict order matters: Python iterates tags in this order), null = variable
  var INTERP_ARITY = [
    ['ScalarInterpolator', 1], ['SplineScalarInterpolator', 1],
    ['PositionInterpolator2D', 2], ['SplinePositionInterpolator2D', 2],
    ['PositionInterpolator', 3], ['SplinePositionInterpolator', 3], ['GeoPositionInterpolator', 3],
    ['ColorInterpolator', 3],
    ['OrientationInterpolator', 4], ['SquadOrientationInterpolator', 4],
    ['CoordinateInterpolator', null], ['NormalInterpolator', null],
    ['CoordinateInterpolator2D', null]
  ];
  var INTERP_BASE = { CoordinateInterpolator: 3, NormalInterpolator: 3, CoordinateInterpolator2D: 2 };

  checks.check_interpolator_keys = function (ctx) {
    var t = ctx.t, py = ctx.py, scene = ctx.scene;
    for (var k = 0; k < INTERP_ARITY.length; k++) {
      var tag = INTERP_ARITY[k][0], arity = INTERP_ARITY[k][1];
      for (var el of t.iterTag(scene, tag)) {                      // scene.iter(tag): non-namespaced only
        var key = t.get(el, 'key'), kv = t.get(el, 'keyValue');
        if (key === null || kv === null) continue;
        var nk = py.countTokens(key), nv = py.countTokens(kv);
        var label = defLabel(ctx, el);
        if (nk === 0) continue;
        if (nv % nk !== 0) {
          ctx.emit('error', 'interpolator-key-length',
            tag + label + ': keyValue has ' + nv + ' values, not divisible by the ' +
            nk + ' key(s). Each key needs a whole keyValue entry.');
          continue;
        }
        var per = Math.floor(nv / nk);
        if (arity !== null && per !== arity) {
          ctx.emit('error', 'interpolator-key-length',
            tag + label + ': expected ' + arity + ' keyValue float(s) per key ' +
            '(' + nk + ' keys -> ' + (nk * arity) + '), got ' + per + ' per key (' + nv + ' total).');
        } else if (arity === null) {
          var base = Object.prototype.hasOwnProperty.call(INTERP_BASE, tag) ? INTERP_BASE[tag] : 1;
          if (per % base !== 0) {
            ctx.emit('error', 'interpolator-key-length',
              tag + label + ': ' + per + ' keyValue float(s) per key is not a ' +
              'multiple of ' + base + ' (one coordinate is ' + base + ' floats).');
          }
        }
      }
    }
  };

  // ---- MF tuple counts -----------------------------------------------------------------
  checks.check_tuple_counts = function (ctx) {
    var t = ctx.t, py = ctx.py, uom = ctx.uom, scene = ctx.scene;
    var types = uom.fieldTypes;
    for (var el of t.iter(scene)) {
      var tag = el.tag;                                             // '' for comment/PI/entity -> not in nodes
      if (!uom.nodeInfo(tag) || tag === 'GaussianSplats') continue;
      var fields = uom.nodeFieldMap(tag);
      var attrs = el.attrs;                                         // el.attrib.items(): document order, '{uri}local' keys
      for (var i = 0; i < attrs.length; i++) {
        var name = attrs[i][0], value = attrs[i][1];
        var f = fields.get(name);
        var ftype = f ? f.type : '';
        var info = Object.prototype.hasOwnProperty.call(types, ftype) ? types[ftype] : null;
        if (!info || !info.isArray || info.tupleSize < 2) continue;
        var n = py.countTokens(value), size = info.tupleSize;
        if (n % size) {
          var label = defLabel(ctx, el);
          ctx.emit('error', 'tuple-count',
            tag + label + ' ' + name + ': ' + n + ' numbers is not a whole number of ' +
            f.type + ' values (' + size + ' numbers each). The XSD ' +
            'pattern lets this through when a number splits across two tuples.');
        }
      }
    }
  };

  // ---- GaussianSplats ------------------------------------------------------------------
  var SPLAT_ARRAYS = [['positions', 3], ['scales', 3], ['orientations', 4], ['opacities', 1]];
  // _SPLAT_SH: [(d, c), name] for d in 0..3, c in 0..2d (dict order)
  var SPLAT_SH = [];
  for (var d_ = 0; d_ < 4; d_++) for (var c_ = 0; c_ < 2 * d_ + 1; c_++) SPLAT_SH.push([d_, c_, 'sphericalHarmonicsDegree' + d_ + 'Coef' + c_]);
  var SPLAT_ORDER_MIN = 100;

  checks.check_gaussian_splats = function (ctx) {
    var t = ctx.t, py = ctx.py, scene = ctx.scene;
    for (var el of t.iterTag(scene, 'GaussianSplats', true)) {     // scene.iter("GaussianSplats", "{*}GaussianSplats")
      var label = defLabel(ctx, el);
      var report = function (level, check, message) { ctx.emit(level, check, 'GaussianSplats' + label + ': ' + message); };

      // arrays = dict(_SPLAT_ARRAYS, **{name: 3 for name in _SPLAT_SH.values()})
      var arrays = SPLAT_ARRAYS.slice();
      for (var s = 0; s < SPLAT_SH.length; s++) arrays.push([SPLAT_SH[s][2], 3]);
      var counts = new Map();                                       // insertion-ordered like a dict
      for (var i = 0; i < arrays.length; i++) {
        var name = arrays[i][0], size = arrays[i][1];
        var v = t.get(el, name);
        if (v === null) continue;
        var n = py.countTokens(v);
        if (n % size) report('error', 'tuple-count', name + ' has ' + n + ' numbers, not a multiple of ' + size + '.');
        counts.set(name, Math.floor(n / size));
      }
      if (!counts.size) continue;
      var expected;
      if (counts.has('positions')) expected = counts.get('positions');
      else { expected = -Infinity; for (var cv of counts.values()) if (cv > expected) expected = cv; }
      for (var e of counts) {
        if (e[1] !== expected) {
          report('error', 'splat-array-length',
            e[0] + ' holds ' + e[1] + ' splats but positions holds ' + expected + '. ' +
            'Every per-splat array needs one entry per splat.');
        }
      }
      var present = new Set();
      for (var p = 0; p < SPLAT_SH.length; p++) if (counts.has(SPLAT_SH[p][2])) present.add(SPLAT_SH[p][0]);
      var degrees = Array.from(present).sort(function (a, b) { return a - b; });
      for (var di = 0; di < degrees.length; di++) {
        var d = degrees[di];
        var missing = [];
        for (var m = 0; m < SPLAT_SH.length; m++) if (SPLAT_SH[m][0] === d && !counts.has(SPLAT_SH[m][2])) missing.push(SPLAT_SH[m][2]);
        if (missing.length) {
          report('warning', 'splat-sh-partial',
            'SH degree ' + d + ' is missing ' + missing.join(', ') + '. Renderers drop a partial ' +
            'degree (X_ITE 16.4.3 treats it as absent), so write all 2d+1 coefficients or none.');
        } else if (d && !present.has(d - 1)) {
          report('warning', 'splat-sh-partial', 'SH degree ' + d + ' is written but degree ' + (d - 1) + ' is not.');
        }
      }
      if (!present.has(0)) report('warning', 'splat-no-color', 'no sphericalHarmonicsDegree0Coef0, so the splats have no base colour.');

      var scales = py.pyFloats(t.get(el, 'scales', ''));
      if (scales.length && pyMin(scales) < 0) {
        var neg = 0;
        for (var si = 0; si < scales.length; si++) if (scales[si] < 0) neg++;
        report('error', 'splat-scale-space',
          neg + ' of ' + scales.length + ' scale values are negative. X3D scales are linear ' +
          'standard deviations; a 3DGS PLY stores ln(scale), so apply exp() when converting.');
      }
      var opacities = py.pyFloats(t.get(el, 'opacities', ''));
      if (opacities.length && (pyMin(opacities) < 0 || pyMax(opacities) > 1)) {
        var bad = 0;
        for (var oi = 0; oi < opacities.length; oi++) { var ov = opacities[oi]; if (!(0 <= ov && ov <= 1)) bad++; }
        report('error', 'splat-opacity-space',
          bad + ' of ' + opacities.length + ' opacities are outside 0 to 1. A 3DGS PLY stores ' +
          'logit(opacity), so apply the sigmoid when converting.');
      }
      var quats = py.pyFloats(t.get(el, 'orientations', ''));
      if (quats.length >= 4) {
        var norms = [];
        for (var qi = 0; qi < quats.length - 3; qi += 4) {
          var a0 = quats[qi], a1 = quats[qi + 1], a2 = quats[qi + 2], a3 = quats[qi + 3];
          // Python: x ** 2 raises OverflowError for a finite x whose square overflows (never inf);
          // float + float only overflows to inf. ** 0.5 == sqrt for correctly rounded libm.
          norms.push(Math.sqrt(pySquare(a0) + pySquare(a1) + pySquare(a2) + pySquare(a3)));
        }
        var zero = 0, off = 0;
        for (var ni = 0; ni < norms.length; ni++) {
          if (norms[ni] === 0) zero++;
          if (Math.abs(norms[ni] - 1) > 1e-3) off++;
        }
        off -= zero;
        if (zero) report('error', 'splat-quaternion-norm', zero + ' orientations are all zero (no rotation is defined).');
        if (off) {
          report('warning', 'splat-quaternion-norm',
            off + ' of ' + norms.length + ' orientations are not unit length (|q| off by more than 1e-3); ' +
            'renderers normalise them, but a unit quaternion round-trips exactly.');
        }
        if (norms.length >= SPLAT_ORDER_MIN) {
          var lead = [0, 0, 0, 0];
          for (var li = 0; li < 4 * norms.length; li += 4) {
            // q = [abs(v) ...]; lead[q.index(max(q))] += 1  (first strictly-greatest element)
            var q0 = Math.abs(quats[li]), q1 = Math.abs(quats[li + 1]), q2 = Math.abs(quats[li + 2]), q3 = Math.abs(quats[li + 3]);
            var idx = 0, best = q0;
            if (q1 > best) { idx = 1; best = q1; }
            if (q2 > best) { idx = 2; best = q2; }
            if (q3 > best) { idx = 3; best = q3; }
            lead[idx] += 1;
          }
          if (lead[0] > 0.6 * norms.length && lead[3] < 0.2 * norms.length) {
            report('warning', 'splat-quaternion-order',
              lead[0] + ' of ' + norms.length + ' orientations have their largest component first and ' +
              'only ' + lead[3] + ' last. Trained splats usually stay near the identity (0 0 0 1), ' +
              'so these look written w x y z; X3D 4.1 reads x y z w.');
          }
        }
      }
    }
  };

  // ---- RigidBodyPhysics ----------------------------------------------------------------
  var JOINT_AXIS_ATTRS = ['axis', 'axis1', 'axis2'];
  var NUMERIC_FIELD = /^(SF|MF)(Float|Double|Time|Vec\d[fd]|Rotation|Matrix\d[fd]|Color|ColorRGBA|Quaternion)$/;
  var physicsCache = null;
  function physicsSets(uom) {
    if (physicsCache && physicsCache.nodes === uom.nodes) return physicsCache;
    var physics = new Set(), joints = new Set();
    for (var name in uom.nodes) {
      if (uom.nodes[name].component === 'RigidBodyPhysics') {
        physics.add(name);
        if (name.slice(-5) === 'Joint') joints.add(name);
      }
    }
    physicsCache = { nodes: uom.nodes, physics: physics, joints: joints };
    return physicsCache;
  }

  checks.check_rigid_body_physics = function (ctx) {
    var t = ctx.t, py = ctx.py, uom = ctx.uom, scene = ctx.scene;
    var ps = physicsSets(uom), physics = ps.physics, joints = ps.joints;
    // defs: first DEF wins
    var defs = new Map();
    for (var el0 of t.iter(scene)) {
      if (el0.kind !== 'element') continue;
      var d0 = t.get(el0, 'DEF');
      if (d0 && !defs.has(d0)) defs.set(d0, el0);
    }
    function resolve(el) {
      var u = t.get(el, 'USE');
      return u ? (defs.has(u) ? defs.get(u) : null) : el;
    }
    function label(el) {
      var name = t.get(el, 'DEF') || t.get(el, 'USE');
      return name ? el.tag + " '" + name + "'" : el.tag;
    }
    function report(level, check, el, message) { ctx.emit(level, check, message); }

    for (var el of t.iter(scene)) {
      var tag = el.tag;
      if (!physics.has(tag)) continue;
      var use = t.get(el, 'USE');
      if (!use) {
        var fmap = uom.nodeFieldMap(tag);
        var attrs = el.attrs;
        for (var i = 0; i < attrs.length; i++) {
          var attr = attrs[i][0], value = attrs[i][1];
          var fdef = fmap.get(attr);
          var ftype = fdef ? fdef.type : '';
          if (NUMERIC_FIELD.test(ftype)) {
            var fl = py.pyFloats(value), allFinite = true;
            for (var j = 0; j < fl.length; j++) if (!Number.isFinite(fl[j])) { allFinite = false; break; }
            if (!allFinite) {
              report('error', 'physics-non-finite', el,
                label(el) + '.' + attr + "='" + value + "' contains NaN or infinity; a " +
                'simulation step with it poisons every body it touches.');
            }
          }
        }
      }

      var parent = el.parent;
      var ptag = parent !== null ? parent.tag : '';
      var cf = t.get(el, 'containerField') || uom.nodes[tag].containerField;

      if (tag === 'RigidBody' && !use) {
        var mass = py.pyFloats(t.get(el, 'mass', '1')).slice(0, 1);
        if (mass.length && (mass[0] < 0 || (mass[0] === 0 && t.get(el, 'fixed') !== 'true'))) {
          report('error', 'physics-mass', el,
            label(el) + " has mass='" + t.get(el, 'mass') + "'; a dynamic body needs a " +
            "mass above zero (mass 0 only makes sense with fixed='true').");
        }
        var orient = py.pyFloats(t.get(el, 'orientation', '0 0 1 0'));
        if (orient.length === 4 && !(truthy(orient[0]) || truthy(orient[1]) || truthy(orient[2]))) {
          report('error', 'physics-zero-axis', el,
            label(el) + " has orientation='" + t.get(el, 'orientation') + "' with a " +
            'zero-length axis; the rotation is undefined.');
        }
        if (ptag !== 'RigidBodyCollection' && !(joints.has(ptag) && (cf === 'body1' || cf === 'body2'))) {
          report('warning', 'physics-not-in-collection', el,
            label(el) + ' is not a child of a RigidBodyCollection, so no ' +
            'simulation will include it.');
        }
      }

      if (joints.has(tag)) {
        for (var ai = 0; ai < JOINT_AXIS_ATTRS.length; ai++) {
          var aname = JOINT_AXIS_ATTRS[ai];
          var araw = t.get(el, aname);
          var axis = araw ? py.pyFloats(araw) : [];
          if (axis.length === 3 && !(truthy(axis[0]) || truthy(axis[1]) || truthy(axis[2]))) {
            report('error', 'physics-zero-axis', el,
              label(el) + '.' + aname + "='" + araw + "' has zero length; the " +
              'joint axis must be a non-zero vector.');
          }
        }
        if (!use && ptag !== 'RigidBodyCollection') {
          report('warning', 'physics-not-in-collection', el,
            label(el) + ' is not a child of a RigidBodyCollection, so no ' +
            'simulation will include it.');
        }
        // ends = {c.get("containerField"): c for c in el if element and cf in (body1, body2)}
        // dict comprehension: key order = first insertion, value = last child with that key
        var ends = new Map();
        var kids = el.children;
        for (var ki = 0; ki < kids.length; ki++) {
          var c = kids[ki];
          if (c.kind !== 'element') continue;
          var ccf = t.get(c, 'containerField');
          if (ccf === 'body1' || ccf === 'body2') ends.set(ccf, c);
        }
        var names = ['body1', 'body2'];
        for (var nn = 0; nn < 2; nn++) {
          if (!ends.has(names[nn])) {
            report('warning', 'physics-joint-body', el,
              label(el) + ' has no ' + names[nn] + '; the joint constrains nothing ' +
              'without two bodies.');
          }
        }
        var bodies = new Map();
        for (var en of ends) bodies.set(en[0], resolve(en[1]));
        for (var be of bodies) {
          if (be[1] !== null && be[1].tag !== 'RigidBody') {
            report('error', 'physics-joint-body', el,
              label(el) + '.' + be[0] + ' refers to a ' + be[1].tag + ', not a RigidBody.');
          }
        }
        if (bodies.size === 2 && bodies.get('body1') !== null && bodies.get('body1') === bodies.get('body2')) {
          report('error', 'physics-joint-body', el,
            label(el) + ' joins ' + label(bodies.get('body1')) + ' to itself (body1 and ' +
            'body2 are the same body).');
        }
        if (ptag === 'RigidBodyCollection') {
          var members = new Set();
          var pk = parent.children;
          for (var mi = 0; mi < pk.length; mi++) {
            var mc = pk[mi];
            if (mc.tag === 'RigidBody' && (t.get(mc, 'containerField') || 'bodies') === 'bodies') members.add(resolve(mc));
          }
          for (var bb of bodies) {
            if (bb[1] !== null && bb[1].tag === 'RigidBody' && !members.has(bb[1])) {
              report('error', 'physics-joint-cross-collection', el,
                label(el) + '.' + bb[0] + ' is ' + label(bb[1]) + ', which is not in the ' +
                'same RigidBodyCollection as the joint.');
            }
          }
        }
      }
    }
  };

  X3DVAL._m.checksC = {
    ids: ['interpolator-key-length', 'tuple-count', 'splat-array-length', 'splat-sh-partial', 'splat-no-color',
      'splat-scale-space', 'splat-opacity-space', 'splat-quaternion-norm', 'splat-quaternion-order',
      'physics-non-finite', 'physics-mass', 'physics-zero-axis', 'physics-not-in-collection',
      'physics-joint-body', 'physics-joint-cross-collection'],
    functions: ['check_interpolator_keys', 'check_tuple_counts', 'check_gaussian_splats', 'check_rigid_body_physics'],
    INTERP_ARITY: INTERP_ARITY, INTERP_BASE: INTERP_BASE, SPLAT_ARRAYS: SPLAT_ARRAYS, SPLAT_SH: SPLAT_SH,
    SPLAT_ORDER_MIN: SPLAT_ORDER_MIN, JOINT_AXIS_ATTRS: JOINT_AXIS_ATTRS, NUMERIC_FIELD: NUMERIC_FIELD,
    physicsSets: physicsSets
  };
})((typeof self !== 'undefined' ? self : globalThis).X3DVAL);
