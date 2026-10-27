# Architecture

PhysicsGuard uses a `src` layout, with Python modules under `src/physicsguard`
and a separate web interface under `web`.

Milestone 1 implements the deterministic numerical foundation. Milestone 2 adds
diagnostic evidence, controlled experiment execution and PhysicsBugBench. The
model-driven investigation and repair workflow remains planned.

| Package | Responsibility | Status |
| --- | --- | --- |
| `api` | Expose application endpoints. | Planned |
| `agent` | Interpret evidence, choose experiments, propose localized repairs. | Planned |
| `numerics` | Advection, interface fluxes, and exact cell-average references. | Milestone 1 |
| `diagnostics` | Independent conservation, accuracy, direction, stability, refinement and invariance measurements. | Milestone 2 |
| `repair` | Restrict changes, preserve originals, create reversible candidates. | Planned |
| `experiments` | Bounded trusted-callable execution, analytic scenarios, public evidence projection. | Milestone 2 |
| `schemas` | Typed physics, strategy, experiment, execution and diagnostic records. | Milestone 2; proposals deferred |
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
