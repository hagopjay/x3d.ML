/* js-port-of-8dd0d3e -- semantic pass driver (X3DVAL._m.semantic).
 * Mirrors validation/semantic.py::semantic_diagnostics at commit 8dd0d3e:
 *   parse with _PARSER flags (huge_tree, resolve_entities=False, no_network) -> find Scene ->
 *   _check_profile_components(root) first, then _ALL_CHECKS in order, each on the Scene.
 * A check that throws (Python: OverflowError in _check_gaussian_splats) propagates; nothing is swallowed.
 */
(function (X3DVAL) {
  var M = X3DVAL._m;

  // semantic.py: diagnostics = _check_profile_components(root); then _ALL_CHECKS (lines 989-1004)
  var ORDER = [
    'check_profile_components',
    'check_duplicate_defs',
    'check_def_use_consistency',
    'check_use_before_def',
    'check_containerfield',
    'check_shape_completeness',
    'check_empty_groups',
    'check_route_validity',
    'check_naming_conventions',
    'check_interpolator_keys',
    'check_tuple_counts',
    'check_gaussian_splats',
    'check_dead_boolean_routes',
    'check_rigid_body_physics',
    'check_missing_viewpoint'
  ];

  function missingChecks() {
    var out = [];
    for (var i = 0; i < ORDER.length; i++) if (typeof M.checks[ORDER[i]] !== 'function') out.push(ORDER[i]);
    return out;
  }

  /**
   * semanticDiagnostics(xml) ->
   *   {status:'report'|'all-clear', diagnostics:[{level, check, message}]}
   *   {status:'parse-error', detail:"<msg>, line L, column C (<string>, line L)", diagnostics:[]}
   *   {status:'no-scene', detail:'No Scene element found in the X3D document.', diagnostics:[]}
   * Throws for anything that is not an XML parse error (like Python).
   */
  function semanticDiagnostics(xml) {
    var t = M.t, lib = t.lib();
    if (!lib) throw new Error('X3DVAL: load() has not completed');
    var missing = missingChecks();
    if (missing.length) throw new Error('X3DVAL: check functions not loaded: ' + missing.join(', '));
    var root;
    try {
      root = t.parseSnapshot(xml, t.SEM_OPTS);
    } catch (e) {
      if (e instanceof lib.XmlParseError) return { status: 'parse-error', detail: t.parseErrorString(e), diagnostics: [] };
      throw e;
    }
    var scene = t.findScene(root);
    if (!scene) return { status: 'no-scene', detail: 'No Scene element found in the X3D document.', diagnostics: [] };
    var diags = [];
    var ctx = {
      root: root, scene: scene, version: t.get(root, 'version', ''), uom: M.uom, py: M.py, t: t,
      emit: function (level, check, message) { diags.push({ level: level, check: check, message: message }); }
    };
    for (var i = 0; i < ORDER.length; i++) M.checks[ORDER[i]](ctx);
    return { status: diags.length ? 'report' : 'all-clear', diagnostics: diags };
  }

  M.semantic = { ORDER: ORDER, semanticDiagnostics: semanticDiagnostics, missingChecks: missingChecks };
})((typeof self !== 'undefined' ? self : globalThis).X3DVAL);
