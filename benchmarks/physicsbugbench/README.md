# PhysicsBugBench — evaluator documentation and ground truth

This directory contains **benchmark answers**. Exclude it from a future
investigator's filesystem, import path and network-accessible context. It is not
part of the installed `physicsguard` package. Public fixture definitions and a
published seed are not secrets or security controls.

## Corpus

| Stable ID | Injected mechanism | Known mathematical behavior | Revealing checks |
| --- | --- | --- | --- |
| PBB-F01 | Reverse velocity, retain stable upwinding | Conservative bounded transport in the wrong direction | Analytical accuracy, direction, periodic shift, refinement |
| PBB-F02 | Add upstream difference instead of subtracting | Conservative anti-diffusion with reversed phase | Accuracy, boundedness, direction, refinement |
| PBB-F03 | Replace upstream seam neighbor with self | Boundary-dependent flux imbalance and loss of cyclic symmetry | Conservation, translation, periodic wrap |
| PBB-F04 | Multiply each step by exp(-0.4 dt) | Nonphysical source causes mass/constant decay | Conservation, constant state, time scaling |
| PBB-F05 | Lose division by dx in dt/dx update | Conservative effective speed a*dx, inconsistent dimensions | Accuracy, domain/velocity scaling, refinement |
| PBB-F06 | Select downstream face state | Conservative anti-diffusion retaining physical phase | Accuracy, boundedness, refinement |
| PBB-C01 | No fault; trusted positive-speed cases | Correct first-order upwind transport | No applicable diagnostic failures |
| PBB-C02 | No fault; trusted negative-speed cases | Correct signed upwind transport | No applicable diagnostic failures |
| PBB-C03 | No fault; trusted solver with domain/velocity scaled by 3 | Same nondimensional evolution | No applicable diagnostic failures |
| PBB-C04 | No fault; 32 cells, CFL .3, travel 1.3 periods | Visible first-order numerical diffusion | Smooth accuracy/bounds; no unjustified refinement decision |
| PBB-C05 | No fault; 8 cells | Expected coarse-grid truncation error | Smooth accuracy bound; direction can be inconclusive |
| PBB-C06 | No fault; phase 11*pi+.7, negative travel 3.37 periods | Correct large phase/multiple periodic crossings | Independent analytical cell-average accuracy |
| PBB-C07 | No fault; discontinuous pulse on 24 cells, CFL .4 | Valid smearing without a smooth-data convergence claim | BV L1 accuracy and maximum principle |

The original three and four additional challenging controls are distinct **case
groups**, all using the unchanged trusted solver. They are not independent solver
implementations. The original six faults and their parameters are unchanged.
PBB-F02 and PBB-F06 have
different discrete symbols: the former reverses the update on an upstream
stencil, while the latter uses the original update sign on a downstream stencil.
Hand-calculated one-step tests distinguish all six operators. No fault fixture
edits or conditionally patches the production numerical solver.

## Fault coverage and overlapping signatures

For a positive velocity and Fourier phase theta, write c=|a|*dt/dx. Correct
upwind has amplification factor `1-c+c*exp(-i*theta)`.

- F01 uses `1-c+c*exp(+i*theta)`: stable, opposite phase direction.
- F02 uses `1+c-c*exp(-i*theta)`: anti-diffusive, opposite physical phase.
- F06 uses `1+c-c*exp(+i*theta)`: anti-diffusive, physical phase direction.
  F02 and F06 are conjugates with identical growth magnitudes. They are distinct
  stencil/sign defects, but share an instability mechanism and strongly overlap
  in accuracy/boundedness/refinement failures. Direction is often inconclusive
  once growth dominates. They are not independent samples of six broad PDE bugs.
- F05 replaces c by c*dx: it is conservative and bounded on the tested grids but
  uses the wrong speed. F01 and F05 both evade mass/maximum-principle checks;
  direction versus physical scaling supplies distinguishing evidence.
- F03 breaks the seam rather than a spatially uniform Fourier operator. F03 and
  F04 both violate mass, but translation equivariance reveals the seam defect,
  while constant-state decay and time scaling reveal F04's artificial damping.

Accuracy, refinement and the CFL-1 exact-shift probe fail somewhere for all six
fixtures. All six preserve linearity and pass measured CFL admissibility in the
recorded benchmark. Thus a signature can overlap several faults, and these tests
do not automatically localize a faulty line or prove an exact cause. Full measured
signatures remain in `detection_by_fault_type.revealing_diagnostics`.

## Reproduction and scoring

From the repository root, after `python -m pip install -e '.[dev]'`:

```sh
python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261027 \
  --output artifacts/physicsbugbench-evaluator.json \
  --public-output artifacts/physicsbugbench-development.json
python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261028 \
  --output artifacts/physicsbugbench-evaluator-20261028.json \
  --public-output artifacts/physicsbugbench-development-20261028.json
```

The JSON separates measured reports from evaluator joins to labels. A fault is
detected when at least one applicable scientific property fails. Scoring includes
every injected variant in the denominator, including any with unavailable
evidence. It records actual failure families, per-base-case detection, false
positives on controls, per-diagnostic applicability/status coverage, execution
errors, runtimes and inconclusive counts. There is no localization, model or
repair-success score.

Schema version 2 adds explicit `evaluation_categories`: known injected-fault
detection on development cases; detection for new seeded parameter configurations
of the same faults; unseen fault mechanisms (**unevaluated**, zero samples and
null rate); and false positives on correct groups. No aggregate generalization
score is produced. The original split metrics keep six faults/three control
groups. Four fixed challenging groups are scored separately in
`challenging_controls`, preserving the original denominators. Their public inputs
and observations are exported without control labels/descriptions. Fixed controls
are independent of the seed, so their repeated results are not new samples.

Infeasible internally generated probes are `unavailable` attempts, with intended
IDs, validation errors and no invented solver output. Dependent checks are
inconclusive. `generated_unavailable_attempts` is separate from actual execution
counts, elapsed solver time and execution errors. Inconclusive counts and coverage
remain explicit; an unflagged control with some inconclusive properties is not a
claim that every property passed.

Six development cases cover signed velocity, sine modes 1/2 and discontinuous
pulses. Mode-2 times avoid half-wavelength ambiguity; the development pulse
straddles the periodic seam. Seeded held-out cases vary phase, velocity magnitude,
domain length, CFL, offset and amplitude. Holdout uses the **same fault code** and
is not evidence of generalization to new defect mechanisms. Both splits execute
the same three-level smooth refinement and metamorphic checks without adapting
thresholds to outcomes.

Only development reports are marked investigator-visible; the exporter rejects
evaluator-only reports. Do not expose the evaluator object, CLI, scoring file,
seed/private parameters or this source tree to the future investigator. A real
private evaluation must use evaluator-owned samples/seed unavailable to that
process. The current milestone has no investigator process or sandbox, so this
is a tested data/API separation plus a required deployment boundary, not an
implemented hostile-code isolation claim.

Published Milestone 2 is commit `be4a422bc28bf8bce8aafdb219327102fa497a67`;
the owner reports its 3.11/3.12/3.13 CI passed. Follow-up changes are local and
uncommitted. See [original validation](../../docs/milestone2_validation.md) and
[Milestone 2.1 validation](../../docs/milestone2_1_validation.md).
