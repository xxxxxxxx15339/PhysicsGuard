# Architecture

PhysicsGuard uses a `src` layout, with Python modules under `src/physicsguard`
and a separate web interface under `web`.

Milestone 1 implements only the deterministic numerical foundation. The rest of
the scientific debugging workflow remains planned.

| Package | Responsibility | Status |
| --- | --- | --- |
| `api` | Expose application endpoints. | Planned |
| `agent` | Interpret evidence, choose experiments, propose localized repairs. | Planned |
| `numerics` | Advection, interface fluxes, and exact cell-average references. | Milestone 1 |
| `diagnostics` | Measure applicable scientific properties with explicit tolerances. | Planned |
| `repair` | Restrict changes, preserve originals, create reversible candidates. | Planned |
| `experiments` | Execute controlled experiments and retain evidence. | Planned |
| `schemas` | Typed physics, strategy, experiment, proposal, and evidence records. | Planned |

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
ranges can overflow intermediate physical fluxes even if a rearranged update
could be represented; those runs explicitly fail rather than return NaN/Inf.

## Independent reference and tests

For `k = 2*pi*mode/L`, a periodic travelling sine wave has cell average
`offset + amplitude * sin(k*dx/2)/(k*dx/2) * sin(k*(x_center-x_min-a*t)+phase)`.
The reference module evaluates that analytic expression, with periodic phase
reduction, and never calls a numerical flux or update. Its only shared helper
validates elementary input types/shapes. No general forcing/MMS interface exists.

Tests compare the reference against separately implemented cosine primitives,
known integrals, and Gauss-Legendre quadrature. Solver tests use primitive-based
references, hand-calculated updates, mass, periodic TV, convergence, linearity,
and grid-shift equivariance. Production diagnostic modules remain placeholders.
Norms are `L1 = mean(abs(error))`, `L2 = sqrt(mean(error**2))`, and
`Linf = max(abs(error))`; L1 and L2 are grid-normalized, not domain-integrated.

Acceptance criteria and executed results are in [Milestone 1 validation](milestone1_validation.md).

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
design decisions for subsequent milestones, not implemented capabilities.
