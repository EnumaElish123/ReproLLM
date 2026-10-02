> **PENDING — proposal only. Not approved, implemented, filed on GitHub, or adopted as gold.**

# Spec proposal: distinguish unknown API provider identity from API compatibility

Status: PENDING MAINTAINER APPROVAL; proposal only. No provider changes have been implemented.

## Concrete inconsistency

Manifest §3 allows provider=other and an endpoint.base_url. OpenAIIntegration.resolve
already sends any non-HF/non-local model to resolve_api_model, which records
provider=other, revision=null/unresolved, source=provider_no_pinning and API
pinnability. However model.revision_pinned recognises only openai/openrouter/anthropic
as APIs: the same other lock becomes CRITICAL for non-exact revision. dtype and
quantization also treat other as a locally inspectable model. provider_known's
WARNING is intentional under §12.4, not itself a defect.

Sources: integrations/openai_.py:55; lock/api_resolver.py:36;
rules/model.py:13,37,205,255; specification §3, §4.3, §12.4.

## Smallest proposed contract

Define provider=other with a nonempty endpoint.base_url as an explicitly declared,
opaque model API. Preserve provider=other in manifest/lock/export; do not relabel
the service OpenAI merely because inference.backend=openai names the client/API
compatibility. Keep provider_known WARNING and improve its hint: provider metadata
is unsupported; record endpoint identity and keep honest API limitations.

Recommended qualified endpoint: an unchanged nonempty string with no leading or
trailing whitespace/control characters, parsed by stdlib urlsplit as HTTP or HTTPS
with a nonempty hostname; no username/password userinfo or fragment. Normal URL
path/query components are allowed only when the original value has zero existing
secret/machine-identity redaction triggers. Check the original before any display
normalization; do not send a request to establish this classification. Absent,
empty, whitespace-only, malformed, unsafe and non-HTTP endpoints do not qualify and
keep the current unsupported-other behavior. This classification is not a new
schema validator and does not make such manifests fail to load.

| Rule / operation | Proposed classification source |
|---|---|
| Level1 presence rules, including dtype/quantization even when audit level is 2 | per-role manifest provider and endpoint.base_url; provider must equal other |
| Level2 model.revision_pinned | per-role effective provider and endpoint.base_url leaves in existing merged State; retain source/confidence/alternatives; provider must equal other |
| lock API resolver | existing per-role ModelSpec declaration; no new endpoint persistence or request |
| diff/export | existing merged State and provenance; never infer provider from inference.backend |

Endpoint presence is an explicit author declaration of an opaque service, not
independent verification that a model is closed-source or its snapshot immutable.
Use no other role's endpoint and no client/backend package to establish identity.

For this explicitly declared API scenario, use the existing D-21 API pinnability
policy in model.revision_pinned: ordinary alias unpinnable → WARNING; date-suffixed
snapshot_alias → INFO; revision remains null/unresolved and neither is exact.
Skip unobservable dtype/quantization requirements in the same way as existing APIs.
Without endpoint.base_url, other retains its existing unsupported-provider policy.

This API classification remains metadata-only and sends no request by default.
Offline lock instantiates no HTTP client; ordinary online lock currently does
instantiate one even without an API request, and a mixed repository's HF resolution
may legitimately use it. This proposal must not accidentally change those existing
contracts or claim that every default lock is offline. --verify-api for
other continues to report unavailable verification unless a separate, reviewed
credential/config contract is added. This proposal introduces no generic key lookup,
endpoint request, new provider enum, SDK dependency or persisted schema field.

## Acceptance criteria

- Unknown API endpoint + ordinary alias keeps other identity and produces honest
  provider/pinnability WARNINGs, with no fabricated revision and no dtype demand.
- Date alias follows existing D-21 snapshot_alias policy without claiming immutable.
- Other without a qualifying endpoint, HF/local, and the three existing API
  providers retain their prior behavior. No request is added for other; offline
  lock instantiates no HTTP client. Mixed HF online resolution remains unchanged.
- Mixed primary-local + judge-other cases apply the classification per model role.
- Changing a declared endpoint after locking makes the manifest hash stale and
  remains reported by existing lock freshness checks; test that explicitly.
  ModelLock currently has no endpoint field (§4.2 and schemas/lock.py), so there is
  no existing per-value manifest-versus-lock endpoint comparison to preserve.
  Endpoint alternatives captured through supported runtime bindings should be
  retained in State; any new endpoint-specific consistency rule or schema field
  needs a separate explicit contract. Tests mock all HTTP.
- Mixed/changed-role tests cover manifest other with stale differently classified
  lock provider, absent versus qualified current endpoint, and runtime-bound
  endpoint alternatives. Applying API pinnability policy cannot suppress the
  existing CRITICAL lock freshness finding or discard source alternatives.

Amend §4.3 and the API applicability notes in §12.4 before implementation. D-08 rule
IDs and D-21 pinnability remain unchanged. No schema/core.engine/core.redaction change
is proposed, so D-41 is avoidable for this narrow option. Adding a transport field,
provider enum or generic key mapping would be a separate schema review.
