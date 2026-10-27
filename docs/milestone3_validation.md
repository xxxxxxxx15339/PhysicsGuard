# Milestones 2.2 and 3 — measured source-code repair

Recorded October 27, 2026 against approved published baseline
`46b6e78c19b0bf37aa15e2c14d91fce2a1d971ef`. The owner reports that Milestone 2.1
passed GitHub Actions on Python 3.11, 3.12 and 3.13. Earlier local measurements in
the Milestone 2/2.1 documents remain historical, not retroactive CI claims.
This new implementation is local and uncommitted. No commits, pushes, publication,
deployment, credentials or paid/model API calls were made.

## Implemented workflow and scope

The workflow is source inspection -> measured development diagnostics -> explicit
AST-pattern hypothesis/localization -> one-line diff -> disposable source copy ->
independent additional experiments and regression comparison -> ACCEPTED,
REJECTED or INCONCLUSIVE verification. A correct solver has no proposal/verification
attempt and records abstention; this is not a fourth verification decision.

Four newly authored standalone direct-upwind fixture modules use the existing
configuration/result and timestep scheduler. They do not call the trusted solver.
Three contain localized errors; one is correct. They share a deliberately simple
scaffold, not independent external project provenance. The original six-branch
PhysicsBugBench corpus, trusted numerics, analytic references and scientific
acceptance thresholds are unchanged. No external code/assets or dependencies
were added.

The proposer takes only a source snapshot and development diagnostic report.
It recognizes three explicit assignment patterns, gated by relevant failed
properties. It does not import evaluator labels, expected lines, reference
patches or additional verifier cases. Proposals honestly record origin
`deterministic`; negative controls record `human`. These are limited source-pattern
rules, not Meta reasoning, general-purpose debugging or unseen-code localization.

The source policy pins four reviewed original hashes and accepts one bounded
assignment RHS in `advance`. A strict one-file/one-hunk/one-line diff, structured
edit, source hashes, full AST equality outside the edited expression and syntax
must agree. Calls, attributes, extra statements/imports, unrelated paths, symlinks,
hardlinks, stale/conflicting edits and wholesale solver replacement are rejected.
Atomic writes create copies in a fresh disposable directory. Neither acceptance
nor failure overwrites original source. Concurrent owner edits are detected and
left intact rather than restored over.

The parent performs all diagnostics. A persistent separate worker executes only
reviewed solver calls, rechecking the original hash and candidate AST itself.
IPC uses bounded JSON rather than pickle/source strings as executable requests.
The validator owns a six-case plan with different signed speeds, cell counts,
profiles, domain lengths, phases and observation times. These cases are not sent
to the proposer; repeated development configurations, including generated probes,
are rejected as insufficiently independent. Proposal-requested checks cannot
remove mandatory verification families or weaken thresholds.

Acceptance requires sufficient executed evidence, resolved independent baseline
failures, passing applicable scientific criteria, at least one conclusive pass in
each mandatory family, no new previously-passing-property failure/lost evidence,
and original integrity/cleanup. Not every error norm must decrease. Expected
inapplicable direction checks on square/stationary cases remain inconclusive.
Missing required evidence, timeouts or unsupported execution are INCONCLUSIVE;
they never count as accepted or as a measured mathematical failure.

## Reproduction and executed checks

Environment: CPython 3.13.11, NumPy 2.4.3, pytest 9.0.1, non-root Linux. No packages
were installed or downloaded. From the repository root, use an editable install
or prefix the CLIs with `PYTHONPATH=src`, as used for these local runs:

```sh
python -m compileall -q src tests benchmarks
python -m pytest -q
python -m pytest tests/test_source_repair.py -q
PYTHONPATH=src python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261027 \
  --output artifacts/physicsbugbench-evaluator.json \
  --public-output artifacts/physicsbugbench-development.json
PYTHONPATH=src python -m benchmarks.source_repair.evaluate \
  --output artifacts/source-repair-evaluator.json
```

- Compilation passed. Full pytest: **318 passed in 17.42 s**; focused source repair
  suite: **51 passed in 12.89 s**. All previous 267 tests remain passing, including
  numerical and generated-experiment budget regressions. Warnings remain errors.
- Tests cover schema/diff parsing, hashing, traversal/symlink/hardlink rejection,
  source scope/size limits, disposable cleanup, original integrity and concurrent
  owner edits, all three real repairs, correct-source abstention, independent
  case separation, scientific regression detection, missing evidence, nonfinite
  output, execution failure, timeouts and JSON reproducibility.
- `test_timeout_terminates_process_and_cleans_workspace` observes the killed child
  and removed workspace. `/proc` checks observe a separate PID, CPU limits of
  10 seconds and address-space limits of 2147483648 bytes. This is resource-limit
  evidence, not proof of complete isolation.
- `test_future_model_origin_is_disabled_without_executing_source` uses an explicitly
  synthetic reserved-origin tag to test refusal. No product report attributes a
  repair to Meta; there were no model responses or calls.
- `test_bounded_tools_do_not_export_verifier_cases_or_answers` checks source lines,
  development evidence, verification summary/history, no private case parameters,
  immutable returned history and bounded operation counts.
- Repeated complete repair evaluations, including all ten negative controls,
  match recursively after excluding runtime fields. Strict JSON serialization
  succeeds; original hashes and cleanup flags remain intact.
- Git comparison against the baseline confirms no change to trusted numerics,
  original numerical tests, accuracy/conservation/stability/refinement formulas or
  the original PhysicsBugBench package. `validate_cases` only shares existing
  collection preflight between the scientific suite and source executor.
- Python 3.11 grammar, whitespace and local documentation links were checked.
  The 3.11/3.12/3.13 CI matrix is retained with a source repair CLI step added.
  Follow-up tests were not executed locally under 3.11/3.12 or on remote Actions.
- An offline wheel build passed with no index/dependency downloads. An unpacked
  wheel under isolated Python (`-I`) repaired reviewed source using an explicit
  `SourceStore`, including child worker execution, strict JSON and original
  integrity. Benchmark/PDF assets are excluded from the wheel. All three README
  Python examples executed successfully from the source checkout. The default
  fixture store/benchmark CLIs are repository-local; installed-library users
  must explicitly supply the reviewed fixture directory.
- Container/network-namespace/mount-isolation security tests were **not executed**:
  that isolation is not implemented and arbitrary untrusted execution is disabled.

Generated evaluator JSON contains full source snapshots, diffs, original/candidate
hashes, before/after reports, additional-case evidence, decisions and integrity
results. It is not an investigator-facing artifact. Generated files are ignored
by Git. No actual original fixture file is modified, even by the rejected cases.

## Actual repairs and measurements

Development measurements below use the first case: N=64, domain [0,1), a=+1,
CFL=.8, T=.23, exact cell-average sine with offset 1, amplitude .2, phase .37.
L1 is the absolute domain-integrated discrete norm, not a relative error.

| Source / supported mechanism | L1 before | L1 after | Absolute mass drift before / after | Direction before / after | Decision |
| --- | ---: | ---: | ---: | --- | --- |
| solver_01.py / reversed transport | 0.2507138736 | 0.0018863498 | 0 / 0 | fail / pass | ACCEPTED |
| solver_02.py / missing dx division | 0.1660746904 | 0.0018863498 | 0 / 0 | inconclusive / pass | ACCEPTED |
| solver_03.py / incoming seam | 0.0351641992 | 0.0018863498 | 0.0334802069 / 0 | inconclusive / pass | ACCEPTED |

Zero measured drift in selected float64 runs is not a requirement of exact zero
for generic data; existing rounding tolerances remain in force. After repairs,
nonzero truncation error remains appropriate for first-order upwind.

Actual localized diffs (only one replaced line each):

```diff
--- a/solver_01.py
+++ b/solver_01.py
@@ -8 +8 @@
-    neighbor_offset = -1 if speed > 0.0 else 1
+    neighbor_offset = 1 if speed > 0.0 else -1
```

```diff
--- a/solver_02.py
+++ b/solver_02.py
@@ -9 +9 @@
-    scale = dt
+    scale = dt / dx
```

```diff
--- a/solver_03.py
+++ b/solver_03.py
@@ -12 +12 @@
-        upstream[0] = state[0]
+        upstream[0] = state[-1]
```

Scientific localization evidence is accuracy/direction for source 01,
accuracy/domain scaling/refinement for source 02, and conservation/cyclic
translation/periodic-wrap failure for source 03. AST inspection then associates
those failures with the respective `advance` assignment. Source 03's injected
seam mistake affects positive velocity only; additional negative-velocity cases
serve as regression checks. Source 04 has no failed development property and
receives no patch.

Independent first-case measurements use N=96, domain [-.2,1.5), a=1.3,
CFL=.67, phase=1.1, T=.19*1.7/1.3, and the same cell-average sine family:

| Source | Independent L1 before | Independent L1 after | Independent mass drift before / after |
| --- | ---: | ---: | ---: |
| solver_01.py | 0.3998786523 | 0.0028080385 | 0 / 0 |
| solver_02.py | 0.2393377050 | 0.0028080385 | 0 / 0 |
| solver_03.py | 0.0316219277 | 0.0028080385 | 0.0298595227 / 0 |

All five verification stages pass for these three candidates. Development failure
counts drop from 12/9/9 to 0/0/0; additional-case failure counts drop from 10/8/9 to
0/0/0. Applicable required evidence is conclusive. Each corrected development
report retains two inapplicable square-profile direction results; each additional
report retains three inapplicable direction results (two squares, one stationary
constant). They are not counted as passing. Full original integrity and temporary
cleanup are true for all four fixture reports and all ten negative attempts.

## Measured populations and rejection controls

| Known source fixture metric | Actual result |
| --- | ---: |
| Defective source files | 3 |
| Detected / useful localization / proposals | 3 / 3 / 3 |
| Source-valid proposals / independently accepted | 3 / 3 |
| Rejected / inconclusive deterministic fixture attempts | 0 / 0 |
| Correct controls / abstentions / false repairs | 1 / 1 / 0 |
| Observed regression rate, known-fixture attempts | 0/3 |
| Average replaced source lines | 1 (one removal plus one addition in the diff) |
| Solver requests / worker sessions, known fixtures | 221 / 13 |
| Candidate additional base-case evaluations | 18 across 6 unique parameter configurations |

One recorded evaluation took 4.7242 s excluding final file serialization/writing;
the three known repairs' verification stages totaled 1.2472 s. Timings vary with
load and include subprocess overhead. Negative controls are separate from repair
recall and add verification cost; their runtime is included in overall evaluation.

All ten negative/unavailable controls are explicitly human-authored test proposals:

| Control | Actual result / evidence |
| --- | --- |
| Constant positive offset direction fix | REJECTED: passes positive-only development, fails additional negative velocity |
| Spatial coefficient with extra state-dependent factor | REJECTED: newly damages conservation and previously passing properties |
| Last-short-step nonfinite coefficient | REJECTED: actual nonfinite-output records and finite-property failure |
| Division-by-zero coefficient | REJECTED: execution contract fails; missing scientific evidence is not called a pass |
| Huge arithmetic computation | INCONCLUSIVE: hard timeout terminates child; no mathematical success/failure invented |
| Unclosed expression | REJECTED before execution: syntax invalid |
| Stale original hash | REJECTED before execution |
| Targeting numerical tests | REJECTED before execution: path/scope violation |
| Targeting README | REJECTED before execution: unrelated file |
| Valid edit with inadequate generated-refinement budget | INCONCLUSIVE: unavailable required verification evidence retained |

Totals: **0 accepted, 8 rejected, 2 inconclusive**. These are gate tests, not ten
extra solver defects or ten failed heuristic repairs. The original diagnostic
benchmark still measures 6/6 known faults and 0/3 original-control false positives
in both development and parameter holdout, plus 0/4 challenging-control false
positives. No 6/6 detection score is transferred to source repair.

Source mutation patterns not used to develop the rules have **0 tested samples**
and are explicitly unevaluated with a null success rate. Additional parameter
cases exercise the same known source mechanisms; they are not new mechanisms or
an independently secured private corpus. Localization is scored after investigation
by matching a measured hypothesis's mechanism/range to evaluator-only injected
locations; that metadata is never a proposer input.

## Execution boundary and remaining risks

Supported execution is reviewed non-root Linux fixtures plus one restricted
arithmetic expression edit. The worker has a sanitized environment, controlled
cwd, bounded pipes, default 2 s per request/5 s startup wall deadlines, 10 s CPU,
2 GiB address space, 64 open files/processes, 1 MiB output-file limit and disabled
core dumps. Process-count limits are per UID, not a container process boundary.
Timeout kills the child process group; measured originals/copies are checked.

**This is not a secure sandbox for arbitrary code.** Host UID, filesystem and
network are shared; no namespaces/read-only mounts/network denial have been
implemented. Pinned source/AST checks and timeouts are guards within this narrow
trust scope, not substitutes for isolation. The tool surface is host-internal,
not an upload endpoint or public service. Meta-origin execution is refused.
Origin labels are provenance, not authentication; do not expose low-level Python
objects/callables to an untrusted investigator.

Before broader execution, enforce non-root process/container isolation, no
credentials, network denial, restricted/read-only mounts and verifier assets,
CPU/memory/process limits and disposable writable copies. Original hashes,
atomic patching and reversible copies remain required. A private verifier needs
independently maintained inputs/answers inaccessible through model-facing tools,
files/imports/network. The public fixture registry and verifier definitions here
do not provide secrecy. Independence currently means separate responsibilities
and additional experiments, not adversarial host-level isolation.

Scientific limits remain: one PDE/method, endpoint boundedness rather than full
trajectory monitoring, finite experiments rather than universal proof, and a
format/variable-name-sensitive set of three explicit source rules. Different
mechanisms, arbitrary scientific repositories and general autonomous repair are
not evaluated. Current hashes intentionally refuse new/unreviewed originals.

## File-by-file changes

| File | Change |
| --- | --- |
| `benchmarks/source_fixtures/solver_01.py` | New reviewed direct-upwind module with direction mistake |
| `benchmarks/source_fixtures/solver_02.py` | New reviewed module with missing dx scaling |
| `benchmarks/source_fixtures/solver_03.py` | New reviewed module with positive seam indexing mistake |
| `benchmarks/source_fixtures/solver_04.py` | New correct source control |
| `benchmarks/source_fixtures/README.md` | Fixture provenance/ground truth, kept outside investigator projection |
| `benchmarks/source_repair/__init__.py` | Evaluator package marker |
| `benchmarks/source_repair/evaluate.py` | Post-investigation localization scoring, measured repairs, human negative controls and JSON CLI |
| `src/physicsguard/schemas/repairs.py` | Typed source/hypothesis/proposal/patch/plan/process/verification/attempt/report records and bounded JSON parser |
| `src/physicsguard/repair/sources.py` | Neutral reviewed hash allowlist, path checks and source snapshots |
| `src/physicsguard/repair/policy.py` | Canonical one-line diff parsing, AST/source integrity and syntax policy |
| `src/physicsguard/repair/workspace.py` | Atomic disposable copies and integrity/cleanup checks |
| `src/physicsguard/repair/proposals.py` | Evidence-gated deterministic AST localization and minimal proposals |
| `src/physicsguard/repair/_worker.py` | Reviewed-source child execution with independent source recheck and POSIX limits |
| `src/physicsguard/repair/executor.py` | Bounded subprocess IPC, deadlines/termination and parent diagnostic orchestration |
| `src/physicsguard/repair/verification_cases.py` | Additional verifier-owned physical cases and mandatory family contract |
| `src/physicsguard/repair/validator.py` | Five-stage measured gate, independent cases, regressions and exact three decisions |
| `src/physicsguard/repair/workflow.py` | Complete investigation/proposal/verification report with abstention |
| `src/physicsguard/repair/tools.py` | Bounded typed internal operations and restricted verification/history projection |
| `src/physicsguard/experiments/runner.py` | Shared caller collection preflight; limits/solver formulas unchanged |
| `src/physicsguard/diagnostics/suite.py` | Reuse shared collection preflight; diagnostics/formulas unchanged |
| `tests/test_source_repair.py` | 51 source repair, integrity, rejection, timeout, independence, tool and replay cases |
| `.github/workflows/tests.yml` | Add source repair CLI; preserve Python 3.11/3.12/3.13 matrix |
| `README.md`, `AGENTS.md` | Current published baseline, supported local repair behavior, commands and limits |
| `docs/architecture.md` | Implemented repair responsibilities and explicit trust boundary |
| `docs/hackathon_provenance.md` | New source provenance and truthful deterministic/human origin records |
| `docs/milestone2_validation.md`, `docs/milestone2_1_validation.md` | Clarify published status while preserving historical measurements |
| `docs/milestone3_validation.md` | This measured follow-up record |

## Milestone 4 integration plan — not started

1. Establish and test the required untrusted-execution and private-verifier
   boundaries before permitting model-origin source execution.
2. Verify current official Meta API/SDK/model/tool-calling documentation under
   separate authorization for credentials/paid usage. No endpoint/model ID is
   assumed implemented by this milestone.
3. Map the bounded `inspect_solver_source`, `run_scientific_experiment`,
   `get_diagnostic_report`, `propose_localized_patch`, `verify_candidate_patch` and
   `get_repair_history` interfaces to one investigator with actual tool calls.
   Keep full verifier cases/reports/answers in the verifier process.
4. Capture actual model-origin hypotheses/patches and tool outputs, enforce call
   budgets, and evaluate localization/repair on independently maintained patterns.
   Do not relabel deterministic proposals or human controls as model repairs.

No Meta client, autonomous model planning, repair deployment, FastAPI application,
browser UI or large multi-agent framework was built or automatically started.
