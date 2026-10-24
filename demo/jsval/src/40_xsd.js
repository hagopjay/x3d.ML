/* src/40_xsd.js (formerly xsd.js) -- js-port-of-8dd0d3e: XSD validation module.
 *
 * Mirrors validation/validate.py::validate_xml of the x3d_mcp fork at commit 8dd0d3e
 * (schema selection, malformed-XML handling, error-string formatting, version hints,
 * GeoLOD content-model hint) on top of libxml2-wasm 0.7.2 (same libxml2 lineage as lxml).
 * This is a port, not the fork itself: label 'js-port-of-8dd0d3e'.
 *
 * Classic script: defines (self|globalThis).X3DVAL._m.xsd. Works via <script>, importScripts()
 * in a Worker, and under Node (see the inline shim in harness/xsd_check.mjs). No eval / new Function; the only
 * dynamic code is WebAssembly.instantiate inside the vendor bundle ('wasm-unsafe-eval').
 *
 *   await X3DVAL._m.xsd.load({base})          // base: URL of the jsval/ directory (trailing slash)
 *   X3DVAL._m.xsd.validateXml(xml, version)   // -> {valid, errors:[str], schema_version?, notes?}
 *
 * load() fetches vendor/libxml2-wasm.bundle.mjs (dynamic import), data/schemas/*.xsd (7 files,
 * byte-identical to the fork) and data/nodes-4.0.json / data/nodes-4.1.json. Schemas compile
 * lazily per version on first use (2-4 s each) unless {precompile:['4.0']} is passed.
 */
(function () {
  'use strict';
  var G = typeof self !== 'undefined' ? self : (typeof globalThis !== 'undefined' ? globalThis : this);
  var X3DVAL = G.X3DVAL || (G.X3DVAL = { label: 'js-port-of-8dd0d3e', _m: {} });
  if (!X3DVAL._m) X3DVAL._m = {};
  var M = X3DVAL._m.xsd = {};

  // ---- constants mirroring validate.py -------------------------------------------------
  var DEFAULT_XSD_VERSION = '4.1';
  var XSD_PATHS = { '4.0': 'x3d-4.0.xsd', '4.1': 'x3d-4.1.xsd' };
  var LEGACY_VERSIONS = { '3.0': 1, '3.1': 1, '3.2': 1, '3.3': 1 };
  var XSI_NS = 'https://www.w3.org/2001/XMLSchema-instance'; // HTTPS on purpose (validate.py XSI_NS)
  var SCHEMA_FILES = [
    'x3d-4.0.xsd', 'x3d-4.1.xsd',
    'x3d-4.0-Web3dExtensionsPublic.xsd', 'x3d-4.0-Web3dExtensionsPrivate.xsd',
    'x3d-4.1-Web3dExtensionsPublic.xsd', 'x3d-4.1-Web3dExtensionsPrivate.xsd',
    'xmldsig-core-schema.xsd'
  ];
  var NODE_LIST_VERSIONS = ['4.0', '4.1'];
  // lxml default parser: NOENT|NOCDATA|NONET|COMPACT|BIG_LINES (validate.py uses etree.fromstring)
  M.XSD_OPTS = 2 | 16384 | 2048 | 65536 | 4194304;
  // semantic.py _PARSER: huge_tree=True, resolve_entities=False -> NOCDATA|NONET|COMPACT|BIG_LINES|HUGE
  M.SEM_OPTS = 16384 | 2048 | 65536 | 4194304 | 524288;
  var XML_ERR_ERROR = 2;

  var MISSING_CHILD_RE = /Element '([A-Za-z0-9_]+)': Missing child element/;

  var ENC = typeof TextEncoder !== 'undefined' ? new TextEncoder() : null;
  var DEC = typeof TextDecoder !== 'undefined' ? new TextDecoder('utf-8') : null;
  var now = (typeof performance !== 'undefined' && performance.now) ? function () { return performance.now(); } : function () { return Date.now(); };

  var state = {
    base: null, lib: null, bufs: null, provider: null, validators: {}, nodesByVersion: null,
    compileMs: {}, loadMs: null, bytes: { vendor: null, schemas: 0, nodes: 0 }, loadPromise: null
  };
  M.state = state;

  // ---- helpers --------------------------------------------------------------------------
  function stripNl(s) { return s.replace(/\n$/, ''); }

  function fetchBytes(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('X3DVAL xsd: fetch ' + url + ' -> HTTP ' + r.status);
      return r.arrayBuffer();
    }).then(function (ab) { return new Uint8Array(ab); });
  }
  function defaultImporter(url) { return import(url); }
  function utf8(u8) { return DEC ? DEC.decode(u8) : String.fromCharCode.apply(null, u8); }

  /** Directory URL of this script (document.currentScript in a page, location in a worker). */
  M.defaultBase = function () {
    try {
      if (typeof document !== 'undefined' && document.currentScript && document.currentScript.src) {
        return document.currentScript.src.replace(/[^/]*$/, '');
      }
    } catch (e) { /* ignore */ }
    if (typeof location !== 'undefined' && location.href) return location.href.replace(/[^/]*$/, '');
    return './';
  };

  /** Shared loader for the libxml2-wasm bundle, reused by the semantic parser module. */
  M.loadLib = function (base, importer, lib) {
    var shared = X3DVAL._m.libxml2 || (X3DVAL._m.libxml2 = { promise: null, lib: null, url: null });
    if (lib) { shared.lib = lib; shared.promise = Promise.resolve(lib); }
    if (shared.promise) return shared.promise;
    var url = base + 'vendor/libxml2-wasm.bundle.mjs';
    shared.url = url;
    shared.promise = Promise.resolve((importer || defaultImporter)(url)).then(function (lib) {
      shared.lib = lib;
      return lib;
    });
    return shared.promise;
  };

  /** resolve_xsd_version(declared) -> [schema_version, note|null] */
  M.resolveVersion = function (declared) {
    if (declared !== null && declared !== undefined && Object.prototype.hasOwnProperty.call(XSD_PATHS, declared)) return [declared, null];
    if (declared !== null && declared !== undefined && Object.prototype.hasOwnProperty.call(LEGACY_VERSIONS, declared)) {
      return ['4.0', 'X3D ' + declared + ' has no bundled schema; validated against X3D 4.0, of which X3D ' + declared + ' is a subset.'];
    }
    if (declared === null || declared === undefined || declared === '') {
      return [DEFAULT_XSD_VERSION, 'No version attribute; validated against X3D ' + DEFAULT_XSD_VERSION + '.'];
    }
    return [DEFAULT_XSD_VERSION, "Unknown version '" + declared + "'; validated against X3D " + DEFAULT_XSD_VERSION + '.'];
  };

  /** str(XMLSyntaxError) as lxml builds it: first error of level >= ERROR -> "msg[, line L[, column C]] (<string>, line L)". */
  M.parseErrorString = function (e) {
    var details = (e && e.details) || [];
    var d = null;
    for (var i = 0; i < details.length; i++) { if (details[i].level >= XML_ERR_ERROR) { d = details[i]; break; } }
    if (!d) d = details[0];
    if (!d) return stripNl(String(e && e.message || e)) + ' (<string>, line 0)';
    var msg = stripNl(d.message), line = d.line || 0, col = d.col || 0;
    if (line > 0) msg += col > 0 ? ', line ' + line + ', column ' + col : ', line ' + line;
    return msg + ' (<string>, line ' + line + ')';
  };

  /** Parse like lxml's default parser (XSD pass) or semantic.py's parser; throws XmlParseError. */
  M.parse = function (xml, opts) {
    var L = state.lib;
    if (!L) throw new Error('X3DVAL xsd: load() has not completed');
    var bytes = (xml instanceof Uint8Array) ? xml : ENC.encode(String(xml));
    // fromBuffer(empty) -> "Document is empty" like lxml; fromString('') would give a detail-less error
    return L.XmlDocument.fromBuffer(bytes, { option: opts === undefined ? M.XSD_OPTS : opts });
  };

  function stripXsi(root) {
    // _strip_xsi: delete root attributes whose lxml key "{uri}name" contains XSI_NS (the https form)
    var attrs = root.attrs;
    for (var i = 0; i < attrs.length; i++) {
      var ns = attrs[i].namespaceUri || '';
      if (ns.indexOf(XSI_NS) !== -1) attrs[i].remove();
    }
  }

  function attrValue(el, name) {
    var a = el.attr(name); // non-namespaced lookup, like lxml el.get(name)
    return a ? a.value : null;
  }

  /** All elements in document order, root first (lxml doc.iter() minus comments/PIs). */
  function allElements(root) {
    return root.find('descendant-or-self::*');
  }

  function versionHints(root, schemaVersion) {
    var nodes = state.nodesByVersion;
    var knownHere = nodes[schemaVersion];
    var hints = [], seen = {};
    var els = allElements(root);
    var laterVersions = NODE_LIST_VERSIONS.filter(function (v) { return v > schemaVersion; }).sort();
    for (var i = 0; i < els.length; i++) {
      var tag = els[i].name; // local name
      if (!tag || knownHere[tag] || seen[tag]) continue;
      var later = laterVersions.filter(function (v) { return nodes[v][tag]; });
      if (later.length) {
        seen[tag] = true;
        hints.push("Node '" + tag + "' is not in X3D " + schemaVersion + '; it was added in X3D ' + later[0] +
          ". Declare version='" + later[0] + "' or remove the node.");
      }
    }
    return hints;
  }

  function geolodHint(el) {
    var geoSystem = attrValue(el, 'geoSystem'); if (geoSystem === null) geoSystem = '"GD" "WE"';
    var center = attrValue(el, 'center'); if (center === null) center = '0 0 0';
    return 'GeoLOD at line ' + el.line + ": the bundled XSD's content model is " +
      '(rootNode children, GeoOrigin, rootNode children), so any inline rootNode ' +
      'child requires a GeoOrigin sibling, although ISO/IEC 19775-1 makes geoOrigin ' +
      "optional. Either add <GeoOrigin containerField='geoOrigin' " +
      "geoSystem='" + geoSystem + "' geoCoords='" + center + "'/> inside the GeoLOD (a " +
      'GeoOrigin re-anchors the local frame, so give every geospatial node the same ' +
      'one by USE), or remove the inline children and load the low-detail model ' +
      'through rootUrl.';
  }
  var CONTENT_MODEL_HINTS = { GeoLOD: geolodHint };

  function contentModelHints(root, errors) {
    var hints = [], seen = {};
    for (var i = 0; i < errors.length; i++) {
      var m = MISSING_CHILD_RE.exec(errors[i]);
      if (!m || seen[m[1]] || !Object.prototype.hasOwnProperty.call(CONTENT_MODEL_HINTS, m[1])) continue;
      seen[m[1]] = true;
      var tag = m[1];
      var els = allElements(root);
      for (var j = 0; j < els.length; j++) {
        if (els[j].name === tag) { hints.push(CONTENT_MODEL_HINTS[tag](els[j])); break; }
      }
    }
    return hints;
  }

  // ---- loading --------------------------------------------------------------------------
  /**
   * load({base, read, importer, precompile, onProgress}) -> Promise<M>
   *   base       directory URL of jsval/ (default: this script's directory)
   *   read(url)  -> Promise<Uint8Array>   (default: fetch; Node shim passes fs)
   *   importer(url) -> Promise<module>   (default: dynamic import())
   *   lib        an already-imported libxml2-wasm module to reuse instead of importing the bundle
   *   precompile ['4.0'] | ['4.0','4.1'] | true (both) -- compile eagerly inside load()
   *   onProgress({stage, ...})
   */
  M.load = function (opts) {
    opts = opts || {};
    if (state.loadPromise) return state.loadPromise;
    var base = opts.base != null ? String(opts.base) : M.defaultBase();
    if (base && !/\/$/.test(base)) base += '/';
    state.base = base;
    var read = opts.read || fetchBytes;
    var importer = opts.importer || defaultImporter;
    var progress = typeof opts.onProgress === 'function' ? opts.onProgress : function () {};
    var t0 = now();
    state.loadPromise = Promise.all([
      M.loadLib(base, importer, opts.lib).then(function (lib) { progress({ stage: 'lib', ms: now() - t0 }); return lib; }),
      Promise.all(SCHEMA_FILES.map(function (f) { return read(base + 'data/schemas/' + f).then(function (u8) { return [f, u8]; }); })),
      Promise.all(NODE_LIST_VERSIONS.map(function (v) { return read(base + 'data/nodes-' + v + '.json').then(function (u8) { return [v, u8]; }); }))
    ]).then(function (r) {
      var lib = r[0], schemas = r[1], nodeLists = r[2];
      state.lib = lib;
      var bufs = {};
      schemas.forEach(function (p) { bufs['schemas/' + p[0]] = p[1]; state.bytes.schemas += p[1].byteLength; });
      state.bufs = bufs;
      var nodes = {};
      nodeLists.forEach(function (p) {
        var set = {}; JSON.parse(utf8(p[1])).forEach(function (n) { set[n] = true; });
        nodes[p[0]] = set; state.bytes.nodes += p[1].byteLength;
      });
      state.nodesByVersion = nodes;
      // xs:include / xs:import schemaLocations resolve against the main doc's url 'schemas/x3d-4.x.xsd'
      var shared = X3DVAL._m.libxml2;
      if (shared.provider) {
        for (var k in bufs) shared.provider.addBuffer(k, bufs[k]);
        state.provider = shared.provider;
      } else {
        state.provider = new lib.XmlBufferInputProvider(bufs);
        if (!lib.xmlRegisterInputProvider(state.provider)) throw new Error('X3DVAL xsd: xmlRegisterInputProvider refused (callback table full)');
        shared.provider = state.provider;
      }
      progress({ stage: 'data', ms: now() - t0, schemaBytes: state.bytes.schemas });
      var pre = opts.precompile === true ? ['4.0', '4.1'] : (Array.isArray(opts.precompile) ? opts.precompile : []);
      pre.forEach(function (v) { M.compile(v); progress({ stage: 'compile', version: v, ms: state.compileMs[v] }); });
      state.loadMs = now() - t0;
      return M;
    });
    return state.loadPromise;
  };

  /** Compile (once) and return the XsdValidator for a bundled schema version. Returns elapsed ms via state.compileMs. */
  M.compile = function (version) {
    if (state.validators[version]) return state.validators[version];
    if (!Object.prototype.hasOwnProperty.call(XSD_PATHS, version)) throw new Error('X3DVAL xsd: no bundled schema for version ' + version);
    var L = state.lib;
    var key = 'schemas/' + XSD_PATHS[version];
    var t0 = now();
    var sdoc = L.XmlDocument.fromBuffer(state.bufs[key], { url: key });
    try {
      state.validators[version] = L.XsdValidator.fromDoc(sdoc);
    } finally {
      sdoc.dispose();
    }
    state.compileMs[version] = now() - t0;
    return state.validators[version];
  };

  M.isReady = function () { return !!state.lib; };

  // ---- validate_xml ---------------------------------------------------------------------
  /**
   * validateXml(xml, version?) -> validate.py result dict:
   *   parse failure: {valid:false, errors:["XML parse error: <msg>, line L, column C (<string>, line L)"]}
   *   otherwise:     {valid, errors:["Line L: <libxml2 message>"...], schema_version, notes?}
   */
  M.validateXml = function (xml, version) {
    var L = state.lib;
    if (!L) throw new Error('X3DVAL xsd: load() has not completed');
    var doc;
    try {
      doc = M.parse(xml, M.XSD_OPTS);
    } catch (e) {
      if (e instanceof L.XmlParseError) return { valid: false, errors: ['XML parse error: ' + M.parseErrorString(e)] };
      throw e;
    }
    try {
      var root = doc.root;
      stripXsi(root);
      var declared = version ? String(version) : attrValue(root, 'version');
      var rv = M.resolveVersion(declared);
      var schemaVersion = rv[0];
      var notes = rv[1] ? [rv[1]] : [];
      var validator = M.compile(schemaVersion);
      var valid = true, errors = [];
      try {
        validator.validate(doc);
      } catch (e) {
        if (!(e instanceof L.XmlValidateError)) throw e;
        valid = false;
        var det = e.details;
        for (var i = 0; i < det.length; i++) errors.push('Line ' + det[i].line + ': ' + stripNl(det[i].message));
      }
      if (!valid) {
        Array.prototype.push.apply(notes, versionHints(root, schemaVersion));
        Array.prototype.push.apply(notes, contentModelHints(root, errors));
      }
      var result = { valid: valid, errors: errors, schema_version: schemaVersion };
      if (notes.length) result.notes = notes;
      return result;
    } finally {
      doc.dispose();
    }
  };

  M.label = 'js-port-of-8dd0d3e';
  M.vendor = { name: 'libxml2-wasm', version: '0.7.2', file: 'vendor/libxml2-wasm.bundle.mjs' };
  M.SCHEMA_FILES = SCHEMA_FILES;
})();
