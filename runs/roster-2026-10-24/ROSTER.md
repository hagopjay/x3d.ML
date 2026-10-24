# NVIDIA roster probe 2026-10-24 20:02Z

`GET https://integrate.api.nvidia.com/v1/models` listed 85 ids (models.json). One chat call per candidate: `Reply with the single word: ready.`, max_tokens 24, 60 s wall, ledger tag `probe` (free tier, 0 USD).

| model | listed | status | latency | first token | tokens out | finish | error / text |
|---|---|---|---:|---:|---:|---|---|
| nvidia/nemotron-3-super-120b-a12b | yes | error | 0.3 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function 'ac74040f-9fc9-4c5e-ac74-279ba516 |
| z-ai/glm-5.3 | yes | ok | 1.6 s | None | 24 | length |  |
| openai/gpt-oss-20b | yes | error | 64.6 s |  |  |  | 502 upstream request failed |
| deepseek-ai/deepseek-v4.1-flash | yes | error | 68.1 s |  |  |  | 502 upstream request failed |
| moonshotai/kimi-k2.6 | yes | error | 3.9 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '23d4f03a-b8a6-4adb-a183-7daa083a |
| minimaxai/minimax-m3.1-flash | yes | ok | 2.9 s | None | 24 | length |  |
| z-ai/glm-5.3-flash | yes | error | 66.3 s |  |  |  | 502 upstream request failed |
| stepfun-ai/step-5-preview | yes | ok | 30.3 s | 30284 | 16 | stop | ready |
| nvidia/nemotron-3-ultra-550b-a55b | yes | ok | 1.7 s | 1431 | 22 | stop | ready |
| nvidia/nemotron-3.5-lightning-30b-a3b | yes | ok | 5.1 s | None | 24 | length |  |
| nvidia/nemotron-3.5-super-vl-120b-a12b | yes | ok | 0.9 s | 859 | 17 | stop | ready |
| nvidia/nemotron-nano-3-30b-a3b | yes | error | 0.2 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '2b2dcd47-c858-425a-9c04-4cacf2ea |
| nvidia/nemotron-3-nano-omni-30b-a3b-reasoning | yes | ok | 1.3 s | 1243 | 50 | stop | ready |
| nvidia/nemotron-4-340b-instruct | yes | error | 0.2 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function 'b0fcd392-e905-4ab4-8eb9-aeae95c3 |
| nvidia/llama-3.1-nemotron-ultra-253b-v1 | yes | error | 0.2 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '84bf12ff-edbd-4435-baea-0fa6a745 |
| nvidia/llama-3.1-nemotron-70b-instruct | yes | error | 0.2 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '9b96341b-9791-4db9-a00d-4e43aa19 |
| mistralai/mistral-large-2-instruct | yes | error | 0.2 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '7fadd4de-e22a-48e4-90e9-f02ef14a |
| mistralai/mistral-large | yes | error | 0.3 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '767b5b9a-3f9d-4c1d-86e8-fa861988 |
| google/gemma-4-31b-it | yes | error | 64.6 s |  |  |  | 502 upstream request failed |
| google/gemma-3-12b-it | yes | error | 0.5 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function 'ee47df99-c92b-4dc9-b3a7-f3fb0f08 |
| poolside/laguna-xs-2.1 | yes | ok | 0.2 s | None | 0 |  |  |
| ai21labs/jamba-1.5-large-instruct | yes | error | 0.2 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '6497fc2b-7ff8-4019-8946-123dccbf |
| 01-ai/yi-large | yes | error | 0.2 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '23bd454d-b225-49a3-8118-582a62fc |
| ibm/granite-34b-code-instruct | yes | error | 0.2 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '4df48b4f-e3c5-4ade-82c7-c06b65e2 |
| mistralai/codestral-22b-instruct-v0.1 | yes | error | 0.2 s |  |  |  | 404 {"status":404,"title":"Not Found","detail":"Function '9a10b012-e6df-46fd-83b2-700dcbc7 |
| meta/llama-3.2-90b-vision-instruct | yes | error | 64.7 s |  |  |  | 502 upstream request failed |
| openai/gpt-oss-120b | no | error | 0.5 s |  |  |  | 410 {"type":"about:blank","title":"Gone","status":410,"detail":"The model 'openai/gpt-oss- |
| qwen/qwen3-coder-480b-a35b-instruct | no | error | 0.2 s |  |  |  | 410 {"type":"about:blank","title":"Gone","status":410,"detail":"The model 'qwen/qwen3-code |
| qwen/qwen3-235b-a22b | no | error | 0.2 s |  |  |  | 404 404 page not found
 |
| meta/llama-3.3-70b-instruct | no | error | 0.2 s |  |  |  | 410 {"type":"about:blank","title":"Gone","status":410,"detail":"The model 'meta/llama-3.3- |
| deepseek-ai/deepseek-v3.1 | no | error | 0.2 s |  |  |  | 404 404 page not found
 |
| moonshotai/kimi-k2-instruct | no | error | 0.2 s |  |  |  | 410 {"type":"about:blank","title":"Gone","status":410,"detail":"The model 'moonshotai/kimi |
| mistralai/mistral-large-3-instruct | no | error | 0.2 s |  |  |  | 404 404 page not found
 |
| google/gemma-3-27b-it | no | error | 0.2 s |  |  |  | 410 {"type":"about:blank","title":"Gone","status":410,"detail":"The model 'google/gemma-3- |
| nvidia/llama-3.3-nemotron-super-49b-v1.5 | no | error | 0.2 s |  |  |  | 410 {"type":"about:blank","title":"Gone","status":410,"detail":"The model 'nvidia/llama-3. |
| minimaxai/minimax-m2 | no | error | 0.2 s |  |  |  | 404 404 page not found
 |

## Reading

- Answered (8): z-ai/glm-5.3 1.6 s, nvidia/nemotron-3.5-super-vl-120b-a12b 0.9 s, nvidia/nemotron-3-ultra-550b-a55b 1.7 s, nvidia/nemotron-3-nano-omni-30b-a3b-reasoning 1.3 s, minimaxai/minimax-m3.1-flash 2.9 s, nvidia/nemotron-3.5-lightning-30b-a3b 5.1 s, stepfun-ai/step-5-preview 30.3 s (30 s to the first token for a one-word answer), poolside/laguna-xs-2.1 0.2 s with 0 tokens out and no text (counted as not usable). A reasoning model spends the 24-token budget thinking, so an empty `text` with 24 tokens out is still an answer.
- 502 `upstream request failed` after about 65 s (5): openai/gpt-oss-20b, deepseek-ai/deepseek-v4.1-flash, z-ai/glm-5.3-flash, google/gemma-4-31b-it, meta/llama-3.2-90b-vision-instruct. Listed, but no response headers inside a minute; the same 502 hit deepseek-v4.1-flash on 17 Oct.
- 404 `Function ... not found for account` (13 listed ids), among them the 17 Oct lane nvidia/nemotron-3-super-120b-a12b: the id is in /v1/models but this account cannot call it any more, so that lane cannot be continued.
- The requested ids that are not listed are gone: 410 end of life (openai/gpt-oss-120b, qwen/qwen3-coder-480b-a35b-instruct, meta/llama-3.3-70b-instruct, moonshotai/kimi-k2-instruct, google/gemma-3-27b-it, nvidia/llama-3.3-nemotron-super-49b-v1.5) or 404 (qwen/qwen3-235b-a22b, deepseek-ai/deepseek-v3.1, mistralai/mistral-large-3-instruct, minimaxai/minimax-m2).
- All probes ledgered with tag `probe` at 0 USD (free tier). Source: probes.jsonl, models.json, probe.log in this folder.

## Lanes picked for the 24 Oct run (up to 4: answered, fast, different families, the strongest coders available)

| lane | why | arm |
|---|---|---|
| z-ai/glm-5.3 | continuity with 17 Oct (its lane is the only one of the two that still answers); strong coder; slow (287 s median call on 17 Oct, reasoning counted in the 8000-token output cap) | A |
| nvidia/nemotron-3-ultra-550b-a55b | the largest model that answers; the NVIDIA family's successor to the 17 Oct nemotron lane (which now 404s); 1.7 s probe | A, B (second fastest) |
| minimaxai/minimax-m3.1-flash | a third family; 2.9 s probe; a current coder-class model | A |
| nvidia/nemotron-3.5-super-vl-120b-a12b | the same size class as the 17 Oct super lane; fastest probe (0.9 s); the dry run's model (18 to 44 s per scene call, first token at 16 to 42 s: it reasons before it writes) | A, B (fastest) |

Alternate: stepfun-ai/step-5-preview (answers, a fourth family, but 30 s to the first token on a one-word prompt). Not picked: the 30b models (lightning, nano-omni) are smaller than every 17 Oct lane.
