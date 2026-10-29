/* js-port-of-8dd0d3e -- public API (window.X3DVAL / self.X3DVAL).
 *
 *   await X3DVAL.load({base})                 base = URL of the jsval/ directory (default: this script's directory)
 *       options: precompile ('4.0' first is what the corpus needs: true | ['4.0'] | ['4.0','4.1']),
 *                onProgress({stage,...}), read(url)->Promise<Uint8Array>, importer(url)->Promise<module>, lib
 *   X3DVAL.validate(xml, {version})          -> {valid, xsd:{valid, errors:[string], schema_version?, notes?, status?:'exception', error?},
 *                                                 semantic:{status, errors:[{id,msg}], warnings:[...], info:[...], fixes:[...], report, detail?},
 *                                                 ms, label:'js-port-of-8dd0d3e'}
 *   X3DVAL.validateXml(xml, version?)         -> validate.py dict
 *   X3DVAL.validateSemantic(xml)              -> semantic.py markdown report string
 *   X3DVAL.semanticDiagnostics(xml)           -> {status, diagnostics:[{level, check, message}], detail?}
 *   X3DVAL.createWorkerClient({base})         -> same load/validate interface backed by worker.js
 *
 * valid = xsd.valid && no semantic error lines, exactly as canary/verdicts.py derives it.
 * This is a port of the x3d_mcp fork at commit 8dd0d3e, not the fork itself.
 */
(function (X3DVAL) {
  var M = X3DVAL._m;
  var G = typeof self !== 'undefined' ? self : globalThis;
  var now = (typeof performance !== 'undefined' && performance.now) ? function () { return performance.now(); } : function () { return Date.now(); };
  var DEC = typeof TextDecoder !== 'undefined' ? new TextDecoder('utf-8') : null;

  // Capture the script's own URL at evaluation time (document.currentScript is null later).
  var SCRIPT_BASE = null;
  try {
    if (typeof document !== 'undefined' && document.currentScript && document.currentScript.src) {
      SCRIPT_BASE = document.currentScript.src.replace(/[^/]*$/, '');
    }
  } catch (e) { /* ignore */ }
  if (!SCRIPT_BASE && typeof location !== 'undefined' && location.href && !/^blob:/.test(location.href)) {
    SCRIPT_BASE = location.href.replace(/[^/]*$/, '');
  }
  X3DVAL.scriptBase = SCRIPT_BASE;

  function fetchBytes(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('X3DVAL: fetch ' + url + ' -> HTTP ' + r.status);
      return r.arrayBuffer();
    }).then(function (ab) { return new Uint8Array(ab); });
  }
  function utf8(u8) { return DEC ? DEC.decode(u8) : String.fromCharCode.apply(null, u8); }

  var state = { promise: null, ready: false, base: null, loadMs: null };
  X3DVAL._state = state;

  X3DVAL.load = function (opts) {
    opts = opts || {};
    if (state.promise) return state.promise;
    var base = opts.base != null ? String(opts.base) : (SCRIPT_BASE || './');
    if (base && !/\/$/.test(base)) base += '/';
    state.base = base;
    var read = opts.read || fetchBytes;
    var t0 = now();
    var progress = typeof opts.onProgress === 'function' ? opts.onProgress : function () {};
    state.promise = Promise.all([
      M.xsd.load({ base: base, read: read, importer: opts.importer, lib: opts.lib, precompile: opts.precompile, onProgress: progress }),
      read(base + 'data/uom-4.1.json'),
      read(base + 'data/nodes-4.0.json'),
      read(base + 'data/nodes-4.1.json')
    ]).then(function (r) {
      M.t.setLib(M.xsd.state.lib);
      M.uom.setData(JSON.parse(utf8(r[1])), JSON.parse(utf8(r[2])), JSON.parse(utf8(r[3])));
      var missing = M.semantic.missingChecks();
      if (missing.length) throw new Error('X3DVAL: check functions not loaded: ' + missing.join(', '));
      state.ready = true;
      state.loadMs = now() - t0;
      progress({ stage: 'ready', ms: state.loadMs });
      return X3DVAL;
    });
    return state.promise;
  };

  X3DVAL.isReady = function () { return state.ready; };

  /** Compile a schema version now (2-4 s) instead of on the first validate(); returns compile ms. */
  X3DVAL.precompile = function (version) {
    if (!state.ready) throw new Error('X3DVAL: load() has not completed');
    M.xsd.compile(version || '4.0');
    return M.xsd.state.compileMs[version || '4.0'];
  };

  X3DVAL.validateXml = function (xml, version) {
    if (!state.ready) throw new Error('X3DVAL: load() has not completed');
    return M.xsd.validateXml(xml, version);
  };

  X3DVAL.semanticDiagnostics = function (xml) {
    if (!state.ready) throw new Error('X3DVAL: load() has not completed');
    return M.semantic.semanticDiagnostics(xml);
  };

  X3DVAL.validateSemantic = function (xml) {
    return M.report.renderReport(X3DVAL.semanticDiagnostics(xml));
  };

  X3DVAL.validate = function (xml, opts) {
    if (!state.ready) throw new Error('X3DVAL: load() has not completed');
    opts = opts || {};
    var t0 = now();
    xml = String(xml);
    var xsdRes;
    try {
      xsdRes = M.xsd.validateXml(xml, opts.version);
    } catch (e) {
      // validate.py raises here too (lxml XMLSchemaValidateError 'Internal error in XML Schema validation' when a
      // pattern facet cannot match a long attribute, e.g. a Coordinate point with 71+ numbers that is not a
      // multiple of 3). The fork raises; the port reports it as status 'exception' instead of throwing.
      xsdRes = { valid: false, errors: [], status: 'exception', error: String(e && e.message || e) };
    }
    var sem, semOut;
    try {
      sem = M.semantic.semanticDiagnostics(xml);
    } catch (e) {
      // Python's validate_semantic does not catch this either (e.g. OverflowError in _check_gaussian_splats):
      // the fork raises; the port reports it as status 'exception' instead of hiding it.
      semOut = { status: 'exception', error: String(e && e.message || e), errors: [], warnings: [], info: [], fixes: [], report: '' };
    }
    if (!semOut) {
      var sections = M.report.splitSections(sem.diagnostics);
      semOut = {
        status: sem.status,
        errors: sections.errors, warnings: sections.warnings, info: sections.info, fixes: sections.fixes,
        report: M.report.renderReport(sem)
      };
      if (sem.detail !== undefined) semOut.detail = sem.detail;
    }
    return {
      valid: !!xsdRes.valid && xsdRes.status !== 'exception' && semOut.errors.length === 0 && semOut.status !== 'exception',
      xsd: xsdRes,
      semantic: semOut,
      ms: now() - t0,
      label: X3DVAL.label
    };
  };

  X3DVAL.info = function () {
    return {
      label: X3DVAL.label, ready: state.ready, base: state.base, loadMs: state.loadMs,
      compileMs: M.xsd.state.compileMs, vendor: M.xsd.vendor, checks: M.semantic.ORDER.slice()
    };
  };

  // ---- Worker client -------------------------------------------------------------------
  /**
   * createWorkerClient({base, workerUrl, type}) -> {load(opts), validate(xml, opts), validateXml, validateSemantic,
   *   semanticDiagnostics, info, terminate(), worker}
   * Starts base+'worker.js' as a classic Worker (importScripts + dynamic import()); if that fails to boot,
   * retries it as a module Worker (worker.js supports both). Every call returns a Promise.
   */
  X3DVAL.createWorkerClient = function (opts) {
    opts = opts || {};
    var base = opts.base != null ? String(opts.base) : (SCRIPT_BASE || './');
    if (base && !/\/$/.test(base)) base += '/';
    var workerUrl = opts.workerUrl || (base + 'worker.js');
    var pending = {}, nextId = 1, worker = null, booted = null;

    function attach(w) {
      w.onmessage = function (ev) {
        var m = ev.data || {};
        if (m.type === 'booted') { if (booted) booted.resolve(w); return; }
        var p = pending[m.id];
        if (!p) return;
        if (m.progress) { if (p.onProgress) p.onProgress(m.progress); return; }
        delete pending[m.id];
        if (m.ok) p.resolve(m.result);
        else { var err = new Error(m.error && m.error.message || 'worker error'); err.name = (m.error && m.error.name) || 'Error'; err.workerStack = m.error && m.error.stack; p.reject(err); }
      };
    }
    function boot() {
      if (booted) return booted.promise;
      booted = {};
      booted.promise = new Promise(function (resolve, reject) {
        booted.resolve = resolve;
        var tryType = function (type, next) {
          var w;
          try { w = type ? new Worker(workerUrl, { type: type }) : new Worker(workerUrl); }
          catch (e) { return next ? next() : reject(e); }
          var settled = false;
          w.onerror = function (e) {
            if (settled) return;
            settled = true;
            try { w.terminate(); } catch (e2) { /* ignore */ }
            if (next) next(); else reject(new Error('X3DVAL worker failed to start: ' + (e && e.message || e)));
          };
          attach(w);
          var origResolve = booted.resolve;
          booted.resolve = function (ww) { settled = true; w.onerror = function (e) { for (var id in pending) { pending[id].reject(new Error('X3DVAL worker error: ' + (e && e.message || e))); } pending = {}; }; worker = ww; origResolve(ww); };
        };
        tryType(opts.type || null, opts.type ? null : function () { tryType('module', null); });
      });
      return booted.promise;
    }
    function call(op, args, onProgress) {
      return boot().then(function (w) {
        return new Promise(function (resolve, reject) {
          var id = nextId++;
          pending[id] = { resolve: resolve, reject: reject, onProgress: onProgress };
          w.postMessage({ id: id, op: op, args: args });
        });
      });
    }
    var client = {
      get worker() { return worker; },
      load: function (o) {
        o = o || {};
        return call('load', [{ base: o.base != null ? String(o.base) : base, precompile: o.precompile }], o.onProgress).then(function () { return client; });
      },
      validate: function (xml, o) { return call('validate', [String(xml), o || {}]); },
      validateXml: function (xml, version) { return call('validateXml', [String(xml), version]); },
      validateSemantic: function (xml) { return call('validateSemantic', [String(xml)]); },
      semanticDiagnostics: function (xml) { return call('semanticDiagnostics', [String(xml)]); },
      precompile: function (v) { return call('precompile', [v]); },
      info: function () { return call('info', []); },
      terminate: function () { if (worker) worker.terminate(); worker = null; booted = null; for (var id in pending) pending[id].reject(new Error('terminated')); pending = {}; }
    };
    return client;
  };

  if (typeof G.window !== 'undefined' && G.window && !G.window.X3DVAL) G.window.X3DVAL = X3DVAL;
})((typeof self !== 'undefined' ? self : globalThis).X3DVAL);
