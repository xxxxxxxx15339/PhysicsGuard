# Architecture

PhysicsGuard uses a `src` layout, with Python modules under `src/physicsguard`
and a separate web interface under `web`.

Milestone 1 implements the deterministic numerical foundation. Milestone 2 adds
diagnostic evidence, controlled experiment execution and PhysicsBugBench. The
Meta-driven investigation and general repository repair remain planned. Milestone
3 implements a deterministic source-repair workflow for reviewed local fixtures.

Milestone 2.1 is published as `46b6e78c19b0bf37aa15e2c14d91fce2a1d971ef`; the
owner reports that baseline's 3.11/3.12/3.13 CI matrix passed. Earlier local
measurements remain historical records. Milestones 2.2/3 are new local work;
see [source repair validation](milestone3_validation.md). The matrix, dependencies,
trusted numerical solver and diagnostic acceptance thresholds are unchanged.

| Package | Responsibility | Status |
| --- | --- | --- |
| `api` | Expose application endpoints. | Planned |
| `agent` | Interpret evidence, choose experiments, propose localized repairs. | Planned |
| `numerics` | Advection, interface fluxes, and exact cell-average references. | Milestone 1 |
| `diagnostics` | Independent conservation, accuracy, direction, stability, refinement and invariance measurements. | Milestone 2 |
| `repair` | Inspect reviewed source, propose bounded expression edits, verify disposable candidates in subprocesses. | Milestone 3, deterministic fixture scope |
| `experiments` | Bounded trusted-callable execution, analytic scenarios, public evidence projection. | Milestone 2 |
| `schemas` | Physics/experiment evidence plus source, proposal, patch and verification records. | Milestones 2/3 |
| `benchmarks/physicsbugbench` | Fault fixtures, control cases, parameter holdout and private scoring. | Milestone 2; excluded from installed package |

Tests live in `tests`, usage examples in `examples`, and generated outputs in
`artifacts`. Implementation details and dependencies will be documented as they
are added.

## Milestone 1 numerical model

Solve `u_t + (a u)_x = 0` on `[x_min, x_max)` with periodic boundaries, constant
real velocity `a`, no sources, and a uniform finite-volume grid. Unknowns are
cell averages `U_i`, with `N` values and `N+1` edges. Position has length units,
speed has length/time units, and time uses the corresponding time unit.

The interface flux is `F_(i+1/2) = max(a, 0) U_i + min(a, 0) U_(i+1)`.
The forward Euler update is
`U_i <- U_i - dt/dx * (F_(i+1/2) - F_(i-1/2))`.
Each face has one shared flux and periodic indices. The mass
`M = dx * sum(U_i)` therefore telescopes algebraically; floating-point rounding
remains, but ordinary time truncation error is not a source of mass drift here.

For this particular method, `|a| dt/dx <= 1` gives a convex upwind update,
boundedness, positivity for nonnegative data, and non-increasing periodic total
variation. These are not assertions about arbitrary PDE solvers. First-order
diffusion of a resolved smooth profile is expected and is not an implementation bug.

## Interfaces and data ownership

| Interface | Contract |
| --- | --- |
| `AdvectionConfig` | Frozen validated controls: positive `n_cells`, finite ordered domain, finite `speed`, `0 < cfl <= 1`, nonnegative `final_time`, positive `max_steps`. |
| `upwind_flux(left, right, *, speed)` | Matching real finite 1D states to an owned float64 face-flux vector. |
| `step_upwind(averages, *, speed, dx, dt)` | One periodic flux-form update, enforcing the method-specific timestep limit. |
| `solve_advection(initial_averages, config)` | Complete deterministic run; initial vector length must match `n_cells`. |
| `AdvectionResult` | Configuration, edges, centers, independent initial/final vectors, and actual `time_steps`; properties `n_steps`, `final_time`, `max_cfl`. |
| `sine_cell_averages(edges, *, time, speed, offset, amplitude, mode, phase)` | Independently integrated periodic sine-wave reference with positive integer mode; supports nonuniform reference cells too. |

All calculations use float64. Scalar controls must be real and finite; implicit
string/boolean conversions are rejected. States must be finite real numeric
vectors. Inputs are copied; completed-result arrays are read-only by default.
Read-only flags are an accidental-mutation safeguard, not a security boundary.

For nonzero velocity, the nominal timestep is `cfl * dx / |a|`. Standard-library
`Fraction` arithmetic computes its full-step count and remaining duration from
the exact supplied binary floats. This avoids accumulated clock drift and an
extra tiny step, and lets the solver enforce `max_steps` before integration.
The remaining duration is taken as the last step. Zero speed is analytically
stationary and needs no updates even when the requested duration is positive.
No full field history is allocated; stored data scale as `O(N + n_steps)`.

Invalid input or nonrepresentable derived grid/timestep controls raise
`ValueError`. Flux or update overflow raises `FloatingPointError`. Extreme dynamic
ranges can overflow intermediate state differences even if a rearranged convex
update could be represented; those runs explicitly fail rather than return
NaN/Inf. The baseline uses a normalized signed flux to avoid overflowing the
physical speed times state. Milestone 2 computes `AdvectionResult.max_cfl` from
an exact binary-float ratio for the largest timestep, avoiding intermediate
product overflow/underflow; the actual solver update is unchanged.

## Independent reference and tests

For `k = 2*pi*mode/L`, a periodic travelling sine wave has cell average
`offset + amplitude * sin(k*dx/2)/(k*dx/2) * sin(k*(x_center-x_min-a*t)+phase)`.
The reference module evaluates that analytic expression, with periodic phase
reduction, and never calls a numerical flux or update. Its only shared helper
validates elementary input types/shapes. No general forcing/MMS interface exists.

Tests compare the reference against separately implemented cosine primitives,
known integrals, and Gauss-Legendre quadrature. Solver tests use primitive-based
references, hand-calculated updates, mass, periodic TV, convergence, linearity,
and grid-shift equivariance. Milestone 2 implements separate diagnostic modules.
Norms are `L1 = mean(abs(error))`, `L2 = sqrt(mean(error**2))`, and
`Linf = max(abs(error))`; L1 and L2 are grid-normalized, not domain-integrated.

Acceptance criteria and executed results are in [Milestone 1 validation](milestone1_validation.md).

## Milestone 2 evidence and boundaries

Frozen standard-library dataclasses provide the five requested evidence schemas
and an explicit `SolverStrategy`. Strict JSON serialization rejects NaN/Infinity;
unavailable measurements use an inconclusive status and an evidence error.
`ExperimentCase` keeps the trusted PDE separate from the declared numerical
method. Candidate source and benchmark labels cannot redefine either. Arbitrary
initial overrides are retained in execution records; analytical diagnostics
refuse comparison when those inputs do not match the declared profile.

The runner uses the same typed callable contract for reference and faulty
solvers. It validates parameters and budgets before invocation, owns input/output
copies, checks shape/finite values/time schedules, and records errors and actual
elapsed time. Limits are 4096 cells, 20000 steps and 2000000 cell updates per run,
with at most 16 base experiments per suite. These bound our trusted fixtures;
there is no hard wall timeout or sandbox for arbitrary callables.

Basic experiments precede three refinement levels and fixed metamorphic probes.
There is no adaptive agent choosing tests yet. Accuracy uses independent analytic
cell integrals and mathematical discretization bounds, never the candidate's
flux or a candidate-computed residual as an oracle. All diagnostics retain units,
assumptions, acceptance criteria, tolerances, evidence errors and supporting case
IDs. A failed property indicates evidence against the contract, not an exact
source location or a validated patch.

Benchmark mutations and labels live outside `src/physicsguard`. The evaluator
joins labels to measured reports only when scoring. Separate development-only
JSON exports use opaque solver IDs and omit fault labels, locations, reference
patches and held-out experiments. Reports default to evaluator-only; the public
projector rejects those. This guards accidental disclosure, not malicious Python
introspection. A future investigator must run across an OS-enforced boundary
with no benchmark/evaluator files, repository-root mount or private sample access.
No investigator process exists in Milestone 2. A public seeded parameter split
is reproducible but is not secret or an unseen-fault evaluation.

See [Milestone 2 validation](milestone2_validation.md) for formulas, real metrics,
known blind spots, file inventory and reproduction commands.

## Milestone 2.1 generated experiment handling

`execute_solver` remains a trusted-callable runner. `execute_generated` is a
small internal wrapper around that same validation/execution path. It constructs
each derived case inside its own error boundary; it never increases budgets.
Invalid caller cases are all prevalidated before any solver is invoked.

| Outcome | Execution record | Scientific interpretation |
| --- | --- | --- |
| Invalid caller input | Raises `ValueError` before execution | No accepted experiment request |
| Infeasible generated controls/budget | `UnavailableExperiment`, status `unavailable`, kind `generated_validation_error` | Dependent properties inconclusive; retain ID/reason |
| Solver exception or invalid returned contract | Status `error`, kind `execution_error` | Output unavailable; no automatic scientific failure |
| Confirmed returned NaN/Inf | Status `error`, kind `nonfinite_output` | Finite-output property fails |
| Successful run with measured violation | Status `success`, failed `DiagnosticResult` | Scientific failure under its declared assumptions; no exact localization claim |

Unavailable attempts retain a validated case when one could be constructed;
otherwise `case=null` and the intended case ID/reason remain. They contain no
invented outputs or solver runtime. Their elapsed time measures preparation and
validation. Actual execution counts/timing exclude them. Refinement keeps any
successful levels and reports missing evidence; each metamorphic comparison
checks its own dependencies so one skipped transformation cannot abort another.

The benchmark retains the original six faults/three control groups and adds a
separate four-group challenging-control evaluation. Categories distinguish known
faults from new parameter samples and unseen mechanisms (currently unevaluated).
They are not pooled into a generalization score or a newly enlarged legacy FPR.
All added controls still use the trusted first-order implementation.

No secure execution or private-holdout deployment is implemented here. Before
untrusted candidate execution, the next milestone must provide a separate process
or container, hard timeouts, CPU/memory limits, filesystem/network restrictions,
immutable originals, reversible patch application, and verifier-owned tests that
the investigator cannot access. Python imports, dataclass audience tags and public
benchmark sources do not enforce that boundary. Only trusted reviewed callables
and internal case factories may enter the current runner; no source-text/model
execution interface is added.

## Later debugging workflow

Keep the trusted physical specification distinct from the declared numerical
strategy and the inspected source revision. A bounded Meta investigator may read
allowlisted source, request development experiments, and propose localized changes.
The scientific engine owns all measurements. The repair policy must reject changes
to trusted specifications, references, tests, and verifier thresholds.

Development checks may return feedback; held-out final scoring must remain separate
from adaptive investigation. Execution success, diagnostic status, and scientific
verification are different records. A verified outcome means a specified suite
passed, not a mathematical proof. These contracts and execution boundaries are
design decisions for subsequent milestones beyond the Milestone 2 evidence
contracts and trusted execution described above.

## Milestone 3 source repair

The immutable source store accepts exactly four reviewed original hashes and
neutral file IDs. Standalone source fixtures implement a direct upwind difference,
sharing the validated configuration/result and timestep scheduler with Milestone 1.
They do not call the trusted solver or reuse the original six-branch fault corpus.
New files contain localized direction, dx-scaling and positive-seam mistakes plus
a correct control. Evaluator labels and expected locations are separate from the
proposer and tool interface.

`proposals.py` consumes a source snapshot and development evidence. Three explicit
AST/source-pattern rules require matching failed scientific diagnostics before
proposing an edit. Hypotheses include the source function/line and evidence IDs;
their origin is deterministic. This is limited rule-based localization, not an
LLM investigation or arbitrary Python debugging. The correct fixture receives
no proposal. Unknown patterns or insufficient evidence yield no justified repair.

`policy.py` accepts one existing assignment RHS inside `advance`, with a bounded
arithmetic/conditional/subscript grammar. It checks original/proposed hashes,
structured edit and canonical single-hunk unified diff, full AST integrity outside
that expression, and syntax. Calls, attributes, new imports, extra statements,
wholesale solver replacement and unrelated paths are rejected. Path reads reject
symlinks/hardlinks; temporary source writes use atomic rename. Disposable copies
are read-only during execution. Originals are never written; concurrent owner
edits are detected and left untouched. Cleanup and integrity are recorded.

`executor.py` runs a persistent reviewed worker in a separate non-root Linux
process, with sanitized environment, controlled cwd, bounded JSON pipes, per-call
wall deadlines, process-group termination and POSIX CPU/address-space/process/file
limits. The child independently rechecks the original hash and candidate AST.
Only solver calls run there; parent-owned diagnostics compute the scientific
verdicts. Parent/child calls reuse ordinary experiment validation and preserve
execution error versus confirmed nonfinite versus generated-unavailable evidence.
The collection preflight was factored into `validate_cases`; its numerical and
resource criteria are unchanged.

`validator.py` owns an additional six-case plan, separate from proposal generation.
It refuses repeated development configurations (including generated probes),
requires the mandatory scientific families, compares original and candidate on
the same additional cases, reruns development regressions, and checks previously
passing properties for new failure/lost evidence. Norms need not decrease in every
case. Valid candidate execution alone cannot accept a repair. Required unavailable
evidence yields INCONCLUSIVE; invalid source, failed mathematical criteria or new
regressions yield REJECTED. ACCEPTED requires observed independent baseline failures
resolved by the candidate, sufficient evidence and no observed regression.

Full repair reports belong to the evaluator. `RepairTools` exposes bounded source
inspection, development experiments/reports, deterministic proposal generation,
verification summaries and history. It does not expose the verifier's case
parameters, measurements or answer registry, and repeated run IDs cannot bypass
the experiment budget. There is no model client, source upload endpoint, API or UI.

This worker is not an arbitrary-code sandbox: host filesystem/network access and
host UID are shared; resource/import/AST checks do not replace OS isolation.
Arbitrary Meta-origin execution is disabled. Public fixture hashes, public
verification-case definitions and audience tags do not make genuinely private
evaluation. Before untrusted integration, isolate mounts/network/credentials and
verifier assets in an independently enforced execution boundary.
