# PhysicsGuard

An AI scientific debugging agent for investigating numerical PDE solver errors,
proposing localized repairs, and verifying them with independent experiments.

**Current status: Milestone 2 diagnostics and PhysicsBugBench implemented locally.** The package
solves source-free periodic 1D linear advection with a first-order conservative
finite-volume upwind method and forward Euler. It includes exact sine-wave cell
averages, deterministic scientific diagnostics and bounded experiment execution.
PhysicsBugBench contains six controlled faults and three correct controls. The
debugging agent, repairs, API and interactive application remain planned.

## Project layout

```text
.github/
└── workflows/
docs/
├── architecture.md
├── hackathon_provenance.md
├── demo_plan.md
├── milestone1_validation.md
├── milestone2_validation.md
├── research_inspirations.md
└── third_party.md
src/
└── physicsguard/
    ├── api/
    │   └── main.py
    ├── agent/
    │   ├── model_client.py
    │   └── planner.py
    ├── numerics/
    │   ├── _validation.py
    │   ├── advection.py
    │   ├── fluxes.py
    │   └── references.py
    ├── diagnostics/
    │   ├── conservation.py
    │   └── accuracy.py
    ├── repair/
    │   ├── proposals.py
    │   └── validator.py
    ├── experiments/
    │   ├── scenarios.py
    │   └── runner.py
    └── schemas/
        └── results.py
web/
├── index.html
├── style.css
└── app.js
tests/
├── test_numerics.py
├── test_diagnostics.py
├── test_agent.py
└── test_api.py
examples/
artifacts/
.env.example
.gitignore
pyproject.toml
README.md
```

Milestone 2 also adds evaluator tooling under `benchmarks/physicsbugbench/`,
diagnostic modules for stability, invariance, refinement and suite orchestration,
an investigator evidence exporter, and experiment/benchmark tests. See the
[benchmark catalog](benchmarks/physicsbugbench/README.md) for all six injected faults.

Python package directories include `__init__.py` files. Empty directories include
`.gitkeep` files so Git preserves the layout.

## Development setup

Use Python 3.11 or later:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

NumPy is the only runtime dependency. No API credentials are needed for
Milestones 1–2. Use `.env.example` to document future configuration variables; local
`.env` files are ignored by Git.

Run the numerical tests or the complete collected suite:

```sh
python -m pytest tests/test_numerics.py -q
python -m pytest -q
```

Pytest can import the source tree without installing it; normal library use
requires the editable install above. API and agent tests remain placeholders.

## Reproduce PhysicsBugBench

After the editable install, run from the repository root:

```sh
python -m pytest -q
python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261027 \
  --output artifacts/physicsbugbench-evaluator.json \
  --public-output artifacts/physicsbugbench-development.json
```

The evaluator file includes ground-truth labels, held-out experiments and full
measurements. Keep it **outside the investigator environment**. The development
file contains opaque solver IDs, PDE/strategy records, actual inputs/outputs and
diagnostics. It omits labels, source locations, patches and held-out evidence.
The exporter rejects reports marked evaluator-only. Benchmark code is excluded
from the installed `physicsguard` wheel and runs as repository-local tooling.

The seeded holdout varies parameters, using the same six fault implementations.
A published seed is reproducibility information, not a security boundary or
evidence of unseen-fault generalization. A future investigator process must have
no filesystem/import/network access to benchmark code, evaluator artifacts or
private evaluation inputs. No investigator process or execution sandbox exists
in this milestone; trusted callables run locally. See the
[boundary and scientific assumptions](docs/milestone2_validation.md).

The recorded run detected **6/6 faults** and flagged **0/3 correct controls** in
each split. It retained **32 inconclusive diagnostic results per split**; an
inconclusive result does not establish correctness. These are controlled-fixture
results, without fault-localization, repair or model-performance claims.
Scientific measurements and verdicts replay deterministically in the tested
environment; measured runtimes vary.

For a single supported solver:

```python
from physicsguard.diagnostics.suite import diagnose_solver
from physicsguard.experiments.scenarios import development_cases
from physicsguard.numerics import solve_advection

report = diagnose_solver(solve_advection, "reference", development_cases())
print(report.to_json())
```

Diagnostic L1/L2 are **absolute domain-integrated** norms:
`L1=dx*sum(abs(error))`, `L2=sqrt(dx*sum(error**2))`; Linf is `max(abs(error))`.
The Milestone 1 convergence example below uses grid-normalized norms instead;
they agree numerically on a unit-length domain.

## Run an advection experiment

```python
from physicsguard.numerics import (
    AdvectionConfig,
    sine_cell_averages,
    solve_advection,
)

config = AdvectionConfig(n_cells=128, speed=-1.0, cfl=0.8, final_time=0.3)
initial = sine_cell_averages(config.cell_edges())
result = solve_advection(initial, config)
reference = sine_cell_averages(
    result.cell_edges, speed=config.speed, time=result.final_time
)

print(result.n_steps, result.final_time, result.max_cfl)
print(abs(result.final_averages - reference).mean())
```

The state is **cell averages**, not point samples or a vector with a duplicated
periodic endpoint. Length, time, and speed must use consistent units. Positive,
negative, and zero speeds are supported; `0 < cfl <= 1` is required for this
specific scheme. The last timestep is shortened when needed. Zero speed and
zero duration preserve the input without updates.

Inputs are copied, result arrays are read-only by default, and no source term,
clipping, smoothing filter, or model-generated values enter the computation.
`ValueError` reports invalid controls/data or a step-budget violation;
`FloatingPointError` reports nonrepresentable numerical arithmetic.

First-order upwind is diffusive. Conservation alone does not establish correct
transport; the tests also check analytical accuracy, convergence, direction,
periodic wrapping, boundedness, and applicable total variation behavior.

## Reproduce the convergence measurements

After installation, run this from the repository root:

```sh
python - <<'PY'
from math import fsum
import numpy as np
from physicsguard.numerics import AdvectionConfig, sine_cell_averages, solve_advection

print("speed N steps L1 L2 Linf absolute_mass_error")
for speed in (1.0, -1.0):
    previous = None
    for n in (64, 128, 256):
        cfg = AdvectionConfig(n_cells=n, speed=speed, cfl=0.8, final_time=0.3)
        initial = sine_cell_averages(cfg.cell_edges())
        run = solve_advection(initial, cfg)
        exact = sine_cell_averages(run.cell_edges, speed=speed, time=run.final_time)
        error = run.final_averages - exact
        l1 = float(np.mean(abs(error)))
        l2 = float(np.sqrt(np.mean(error**2)))
        linf = float(np.max(abs(error)))
        drift = abs(cfg.dx * fsum(run.final_averages) - cfg.dx * fsum(initial))
        print(f"{speed:+.0f} {n} {run.n_steps} {l1:.9e} {l2:.9e} {linf:.9e} {drift:.9e}")
        if previous is not None:
            print("L1 order:", np.log2(previous / l1))
        previous = l1
PY
```

See [recorded validation](docs/milestone1_validation.md) for actual measurements,
the tested environment, acceptance criteria, and untested scope. Direct dependency
versions for that environment are recorded in [third-party attribution](docs/third_party.md).

Open `web/index.html` to view the static placeholder. No API server is configured;
the benchmark CLI above is available.

See [architecture](docs/architecture.md),
[hackathon provenance](docs/hackathon_provenance.md), and
[demo plan](docs/demo_plan.md) for the design and planning documents.
