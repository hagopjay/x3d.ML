"""Streaming chat client for the recorded live run: Gemini on Vertex, OpenAI and NVIDIA through the container's credential-injecting proxy (no key in this file).
Streaming keeps the proxy's 30 s whole-response cap from cutting long generations. Every call goes through the ledger: the worst case is reserved before the call and the
usage-based charge is written before the text is returned. Env GCP_PROJECT names the Vertex project (never committed)."""
import json, os, subprocess, threading, time, requests
from ledger import Budget, BudgetStop, price

CA = os.environ.get("CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
_tok = {"t": None, "at": 0.0}; _lk = threading.Lock()


class CallError(Exception):
    def __init__(self, msg, status=None, retry=False, billable=False, partial=0):
        super().__init__(msg); self.status, self.retry, self.billable, self.partial = status, retry, billable, partial     # billable: HTTP 200 was received, so the model may have run


def _gtoken():
    with _lk:
        if time.time() - _tok["at"] > 2400:
            _tok["t"] = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip(); _tok["at"] = time.time()
        return _tok["t"]


def _sse(r):
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            d = line[5:].strip()
            if d == "[DONE]": return
            try: yield json.loads(d)
            except Exception: pass


MAX_WALL = float(os.environ.get("CALL_MAX_WALL_S", "420"))     # a stream that keeps trickling bytes past this is cut and retried


def _once(provider, model, messages, max_out, temp):
    """One streaming call. Returns dict(text, tin, tout, finish, t0, t1, ms). Raises CallError."""
    t0 = time.time(); txt = []; tin = tout = 0; finish = None
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    turns = [m for m in messages if m["role"] != "system"]
    if provider in ("openai", "nvidia"):
        url = "https://api.openai.com/v1/chat/completions" if provider == "openai" else "https://integrate.api.nvidia.com/v1/chat/completions"
        body = {"model": model, "messages": messages, "stream": True, "stream_options": {"include_usage": True}}
        body["max_completion_tokens" if provider == "openai" else "max_tokens"] = max_out
        if temp is not None: body["temperature"] = temp
        r = requests.post(url, json=body, stream=True, timeout=(20, 150), verify=CA)
        if r.status_code != 200: raise CallError(f"{r.status_code} {r.text[:300]}", r.status_code, r.status_code in (429, 500, 502, 503, 504) and "insufficient_quota" not in r.text)   # an empty account is not worth retrying
        try:
            for d in _sse(r):
                if time.time() - t0 > MAX_WALL: r.close(); raise CallError(f"stream exceeded {MAX_WALL:.0f}s", None, True)
                if d.get("usage"): tin = d["usage"].get("prompt_tokens", 0); tout = d["usage"].get("completion_tokens", 0)
                for c in d.get("choices") or []:
                    x = (c.get("delta") or {}).get("content")
                    if x: txt.append(x)
                    if c.get("finish_reason"): finish = c["finish_reason"]
        except (requests.RequestException, CallError) as e:
            raise CallError(type(e).__name__ + " " + str(e)[:160], None, True, True, len("".join(txt)))
    elif provider == "vertex":
        proj = os.environ["GCP_PROJECT"]
        url = f"https://aiplatform.googleapis.com/v1/projects/{proj}/locations/global/publishers/google/models/{model}:streamGenerateContent?alt=sse"
        gc = {"maxOutputTokens": max_out}
        if temp is not None: gc["temperature"] = temp
        if os.environ.get("VERTEX_THOUGHTS", "1") == "1": gc["thinkingConfig"] = {"includeThoughts": True}      # thought summaries stream early and keep the connection from idling (a long silent think ended in 502); they are not kept
        body = {"contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in turns], "generationConfig": gc}
        if system: body["systemInstruction"] = {"parts": [{"text": system}]}
        r = requests.post(url, json=body, stream=True, timeout=(20, 150), verify=CA, headers={"Authorization": "Bearer " + _gtoken()})
        if r.status_code != 200: raise CallError(f"{r.status_code} {r.text[:300]}", r.status_code, r.status_code in (429, 500, 502, 503, 504))
        try:
            for d in _sse(r):
                if time.time() - t0 > MAX_WALL: r.close(); raise CallError(f"stream exceeded {MAX_WALL:.0f}s", None, True)
                u = d.get("usageMetadata")
                if u: tin = u.get("promptTokenCount", 0); tout = u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
                for c in d.get("candidates") or []:
                    for p in (c.get("content") or {}).get("parts") or []:
                        if p.get("text") and not p.get("thought"): txt.append(p["text"])
                    if c.get("finishReason"): finish = c["finishReason"]
        except (requests.RequestException, CallError) as e:
            raise CallError(type(e).__name__ + " " + str(e)[:160], None, True, True, len("".join(txt)))
    else:
        raise ValueError(provider)
    t1 = time.time()
    return {"text": "".join(txt), "tin": tin, "tout": tout, "finish": finish, "t0": t0, "t1": t1, "ms": int((t1 - t0) * 1000)}


def call(budget, provider, model, messages, tag, max_out=8000, temp=None, tries=None, **extra):
    """Reserve, call (retrying 429/5xx), charge, return. A charge row is written for every call that returned usage; a call that fails after the model ran but returned no usage is
    charged by character count (3.5 chars per token, marked est) so the ledger never under-reports."""
    tries = tries or (6 if provider == "nvidia" else 3)
    tin_est = sum(len(m["content"]) for m in messages) // 3 + 1
    worst = budget.reserve(model, provider, tin_est, max_out)
    err = None
    for k in range(tries):
        try:
            res = _once(provider, model, messages, max_out, temp)
            if not res["tin"] and not res["tout"]:      # no usage reported: estimate and say so
                res["tin"], res["tout"] = tin_est, len(res["text"]) // 3; extra = {**extra, "est": True}
            res["usd"] = budget.charge(worst, model, provider, tag, res["tin"], res["tout"], ms=res["ms"], finish=res["finish"], **extra)
            return res
        except CallError as e:
            err = e
            if e.billable:     # the model had started: a paid provider bills what it produced, so charge an estimate (3.5 chars per token; NVIDIA prices at 0)
                budget.charge(0.0, model, provider, tag, tin_est, max(e.partial // 3, 1), err=str(e)[:120], est=True, **extra)
            if not e.retry or k == tries - 1: break
            time.sleep(min(60, 5 * 2 ** k) if e.status == 429 else 4 * (k + 1))     # rate limits (the free NVIDIA tier) back off harder
        except requests.RequestException as e:      # connection cut: the model may have run; treat as retryable
            err = CallError(type(e).__name__ + " " + str(e)[:200], None, True)
            if k == tries - 1: break
            time.sleep(4 * (k + 1))
    budget.charge(worst, model, provider, tag, 0, 0, err=str(err)[:200], **extra)     # failed call: 0 tokens known, row kept for the record
    raise err


def strip_x3d(t):
    """Same extraction as the 11 Oct GPU-phase harness: drop fences and anything outside <X3D ... </X3D>."""
    t = (t or "").strip()
    if t.startswith("```"): t = t.split("\n", 1)[1].rsplit("```", 1)[0]
    i = t.find("<X3D")
    if i < 0: return t
    j = t.rfind("</X3D>")
    return t[i:j + 6] if j > i else t[i:]
