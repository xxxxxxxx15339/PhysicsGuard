# Milestone 4 — keyless local investigator validation

Recorded October 29, 2026. This is local implementation and validation only.
No commits, pushes, deployments, purchases, hosted model requests, real API-key
access or model downloads were performed. Optional client packages were downloaded
with approval; public official documentation was consulted. All model requests
targeted the installed loopback Ollama server.

The inherited tree was clean at `c18172ad0c1e14545e65ed2bd1ad981cea221f89`
(`Milestone3`) and contained the Milestone 3.1 hardening described in
[its historical validation](milestone3_1_validation.md). Historical publication
and CI statements are preserved as owner-reported history, not new measurements.

## Architecture and changed files

| Files | Implemented responsibility |
| --- | --- |
| `src/physicsguard/agent/protocol.py` | Validated tool request/response, explanation, provenance, trace and final records; bounded strict JSON; seven tool schemas |
| `src/physicsguard/agent/instructions.py` | Scientific assumptions, evidence requirements, signed experiments, diffusion cautions and verifier authority; no fixture answers |
| `src/physicsguard/agent/boundary.py` | Explicit public result projection and sanitized errors; excludes private verification reports/parameters, raw arrays, runtime noise and unexpected host fields |
| `src/physicsguard/agent/model_client.py` | JSON-only provider protocol, deterministic public-evidence mock and optional local Llama OpenAI-compatible adapter |
| `src/physicsguard/agent/planner.py` | Bounded investigation, evidence/ID/source scope, tool continuation, hypotheses, host verification and per-run provenance |
| `src/physicsguard/agent/demo.py` | CLI, evidence/diff/decision/lifecycle display and exclusive mode-0600 JSON artifacts |
| `tests/test_agent.py` | Real reviewed-worker mock investigations, deterministic replay, protocols, privileges, budgets, cleanup, CLI and opt-in live smoke test |
| `tests/test_agent_ollama.py` | Offline SDK/transport fakes, identity/errors/timeouts, continuation, optional-dependency absence and no fallback |
| `pyproject.toml` | Optional `ollama = ["openai>=1.40,<3"]`; NumPy remains the sole mandatory dependency |
| `README.md`, `docs/architecture.md`, `docs/hackathon_provenance.md`, `docs/third_party.md` | Usage, architecture, actual work attribution and optional-client provenance |
| `docs/milestone4_validation.md` | This executed validation record |

The host retains `RepairTools`, source store, run/proposal registries and original
snapshot. Both clients receive only JSON strings containing messages and tool
descriptions. The dispatcher is invoked through `RepairTools.call()` only.
Source, run and proposal identities are bound to one investigation. No model text
is evaluated, imported, compiled or accepted as replacement source. A model can
select exactly `restore_signed_upwind`, `normalize_time_by_cell_width` or
`wrap_incoming_neighbor`; the existing host rules author the patch and retain
`origin: deterministic`. The existing verifier alone supplies the final decision.

The JSON protocol rejects duplicate keys, NaN/Infinity/overflowing JSON floats,
malformed objects, unexpected fields, oversized data, unknown tools, privileged
plans/tolerances/reports/source arguments and unsupported physical contracts.
Experiment inputs are validated against existing scientific/resource limits.
Diagnostics retain actual measurements, assumptions, applicability, criteria,
tolerances and public case references. Execution arrays, variable runtimes and
free-form error strings are omitted. Hypotheses may be recorded before repair
selection. Final narrative citations must refer to observed development evidence;
the authoritative host explanation is built from the actual verifier summary.

Default limits: 16 turns, 12 tool actions, 4 development experiments, 2 verification
attempts, 2 consecutive invalid responses, 120,000 conversation/schema bytes,
1,000,000 cumulative input bytes, 8,192 output-token allowance and 1,024 output
tokens per turn. Hard configuration ceilings also apply. Serialized input bytes
provide a conservative content budget without an added tokenizer. `output_tokens`
is budget accounting: malformed backend responses without usable usage information
are conservatively charged the requested output allowance. It is not a model
performance or exact total-token metric. Identical operation/argument calls and
reused call IDs terminate safely. Tool errors terminate immediately. No real-model
failure falls back to mock.

The adapter pins `llama3.1:8b`, validates the returned model identity and accepts
only loopback HTTP `/v1` endpoints, canonicalizing `localhost` without DNS. It
disables environment proxies, redirects, retries and environment organization/
project headers. The SDK's literal `ollama-local-placeholder` is not a Meta key.
Default timeout is 45 seconds, configurable from .1 to 60 seconds; the raw HTTP
body is read incrementally with a 32 KiB cap and elapsed-time checks. This is a
bounded HTTP client, not a hard-deadline process supervisor for a hostile server.
The CLI endpoint is fixed at `http://127.0.0.1:11434/v1`.

Official documentation consulted:
[Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility),
[tool calling](https://docs.ollama.com/capabilities/tool-calling), and
[Llama 3.1 model catalog](https://ollama.com/library/llama3.1).
No Muse endpoint/model ID or hosted behavior was selected or implemented.

## Environment and commands actually executed

Non-root Linux, UID 1000, CPython 3.13.11, NumPy 2.5.4, pytest 9.2.0, using the
existing `.venv/bin/python`. The optional installation supplied OpenAI SDK 2.54.0
and HTTPX 0.28.1 plus their dependencies. No Python 3.11/3.12 runtime or new remote
CI matrix was executed. Python 3.11 grammar parsing is a separate static check.

Core commands, from the repository root:

```sh
id
uname -s
.venv/bin/python -m pytest -q
.venv/bin/python -m pip install 'openai>=1.40,<3'
.venv/bin/python -m pip install --no-cache-dir 'openai>=1.40,<3'
.venv/bin/python -m compileall -q src/physicsguard/agent
.venv/bin/python -m pytest tests/test_agent.py -q
.venv/bin/python -m pytest tests/test_agent.py tests/test_agent_ollama.py -q
.venv/bin/python -m compileall -q src tests benchmarks
.venv/bin/python -m pytest -q
.venv/bin/python -m benchmarks.source_repair.evaluate \
  --output artifacts/milestone4-deterministic-baseline.json
.venv/bin/python -m physicsguard.agent.demo --backend mock --source solver_04.py \
  --trace milestone4-final-cli-control.json
git diff --exit-code -- src/physicsguard/numerics src/physicsguard/diagnostics \
  src/physicsguard/repair src/physicsguard/experiments benchmarks tests/test_numerics.py .github
git diff --check
```

The first pip attempt could not resolve the package index in the sandbox. The
approved retry installed the optional dependency in the existing virtual
environment. Loopback sockets were also blocked in the sandbox; approved local
commands were run outside that socket restriction. No privileged/root scientific
execution, server deployment or secret-file access was used.

Mock CLI invocations were run first with `milestone4-mock-solver_XX.json` trace
names and then with the final protocol:

```sh
for fixture in solver_01.py solver_02.py solver_03.py solver_04.py; do
  .venv/bin/python -m physicsguard.agent.demo --backend mock \
    --source "$fixture" --trace "milestone4-final-mock-${fixture%.py}.json"
done
```

Real-model commands, including failed attempts, were:

```sh
.venv/bin/python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --source solver_01.py --trace milestone4-ollama-solver_01.json
.venv/bin/python -u -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --timeout 60 --source solver_01.py --trace milestone4-ollama-solver_01-retry.json
ollama ps
curl --fail --silent --show-error --noproxy '*' --max-time 60 \
  http://127.0.0.1:11434/v1/chat/completions -H 'Content-Type: application/json' \
  --data '{"model":"llama3.1:8b","messages":[{"role":"user","content":"Reply with one word: ready"}],"max_tokens":8,"stream":false}' \
  --output artifacts/milestone4-ollama-connectivity.json
.venv/bin/python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --timeout 60 --source solver_01.py --trace milestone4-ollama-solver_01-warm.json
.venv/bin/python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --timeout 60 --source solver_02.py --trace milestone4-ollama-solver_02.json
.venv/bin/python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --timeout 60 --source solver_03.py --trace milestone4-ollama-solver_03.json
.venv/bin/python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --timeout 60 --source solver_04.py --trace milestone4-ollama-solver_04.json
.venv/bin/python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --timeout 60 --source solver_01.py --trace milestone4-ollama-solver_01-schema-feedback.json
.venv/bin/python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --timeout 60 --source solver_02.py --trace milestone4-final-ollama-solver_02.json
.venv/bin/python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --timeout 60 --source solver_03.py --trace milestone4-final-ollama-solver_03.json
.venv/bin/python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b \
  --timeout 60 --source solver_04.py --trace milestone4-final-ollama-solver_04.json
```

A loopback-only `urllib.request` GET of `/api/tags` confirmed the installed model:
`llama3.1:8b`, 8.0B, Q4_K_M, GGUF, digest
`46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`.
This is server-reported identity, not independent weight attestation. The
connectivity probe returned a genuine matching-model completion with two output
tokens. It is not an investigation/repair result. `ollama ps` returned no loaded
model at the instant it was queried; no cause of the earlier timeouts is asserted.

## Observed tests and frozen baseline

| Check | Actual outcome |
| --- | --- |
| Inherited suite before edits | 405 passed in 51.94 s |
| Focused final agent/adapter tests | 102 passed, 1 skipped in 10.65 s |
| Complete suite, final code including CLI evidence display | 507 passed, 1 skipped in 77.60 s |
| Compileall | Passed |
| Python 3.11 grammar | All 67 Python files under src/tests/benchmarks parsed |
| Live pytest smoke test | Not executed; explicitly opt-in and skipped in standard suite |
| New hosted requests, remote CI, container/isolation validation | Not executed |

Development tests initially caught a reserved pytest parameter name and a
proposal/verification bookkeeping mismatch after a second unverified proposal.
Both were corrected. The final result now retains the proposal actually bound
to the recorded verification; a later proposal cannot inherit its acceptance.

Offline tests exercise actual reviewed solver subprocesses for all four fixtures,
credential/SDK/network-free mock use, strict parsing/privilege rejection, repeated
invalid responses, timeouts/errors, action/input/output/experiment/verification
budgets, duplicate calls/IDs, tool-result continuation, evidence scopes, rejection
of self-declared acceptance, synthetic rejected/inconclusive host decisions,
safe errors, lifecycle tracking, original-byte preservation, deterministic traces
and output-path protections. SDK fakes are test-owned synthetic protocol checks,
not genuine inference or scientific-performance samples.

The rerun of `benchmarks.source_repair.evaluate` matches the preexisting frozen
`artifacts/source-repair-evaluator.json` **exactly after recursively removing
fields containing `seconds`**, including all measurements and category records.
Comparison used JSON decoding and recursive dictionary/list traversal, rather
than a category-only acceptance check. The original artifact was not overwritten.

Deterministic baseline: 3/3 independently accepted repairs, 1/1 correct abstention,
272 solver requests/16 worker sessions; 14 negative proposals give 13 REJECTED,
1 INCONCLUSIVE, 0 ACCEPTED; static source recognition remains 9/12 and independent
correct-callable controls remain 2/2 unflagged. These are the unchanged host
benchmark's results, separate from both mock orchestration and Llama performance.
The original PhysicsBugBench seeds were not rerun in this milestone; their
existing tests passed in the complete suite. No claim of a new seed measurement
is made.

## Mock investigations

All rows are `backend: mock`, `model: null`, `model_inference: false`.
The scripted policy inspects source, selects positive and negative sine experiments,
reads actual diagnostics, records a cited hypothesis, selects a permitted operation,
and requests independent verification. It uses observed failed diagnostic families,
never filename-to-answer mappings, labels or private verifier parameters.

| Source | Public evidence and scripted choice | Host verifier / final outcome |
| --- | --- | --- |
| `solver_01.py` | Accuracy and direction fail for both signs; conservation passes; `restore_signed_upwind` | ACCEPTED; 7 tool actions, 1 verification |
| `solver_02.py` | Accuracy, refinement and spatial scaling fail; direction remains inconclusive; `normalize_time_by_cell_width` | ACCEPTED; 7 tool actions, 1 verification |
| `solver_03.py` | Positive motion fails mass/translation/wrapping checks; tested negative motion passes; `wrap_incoming_neighbor` | ACCEPTED; 7 tool actions, 1 verification |
| `solver_04.py` | All 13 diagnostics pass for each signed development report | Abstained; no proposal, no verification; 5 tool actions |

Positive default-case L1 errors before repair are respectively
0.2507138735597209, 0.16607469042511158, 0.035164199164466795 and
0.0018863498034673992. Corresponding absolute mass drifts are 0, 0,
0.03348020691826137 and 0. These are actual public experiment measurements, not
mock-invented numerical results. The tools' existing independent verifier
supplies all three acceptances. Source diffs remain one line. Original integrity
and workspace cleanup are true for all four investigations. Tests replay all
four complete strict JSON mock traces byte-for-byte and track actual temporary
directory removal.

## Genuine local Llama outcomes

**Genuine Ollama inference was executed. No successful Llama repair investigation
has been demonstrated.** Both initial solver-01 requests timed out before a valid
completion reached the client, so their traces conservatively record
`backend: ollama`, `model_inference: false`, zero successful inference responses
and no decision. They never fall back to mock.

After the minimal connectivity probe, the four full investigations below each
received **three genuine matching-model inference responses** and truthfully
record `backend: ollama`, `model: llama3.1:8b`, `model_inference: true`:

| Source / artifact suffix | Valid tool actions | Observed termination | Repair result |
| --- | --- | --- | --- |
| `solver_01.py` / `solver_01-warm` | Inspect source | Two consecutive invalid responses | No proposal; no verification |
| `solver_02.py` / `solver_02` | Inspect source | Invalid response, then unexpected experiment arguments | No proposal; no verification |
| `solver_03.py` / `solver_03` | Inspect source | Invalid response, then unexpected experiment arguments | No proposal; no verification |
| `solver_04.py` / `solver_04` | Inspect source | Invalid response, then unexpected experiment arguments | No proposal; no verification; not a scientific correct-control abstention |

All four stopped safely at `invalid_response_limit` with original integrity and
cleanup true. Their CLI exit code is 2. These are incomplete model investigations,
not accepted repairs, measured scientific hypotheses, or successful correct-control
classification. There is no pooled mock/Llama repair-success score. Model narrative
and mock orchestration do not determine verifier decisions.

A further solver-01 run tested generic valid experiment-shape feedback after
schema errors, without changing numerical criteria or relaxing argument validation.
It received five genuine completions, inspected source and executed one positive
development experiment. The model then repeated the identical experiment request;
the host stopped at `duplicate_call` before rerunning it. No diagnostic report was
read, hypothesis/proposal produced or verification requested. Original integrity
and cleanup were true. Its artifact is retained separately from the four earlier
outcomes. The generic feedback change is the final implementation, not a change
to expected numerical answers.

The remaining fixtures were also rerun with that final feedback. Final-code
outcomes are therefore available for all four sources:

| Source | Final trace under `artifacts/` | Genuine responses | Actual outcome |
| --- | --- | --- | --- |
| `solver_01.py` | `milestone4-ollama-solver_01-schema-feedback.json` | 5 | One experiment executed; duplicate request blocked; no verification |
| `solver_02.py` | `milestone4-final-ollama-solver_02.json` | 5 | One experiment executed; duplicate request blocked; no verification |
| `solver_03.py` | `milestone4-final-ollama-solver_03.json` | 5 | One experiment executed; duplicate request blocked; no verification |
| `solver_04.py` | `milestone4-final-ollama-solver_04.json` | 5 | One experiment executed; duplicate request blocked; no verification or scientific abstention |

All final rows report genuine inference and `termination: duplicate_call`, with
two tools actually dispatched (inspect and experiment), two intervening invalid
responses and one repeated experiment request rejected before dispatch. No row
read the diagnostic report or produced a hypothesis, patch or verifier decision.
Every row retained original integrity and workspace cleanup. This is **0/3
verified model repairs**, with an incomplete correct-control investigation, in
this particular configuration. Failure handling worked; model investigation
performance did not meet the intended end-to-end demo behavior. Earlier failures
remain preserved, rather than being overwritten or silently counted as successes.

The final audit strictly parsed generated trace JSON, scanned for private report/
answer markers across all 19 retained traces and rechecked all reviewed hashes.
A generated
`artifacts/milestone4-validation-summary.json` records those outcomes and every
retained trace's backend, inference flag, termination and verifier decision.
The summary itself is host validation evidence, not a model input.

## Scientific/security limits and remaining work

The scope remains one PDE, periodic boundaries, uniform cell averages and one
declared first-order method, four hash-pinned original sources and three existing
host repair rules. Conservation is necessary but insufficient; expected diffusion,
inapplicable direction tests and unavailable refinement evidence remain distinct
from faults. The finite independent suite establishes only its measured contract.
No unknown-source/unseen-mechanism generalization or model-authored-code execution
is claimed. No numerical solver, diagnostic threshold, verifier rule, ground-truth
registry or original fixture was changed.

The external model has only serialized tool access, but the Python provider and
local Ollama server are trusted host software, not sandboxed extensions. The
reviewed worker still shares the host UID/filesystem/network. Public verifier
cases are not a securely private holdout; Python visibility and JSON projection
are not OS isolation. Raw code, arbitrary sources and unrestricted commands remain
disabled. Native model identity is checked against the returned tag, not a signed
weight attestation. Configuring a malicious local forwarding service is outside
this trust model.

Evidence IDs are checked mechanically; this does not prove that an LLM's prose is
semantically faithful. The final host explanation and verification fields carry
authority; cited narratives are explicitly investigator statements. Model behavior,
Ollama context truncation and runtime/hardware vary; temperature zero alone is not
a determinism claim for real inference. OpenAI-compatible requests do not configure
Ollama's local context window; no server/model settings were changed here.

Before a convincing Milestone 5 model demo, resolve the observed invalid experiment
requests and demonstrate complete, genuine Llama investigations with separately
recorded failures/abstentions. Improve provider compatibility generically, with
strict validation retained; do not hardcode fixture answers or substitute mock
traces. Hosted Muse remains a future adapter requiring official API/model/tool
documentation verification, credentials and separate hosted/paid-use approval.
FastAPI orchestration and custom HTML/CSS/JS investigation UI remain Milestone 5
work; no web workflow/server was started. Broader execution/private evaluation
requires separately tested OS isolation and independent verifier assets.
