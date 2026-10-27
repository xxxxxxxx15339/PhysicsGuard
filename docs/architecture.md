# Architecture

PhysicsGuard uses a `src` layout, with Python modules under `src/physicsguard`
and a separate web interface under `web`.

The package is scaffolded; the responsibilities below describe the intended design.

| Package | Responsibility |
| --- | --- |
| `api` | Expose application endpoints. |
| `agent` | Connect to a model and plan diagnostic or repair steps. |
| `numerics` | Implement advection solvers and numerical fluxes. |
| `diagnostics` | Measure conservation and accuracy. |
| `repair` | Represent repair proposals and validate candidates. |
| `experiments` | Define scenarios and coordinate experiment runs. |
| `schemas` | Define shared result structures. |

Tests live in `tests`, usage examples in `examples`, and generated outputs in
`artifacts`. Implementation details and dependencies will be documented as they
are added.
