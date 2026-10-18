# Cost ledger: Traceability thread, AI-service grant of 10 USD (19:45Z 17 Oct 2026)

Private. Written by the Traceability thread. Numbers are estimates from reported token counts, not an invoice.

## What was granted and how it was spent

- Grant: 10 USD of AI-service spend for this thread (relayed ask of 19:45Z, 17 Oct 2026), to make the demo more visual with real recorded model calls.
- Reading of the grant: metered API calls only, through the project's credential-injecting proxy (Gemini on Vertex, OpenAI, NVIDIA). No new resources, quota, VMs or role grants were created.
- Hard stop in code: the runner (`demo/live/run_live.py`) refuses a paid call once the ledger reaches the cap (`--cap`). The first segment ran with a cap of 8.0 USD and the later ones with 8.5 USD; both below the grant.
- Every call is appended to `demo/live/ledger.jsonl` before its result is used, so a crash cannot hide a charge.
- Final estimate: **8.3128 USD of 10 USD (83%)**. The two NVIDIA-hosted open models ran on a free trial tier and are counted as 0.

## Ledger

Estimates from reported token usage at list prices per 1M tokens (in/out): gemini-3.8-flash 0.75/3.75; gemini-3.1-pro-preview 2.0/12.0; gpt-6.1-sol 2.0/10.0; NVIDIA calls on free trial credits count 0. Not an invoice.
Hard stop in code: 8.50 USD (set per run with `--cap`). Machine-readable source: `demo/live/ledger.jsonl` (one line per call, appended before the result is used).

| batch | service | model | calls | tokens in | tokens out | est. USD | first | last |
|---|---|---|---:|---:|---:|---:|---|---|
| probe | nvidia | moonshotai/kimi-k2.6 | 1 | 0 | 0 | 0.0000 | 2026-10-17T20:03:21Z | 2026-10-17T20:03:21Z |
| probe | nvidia | nvidia/nemotron-3-ultra-550b-a55b | 1 | 15 | 0 | 0.0000 | 2026-10-17T20:03:21Z | 2026-10-17T20:03:21Z |
| probe | nvidia | nvidia/nemotron-3-super-120b-a12b | 1 | 27 | 25 | 0.0000 | 2026-10-17T20:03:22Z | 2026-10-17T20:03:22Z |
| probe | openai | gpt-6.1-sol | 1 | 21 | 4 | 0.0001 | 2026-10-17T20:03:22Z | 2026-10-17T20:03:22Z |
| probe | vertex | gemini-3.8-flash | 1 | 11 | 83 | 0.0003 | 2026-10-17T20:03:23Z | 2026-10-17T20:03:23Z |
| probe | vertex | gemini-3.1-pro-preview | 2 | 418 | 8,645 | 0.1046 | 2026-10-17T20:03:24Z | 2026-10-17T20:33:38Z |
| probe | nvidia | z-ai/glm-5.3 | 1 | 24 | 61 | 0.0000 | 2026-10-17T20:03:25Z | 2026-10-17T20:03:25Z |
| probe | nvidia | deepseek-ai/deepseek-v4.1-flash | 1 | 0 | 0 | 0.0000 | 2026-10-17T20:05:04Z | 2026-10-17T20:05:04Z |
| live | vertex | gemini-3.8-flash | 95 | 134,197 | 399,826 | 1.6000 | 2026-10-17T20:06:47Z | 2026-10-17T20:46:45Z |
| live | openai | gpt-6.1-sol | 67 | 37,467 | 107,829 | 1.1532 | 2026-10-17T20:06:48Z | 2026-10-17T20:44:03Z |
| live | nvidia | z-ai/glm-5.3 | 82 | 43,146 | 405,990 | 0.0000 | 2026-10-17T20:06:52Z | 2026-10-17T21:44:50Z |
| live | vertex | gemini-3.1-pro-preview | 98 | 61,078 | 436,040 | 5.3546 | 2026-10-17T20:07:01Z | 2026-10-17T20:56:20Z |
| live | nvidia | nvidia/nemotron-3-super-120b-a12b | 122 | 118,820 | 300,243 | 0.0000 | 2026-10-17T20:07:06Z | 2026-10-17T21:36:56Z |
| killed-in-flight (estimate) | vertex+openai | paid models, about 7 calls cut off | 1 | 0 | 0 | 0.1000 | 2026-10-17T20:22:28Z | 2026-10-17T20:22:28Z |

**Total estimated spend: 8.3128 USD of the 10 USD grant (hard stop 8.50).**

## Ledger against the scenes on the page

The page embeds only finished chains (attempts 1 to n, the last one valid or the third). Calls that failed with a rate limit or gateway error, and chains cut off by the cap or the time box, are in the ledger but not on the page.

| model | ledger calls | on the page | not on the page | ledger USD | page USD | not on the page USD | tokens out not on the page |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.8-flash | 95 | 92 | 3 | 1.6000 | 1.6000 | 0.0000 | 0 |
| gemini-3.1-pro-preview | 98 | 72 | 26 | 5.3546 | 4.8446 | 0.5100 | 42,159 |
| gpt-6.1-sol | 67 | 53 | 14 | 1.1532 | 1.1532 | 0.0000 | 0 |
| z-ai/glm-5.3 | 82 | 53 | 29 | 0.0000 | 0.0000 | 0.0000 | 88,203 |
| nvidia/nemotron-3-super-120b-a12b | 122 | 88 | 34 | 0.0000 | 0.0000 | 0.0000 | 31,679 |
| all models | 464 | 358 | 106 | 8.1079 | 7.5978 | 0.5100 | 162,041 |

ledger total 8.3128 USD = live calls 8.1079 + probes 0.1050 + killed-in-flight estimate 0.1000
page shows 7.5978 USD of it; the rest is chains cut off by the cap or the time box (0.5100), probes and the estimate

## Events that changed the spend

1. OpenAI account out of credits at about 20:34Z (`insufficient_quota`): that lane stopped at 43 of 50 prompts. Not a code stop; the provider refused the call.
2. Spend cap: the Gemini Pro lane stopped at 47 of 50 prompts when the ledger reached the cap. Its 3 unfinished chains (0.51 USD with failed calls) are in the ledger but not on the page.
3. Global stop: a paid call hitting the cap set one stop flag that also halted the two free lanes. They were resumed on their own (free tier, 0 USD, a longer per-call time limit, a 22-minute time box) and stopped by hand at about 21:44Z, which left 14 unfinished free-lane chains out of the page.
4. Killed in flight: a process stop cut off about 7 paid calls. They are counted as one row at 0.10 USD, an upper estimate, so the total cannot be too low.
5. Probes: 8 one-call probes of the available models cost 0.1050 USD, mostly one 8,000-token reasoning call.

## Not done

- No reconciliation against the real invoices: that needs the billing console. Prices used are the list prices in the header; reported provider token counts are taken at face value.
- The spend is not apportioned to a billing project beyond the proxy's own accounting.
