# DeepSeek API research for supplementary judge validation

Research date: **2026-09-27**. The initial research used public documentation and
pinned source only; the research agent did not read a credential or call an
account endpoint. After the maintainer approved the adapter and CNY 3 budget,
the root agent completed two real requests at 04:11 UTC. See
[the execution report](m4-m6-linux-validation.md#deepseek-fastchat-live-pair--2026-09-27)
and [pre-execution gold](../../val.md#84-approved-deepseekfastchat-supplementary-judge-2026-09-27).
Public documentation can change; verify model/tariff again for any new run.

The root agent subsequently made one **unauthenticated** reachability probe on
2026-09-27: `GET https://api.deepseek.com/models` returned HTTP 401 in 0.973334
seconds, with no credential or request body. This establishes endpoint
reachability only; it does not validate the supplied key, account balance, model
availability, or a real judge response.

## Endpoint and model configuration

The official OpenAI-compatible base URL is `https://api.deepseek.com`. Chat
generation uses `POST /chat/completions`, JSON content, and an
`Authorization: Bearer <API key>` header. The documented current request IDs
are `deepseek-flash` and `deepseek-v4-pro`.
[Official first-call guide](https://api-docs.deepseek.com/).

The pricing page identifies their current underlying versions as
DeepSeek-V4.1-Flash and DeepSeek-V4-Pro-0813. Old `deepseek-v4-flash` and
`deepseek-v4-flash-vision-exp` names now route to V4.1-Flash. For the proposed
small validation use `deepseek-flash`; do not assume remembered legacy names
identify the current service.
[Official models and pricing](https://api-docs.deepseek.com/quick_start/pricing/).

Thinking is enabled by default. Explicitly send `thinking.type: disabled` so
the requested temperature has an effect; thinking mode ignores temperature.
For the modern OpenAI Python client, the custom field belongs in
`extra_body={"thinking": {"type": "disabled"}}`. Raw HTTP puts `thinking`
directly in the JSON body.
[Official thinking-mode guide](https://api-docs.deepseek.com/guides/thinking_mode/).

Minimal non-streaming request body, presented as an example only:

```json
{
  "model": "deepseek-flash",
  "messages": [
    {"role": "system", "content": "Return only [[1]] if correct, otherwise [[0]]."},
    {"role": "user", "content": "Question: 2 + 2? Answer: 4."}
  ],
  "thinking": {"type": "disabled"},
  "temperature": 0,
  "max_tokens": 32,
  "stream": false
}
```

`temperature` accepts 0–2; `max_tokens` limits generated tokens. A real MT-Bench
judge must use its reviewed prompt and bounded answer inputs, not the arithmetic
example. `finish_reason: length` signals truncation and cannot establish a valid
completed judgment.
[Official Chat Completions reference](https://api-docs.deepseek.com/api/create-chat-completion/).

`GET https://api.deepseek.com/models` is the documented read-only model-list
endpoint. With the provisioned Bearer credential, check `data[].id` before
generation; this lists metadata and does not request a completion. The public
reference does not state a separate charge for this endpoint, so this note makes
no billing guarantee about account operations. It was not executed during the
initial research; the later approved live validation returned HTTP 200 and
confirmed `deepseek-flash` before either completion was sent.
[Official model-list reference](https://api-docs.deepseek.com/api/list-models/).

## Current token prices and bounded spending

Each rate below is per **1,000,000 tokens**; CNY and USD are independently
published tariffs, not an exchange-rate conversion.

| Model | Currency | Off-peak input hit / miss / output | Peak input hit / miss / output |
|---|---|---|---|
| `deepseek-flash` | CNY | 0.02 / 1 / 4 | 0.04 / 2 / 8 |
| `deepseek-v4-pro` | CNY | 0.15 / 4.5 / 13.5 | 0.30 / 9 / 27 |
| `deepseek-flash` | USD | 0.003 / 0.15 / 0.6 | 0.006 / 0.3 / 1.2 |
| `deepseek-v4-pro` | USD | 0.022 / 0.66 / 1.98 | 0.044 / 1.32 / 3.96 |

Sources: [official CNY tariff](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/),
[official USD tariff](https://api-docs.deepseek.com/quick_start/pricing/).
Peak hours are 09:00–12:00 and 14:00–18:00 Beijing time, Monday–Friday excluding
Chinese public holidays; other times receive the off-peak rate. Prices may change.
Fees are deducted from the account balance, using granted balance first.

Calculate the observation-derived charge as:

```text
cost = (prompt_cache_hit_tokens × input_hit_rate
      + prompt_cache_miss_tokens × input_miss_rate
      + completion_tokens × output_rate) / 1,000,000
```

The response separates cache hits/misses; `prompt_tokens` is their sum and
`total_tokens` includes completion tokens. Preserve all `usage` counters plus
request model, returned model, response ID, `system_fingerprint` when supplied,
finish reason, and timestamp. Do not multiply `total_tokens` by one rate.
[Official response schema](https://api-docs.deepseek.com/api/create-chat-completion/).
Character-based estimates are approximate; reported usage is the accounting
source of truth.
[Official token-usage guide](https://api-docs.deepseek.com/quick_start/token_usage/).

Derived example, **not an executed charge or budget guarantee**: two Flash
requests, each with at most 4,000 uncached input tokens and output caps of
256 then 384 tokens, cost at most CNY 0.02112 or USD 0.003168 at the listed
peak rates. Actual input length must be checked; output caps alone do not bound
input cost. Budget for every request attempt, including retries. Use the
provisioned account's billing currency and approved total ceiling.

## Errors and retry boundary

The official error table maps 400/422 to invalid format/parameters, 401 to
authentication failure, 402 to insufficient balance, 429 to rate limiting, and
500/503 to server failure/overload. Correct request/authentication/balance issues;
pace rate-limited requests; wait briefly before retrying server failures.
[Official error codes](https://api-docs.deepseek.com/quick_start/error_codes/).

For this bounded experiment, use sequential requests and an explicit total
attempt count. Disable client-library implicit retries; count any deliberate
retry against the remaining budget. A timeout after submission leaves completion
and charging uncertain, so do not assume it was free. These are experiment
controls, not a DeepSeek retry or refund guarantee. Do not change provider/model
silently to recover an error.

Non-streaming responses may contain keep-alive blank lines. DeepSeek says a
connection closes if inference has not started after ten minutes. A separate
client deadline should keep the validation bounded; an HTTP read timeout alone
can be extended by incoming keep-alives.
[Official rate-limit and connection guide](https://api-docs.deepseek.com/quick_start/rate_limit/).

## FastChat adaptation and validation interpretation

At pinned FastChat commit `587d5cfa1609a43d192cedb8441cac3c17db105d`:

- `common.py` calls legacy `openai.ChatCompletion.create`; its retry loop permits
  16 attempts with ten-second sleeps.
- The single-judge path accepts names through `OPENAI_MODEL_LIST`, which contains
  `gpt-4-0613` but no current DeepSeek API IDs. It requests temperature 0 and
  2,048 output tokens.
- Merely changing the base URL does not resolve SDK, model selection,
  conversation-template, thinking-mode, or request-budget differences.

Sources: [pinned common helpers](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge/common.py),
[pinned model adapters](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/model/model_adapter.py).
The existing [runtime compatibility review](m5-m6-runtime-gold.md) also documents
the old OpenAI SDK extra's conflict with the modern runtime environment.

The executing agent must review an explicit adapter in a disposable checkout
before making calls: retain reviewed MT-Bench prompt construction and parsing,
identify the real DeepSeek model and endpoint, select the correct message
template, enforce thinking/output/attempt controls, and preserve sanitized usage.
Capture the adapter and prompt/input hashes with the run. This note does not
implement or approve a specific adapter.

DeepSeek judge results are an **independent supplementary scenario**. They cannot
pass the original `gpt-4-0613` judge gold by substitution. A paid response alone
also cannot establish runtime capture or semantic-diff correctness. Before
activation, record the bounded command, input hashes, expected capture fields,
parser checks, and any paired parameter drift independently of ReproLLM output,
as required by [the validation baseline](../../val.md#8-mandatory-validation-gates).

Use the actual model identity in the manifest and record the alias as
`unpinnable`; the display version or returned fingerprint is not an immutable
provider revision. Temperature 0 does not justify byte-identical-output claims.
Expected judgment text or quality scores are not deterministic gold. For a pair
changing only `evaluation.judge.params.max_tokens`, distinguish the intended
importance from the current specified matching rule: §18 lists
`evaluation.judge.*: HIGH`, but §1 defines `*` as one segment. The nested
`params.max_tokens` leaf therefore falls through to MEDIUM, independently of
the HIGH configuration-file hash. The root agent also confirmed this using
`SeverityResolver` without an API call. Record this existing policy gap rather
than declaring the leaf HIGH or concealing it behind the aggregate exit status.
The subsequently executed pair confirmed this MEDIUM leaf. These conclusions follow
[D-21](../plan/00_architecture_and_decisions.md) and
[specification §§1, 3, 5, 15, 18](../plan/01_specification.md).

Live execution details remain in the separate execution report. The root agent
injected the provisioned key through hidden terminal input into process memory
and the child environment; its value was not written to files or argv. Both
captured runs retain only credential presence. The research agent's sole write
was this document; subsequent execution annotations are by the root agent.
