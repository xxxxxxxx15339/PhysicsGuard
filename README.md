# PhysicsGuard

An AI scientific debugging agent for investigating numerical PDE solver errors,
proposing localized repairs, and verifying them with independent experiments.

**Current status: Milestone 4 local implementation: keyless agent orchestration over reviewed source fixtures.** The package
solves source-free periodic 1D linear advection with a first-order conservative
finite-volume upwind method and forward Euler. It includes exact sine-wave cell
averages, deterministic scientific diagnostics and bounded experiment execution.
PhysicsBugBench contains six controlled faults, three original correct control
groups and four additional challenging correct groups. The
Investigation supports a deterministic mock and optional local Meta Llama 3.1 8B
through Ollama. Mock traces are explicitly not model inference. Hosted Muse,
general autonomous repair, API and interactive application remain planned. See
[Milestone 4 validation](docs/milestone4_validation.md) for executed evidence.

Published Milestone 3 baseline: `622c9cd1ac11e9247a4746555faed3a9485f1abf`.
The owner reports its GitHub Actions matrix passed on Python 3.11, 3.12 and 3.13.
Original milestone validation measurements remain historical local evidence.
Historical publication statements describe the owner-reported baselines.
Milestone 4 work has not been committed or pushed.

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

NumPy is the only mandatory runtime dependency. No API credentials are needed
for the solver, mock investigator or local Ollama investigator. Use `.env.example`
to document future configuration variables; local
`.env` files are ignored by Git.

Run the numerical tests or the complete collected suite:

```sh
python -m pytest tests/test_numerics.py -q
python -m pytest -q
```

Pytest can import the source tree without installing it; normal library use
requires the editable install above. Agent tests run offline; the API remains a placeholder.

## Run the keyless investigator

From the repository root on non-root Linux:

```sh
python -m physicsguard.agent.demo --backend mock --source solver_01.py
python -m pip install -e '.[dev,ollama]'
python -m physicsguard.agent.demo --backend ollama --model llama3.1:8b --source solver_01.py
```

The real backend requires a separately running local Ollama server with
`llama3.1:8b` already available. PhysicsGuard does not start the server, download
weights, use real credentials, or call hosted providers. Its fixed CLI endpoint
is `http://127.0.0.1:11434/v1`; the library also accepts validated loopback origins.
The SDK uses a literal local placeholder token, which is not a Meta API key.
Model IDs are pinned to this local Llama tag to exclude cloud model selection.

Each invocation prints selected tools, measured evidence, a hypothesis or
abstention, a host-rendered diff, independent verifier decision, integrity and
cleanup. A private strict JSON trace is created under `artifacts/`. `--trace`
accepts a new JSON basename only; existing files are refused. `--timeout`,
`--max-actions`, `--max-turns` and `--max-verifications` control bounded budgets.
Unavailable Ollama requests produce explicit failures, never a mock fallback.

The investigator selects experiments/host operations; existing deterministic host
rules author the one-line patch and the independent verifier owns acceptance.
No raw model-authored source is executable. Public summaries omit evaluator
cases, answers, raw errors, execution arrays and variable runtimes. Providers
receive serialized messages, not host Python objects. This transport boundary
does not provide OS isolation for arbitrary code or private benchmark deployment.

Standard tests require neither the optional SDK nor network/model access. Live
inference is explicitly opt-in and reports only a bounded smoke-test outcome:

```sh
PHYSICSGUARD_LIVE_OLLAMA=1 python -m pytest tests/test_agent.py::test_live_ollama_investigation -q
```

The adapter follows [Ollama's OpenAI compatibility documentation](https://docs.ollama.com/api/openai-compatibility)
and [tool-calling documentation](https://docs.ollama.com/capabilities/tool-calling).
[Llama 3.1](https://ollama.com/library/llama3.1) is a Meta model; this is neither
Muse Spark nor Meta Model API access.

## Reproduce PhysicsBugBench

After the editable install, run from the repository root:

```sh
python -m pytest -q
python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261027 \
  --output artifacts/physicsbugbench-evaluator.json \
  --public-output artifacts/physicsbugbench-development.json
python -m benchmarks.physicsbugbench.evaluate \
  --seed 20261028 \
  --output artifacts/physicsbugbench-evaluator-20261028.json \
  --public-output artifacts/physicsbugbench-development-20261028.json
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
in this milestone; trusted callables run locally. Package exclusion and audience
tags prevent accidental export, not hostile access. No genuinely private holdout
has been deployed. See the
[boundary and scientific assumptions](docs/milestone2_validation.md).

The original October 27 run detected **6/6 faults** and flagged **0/3 correct controls** in
each split. It retained **32 inconclusive diagnostic results per split**; an
inconclusive result does not establish correctness. These are controlled-fixture
results, without fault-localization, repair or model-performance claims.
Scientific measurements and verdicts replay deterministically in the tested
environment; measured runtimes vary.

Milestone 2.1 retains those legacy results for seeds **20261027 and 20261028**.
Both runs also flag **0/4 challenging correct groups** despite visible diffusion,
coarse-grid error, multiple periodic crossings and pulse smearing. These controls
use the same trusted implementation; they do not establish cross-solver coverage.
The evaluator's `evaluation_categories` separates known injected-fault detection,
new parameter configurations and correct-control false positives. Detection of
genuinely unseen fault mechanisms is explicitly **unevaluated**, with a null rate.
There is no combined generalization score. The additive report changes use JSON
schema version 2. See [follow-up validation](docs/milestone2_1_validation.md).

Caller-invalid cases still raise before solver execution. Automatically generated
experiments retain the same resource limits: infeasible requests are recorded
with `status="unavailable"`, their intended case ID and validation reason. Dependent
diagnostics become inconclusive, and valid evidence and unrelated checks remain
available. Such attempts are counted separately from actual executions, solver
errors, nonfinite outputs and valid scientific failures.

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

## Reproduce source-code repair

After an editable install, run from the repository root on non-root Linux:

```sh
python -m pytest tests/test_source_repair.py -q
python -m benchmarks.source_repair.evaluate --output artifacts/source-repair-evaluator.json
```

Alternatively prefix the CLI with `PYTHONPATH=src` without installation. Four new
standalone modules under `benchmarks/source_fixtures/` contain three numerical
defects and one correct control. The original six-branch PhysicsBugBench corpus
is unchanged. The source benchmark measures **3/3 detected, localized, proposed
and independently accepted repairs**, each replacing one source line. The
correct control abstains. Fourteen bad/unsupported proposal controls produce **13
rejections, 1 inconclusive decision and zero acceptances**. Dangerous arithmetic
previously stopped by a timeout is now rejected by policy before execution.
Separate real-child timeout tests still return insufficient execution evidence.
These populations are scored separately; unseen mechanisms remain unevaluated.
Static source-format probes recognize 9/12 variations (no extra verified repairs).
Two separately structured correct implementations pass scientific diagnostics
without proposals; their unreviewed sources remain refused by the repair policy.

For one source file:

```python
from physicsguard.repair.sources import default_source_store
from physicsguard.repair.workflow import repair_source

report = repair_source(default_source_store(), "solver_01.py")
attempt = report.attempts[0]
print(attempt.proposal.unified_diff)
print(attempt.verification.decision)
print(report.original_integrity, report.workspaces_cleaned)
```

The pipeline inspects a hashed source snapshot, runs development diagnostics,
uses explicit deterministic AST rules to propose one localized expression edit,
applies it only to a disposable copy, and invokes an independent scientific gate.
The gate freshly measures original and candidate development evidence and additional signed-velocity, profile,
grid, domain and observation-time cases that were not given to the proposer.
It accepts from actual measured properties, without requiring every error norm
to decrease. Original source files are never patched. The full JSON retains
source regions, diffs, hashes, measurements, decisions and cleanup/integrity
results. It belongs to the evaluator; the future investigator tool surface
returns development evidence and a verification summary without additional-case
parameters or answers.

Execution supports **only four hash-pinned reviewed originals and one restricted
assignment-expression change**. Child processes have hard wall timeouts, a
sanitized environment and POSIX CPU/address-space/file/process limits. They share
the host UID/filesystem/network: this is **not an arbitrary-code sandbox**.
Model-origin execution is disabled. A future private deployment must isolate
verifier assets and candidate execution at the OS level. Arbitrary source
uploads, raw model-authored repairs, FastAPI and UI remain unimplemented. The
Milestone 4 investigator uses this same constrained host engine.

The production verifier accepts no caller reports, custom plans or tolerances.
Every required experiment must supply its applicable evidence. The JSON tool
adapter accepts bounded operation identifiers and experiment records; the host
renders supported edits. It accepts no raw Python, plans or evaluator objects.
Host-only internal testing hooks are not investigator operations. These transport
restrictions require a separate investigator process to become an access boundary.

See [Milestone 3.1 validation](docs/milestone3_1_validation.md), the preserved
[Milestone 3 record](docs/milestone3_validation.md),
[Linux/container instructions (container untested)](dev/README.md) and
[fixture provenance](benchmarks/source_fixtures/README.md).

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
