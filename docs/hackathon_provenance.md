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

[Validation](milestone1_validation.md) records actual computations and the tested
environment. It does not claim defect localization, repair, a Meta integration,
independent hidden verification, an API, or an interactive application. There were
no model inference/API calls during Milestone 1. Coding assistance is distinct
from the proposed product's future Meta investigator.

See [research inspirations](research_inspirations.md) for paper-to-design mappings
and [third-party audit](third_party.md) for dependency versions and upstream reuse
restrictions. No upstream code reuse is authorized by a citation alone.

## Publication review still required

The three local research PDFs are already tracked in the pre-milestone commit
`23e467c`. The new ignore patterns prevent new study copies from being added by
default; they do not remove tracked files or prior history. AutoNumerics' arXiv
non-exclusive distribution grant is not a general redistribution permission.
Review paper removal/permissions and repository history before a public release.
This milestone does not remove existing tracked PDFs or rewrite history.

No project license has been selected. Final authorship, dependency/transitive
notices, asset permissions, public-repository access, event rules, and submission
materials remain release tasks. No commits or publication are made automatically.
