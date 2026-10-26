"""Gemini over the Vertex proxy: streaming (the proxy cuts silent responses at 30 s), retries, spend ledger."""
import json, os, ssl, time, urllib.request, urllib.error, threading
PROJ = os.environ.get('GCP_PROJ', 'key-tokenizer-237718')
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spend.jsonl')
# assumed list prices, USD per 1M tokens (in, out): ASSUMED, logged as such
PRICE = {'gemini-3.8-flash': (0.30, 2.50), 'gemini-3.1-pro': (2.00, 12.00), 'gemini-3.1-pro-preview': (2.00, 12.00)}
_lock = threading.Lock()
CTX = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')

def spent():
    t = 0.0
    if os.path.exists(LEDGER):
        for l in open(LEDGER):
            t += json.loads(l)['usd']
    return t

def call(model, prompt, system=None, temperature=0.2, max_out=16000, json_mode=True, tag='', cap=15.0, retries=4, thinking=None):
    if spent() >= cap:
        raise RuntimeError('spend cap reached')
    url = 'https://aiplatform.googleapis.com/v1/projects/%s/locations/global/publishers/google/models/%s:streamGenerateContent?alt=sse' % (PROJ, model)
    gc = {'temperature': temperature, 'maxOutputTokens': max_out}
    if json_mode: gc['responseMimeType'] = 'application/json'
    gc['thinkingConfig'] = {'includeThoughts': True} if thinking is None else {'thinkingBudget': thinking, 'includeThoughts': True}   # thought parts stream early, which keeps the proxy's 30 s silence cut away
    body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': gc}
    if system: body['systemInstruction'] = {'parts': [{'text': system}]}
    data = json.dumps(body).encode()
    err = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            out = []; tin = tout = 0; t0 = time.time()
            with urllib.request.urlopen(req, timeout=240, context=CTX) as r:
                for raw in r:
                    raw = raw.decode('utf8', 'ignore').strip()
                    if not raw.startswith('data:'): continue
                    j = json.loads(raw[5:])
                    for c in j.get('candidates', []):
                        for p in c.get('content', {}).get('parts', []):
                            if p.get('text') and not p.get('thought'): out.append(p['text'])
                    u = j.get('usageMetadata')
                    if u: tin = u.get('promptTokenCount', tin); tout = (u.get('candidatesTokenCount', 0) + u.get('thoughtsTokenCount', 0)) or tout
            pi, po = PRICE.get(model, (2.0, 12.0))
            usd = tin * pi / 1e6 + tout * po / 1e6
            with _lock:
                open(LEDGER, 'a').write(json.dumps({'t': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'model': model, 'tag': tag, 'tin': tin, 'tout': tout, 'usd': round(usd, 5), 'sec': round(time.time() - t0, 1), 'priced': 'assumed list price'}) + '\n')
            return ''.join(out)
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf8', 'ignore')[:200].replace(PROJ, '<proj>')
            err = 'HTTP %s %s' % (e.code, msg)
            time.sleep(20 * (k + 1) if e.code == 429 else 5 * (k + 1))
        except Exception as e:
            err = repr(e)[:200].replace(PROJ, '<proj>'); time.sleep(5 * (k + 1))
    raise RuntimeError('gemini failed: ' + str(err))

def jcall(*a, **k):
    t = call(*a, **k)
    t = t.strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[1].rsplit('```', 1)[0]
    return json.loads(t)
