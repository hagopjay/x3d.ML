/* js-port-of-8dd0d3e -- parser + tree snapshot helpers (X3DVAL._m.t).
 * The libxml2-wasm module (vendor/libxml2-wasm.bundle.mjs) is injected with setLib()
 * because the bundle is an ES module (top-level await) and this file is a classic script.
 * Checks never touch the libxml2 DOM: parseDoc() + snapshot() turn it into a plain JS
 * tree mirroring what lxml exposes (children = element|comment|PI|entity-ref, no text),
 * and the libxml2 document is disposed right away.
 */
(function (X3DVAL) {
  var lib = null;
  var nextGetter = null;

  function setLib(l) {
    lib = l;
    // XmlProcessingInstructionNode is not an XmlTreeNode (no .next); the prototype getter
    // only reads this._nodePtr, so applying it to any node continues a sibling walk past PIs
    // and still yields entity-reference nodes (XPath child::node() drops those).
    nextGetter = Object.getOwnPropertyDescriptor(l.XmlTreeNode.prototype, 'next').get;
  }
  function getLib() { return lib; }

  // libxml2 parser flags (same values as lxml's): lxml default parser vs semantic.py _PARSER.
  var PO = { NOENT: 2, NONET: 2048, NOCDATA: 16384, COMPACT: 65536, HUGE: 524288, BIG_LINES: 4194304 };
  var XSD_OPTS = PO.NOENT | PO.NOCDATA | PO.NONET | PO.COMPACT | PO.BIG_LINES;
  var SEM_OPTS = PO.NOCDATA | PO.NONET | PO.COMPACT | PO.BIG_LINES | PO.HUGE;

  var encoder = typeof TextEncoder !== 'undefined' ? new TextEncoder() : null;
  function parseDoc(xml, opts) {
    if (!lib) throw new Error('X3DVAL: libxml2-wasm not loaded (call X3DVAL.load first)');
    var buf = encoder.encode(String(xml));          // empty input -> "Document is empty" like lxml
    return lib.XmlDocument.fromBuffer(buf, { option: opts === undefined ? SEM_OPTS : opts });
  }
  // str(etree.XMLSyntaxError) as lxml builds it (_ErrorLog._buildParseException + SyntaxError.__str__):
  // message of the FIRST log entry with level >= XML_ERR_ERROR (2), one trailing "\n" removed;
  // ", line L, column C" when column > 0, ", line L" when only line > 0; then " (<string>, line L)".
  function parseErrorString(e) {
    var details = (e && e.details) || [];
    var d = null;
    for (var i = 0; i < details.length; i++) { if (details[i].level >= 2) { d = details[i]; break; } }
    if (!d) d = details[0];
    if (!d) return String(e && e.message || e).replace(/\n$/, '') + ' (<string>, line 0)';
    var msg = String(d.message).replace(/\n$/, '');
    var line = d.line || 0, col = d.col || 0;
    if (line > 0) msg += col > 0 ? ', line ' + line + ', column ' + col : ', line ' + line;
    return msg + ' (<string>, line ' + line + ')';
  }

  function mkElement(el, parent) {
    var attrs = el.attrs, pairs = new Array(attrs.length), a = Object.create(null);
    for (var i = 0; i < attrs.length; i++) {
      var at = attrs[i], uri = at.namespaceUri, v = at.value;
      if (uri) pairs[i] = ['{' + uri + '}' + at.name, v];
      else { pairs[i] = [at.name, v]; a[at.name] = v; }
    }
    return { tag: el.name, ns: el.namespaceUri || '', attrs: pairs, a: a, children: [], parent: parent, line: el.line, kind: 'element' };
  }
  function mkOther(n, parent, kind) {
    return { tag: '', ns: '', attrs: [], a: Object.create(null), children: [], parent: parent, line: n.line, kind: kind };
  }
  // Snapshot the document element into a plain tree (iterative: deep documents must not overflow the stack).
  function snapshot(doc) {
    var XmlElement = lib.XmlElement, XmlText = lib.XmlText, XmlCData = lib.XmlCData;
    var XmlComment = lib.XmlComment, XmlEntityReference = lib.XmlEntityReference;
    var root = doc.root;
    var top = mkElement(root, null);
    var stack = [root, top];
    while (stack.length) {
      var sn = stack.pop(), xn = stack.pop();
      for (var c = xn.firstChild; c; c = nextGetter.call(c)) {
        if (c instanceof XmlElement) { var s = mkElement(c, sn); sn.children.push(s); stack.push(c, s); }
        else if (c instanceof XmlText || c instanceof XmlCData) continue;   // lxml: text is not a child
        else if (c instanceof XmlComment) sn.children.push(mkOther(c, sn, 'comment'));
        else if (c instanceof XmlEntityReference) sn.children.push(mkOther(c, sn, 'entityref'));
        else sn.children.push(mkOther(c, sn, 'pi'));
      }
    }
    return top;
  }
  function parseSnapshot(xml, opts) {
    var doc = parseDoc(xml, opts);
    try { return snapshot(doc); } finally { doc.dispose(); }
  }

  function localTag(n) { return n.tag; }
  // el.iter(): preorder including el itself and ''-tag (comment/PI/entity) nodes.
  function iter(n) {
    var stack = [n];
    return {
      [Symbol.iterator]: function () { return this; },
      next: function () {
        if (!stack.length) return { done: true, value: undefined };
        var x = stack.pop(), ch = x.children;
        for (var i = ch.length - 1; i >= 0; i--) stack.push(ch[i]);
        return { done: false, value: x };
      }
    };
  }
  // el.iter("Tag") (non-namespaced only) or el.iter("Tag", "{*}Tag") with anyNs=true.
  function iterTag(n, name, anyNs) {
    var it = iter(n);
    return {
      [Symbol.iterator]: function () { return this; },
      next: function () {
        for (;;) {
          var r = it.next();
          if (r.done) return r;
          var x = r.value;
          if (x.tag === name && (anyNs || x.ns === '')) return r;
        }
      }
    };
  }
  function children(n) { return n.children; }
  function len(n) { return n.children.length; }
  function elementChildren(n) { return n.children.filter(function (c) { return c.kind === 'element'; }); }
  // el.get(attr[, default]) -- non-namespaced attribute, null when absent (Python None).
  function get(n, attr, def) {
    var a = n.a;
    return (attr in a) ? a[attr] : (def === undefined ? null : def);
  }
  // _find_scene: root itself if its local tag is Scene, else first descendant (preorder) with local tag Scene.
  function findScene(root) {
    for (var el of iter(root)) if (el.tag === 'Scene') return el;
    return null;
  }

  X3DVAL._m.t = {
    setLib: setLib, lib: getLib, PO: PO, XSD_OPTS: XSD_OPTS, SEM_OPTS: SEM_OPTS,
    parseDoc: parseDoc, parseErrorString: parseErrorString, snapshot: snapshot, parseSnapshot: parseSnapshot,
    localTag: localTag, iter: iter, iterTag: iterTag, children: children, len: len,
    elementChildren: elementChildren, get: get, findScene: findScene
  };
})((typeof self !== 'undefined' ? self : globalThis).X3DVAL);
