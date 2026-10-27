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

Controls are three distinct **case groups**, using the unchanged trusted solver,
not three invented independent solver implementations. PBB-F02 and PBB-F06 have
different discrete symbols: the former reverses the update on an upstream
stencil, while the latter uses the original update sign on a downstream stencil.
Hand-calculated one-step tests distinguish all six operators. No fault fixture
edits or conditionally patches the production numerical solver.

## Reproduction and scoring

From the repository root, after `python -m pip install -e '.[dev]'`:

```sh
python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261027 \
  --output artifacts/physicsbugbench-evaluator.json \
  --public-output artifacts/physicsbugbench-development.json
```

The JSON separates measured reports from evaluator joins to labels. A fault is
detected when at least one applicable scientific property fails. Scoring includes
every injected variant in the denominator, including any with unavailable
evidence. It records actual failure families, per-base-case detection, false
positives on controls, per-diagnostic applicability/status coverage, execution
errors, runtimes and inconclusive counts. There is no localization, model or
repair-success score.

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

See [measured validation and blind spots](../../docs/milestone2_validation.md).
