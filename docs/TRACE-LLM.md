# x3dtrace on LLM traces (`src/x3dtrace_llm.py`)

An LLM that is asked to cite returns, beside its answer, claims in x3dtrace's own shape: `{field, value, quote, source}`. The trace (Langfuse, LangSmith, OpenTelemetry GenAI) already records what the model read:
- the documents a retriever returned;
- the outputs of tool calls.

`x3dtrace_llm` turns those into sources and runs `check_claims` on every generation's citations. As everywhere in x3dtrace, no model is involved: FIND, COMPARE and LOCATE are plain code.

```bash
python3 -I src/x3dtrace_llm.py tests/fixtures/llm-trace/langfuse-rag-support-agent.synthetic.json
```

| input | taken as |
|---|---|
| Langfuse export `{trace, observations: {data: [ObservationV2]}, scores}`, or a bare list of ObservationV2 | observations |
| `RETRIEVER` output `documents[]` with `id` and `text` | one source per document id |
| `TOOL` output (level below `ERROR`) | source `tool:<name>`, text = the output as JSON |
| `GENERATION` output `citations[]` | the claims; `output.answer` is where the values are located |

Two additions on top of the engine:

- **Where the value sits in the answer.** The value is matched as a whole token, so a `5` inside `2025-05-12` does not count. Of several candidates, the one whose three neighbouring words on each side overlap the quote most wins, and the number of candidates is reported. This is the "first hit is wrong" lesson from chapter 23 and the trace-viewer demo, met again in the x3d.demo `llm-trace-3d` scene, where the first build marked the `5` in the date.
- **A citation to the wrong source is counted.** The engine keeps a quote found in another source as `verified` with status `moved` (see BUG-31 in `docs/TRACE-REVIEW.md`). For a model, that means it cited the wrong document, so each item carries `cited_source` and `source_moved`, and the summary counts `moved`.

Fixture: `tests/fixtures/llm-trace/langfuse-rag-support-agent.synthetic.json` is **synthetic**. `make_trace.py` rebuilds it byte-identically. Its field names follow Langfuse's public OpenAPI (sha256 `cdaac03b…`, fetched 2026-11-20). One of its 7 citations is planted wrong.

Limits are the engine's: a verified citation shows that the quote is in the source and the value is in the quote. It does not show that the source is the right one to use, that the value is true, or that the model actually read it.
