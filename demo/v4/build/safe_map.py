"""safe_map.py: the SAFE map for the SHARE build of Tether Firehose 4 (SPEC-v4 section 15; owner's word 29 Oct: "simplest leak sweep").
One text transform, applied by build_v4.py --share to every decoded part, data/*.json, hero.json, the physics ledger and the baked page
(the JS bundle included, so code that compares a provider string stays consistent with the data it reads). Nothing is hard-coded per
page: the model ids come from the data itself, in first-seen order (live.json meta, replay, run24), and become stable lane labels.

Shape (SafeMap.shape()):
  lanes      {model id: "lane-A" ...}            ids and their model_dir forms (slash -> underscore) both map to the label
  providers  {"vertex": "hosted", "openai": "hosted", "nvidia": "open-weights"}   quoted provider strings and the `prov!=="nvidia"` checks
  hardware   the g2-standard / GPU / serving-stack / region strings -> "redacted (cloud GPU, serving stack, region)"
  branches   (feat|fix|perf|claude)/<name> -> "branch-redacted"
  people     HagopJay -> "the owner"; x3d.ML -> "this project"; claude.ai/artifact/ links -> ""
  vendors    leftover vendor / model words (gemini, openai, nemotron, nvidia, minimax, z-ai, glm, qwen, gpt-oss, gpt-6 ...) -> "vendor"
  costs      non-zero "rc" (replay run-cost estimates) -> 0; Apple M* / macOS / loadavg strings in the ledger env block -> redacted
  fields     modelTierApplied / modelApplied (sample-capability field names in dormant private-tier code) -> mTierApplied / mApplied
Long base64 runs (>= 120 chars: thumbnails) are never touched. apply() is pure; sha() is the sha256 of the rule list (BUILD.safe_map_sha)."""
import re, json, hashlib
B64 = re.compile(r"[A-Za-z0-9+/=]{120,}")
VENDOR_WORDS = r"gemini|openai|chatgpt|nemotron|nvidia|minimaxai|minimax|z-ai|glm|qwen[\w.-]*|gpt-oss[\w-]*|gpt-?\d[\w.-]*|anthropic|deepmind|alibaba|kimi|deepseek|moonshotai|moonshot|stepfun|poolside|mistralai|mistral|llama|gemma|cohere|meta-llama"
class SafeMap:
    def __init__(self, model_ids, providers=None):
        self.lanes = {}
        for i, m in enumerate(model_ids):
            if m not in self.lanes: self.lanes[m] = "lane-" + chr(65 + len(self.lanes))
        self.providers = providers or {"vertex": "hosted", "openai": "hosted", "nvidia": "open-weights", "google": "hosted"}
        rules = []
        # 1. model ids (longest first; the model_dir form with the slash replaced too), word-bounded so prefixes never match inside other ids
        for m, lab in sorted(self.lanes.items(), key=lambda kv: -len(kv[0])):
            for form in sorted({m, m.replace("/", "_")}, key=len, reverse=True):
                rules.append((re.compile(r"(?<![\w.-])" + re.escape(form) + r"(?![\w.-])"), lab, "lane " + form))
        # 2. providers: quoted data strings and the code's string compares
        for p, to in self.providers.items():
            rules.append((re.compile(r'(?<=["\'])' + re.escape(p) + r'(?=["\'])'), to, "provider " + p))
        # 3. hardware / region / serving stack
        rules.append((re.compile(r"g2-standard-\d+[^\"\\\n]*?(?:us-central1|us-east1)"), "redacted (cloud GPU, serving stack, region)", "hardware string"))
        rules.append((re.compile(r"(?i)g2-standard-\d+|\bNVIDIA L4 24 GB\b|us-central1|us-east1"), "redacted", "hardware / region"))
        rules.append((re.compile(r"\bvllm_l4\b"), "serving-stack", "serving stack id"))
        rules.append((re.compile(r"\bvLLM\b( \d[\w.]*)?"), "serving stack", "serving stack name"))
        # 4. branches, people, private links
        rules.append((re.compile(r"(?i)\b(feat|fix|perf|claude)/[a-z0-9][a-z0-9-]*"), "branch-redacted", "branch name"))
        rules.append((re.compile(r"(?i)hagopjay"), "the owner", "person"))
        rules.append((re.compile(r"x3d\.ML"), "this project", "project host"))
        rules.append((re.compile(r"https://claude\.ai/artifact/[A-Za-z0-9]*"), "", "private artifact link"))
        # 5. costs and the ledger's environment block
        rules.append((re.compile(r'"rc":(?!0[,}])[0-9.]+'), '"rc":0', "replay run-cost estimate"))
        rules.append((re.compile(r"(?i)apple m\d[\w ]*?(?=&quot;|\"|,)"), "cpu-redacted", "cpu string"))
        rules.append((re.compile(r"(?i)macos"), "os-redacted", "os string"))
        rules.append((re.compile(r"(?i)loadavg(_1m)?"), "load-redacted", "load string"))
        # 6. dormant sample-capability field names
        rules.append((re.compile(r"modelTierApplied"), "mTierApplied", "sample field"))
        rules.append((re.compile(r"modelApplied"), "mApplied", "sample field"))
        # 6b. the host product in prose and local render paths (the runtime API forms window.claude / claude.use are allowed by the sweep and untouched)
        rules.append((re.compile(r"claude\.ai artifact"), "artifact", "host prose"))
        rules.append((re.compile(r"(?<![\w.])Claude\b"), "the assistant", "host prose"))
        rules.append((re.compile(r"/tmp/claude-0/[^\"\s]*"), "render-path-redacted", "local render path"))
        rules.append((re.compile(r"(?<![\w.])claude(?![\w.:])"), "host", "host word"))   # 'claude (viewer)' labels, comments, embedded regex text; window.claude / claude.use keep their dots
        # 7. leftover vendor / model words in prose (after the ids, so a label never carries one)
        rules.append((re.compile(r"(?i)\b(" + VENDOR_WORDS + r")\b"), "vendor", "vendor word"))
        rules.append((re.compile(r"(?i)\bgoogle\b"), "vendor", "vendor word"))
        self.rules = rules
        self.counts = {}
    def _seg(self, s):
        for rx, to, note in self.rules:
            s, n = rx.subn(to, s)
            if n: self.counts[note] = self.counts.get(note, 0) + n
        return s
    def apply(self, text):
        out = []; pos = 0
        for m in B64.finditer(text):
            out.append(self._seg(text[pos:m.start()])); out.append(m.group(0)); pos = m.end()
        out.append(self._seg(text[pos:])); return "".join(out)
    def shape(self):
        return {"lanes": sorted(self.lanes.values()), "providers": self.providers, "rules": [n for _, _, n in self.rules if n not in ("lane",)], "n_rules": len(self.rules)}
    def sha(self):
        return hashlib.sha256(json.dumps([(r.pattern, to, n) for r, to, n in self.rules], sort_keys=True).encode()).hexdigest()
