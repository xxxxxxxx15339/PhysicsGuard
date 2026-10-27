# Hackathon provenance

## Scope and dated work

Project: PhysicsGuard, intended for the Meta Global AI Developer Hackathon 2026
(October 26–November 4, as supplied by the project owner). Track: Indie Developer;
theme: Push the Frontier. Competition eligibility and final submission compliance
are separate checks, not established by this document.

On October 27, 2026, the project owner explicitly authorized **Milestone 1** after
architecture/research review. This milestone independently implements:

- First-order periodic finite-volume upwind advection with forward Euler.
- Signed/zero velocity handling, bounded timestep scheduling, validation, and
  reproducible numerical records.
- Analytical sine-wave cell averages and scientific regression tests.
- Setup, architecture, research attribution, and measured validation documentation.

The project owner supplied the scientific goals, mathematical requirements, and
scope decisions. Codex assisted with design, new code, tests, and documentation.
The upwind algorithm and analytical solution are established mathematics, not
claimed as original research. Author names and final copyright ownership must be
confirmed by the owner before publication.

No WENO-NN/NN-TENO source, trained models, plots, or experimental results were
imported from the owner's earlier research. No upstream research-system code,
datasets, diagrams, prompts, or checkpoints were incorporated into this milestone.
NumPy performs array arithmetic; pytest runs tests; Python/setuptools supply the
runtime and packaging. These external tools are not hackathon inventions.

## Evidence and limits

On October 27, 2026, the owner separately authorized **Milestone 2** against
baseline `d2159cff40a84a27b2e5a996b1b8fe6cc1d5a072`. Newly written work adds:

- Typed physics/strategy/experiment/execution/diagnostic records and strict JSON.
- Independent conservation, analytical accuracy, direction, conditional
  stability/boundedness, refinement and metamorphic diagnostics.
- Bounded trusted-callable experiments and independent square-pulse integrals.
- Six controlled fault implementations, three correct control cases, a seeded
  parameter holdout, development-only evidence export and measured evaluation.
- Scientific tests, CI benchmark invocation, documentation and a robust
  `max_cfl` measurement (without changing the trusted update algorithm).

The sine truncation bound and square-pulse BV/random-walk bound are derived from
standard numerical analysis, not claimed as new mathematics. Paper ideas are
attributed in [research inspirations](research_inspirations.md). The local study
copies of AutoPDE, AutoNumerics and DiffPDE were consulted; GAV §§3.1–3.3 was
consulted through its primary arXiv HTML. No external solver/source, research
results, images or additional assets were copied or redistributed. No packages
were added, no credentials accessed and no model API credits spent. There is
no fault-localization, repair-success or model-performance result in this phase.

[Milestone 2 validation](milestone2_validation.md) records measured results and
limitations. Work remains uncommitted until separately approved by the owner.

[Validation](milestone1_validation.md) records actual computations and the tested
environment. It does not claim defect localization, repair, a Meta integration,
independent hidden verification, an API, or an interactive application. There were
no model inference/API calls during Milestone 1. Coding assistance is distinct
from the proposed product's future Meta investigator.

See [research inspirations](research_inspirations.md) for paper-to-design mappings
and [third-party audit](third_party.md) for dependency versions and upstream reuse
restrictions. No upstream code reuse is authorized by a citation alone.

## Publication review still required

The three research PDFs exist in historical commit `23e467c`. They are absent
from the approved baseline's tracked tree; local `papers/` study copies are
ignored. Ignore patterns do not remove historical blobs. AutoNumerics' arXiv
non-exclusive distribution grant is not a general redistribution permission.
Review paper removal/permissions and repository history before a public release.
This milestone does not remove existing tracked PDFs or rewrite history.

No project license has been selected. Final authorship, dependency/transitive
notices, asset permissions, public-repository access, event rules, and submission
materials remain release tasks. No commits or publication are made automatically.
