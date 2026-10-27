# Milestone 2.1 — corrections and benchmark credibility

> Historical local validation retained unchanged below. Milestone 2.1 was later
> committed/pushed as `46b6e78c19b0bf37aa15e2c14d91fce2a1d971ef`; the owner reports
> GitHub Actions passed on Python 3.11, 3.12 and 3.13. Statements below describing
> uncommitted work or unrun remote checks refer to the original validation time.
> [Milestones 2.2/3 validation](milestone3_validation.md) records the new local work.

Follow-up recorded October 27, 2026 against published Milestone 2 baseline
`be4a422bc28bf8bce8aafdb219327102fa497a67`. The owner reports that baseline's
GitHub Actions passed on Python 3.11, 3.12 and 3.13. The measurements below are
new local results, not a new remote CI run. These corrections are uncommitted;
no commit, push, deployment, credential access or model API call was performed.

The [original validation](milestone2_validation.md) retains its historical
October 27 measurements. No trusted numerical solver, fault implementation,
mathematical formula, acceptance tolerance or dependency was changed.

## Fixed issues

1. **Generated budgets could abort an entire suite.** The supplied reproduction,
   N=32, a=1, T=1, CFL=.8, max_steps=100, ran its 40-step base case but then
   raised `ValueError: run requires 160 steps, exceeding max_steps=100` at N=128.
   Every derived probe now goes through `execute_generated`, which reuses the
   ordinary runner's validation. N=64 remains available; N=128 and N=256 retain
   their exact identifiers, required-step errors and original 100-step budgets.
   Refinement becomes inconclusive without removing valid measurements.
2. **Metamorphic construction/execution had no independent failure boundary.**
   Case transformations now happen inside that same helper. Tests cover a scaled
   domain needing an extra timestep, an unresolvable transformed spatial grid and
   doubled time overflowing representability. Other comparisons continue.
3. **Unavailable evidence needed a distinct record.** `UnavailableExperiment`
   has status `unavailable`, kind `generated_validation_error`, intended case ID,
   reason, preparation/validation elapsed time and a validated case when one
   exists (`case=null` if construction itself failed). It has no fabricated
   numerical output. Solver errors remain `execution_error`, confirmed NaN/Inf
   remains `nonfinite_output`, and valid measured violations remain diagnostic
   failures. Caller-invalid requests still raise before invoking any solver.
4. **Failure reasons were incomplete in multi-run checks.** Refinement and
   metamorphic evidence now identify each failed supporting experiment and its
   error kind. Linearity retains all failed dependencies, not just one. Generated
   unavailable attempts are counted separately from actual executions/errors
   and are excluded from summed/median solver elapsed times.
5. **Evaluation categories could be easier to overinterpret.** JSON schema
   version 2 explicitly separates known injected faults, new parameter samples,
   unseen fault mechanisms and correct-control false positives. Unseen mechanisms
   have status `unevaluated`, zero samples and a null rate. No generalization score
   merges those categories. Four challenging correct groups are separate from
   the legacy score denominators. Public case IDs are neutral `dev-probe-*` IDs;
   correctness labels/descriptions stay in evaluator records.
6. **Documentation described unpublished work as current.** README, AGENTS,
   architecture, provenance and benchmark documentation now distinguish the
   published baseline, owner-reported baseline CI, historical local measurements,
   and this uncommitted local correction milestone.

## Executed checks and regression tests

Environment: CPython 3.13.11, NumPy 2.4.3, pytest 9.0.1, Linux. No packages were
installed or downloaded. The source package is not installed in this environment,
so the two CLI runs used `PYTHONPATH=src` as documented in the original README.

```sh
python -m compileall -q src tests benchmarks
python -m pytest -q
PYTHONPATH=src python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261027 \
  --output artifacts/physicsbugbench-evaluator.json \
  --public-output artifacts/physicsbugbench-development.json
PYTHONPATH=src python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261028 \
  --output artifacts/physicsbugbench-evaluator-20261028.json \
  --public-output artifacts/physicsbugbench-development-20261028.json
```

- Compilation passed. Complete pytest: **267 passed in 5.12 seconds**, with
  warnings treated as errors. All 252 previous tests pass; 15 additional
  collected cases cover this follow-up. All original numerical tests are retained.
- Both CLI commands completed successfully and wrote strict JSON. All four
  artifact files were parsed, reserialized with `allow_nan=False`, and checked for
  correct development-only projection. Generated files remain ignored by Git.
- Repeated evaluations for both seeds were compared recursively after excluding
  timing fields, including all new controls/categories and public evidence.
- A saved pre-edit baseline evaluation was compared with the new seed-20261027
  evaluation: all original development/heldout inputs, outputs, diagnostic
  measurements, tolerances and verdicts match exactly apart from timing.
- `git diff --exit-code be4a422bc28bf8bce8aafdb219327102fa497a67 --
  src/physicsguard/numerics tests/test_numerics.py
  benchmarks/physicsbugbench/variants.py .github/workflows/tests.yml` passed.
  The trusted solver, numerical tests, six faults and CI matrix are unchanged.
- All Python files parsed using Python 3.11 grammar. A source AST check found
  no `exec`, `eval` or `__import__` calls. Static inspection confirms no new
  shell/source-text/model-output execution interface. This is not a sandbox test.
- `git diff --check` and local Markdown link checks passed. Actual follow-up
  execution on Python 3.11/3.12 and remote CI have not run during this milestone.

New/expanded regression names and outcomes:

| Pytest name | Outcome |
| --- | --- |
| `test_generated_refinement_budget_preserves_valid_measurements` | Passed: base/64-cell evidence survives; both unavailable levels recorded |
| `test_generated_metamorphic_step_budget_does_not_abort_other_checks` | Passed: scaled probe unavailable, time scaling/wrap still pass |
| `test_unrepresentable_generated_controls_are_structured` | Both parameter cases passed: invalid transformed grid and time construction |
| `test_all_caller_cases_are_validated_before_any_solver_execution` | Passed: a later invalid caller case prevents every solver invocation |
| `test_generated_execution_errors_are_distinct_from_infeasible_requests` | Passed: solver exception remains an execution error, not scientific failure |
| `test_generated_nonfinite_output_is_a_scientific_failure` | Passed: confirmed output Inf fails the finite-output property |
| `test_evaluation_categories_do_not_claim_unseen_fault_generalization` | Passed: separate categories; unseen mechanisms explicitly unevaluated |
| `test_challenging_correct_controls_keep_legitimate_truncation_error` | All four cases passed, with nonzero errors retained |
| `test_unavailable_generated_attempts_are_neither_executions_nor_passing_diagnostics` | Passed: unavailable count is 2, refinement pass count is 0 |
| `test_public_export_serializes_unavailable_generated_requests_without_labels` | Passed: strict JSON with IDs/reasons and no benchmark labels |
| `test_benchmark_replays_deterministically_apart_from_timing` | Both seed cases passed; existing replay test expanded |

Existing execution-error tests also verify every failed linearity dependency ID
is retained. Existing public-projection tests now cover all four added controls,
exclude their evaluator descriptions and reject correctness labels in case IDs.
The private-report rejection test remains an accidental-export guard, not evidence
of OS-enforced access control.

## Actual benchmark outcomes

The original corpus is unchanged: six known fault implementations and three
correct groups, with six base cases per fault and 12 correct base cases per split.

| Seed | Development detection | Parameter-holdout detection | Original control false positives, development / holdout | Additional challenging controls |
| --- | ---: | ---: | ---: | ---: |
| 20261027 | 6/6 | 6/6 | 0/3 / 0/3 | 0/4 falsely flagged |
| 20261028 | 6/6 | 6/6 | 0/3 / 0/3 | 0/4 falsely flagged |

For **both seeds**, each individual known fault type is detected (1/1) in each
split, and basic diagnostics flag 36/36 faulty base cases and 0/12 correct base
cases in each split. This is measured detection of the known mutations, not
localization, repair success or model performance.

| Per-seed component | Actual executions | Execution errors | Generated unavailable attempts | Inconclusive diagnostic records |
| --- | ---: | ---: | ---: | ---: |
| Development | 147 | 0 | 0 | 32 |
| Parameter holdout | 147 | 0 | 0 | 32 |
| Four challenging controls | 48 | 0 | 0 | 7 |

Thus each run contains 342 actual executions and 71 inconclusive diagnostic
records. Zero unavailable attempts here reflects the ordinary benchmark budgets;
the regression suite separately exercises infeasible probes. Inconclusive
records are not counted as passes. An unflagged control does not mean every
diagnostic was conclusive. The original splits retain 351 diagnostic records
each; the added controls contribute 56.

| Seed | Development suite time | Holdout suite time | Challenging suites time | Overall evaluator time, excluding file writes |
| --- | ---: | ---: | ---: | ---: |
| 20261027 | 0.1773 s | 0.1914 s | 0.4367 s | 0.8398 s |
| 20261028 | 0.1884 s | 0.1822 s | 0.4439 s | 0.8514 s |

Times are actual local measurements and vary with load. Fixed development cases
and challenging controls are identical across seeds; repeated execution does not
create additional independent examples. Only the heldout parameter samples vary.

Added correct cases retain substantial legitimate error:

| Control | Regime | Measured basic Linf error | Appropriate outcome |
| --- | --- | ---: | --- |
| PBB-C04 | N=32, CFL=.3, T=1.3; numerical diffusion | 0.0857337637 | Smooth accuracy passes; long-travel refinement inconclusive |
| PBB-C05 | N=8, CFL=.8, T=.23; low resolution | 0.0276898302 | Smooth accuracy passes; refinement uses separate resolved levels |
| PBB-C06 | Phase=11*pi+.7, a=-1, T=3.37 | 0.0376469611 | Correct multi-period analytical translation; long-travel refinement inconclusive |
| PBB-C07 | Square pulse, N=24, CFL=.4, a=-1 | 0.3367321161 | BV L1 accuracy passes; smooth refinement/direction are inconclusive |

The four groups use the same trusted implementation, not four independent solver
algorithms. Their observations do not establish cross-implementation coverage.

## Contract and fault-coverage audit

No formula error requiring correction was found. Existing formulas and thresholds
were retained; the following contracts remain explicit and tested:

| Diagnostic | Assumptions and limits checked |
| --- | --- |
| Conservation | Validated `PhysicsSpecification` rejects sources, nonperiodic BCs and unsupported PDE/state semantics; mass uses cell averages and a cancellation-safe rounding envelope |
| Accuracy | Actual initial data must match the independently integrated analytical profile; smooth Linf and discontinuous BV L1 bounds remain distinct |
| Direction | Requires separated physical/opposite references above the method error budget; zero travel and ambiguous times remain inconclusive |
| Stability/bounds | Finite-output failure differs from missing evidence; CFL and maximum principle require the supported upwind/Euler strategy, and bounds observe endpoints only |
| Refinement | Same physics, profile, CFL and observation time, resolved smooth data and decreasing dx; all required runs must be available |
| Invariance | Linear periodic upwind contract; every comparison checks its own supporting runs; missing evidence is not passed |
| Shared evidence | Units, assumptions, IDs, numerical tolerances and reasons remain recorded; arithmetic errors become inconclusive and strict JSON rejects nonfinite numbers |

The [benchmark audit](../benchmarks/physicsbugbench/README.md#fault-coverage-and-overlapping-signatures)
documents Fourier factors and observed signature overlap. In particular, F02
and F06 are conjugate anti-diffusive operators with equal growth magnitudes but
opposite phase; F01/F05 are conservative wrong-transport schemes on the tested
meshes; F03/F04 share mass failures but differ under translation/constant checks.
Accuracy/refinement/exact-shift failures overlap all six. These are distinct
operators with correlated symptoms, not six independent broad classes of unseen
scientific errors. A failed property alone does not identify a faulty source line.

## Boundary assessment, remaining risks and Milestone 3 readiness

No genuinely private holdout or secure executor is implemented. The public source,
published seeds, Python import separation, opaque identifiers and audience tags
are not security boundaries. Tests establish JSON projection and accidental-export
behavior only. No investigator process currently exists. Unseen fault mechanisms
remain unevaluated, explicitly represented by zero samples and a null rate.

Priorities before proceeding beyond trusted callables:

- **P0:** put untrusted candidate execution in a separate process/container with
  hard timeouts, CPU/memory limits, restricted filesystem/network access and no
  credentials. The current runner and case factories must remain trusted-only.
- **P0:** preserve immutable originals and implement reversible restricted patch
  application plus independent verifier-owned tests. Candidate/model decisions
  cannot override physics, diagnostics or acceptance criteria.
- **P1:** genuinely private evaluation requires evaluator-owned samples/manifests,
  faults and tests inaccessible to the investigator's files/imports/tools/network.
  Do not mount the repository root or evaluator artifacts into that environment;
  public benchmark source cannot be treated as a hidden answer key.
- **P1:** expand mechanism and implementation diversity through independently
  justified experiments before claiming generalization. Current signatures are
  correlated; endpoint-only monitoring and ambiguous observations remain limits.

The corrected evidence layer is ready to support a **separately authorized**
Milestone 3 on restricted repair representation and independent verification.
It is not ready to execute arbitrary patches or model-generated Python through
the existing runner. No repair execution, model integration, agent planning,
FastAPI workflow or web application was built or automatically started here.

## File-by-file changes

| File | Change |
| --- | --- |
| `src/physicsguard/schemas/results.py` | Typed unavailable attempt, common case ID access and report attempt union |
| `src/physicsguard/experiments/runner.py` | Shared generated-case construction/validation boundary; explicit trusted-callable/factory documentation |
| `src/physicsguard/experiments/scenarios.py` | Share the existing refinement resolution tuple; values unchanged |
| `src/physicsguard/diagnostics/suite.py` | Route each generated refinement through the shared helper; keep partial evidence |
| `src/physicsguard/diagnostics/invariance.py` | Isolate each transformation, continue independent checks, retain all failed dependencies |
| `src/physicsguard/diagnostics/refinement.py` | Inconclusive missing-run evidence names every failed ID/kind/reason |
| `src/physicsguard/diagnostics/_common.py` | Shared supporting-attempt error formatting; formulas unchanged |
| `benchmarks/physicsbugbench/controls.py` | Four new challenging correct groups with neutral public case IDs |
| `benchmarks/physicsbugbench/evaluate.py` | Separate unavailable accounting, explicit evaluation categories and separate challenging-control metrics; schema version 2 |
| `tests/test_experiments.py` | Generated budget/construction/grid/error/nonfinite regressions and full caller prevalidation |
| `tests/test_physicsbugbench.py` | Correct-control measurements, category/accounting/export checks and both-seed replay |
| `README.md` | Published baseline/current local status, both reproduction commands and category/error semantics |
| `AGENTS.md` | Current published baseline and local follow-up status |
| `docs/architecture.md` | Outcome contracts and required future execution boundaries |
| `docs/milestone2_validation.md` | Historical-status clarification and separate follow-up link; original measurements preserved |
| `docs/hackathon_provenance.md` | Clarify published baseline versus historical/local follow-up evidence |
| `benchmarks/physicsbugbench/README.md` | Fault overlap audit, new controls, categories and limits |
| `docs/milestone2_1_validation.md` | This follow-up evidence, regression inventory and readiness assessment |
