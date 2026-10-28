# Milestone 3.1 — repair hardening and scientific verification audit

Recorded October 27–28, 2026 against published Milestone 3 baseline
`622c9cd1ac11e9247a4746555faed3a9485f1abf`. The owner reports that published
commit passed GitHub Actions on Python 3.11, 3.12 and 3.13. Its original local
318-test validation, three repairs and 8 rejected/2 inconclusive controls remain
preserved in [the historical record](milestone3_validation.md). They have not
been relabeled as CI measurements or replaced by this follow-up.

This work is local, uncommitted and unpushed. No model calls, credentials, API
credits, publication, deployment, license changes or history rewrites occurred.

## Demonstrated problems before modification

The following were reproduced against the baseline before implementation:

1. Source policy accepted `scale = 9 ** (9 ** 9)`, `scale = 1e309` and
   `scale = state[dt]`. These needed no power, infinite constant or dynamic index
   for any legitimate supported repair. Execution limits were a later fallback.
2. Corrupting a disposable candidate then raising a body exception skipped the
   integrity check after `yield`. The temporary directory was removed, but no
   corruption evidence was attached to the original exception.
3. The public verifier accepted a positive-velocity-only direction patch when
   given a positive-only custom verification plan. This demonstrated a host
   API weakness; no Meta agent was involved.
4. In a controlled audit harness, removing the candidate direction record for
   independent case `verify-02` still produced ACCEPTED: another direction pass
   satisfied the family-level check. This was host-side report fault injection,
   not a demonstrated ability of candidate code to mutate parent reports.
5. Tool proposals for solver 01 and solver 02 collided at
   `proposal-490fe581a243b953`: both repair to identical source bytes. The second
   cached proposal replaced the first despite representing a different source.

Source inspection also found a checked-text/import-loader reopen gap and worker
cleanup that killed a process group only while its leader was running. New tests
exercise exact-byte compilation and a real forked descendant after leader exit.
A final controlled report audit also reproduced acceptance after removing an
aggregate diagnostic's supporting execution while retaining its passing record.
Coverage now requires those referenced executions; the regression is inconclusive.
These observations do not establish arbitrary-code sandbox escape claims.

## Corrections and unchanged scientific contracts

The policy now admits one assignment RHS with **48 AST nodes, depth 10 and finite
numeric literals of magnitude at most 128**. No exponentiation, vector arithmetic,
arbitrary variable, call, attribute, comprehension or dynamic indexing is allowed.
Boundary reads are limited to `state[0]` and `state[-1]`; neighbor choices are
adjacent offsets +1/-1. Division accepts cell width or a bounded literal of
magnitude at least 1e-12. These are explicit source-policy limits, not diagnostic
tolerances. Bounded conditionals permit meaningful bad-patch gate controls.

The full AST outside the edited RHS, allowed assignment, hypothesis mechanism,
original/proposed hashes, structured line replacement and canonical unified diff
must agree. Proposal JSON rejects duplicate keys and nonfinite numbers. Original
snapshots are never silently refreshed to accommodate stale proposals.

Source reads use no-follow directory-descriptor traversal, reject nonregular
files/hardlinks and check file identity/metadata before and after reading. The
child compiles the exact bytes checked against the proposed hash, rather than
reopening them through an import loader. Parent and child both enforce source
identity; request/reply ordinals and hashes bind numerical evidence to that
candidate. Immutable OS mounts are still required against a hostile same-UID
environment: Python checks do not exclude every rename or concurrent-write race.

Workspace integrity checks inspect both copies in `finally` on successful and
exceptional exits. Cleanup always runs. Integrity/cleanup failures attach notes
to an existing body exception rather than masking it. The original repository
file is never overwritten or restored over an independent owner edit.

Production `verify_candidate` has **no plan or caller-report argument**. It owns
the mandatory six-case plan and freshly measures original/candidate development
and independent evidence. The explicitly internal testing hook is absent from
JSON dispatch. Plans validate nonempty unique cases/families, physical independence
including generated development probes, supported strategy, signed smooth motion,
profiles, grids and domains. Descriptive unit relabeling cannot create a new
experiment. Infeasible plans/generated probes retain unavailable evidence.

`coverage.py` requires the exact expected diagnostic records for every requested
case and aggregate experiment. Missing, duplicated or falsely inapplicable
moving-case direction evidence blocks acceptance. Direction applicability is
recomputed from existing diagnostics. Stationary, ambiguous and discontinuous
direction checks remain legitimately inapplicable; they cannot substitute for
identifying evidence on both signed smooth groups. All mandatory independent
families must have conclusive applicable evidence. Missing evidence never passes.

The gate compares previously passing properties and validates hypothesis evidence
against fresh measurements. Numeric execution failures, confirmed nonfinite
outputs, generated-unavailable probes, protocol/resource/time failures and measured
scientific violations remain distinguishable. Norms need not decrease everywhere.
Finite experiments support acceptance under this contract, not universal proof.

Git comparison confirms **no changes** to `numerics/`, `diagnostics/`,
`experiments/`, analytical references, diagnostic thresholds, original
PhysicsBugBench implementations, the four original source fixtures,
`tests/test_numerics.py` or the GitHub Actions workflow/matrix.

## Executed validation

Environment: non-root Linux, CPython **3.13.11**, NumPy **2.5.4**, pytest **9.2.0**.
Existing `.venv/bin/python` was used; no dependencies were installed/downloaded.
The following ran from the repository root:

```sh
.venv/bin/python -m compileall -q src tests benchmarks
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_source_repair.py -q
.venv/bin/python -m pytest tests/test_repair_hardening.py -q
.venv/bin/python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261027 --output artifacts/physicsbugbench-evaluator.json \
  --public-output artifacts/physicsbugbench-development.json
.venv/bin/python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261028 --output artifacts/physicsbugbench-evaluator-20261028.json \
  --public-output artifacts/physicsbugbench-development-20261028.json
.venv/bin/python -m benchmarks.source_repair.evaluate \
  --output artifacts/source-repair-evaluator.json
```

| Check | Actual outcome |
| --- | --- |
| Compileall | Passed |
| Complete suite | **405 passed in 21.85 s** |
| Original source-repair module, updated earlier-rejection expectations | **57 passed in 14.07 s** |
| New hardening module | **81 passed in 3.50 s** |
| Python 3.11 grammar | Parsed all 62 Python files under src/tests/benchmarks |
| Strict JSON | Evaluator/development/source reports parsed with duplicate-key and nonfinite rejection |
| Reproducibility | Full source evaluations match after excluding runtime fields, checked by pytest |
| Original source hashes and cleanup | True for four fixture reports and all 14 negative attempts |
| GitHub workflow | Existing Linux Python 3.11/3.12/3.13 matrix unchanged |
| Local Python 3.11/3.12 execution / new remote CI | **Not executed** |
| Container build/runtime/security tests | **Not executed**; Docker and Podman unavailable |

New regression names include (parameterized cases account for the 81 tests):

- `test_bounded_expression_rejects_unsafe_arithmetic`
- `test_structured_patch_fields_cannot_disagree`
- `test_hypothesis_cannot_claim_different_assignment`
- `test_workspace_integrity_checked_on_every_exit`
- `test_cleanup_failure_preserves_body_exception`
- `test_fifo_and_ancestor_symlink_are_rejected_without_blocking`
- `test_directory_substitution_between_check_and_open_is_rejected`
- `test_mutation_during_snapshot_read_is_rejected`
- `test_worker_compiles_checked_bytes_instead_of_reopening_source`
- `test_public_verifier_does_not_accept_reports_or_plans`
- `test_verification_plan_rejects_empty_and_duplicate_records`
- `test_plan_contract_blocks_inadequate_evidence`
- `test_relabeling_units_does_not_make_development_case_independent`
- `test_every_required_moving_case_needs_its_own_direction_evidence`
- `test_aggregate_pass_cannot_replace_missing_supporting_execution`
- `test_worker_failure_never_accepts_patch`
- `test_baseline_execution_failure_is_inconclusive`
- `test_fabricated_evidence_case_ids_cannot_be_accepted`
- `test_protocol_rejects_malformed_nonfinite_duplicate_json`
- `test_request_and_response_size_limits_are_enforced`
- `test_child_failures_are_classified_reaped_and_cleanup`
- `test_parent_rejects_unapproved_candidate_hash`
- `test_startup_failure_reaps_child`
- `test_cpu_limit_exit_is_unavailable_evidence`
- `test_numeric_errors_are_distinct_from_protocol_and_resource_failures`
- `test_cleanup_terminates_descendants_after_leader_exit`
- `test_tool_json_dispatch_rejects_privileged_arguments`
- `test_tool_stable_ids_duplicate_cache_and_bounded_selection`

The source-repair module also adds static presentation and independent correct
control checks, plus domain/grid/profile/wrong-speed rejection expectations.
Protocol/error-classification probes use explicitly test-owned fake child programs,
never a configurable product command. Real child timeout, process termination,
CPU-limit exhaustion, pipe corruption/oversize, startup failure, and forked-child
cleanup were exercised. Existing `/proc` tests check actual worker CPU/address
limits. No container isolation test was silently treated as passing.

## Actual source repairs and benchmark outcomes

The stable known-fixture result remains **3/3 detected, usefully localized,
proposed, source-valid and independently ACCEPTED**. Each replaces one line:

```diff
 # solver_01.py:8
-    neighbor_offset = -1 if speed > 0.0 else 1
+    neighbor_offset = 1 if speed > 0.0 else -1
 # solver_02.py:9
-    scale = dt
+    scale = dt / dx
 # solver_03.py:12
-        upstream[0] = state[0]
+        upstream[0] = state[-1]
```

For development case `dev-sine-m1-+1` (64 cells, [0,1), speed 1, CFL .8,
time .23, offset 1, amplitude .2, mode 1, phase .37), independent measurements are:

| Source | Absolute L1 before → after | Absolute mass drift before → after | Development failures | Additional failures |
| --- | --- | --- | --- | --- |
| solver_01.py | .2507138736 → .0018863498 | 0 → 0 | 12 → 0 | 10 → 0 |
| solver_02.py | .1660746904 → .0018863498 | 0 → 0 | 9 → 0 | 8 → 0 |
| solver_03.py | .0351641992 → .0018863498 | .0334802069 → 0 | 9 → 0 | 9 → 0 |

All three have every verification stage passing and no observed regression.
The original correct fixture abstains with no proposal or modification: **1/1**.
False accepted repairs on that control: **0**; known-repair regression rate **0/3**.
Average changed source lines: **1**. All original/copy integrity and cleanup flags
are true. There are 18 candidate additional base-case evaluations across six
configurations, not 18 distinct repaired defects.

Known-fixture cost is **272 solver requests / 16 worker sessions**, increased from
historical 221/13 because the verifier now freshly measures its own development
baseline. The recorded CLI evaluation took **5.6278 s** including negative controls
and variation/correct-control evaluation; known-repair verification totaled
**1.6514 s**. Timing varies with load and includes subprocess overhead.

| Gate control | Measured decision and reason |
| --- | --- |
| Positive-only direction edit | REJECTED; development passes, independent negative motion fails accuracy/direction |
| Domain-specific scaling | REJECTED; development passes, additional accuracy/wrap/refinement/scaling fail |
| Grid-specific seam edit | REJECTED; development passes, additional conservation/accuracy/translation/refinement/wrap fail |
| Profile-conditional seam edit | REJECTED; conservation and other criteria fail; previously passing boundedness/linearity regress |
| Conservative half-speed update | REJECTED; conservation passes, independent accuracy fails |
| Vector coefficient / infinite literal / zero divisor / huge power | REJECTED by source policy before candidate execution |
| Invalid syntax / stale hash / test path / unrelated path | REJECTED before candidate execution |
| Valid edit with insufficient generated-probe budget | INCONCLUSIVE; `verify-01-n256` needs 73 steps with max_steps=50 |

Totals: **14 attempts, 13 REJECTED, 1 INCONCLUSIVE, 0 ACCEPTED**. The original ten
controls now yield 9 rejections/1 inconclusive: the huge-power case moved from
timeout to source rejection. Vector, infinite-literal and zero-divisor cases also
stop earlier than in Milestone 3. Their earlier dynamic-failure evidence is
preserved historically; it is not claimed to execute under the new grammar.
Separate worker tests still demonstrate timeout/resource INCONCLUSIVE handling.

PhysicsBugBench was rerun for both seeds **20261027 and 20261028**. For each:

| Population | Detection / false positives | Inconclusive diagnostics |
| --- | --- | --- |
| Development, six known faults | 6/6 detected; 0/3 correct groups flagged | 32 |
| Parameter holdout, same six mechanisms | 6/6 detected; 0/3 correct groups flagged | 32 |
| Challenging correct controls | 0/4 flagged | 7 |

These are detection results, not repair scores or unseen-mechanism generalization.
Inapplicable/inconclusive checks are retained and never counted as passes.

## Source variation and independent correct controls

Twelve static probes cover spacing, RHS parentheses, comments and equivalent
expressions across the three known faulty sources. **9/12** produce syntactically
valid proposals; **3/12** unfamiliar equivalent expressions correctly remain
unsupported. The nine formatting probes have identical ASTs and reuse original
program evidence. The three equivalent-expression probes test source recognition
only. No varied source is executed or counted as independently repaired: every
unreviewed source remains outside the execution policy. This tests formatting and
recognition limits, not new mutation mechanisms.

Two newly authored correct implementations use explicit face fluxes and convex
mixing/concatenation respectively. As trusted evaluator callables, **2/2** complete
scientific evaluation with zero flagged defects and zero unnecessary proposals.
The reviewed-source policy refuses **2/2**: mathematical validation as a trusted
callable is distinct from supported source repair execution. They share the
existing result/configuration and time scheduler, but use separate update
structures. They are additional correct controls, not independent external solvers.

Genuinely unseen mutation mechanisms remain **0 samples, unevaluated, null rate**.
Known fixtures, parameter variation, source formatting, bad proposals and correct
controls are separate benchmark categories. No model performance is reported.

## Execution and tool boundary assessment

The worker remains **reviewed non-root Linux code plus one bounded expression**.
It runs with sanitized environment, controlled cwd, 2-second default per-request
and 5-second startup deadlines, 10-second CPU, 2 GiB address space, 64-file/process,
1 MiB file-size limits and no core dumps. Parent request/response caps are 1/2 MiB,
with at most 64 requests per worker. Nonfinite JSON and duplicate keys are rejected.
Terminal failures kill/reap the child group; numerical errors remain measurements
in parent-owned diagnostics. Limits are defenses in scope, not complete isolation.

There is no enforced host filesystem/network/credential separation, and UID-based
process limits are not a namespace. AST checking, a subprocess, a timeout, Docker
or rootless mode alone does not make arbitrary Python safe. Raw `origin="meta"`
execution remains disabled. No arbitrary-source endpoint or command override was
added. The worker's `exec` receives only compiled, hash-checked, constrained
reviewed bytes in the child; no model text is evaluated in the application.

`RepairTools.call(operation, arguments)` returns JSON only. It validates exact
argument sets, experiment assumptions/budgets and operation IDs. A caller cannot
supply plans, reports, tolerances, arbitrary source edits or commands. Selection
of a supported operation asks the host to render its deterministic rule; it is
not model-authored source. IDs bind source and experiment evidence, duplicate
experiments reuse immutable cache entries while still consuming call budget,
and returned dictionaries cannot mutate stored records. Verification summaries
strip detailed private-case reasons; full reports remain host-only.

**These are host API contracts, not an OS access boundary.** Internal Python
hooks, public source registries and public verifier cases are accessible to a
host process. A future investigator must receive only serialized dispatch
messages and have no evaluator imports, files, answers, privileged callables or
private cases. A real private evaluation requires independently maintained data
in a separate protected environment. This deployment has not been built.

The optional [Linux container recipe](../dev/README.md) specifies non-root,
offline runtime, read-only image, dropped capabilities, no-new-privileges,
CPU/memory/PID caps, disposable tmpfs/artifacts and no host secret mounts. It is
**untested** because neither Docker nor Podman is installed. The image includes
public verifier assets and is an evaluator image, never a private investigator
environment. Record a verified official base-image digest/platform for replay;
the default tag alone is not a bit-reproducible build.

## Exact file-by-file changes

| File | Change |
| --- | --- |
| `src/physicsguard/repair/policy.py` | Bounded finite scalar grammar and hypothesis/assignment consistency |
| `src/physicsguard/repair/proposals.py` | Source-bound proposal IDs; preserve parentheses/comments around edited AST values |
| `src/physicsguard/repair/sources.py` | Descriptor-anchored no-follow reads, nonblocking opens and snapshot identity checks |
| `src/physicsguard/repair/workspace.py` | Exceptional-exit integrity and cleanup without masking the body exception |
| `src/physicsguard/repair/verification_cases.py` | Host plan validation and physical experiment signatures |
| `src/physicsguard/repair/coverage.py` | New exact per-case/aggregate evidence coverage checks |
| `src/physicsguard/repair/validator.py` | Host-only production plan, fresh baselines, per-case gate and evidence validation |
| `src/physicsguard/repair/protocol.py` | New finite duplicate-free bounded JSON framing |
| `src/physicsguard/repair/_worker.py` | Compile checked bytes, source-bound request identity and strict error protocol |
| `src/physicsguard/repair/executor.py` | Protocol/shape/clock validation, classified terminal failures and lifecycle cleanup |
| `src/physicsguard/repair/tools.py` | Bounded JSON dispatch, structured edit selection, cache/ID integrity and sanitized summaries |
| `src/physicsguard/repair/workflow.py` | Use protected verifier signature |
| `src/physicsguard/schemas/repairs.py` | Plan validation, strict proposal JSON, process statuses and fresh-baseline evidence field |
| `benchmarks/source_repair/evaluate.py` | Four targeted bad edits, fresh-baseline cost accounting and separate evaluation categories |
| `benchmarks/source_repair/variations.py` | New static recognition probes and correct-control evaluation |
| `benchmarks/source_variations/__init__.py` | Trusted evaluator control package marker |
| `benchmarks/source_variations/correct_flux.py` | New correct face-flux implementation |
| `benchmarks/source_variations/correct_convex.py` | New correct convex mixing implementation |
| `tests/test_source_repair.py` | Updated early-rejection expectations and additional bad/format/correct controls |
| `tests/test_repair_hardening.py` | New 81-case policy, filesystem, verifier, protocol/lifecycle and tool regressions |
| `.dockerignore` | Restricted build context excluding secrets/caches |
| `dev/repair.Dockerfile` | Untested non-root Linux evaluator image recipe |
| `dev/repair-requirements.txt` | Pinned container development/build dependencies |
| `dev/README.md` | Offline restricted runtime commands, reproducibility and explicit untested/security limits |
| `README.md` | Published status, current metrics, host tool/verifier scope and reproduction links |
| `AGENTS.md` | Published Milestone 3 and local Milestone 3.1 status |
| `docs/architecture.md` | Enforced contracts versus deployment-only trust boundaries |
| `docs/hackathon_provenance.md` | Publication follow-up and newly authored hardening/control provenance |
| `docs/milestone3_validation.md` | Publication clarification preserving all historical measurements |
| `docs/milestone3_1_validation.md` | This separate executed validation/audit report |

Generated artifacts are ignored, evaluator-owned local outputs; they are not
source changes or investigator inputs.

## Remaining risks and Milestone 4 readiness

- **Priority 1, orchestration boundary:** implement/test serialized tool transport
  to one real investigator without exposing host Python objects or verifier
  files. Public Python privacy is insufficient. Keep raw model patches disabled.
- **Priority 1, broader execution:** arbitrary/unreviewed source remains unsupported.
  Before enabling it, independently test no-network/no-secrets/non-root isolation,
  restricted read-only mounts, immutable verifier/originals, CPU/memory/process
  and hard wall limits, restricted commands and disposable patches.
- **Priority 2, scientific coverage:** finite endpoint tests, one PDE/method,
  three explicit source rules and public cases remain limited. Expand evaluation
  through independently authored mechanisms/correct implementations before
  claiming unknown-source or unseen-mechanism repair generalization.
- **Priority 2, platform validation:** run the container recipe and new remote
  3.11/3.12/3.13 matrix after owner authorization. Only current non-root Linux
  Python 3.13 execution is measured here.

The deterministic host engine is ready for bounded reviewed-fixture tool
orchestration; it is not ready for arbitrary model-authored Python. Milestone 4
should (1) verify official Meta SDK/model/tool-calling documentation and obtain
separate credentials/paid-use authorization if needed, (2) wire one real
investigator to the explicit JSON operations, (3) capture actual hypotheses,
operation selections and tool outputs with budgets, and (4) compare those results
with this separately labeled deterministic baseline. The host keeps verification
plans/tolerances and acceptance decisions. No Meta integration, API/UI, additional
repair rules or autonomous framework was started during this milestone.
