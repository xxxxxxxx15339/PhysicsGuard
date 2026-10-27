# Milestone 2 — scientific diagnostics and PhysicsBugBench

Recorded October 27, 2026, from actual local execution against approved baseline
`d2159cff40a84a27b2e5a996b1b8fe6cc1d5a072` plus the uncommitted Milestone 2 changes.
No commits, pushes, deployments, credentials or paid model calls were made.

## Executed validation

- CPython 3.13.11, NumPy 2.4.3, pytest 9.0.1, Linux. No new dependencies.
- `python -m pytest -q`: **252 passed in 2.40 s**, warnings treated as errors.
  The approved baseline collected 150 passing tests locally; its numerical test
  file is unchanged. This milestone adds 102 tests.
- `python -m compileall -q src tests benchmarks`: passed.
- All Python files also parsed with Python 3.11's grammar through `ast.parse`.
  Actual new tests were not executed locally under Python 3.11/3.12.
- Existing GitHub Actions matrix remains Python 3.11, 3.12, 3.13; it now compiles
  the benchmark package and runs the deterministic evaluation CLI after pytest.
  Updated remote Actions have **not** run because this work has not been pushed.
- Offline wheel build passed with `--no-index --no-deps --no-build-isolation
  --no-cache-dir`. The 32-entry wheel included the diagnostic/experiment modules,
  excluded benchmark code and PDFs, and passed an isolated `python -I` import/run
  check. Both README Python examples executed against that wheel. This used
  installed NumPy; it was not a fresh-environment dependency installation.
- `git diff --check`: passed. Licensing and Git history are unchanged.

Tests independently verify hand-calculated fault updates, absolute norm/mass
values, units, rounding tolerance, analytic integrals, invalid input/budget
handling, malformed candidate outputs, unavailable vs nonfinite evidence,
diagnostic applicability, nonunit-domain scaling, repeated scientific outcomes,
public export restrictions and detection across three initial profiles.

## Reproduce

After an editable install, from the repository root:

```sh
python -m pytest -q
python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261027 \
  --output artifacts/physicsbugbench-evaluator.json \
  --public-output artifacts/physicsbugbench-development.json
```

Without installation, `PYTHONPATH=src` can prefix the benchmark command. The
evaluator JSON contains complete measurements and label joins; the development
JSON is a separate investigator projection. Keep evaluator files private from
that future process. Generated artifacts are ignored by Git. During this local
validation the equivalent files were written under `/tmp/physicsguard-m2-*.json`.
Seed, Python and NumPy versions are recorded in evaluator JSON. Runtimes are
measurements and are excluded when asserting deterministic replay.

## Measured outcomes

Each split evaluates six faulty solver implementations and three correct case
groups. Controls use the trusted solver with positive velocity, negative velocity,
and consistently rescaled domain/velocity. They are not independent algorithms.
Each fault gets six base cases; the control groups get 3, 3 and 6 base cases.
Every group also receives three refinement executions and eight metamorphic
executions, producing 147 executions and 351 diagnostic records per split.

| Metric | Development | Parameter holdout |
| --- | ---: | ---: |
| Fault variants detected | 6/6 (100%) | 6/6 (100%) |
| Each individual fault type | 1/1 | 1/1 |
| Base faulty cases with a failed basic diagnostic | 36/36 | 36/36 |
| Correct groups falsely flagged | 0/3 (0%) | 0/3 (0%) |
| Correct base cases falsely flagged | 0/12 | 0/12 |
| Executions / execution errors | 147 / 0 | 147 / 0 |
| Conclusive diagnostic records | 319/351 (90.88%) | 319/351 (90.88%) |
| Inconclusive diagnostic records | 32 | 32 |
| Groups with some inconclusive evidence | 9/9 | 9/9 |
| Entirely inconclusive groups | 0 | 0 |
| Sum execution elapsed time | 0.1187 s | 0.1185 s |
| Median execution elapsed time | 0.000528 s | 0.000558 s |
| Sum suite elapsed time | 0.1922 s | 0.1910 s |

Combined evaluator elapsed time was 0.4108 s, excluding final JSON file writing.
Timing varies with machine load. Detection means at least one measured scientific
property failed, with all injected variants retained in the denominator. Neither
an inconclusive result nor an execution error is silently counted as a pass.
There are no localization, repair-success or model-performance scores.

| Fault | Failed diagnostic families observed in both splits |
| --- | --- |
| PBB-F01 reversed direction | Accuracy, direction, exact periodic shift, refinement |
| PBB-F02 reversed update sign | Accuracy, boundedness, direction, exact shift, refinement |
| PBB-F03 seam indexing | Conservation, accuracy, translation equivariance, exact shift, refinement |
| PBB-F04 artificial damping | Conservation, accuracy, boundedness, constant state, time scaling, exact shift, refinement |
| PBB-F05 missing dx scaling | Accuracy, physical domain/velocity scaling, exact shift, refinement |
| PBB-F06 downstream state | Accuracy, boundedness, exact shift, refinement |

All six variants pass measured CFL admissibility; an admissible timestep does
not establish a correct stencil. All six also preserve linearity to tolerance,
showing that this property alone cannot certify a linear solver's correctness.
The JSON includes full per-family applicability/pass/fail/inconclusive counts.

### Conservative wrong transport counterexample

For PBB-F01, development sine mode 1, N=64, a=+1, T=0.23, CFL=0.8,
phase=0.37, offset=1 and amplitude=0.2:

- Initial/final mass both measured 1.0; drift 0.0, tolerance 1.7053e-13.
- Bounds are preserved.
- Analytical errors: L1=0.2507138736, L2=0.2784263894,
  Linf=0.3936059262, compared with a priori Linf budget 0.0253895573.
- Linf error against opposite translation is 0.0029621028; analytical direction
  separation is 0.3965484215. The direction diagnostic fails decisively.

These are new local results, not borrowed research plots/results. Conservation
passing does not establish physical accuracy or transport direction.

## Scientific definitions and tolerance derivations

All implemented physics uses `u_t + (a*u)_x = 0`, constant real `a`, no source,
uniform periodic finite volumes, and unknowns that are **cell averages**.
Unsupported physics is rejected. Numerical method declarations are separate from
the trusted physical specification; unsupported methods make method-dependent
assertions inconclusive rather than importing upwind assumptions into them.

**Conservation.** `M=dx*fsum(U_i)`. Report initial/final mass, absolute drift and
drift normalized by `S=dx*max(sum(abs(U_initial)),sum(abs(U_final)))`. Zero data
has zero normalized drift. The tolerance is `gamma_k*S`, where
`gamma_k=k*eps64/(1-k*eps64)` and `k=32*(steps+1)+2*N`. This conservative
operation-count envelope allows accumulated update/reduction rounding and avoids
normalizing by a near-zero signed mass. It is an engineering bound under the
supported stable method assumptions, not a formal roundoff proof for arbitrary
algorithms. Exact zero is never required for generic data. Mass units are
field times length.

**Reference and norms.** Sine references integrate the exact travelling wave;
square references integrate a periodic interval indicator using its continuous
primitive. Neither calls a numerical flux/update. Separate cosine-primitive and
interval-overlap tests validate these integrals. Analytical diagnostics verify
that actual initial values match the declared profile; arbitrary overrides do
not acquire a reference merely through a label.

`L1=dx*sum(abs(e))`, `L2=sqrt(dx*sum(e^2))`, `Linf=max(abs(e))` are absolute,
domain-integrated discrete norms (Linf is unscaled). Their units are field*length,
field*sqrt(length) and field, respectively. L2 evaluation scales by the maximum
error to avoid unnecessary squaring overflow. Milestone 1's standalone tests
use grid-normalized L1/L2; on a unit domain their values agree.

For smooth sine/constant data, upwind spatial consistency is bounded by
`dx/2*||u_xx||inf` and Euler's time residual by `a^2*dt^2/2*||u_xx||inf`.
A monotone step at CFL<=1 is Linf nonexpansive. Summing these local defects gives
the conservative global Linf budget
`0.5*||u_xx||inf*(|a|*T*dx + a^2*sum(dt^2)) + gamma_k*field_scale`.
Sine curvature is `abs(amplitude)*(2*pi*mode/L)^2`. No numerical reference solve
or benchmark-fitted threshold enters this derivation.

For discontinuous square data, the smooth bound is inapplicable. Upwind is an
expectation over independent Bernoulli cell translations. The random displacement
has mean `a*T` and variance `sum(|a|*dt*dx-(a*dt)^2)`. The BV translation inequality
and Jensen give the L1 budget `TV(u0)*sqrt(variance)`; cell averaging is L1
contractive. Here `TV(u0)=2*abs(amplitude)`, and length-scaled roundoff is added.
This supplies an independent discontinuous-data criterion rather than weakening
the smooth-data tolerance.

**Direction.** Compare errors against independently evaluated translations by
`a*T` and `-a*T`. Only apply an identifying decision when their Linf separation
exceeds four smooth error budgets. Pass if the physical reference error is within
budget; fail if the opposite-reference error plus budget is smaller than the
physical-reference error. Otherwise retain an inconclusive result. Zero travel,
complete/half-period coincidence and unsupported data cannot establish direction.

**Stability/bounds.** Validate finite output and actual returned timestep data;
compute measured CFL independently from those steps and the trusted PDE/grid.
Confirmed returned NaN/Inf fails the finite-output check. Exceptions without
numerical output leave it inconclusive and remain explicit execution errors.
An upwind/Euler maximum principle is checked only at admissible CFL, against
initial extrema with a rounding envelope. Only initial/final states are stored;
transient instability that later cancels is not ruled out.

**Refinement.** Fixed physics/profile/time/CFL, sine data, at least 32 cells per
mode, CFL in [0.1,0.9], and travel in [0.05,0.5] domain lengths. On 64/128/256
cells, estimate `p=log(E_coarse/E_fine)/log(dx_coarse/dx_fine)` from L1 errors.
Orders in [0.7,1.3] indicate qualitative first-order behavior. This is an explicit
empirical envelope, not a universal asymptotic guarantee. Errors near the rounding
floor, stationary cases, CFL=1, incompatible grids and nonsmooth data are
inconclusive. Development positive control orders were 1.042885 and 1.003529;
its held-out orders were 1.015937 and 0.998375.

**Metamorphic checks.** Constants, cyclic shifts, superposition, consistent
length/velocity scaling, consistent time/velocity scaling, and CFL-1 exact
one-cell transport including the seam. Compare Linf differences with four times
the sum of per-execution rounding envelopes. Supporting input vectors, controls,
outputs and case IDs are retained. These properties are specific to this linear
periodic method and are not asserted for arbitrary future PDEs.

## Known blind spots and evaluation boundary

- A regression test preserves an actual missed basic-check case: mode-2 reversed
  transport at T=0.23 on N=64. References approach a half-wavelength coincidence
  closely enough that the conservative error envelope cannot identify the
  direction. The full suite detects it with an exact-shift follow-up. Development
  mode-2 cases use T=0.125, without changing acceptance thresholds.
- A pulse that never encounters the seam can miss an indexing error. Development
  square pulses straddle it; heldout phases vary. Multi-case results are not a
  claim that every observation reveals every fault.
- The 32 inconclusive records per split are direction checks: 16 square-profile
  records have no smooth direction budget, and 16 smooth outputs fit neither
  direction within that budget. Other families still supply measured evidence.
- The seeded holdout contains parameter variations of the same six known faults,
  not new mutation classes, real external solver projects or adaptive-agent tests.
  Detection rates over this small constructed corpus have no generalization or
  statistically calibrated confidence claim.
- Benchmark code, labels and private scoring live outside the installed package.
  Development exports omit labels, locations, patches and heldout reports; the
  exporter rejects evaluator-only audiences by default. Audience tags and opaque
  IDs prevent accidental disclosure, not malicious introspection. A published
  seed is not a secret or security boundary.
- There is no investigator process in this milestone. Before one exists, enforce
  filesystem/import/network isolation so it receives only the public JSON/tool
  capability and cannot access this benchmark directory, repository-root docs,
  evaluation artifacts or evaluator-owned heldout samples. Repository/package
  separation alone is insufficient. Actual private scoring should use unseen
  evaluator-owned inputs, not claim secrecy for this published reproducibility
  seed. No untrusted-source execution is implemented.
- Request validation limits each trusted run to 4096 cells, 20000 steps and
  2000000 cell updates. These do not stop a malicious or hanging callable. A
  future repair executor needs process isolation, hard time/memory limits and
  restricted filesystem/network access.
- Extremely ill-scaled floating-point physics may make reference/tolerance
  arithmetic unavailable. The solver still has representability limits for its
  timestep schedule and intermediate state differences. `max_cfl` itself now
  avoids avoidable intermediate multiplication underflow/overflow, covered by
  extreme-scale regression tests; no universal extreme-scale solver claim is made.

## File inventory and next milestone

- `src/physicsguard/schemas/results.py`: physics, strategy, case, execution,
  diagnostic and report dataclasses, strict JSON and evidence audience.
- `src/physicsguard/experiments/{scenarios,runner,public}.py`: analytic scenarios,
  validated bounded execution and allowlisted development evidence projection.
- `src/physicsguard/diagnostics/{_common,conservation,accuracy,stability,refinement,invariance,suite}.py`:
  independent measurements, tolerances, applicability and orchestration.
- `src/physicsguard/numerics/advection.py`: only the `max_cfl` measurement changed;
  trusted flux, update and scheduling algorithms are preserved.
- `benchmarks/__init__.py`, `benchmarks/physicsbugbench/{__init__,variants,evaluate}.py`
  and its README: isolated controlled faults, control groups, holdout and scoring.
- `tests/{test_diagnostics,test_experiments,test_physicsbugbench}.py`: 102 new tests.
- `pyproject.toml`, `.github/workflows/tests.yml`: repository-local benchmark
  discovery for tests, syntax checks and CI evaluation. Dependencies unchanged.
- `README.md`, `AGENTS.md`, the three `PHYSICSGUARD_*` context/decision documents,
  and `docs/{architecture,demo_plan,hackathon_provenance,research_inspirations,third_party}.md`:
  current status, historical context, research attribution and accurate provenance.
- This validation document records measurements and limits. Milestone 1's
  original validation report remains a historical result.

Recommended next work is **Milestone 3: restricted repair representation and
independent candidate verification**, with immutable originals, narrow reversible
changes, verifier-owned tests and process/resource isolation before executing
any untrusted candidate. Fault localization needs its own evidence and evaluation.
Meta integration remains a separately authorized later milestone.
