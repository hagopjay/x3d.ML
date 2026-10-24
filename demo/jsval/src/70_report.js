/* js-port-of-8dd0d3e -- markdown report renderer (X3DVAL._m.report).
 * Byte-exact mirror of validation/semantic.py::validate_semantic's string assembly at commit 8dd0d3e:
 *   parse error : "# Semantic Check: Parse Error\n\n" + str(XMLSyntaxError)
 *   no scene    : "# Semantic Check: No Scene\n\n" + "No Scene element found in the X3D document."
 *   all clear   : fixed text
 *   otherwise   : "# Semantic Check Report", "", "Found E error(s), W warning(s), I info(s).", "",
 *                 ["## Errors", "", items..., ""] ["## Warnings", "", items..., ""] ["## Info", "", items...]
 *                 joined with "\n" (so the report ends with "\n" iff I == 0 and E + W > 0).
 */
(function (X3DVAL) {
  var M = X3DVAL._m;

  var ALL_CLEAR = '# Semantic Check: All Clear\n\n' +
    'No semantic issues found. The scene looks well-structured.\n' +
    'Note: This checks common authoring issues beyond XSD schema validation. ' +
    'Use validate_x3d for schema-level validation.';

  function item(d) { return '- **[' + d.check + ']** ' + d.message; }

  function renderReport(sem) {
    if (sem.status === 'parse-error') return '# Semantic Check: Parse Error\n\n' + sem.detail;
    if (sem.status === 'no-scene') return '# Semantic Check: No Scene\n\n' + sem.detail;
    var diags = sem.diagnostics || [];
    if (!diags.length) return ALL_CLEAR;
    var errors = [], warnings = [], infos = [];
    for (var i = 0; i < diags.length; i++) {
      var d = diags[i];
      if (d.level === 'error') errors.push(d);
      else if (d.level === 'warning') warnings.push(d);
      else if (d.level === 'info') infos.push(d);
    }
    var lines = ['# Semantic Check Report', '', 'Found ' + errors.length + ' error(s), ' + warnings.length + ' warning(s), ' + infos.length + ' info(s).', ''];
    if (errors.length) { lines.push('## Errors', ''); for (i = 0; i < errors.length; i++) lines.push(item(errors[i])); lines.push(''); }
    if (warnings.length) { lines.push('## Warnings', ''); for (i = 0; i < warnings.length; i++) lines.push(item(warnings[i])); lines.push(''); }
    if (infos.length) { lines.push('## Info', ''); for (i = 0; i < infos.length; i++) lines.push(item(infos[i])); }
    return lines.join('\n');
  }

  /** {errors, warnings, info, fixes} as [{id, msg}] in report order; fixes = ids ending in "-fix". */
  function splitSections(diags) {
    var out = { errors: [], warnings: [], info: [], fixes: [] };
    diags = diags || [];
    for (var i = 0; i < diags.length; i++) {
      var d = diags[i], e = { id: d.check, msg: d.message };
      if (d.level === 'error') out.errors.push(e);
      else if (d.level === 'warning') out.warnings.push(e);
      else if (d.level === 'info') out.info.push(e);
      if (/-fix$/.test(d.check)) out.fixes.push(e);
    }
    return out;
  }

  /** Inverse of renderReport for a "# Semantic Check Report" string -> [{level, check, message}] (harness use). */
  function parseReport(report) {
    var LEVEL = { Errors: 'error', Warnings: 'warning', Info: 'info' };
    var out = [];
    var parts = report.split(/\n## (Errors|Warnings|Info)\n\n/);
    for (var i = 1; i < parts.length; i += 2) {
      var level = LEVEL[parts[i]], body = parts[i + 1];
      if (parts[i] !== 'Info') body = body.replace(/\n$/, '');
      var items = body.split(/\n(?=- \*\*\[)/);
      for (var j = 0; j < items.length; j++) {
        var it = items[j];
        if (it.indexOf('- **[') !== 0) continue;
        var close = it.indexOf(']** ');
        if (close < 0) continue;
        out.push({ level: level, check: it.slice(5, close), message: it.slice(close + 4) });
      }
    }
    return out;
  }

  M.report = { ALL_CLEAR: ALL_CLEAR, renderReport: renderReport, splitSections: splitSections, parseReport: parseReport };
})((typeof self !== 'undefined' ? self : globalThis).X3DVAL);
