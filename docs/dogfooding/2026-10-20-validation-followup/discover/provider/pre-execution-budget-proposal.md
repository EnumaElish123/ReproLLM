# Current-candidate discover validation: input and budget proposal

Prepared 2026-10-20 for candidate `948d16423023027fff77322b8a872acaba306691`. **Not authorized or sent.**

The five initialized offline previews pass independent complete source/message/privacy checks. Project C retains the val section 2 upstream pin and section 8.6 scenario: only public pinned source and operator-generated intent, collection budget 30,000, actual user message 31,337 characters / 31,342 UTF-8 bytes. No weights or dataset content are sent. The system prompt is unchanged.

The current initializer/collector produces three different manifest/collection/user hashes from the historical section 8.6 record. Original historical bytes are not claimed recovered, and no historical gold is replaced. Approval here accepts the exact new current-candidate inputs for this same scenario; it is not an exact historical-input replay.

| Artifact | Current SHA-256 | Historical equality |
|---|---|---|
| manifest | `c7794c7c6303f48aace66aedd3c009a55bf71bc4a1daf676f97ab4a3f144c999` | False |
| rendered_collection | `c9f17e5d9e03ac2a8ae15a66ec960f42ec42f52386cda287b6a3841ae0a8dc62` | False |
| actual_user_message | `1d11cb30bc05ad047f07abbb37a02a342a86643eafe72db2e95b3b6cb48cd414` | False |
| system_prompt | `e93ac5604c0defc347ae67e18c58eca21589c7ee1627c9040c784d8930d207c2` | True |

Requested authorization: at most **CNY 4**, **one actual HTTP POST** to the official DeepSeek chat-completions endpoint using `deepseek-flash`; no automatic or implicit second send. Retain the unmodified production fields (model, temperature 0, messages, response_format), including its current absence of max_tokens and thinking overrides. The production per-phase request timeout is at most 120 seconds; enforce a 400-second whole-run deadline. A submitted timeout retains its cost reservation and is not retried.

The official model listing returns 200 and includes the selected model. Current official peak prices are CNY 2 / million input tokens and CNY 8 / million output tokens; the documented maximum output is 384K. Reserve 393,216 output tokens conservatively plus 33,711 input tokens (both message UTF-8 byte counts plus 1,024 framing allowance): **CNY 3.213150** before sending, below CNY 4. These are a conservative reservation and a current usage-based pricing calculation, not an account invoice.

[Official pricing](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/), [exact preflight](../inputs/project-c-preflight.json), [model availability](model-preflight.json).

The observer rejects changed fields/messages/endpoint/model/time limits, requests lacking real authorization, and all second POSTs before network. Production-client/schema/finalizer mock checks cover a success and sixteen negatives; no real request is used for those checks. Real execution is by the parent only after the maintainer accepts these exact inputs and budget.

A successful provider response is only the first layer. Then independently review sent-source candidate evidence, stable IDs and full artifact privacy; accept a justified candidate in the disposable clone; verify missing-field WARNING, explicitly sourced validation declaration to PASS, duplicate acceptance exit 2, and repeat complete audit equality. Do not send another request to fix an observer or a candidate-review issue.

The budget must be explicitly provisioned under val section 8; the old judge CNY 3 ceiling is not reused. No HF gated success, original metadata recovery, policy amendment or release is implied.

| Observer | SHA-256 |
|---|---|
| paid_guard.py | `86180019ceb6a1bb1f78ffb8f644e8394daa2a8692cb3450b0c1f53ac5a4c521` |
| discover_controller.py | `0619fde63a68863fef88a43c1350b192ee5658f4dc852a182fcd413e59eeccc3` |
| transport_selfcheck.py | `bfd480a27211714cdceffd264e49160d5c56543da1e8bc43ac8b88e5161b7699` |
