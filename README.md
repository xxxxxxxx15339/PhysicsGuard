# PhysicsGuard

Project scaffold for numerical experiments, conservation and accuracy diagnostics,
and agent-assisted repair. The modules and test files are placeholders; application
behavior is not implemented yet.

## Project layout

```text
.github/
└── workflows/
docs/
├── architecture.md
├── hackathon_provenance.md
└── demo_plan.md
src/
└── physicsguard/
    ├── api/
    │   └── main.py
    ├── agent/
    │   ├── model_client.py
    │   └── planner.py
    ├── numerics/
    │   ├── advection.py
    │   └── fluxes.py
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

Python package directories include `__init__.py` files. Empty directories include
`.gitkeep` files so Git preserves the layout.

## Development setup

Use Python 3.11 or later:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

The package has no runtime dependencies yet. Add them to `pyproject.toml` when
implementing integrations. Use `.env.example` to document configuration variables;
local `.env` files are ignored by Git.

The test modules are reserved for future tests. Once tests are implemented, run
them with `python -m pytest`. Until then, pytest will report that no tests were
collected.

Open `web/index.html` to view the static placeholder. No API server or command-line
entry point is configured yet.

See [architecture](docs/architecture.md),
[hackathon provenance](docs/hackathon_provenance.md), and
[demo plan](docs/demo_plan.md) for the design and planning documents.
