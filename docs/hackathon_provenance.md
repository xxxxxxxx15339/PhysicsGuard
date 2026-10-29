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

[Milestone 2 validation](milestone2_validation.md) records the original local
measurements and limitations. At that validation the work was uncommitted; it
was subsequently committed and pushed as
`be4a422bc28bf8bce8aafdb219327102fa497a67`. The owner reports that baseline's
GitHub Actions passed on Python 3.11, 3.12 and 3.13. This does not retroactively
turn the original local measurements into GitHub measurements.

## Milestone 2.1 follow-up

The owner separately authorized corrections against that published Milestone 2
baseline. New work provides one shared internal generated-experiment helper,
typed unavailable-attempt evidence, independent continuation of refinement and
metamorphic probes, four challenging correct control groups, explicit evaluation
categories and regression tests. It preserves the numerical solver, all six fault
implementations, mathematical formulas, acceptance tolerances and original
benchmark scores. Both seeds 20261027 and 20261028 are evaluated from actual runs.

[Follow-up validation](milestone2_1_validation.md) contains the new test outcomes,
measured scores and contract audit. Unseen fault mechanisms remain unevaluated;
the publicly reproducible parameter split is not a genuinely private holdout.
No new dependencies, copied code/assets, licensing changes, source-text execution,
model calls, credentials or API credits are involved. No repair, agent, API or UI
workflow was implemented in Milestone 2.1. At that validation the correction work was uncommitted;
no new push, deployment or remote CI run was performed during that local milestone.
The owner subsequently published it as
`46b6e78c19b0bf37aa15e2c14d91fce2a1d971ef` and reports its GitHub Actions passed
on Python 3.11, 3.12 and 3.13. The original local timings are not CI measurements.

## Milestones 2.2 and 3

Separately authorized against that published baseline, this phase adds newly
authored standalone direct-upwind source fixtures, typed source repair records,
deterministic AST/evidence-based localization rules, one-expression diffs,
disposable source copies, reviewed-source subprocess execution, an independent
scientific gate, bounded internal tool methods and a measured source-repair
benchmark. All new source is developed in this hackathon workspace. No upstream
research implementation or pre-hackathon solver/results/assets were copied.

Fixtures share only existing validated configuration/result records and the
time-step scheduler. Their direct neighbor-difference update is newly written;
candidate patches change source expressions instead of replacing a solver with
the trusted implementation. The original six-branch corpus, trusted numerical
solver, analytical references and diagnostic thresholds are preserved. Standard
AST, hashing, subprocess, POSIX resource-limit and tempfile facilities are Python
dependencies, not claimed research inventions. No new packages or licenses were
introduced and no additional research assets were redistributed.

Proposals are explicitly deterministic or human negative-test controls, not Meta
reasoning. Public verifier cases are withheld from the proposer but are not
securely hidden from a hostile host process. Source recognition and repair scores
cover known patterns; unseen mechanisms remain unevaluated. Resource-limited
subprocesses are not an arbitrary-source sandbox, and Meta-origin execution is
disabled. [New validation](milestone3_validation.md) contains real examples,
rejected/inconclusive proposals, metrics, integrity and test evidence. At that
validation these changes were uncommitted; no commit/push/publish/deployment or
paid API call was performed. The owner subsequently published Milestone 3 as
`622c9cd1ac11e9247a4746555faed3a9485f1abf` and reports its Python
3.11/3.12/3.13 Actions matrix passed. Original timings remain local measurements.
Model integration, general autonomy, FastAPI and UI remain planned.

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


## Milestone 3.1 follow-up

Authorized hardening against published Milestone 3 preserves the original four
source fixtures, six-branch defect corpus, numerical solver, reference equations
and diagnostic thresholds. New work narrows expression policy, binds execution
to checked source bytes, strengthens per-case host-owned verification, makes
cleanup exception-safe and supplies finite bounded JSON orchestration. The
proposer still has exactly three explicit deterministic rules. Structured edit
selection renders a host rule; it is not model-authored source or Meta reasoning.
No Meta calls, credentials, new framework/dependency or external repository code
were used. New correct flux/convex controls and static source-format probes were
authored here; they reuse only existing configuration/result/time scheduling.
They do not expand the reviewed-source execution allowlist or prove unseen-bug
generalization. The container recipe uses standard Docker options with official
documentation attribution in `dev/README.md`; no runtime was available to test it.
[Follow-up validation](milestone3_1_validation.md) separates actual local results,
preserved historical publication/CI claims and untested deployment requirements.
Milestone 3.1 remains uncommitted/unpushed; no history rewrite, licensing change,
asset redistribution, publication, deployment or paid API call was performed.

## Milestone 4 keyless local investigator

On October 29, 2026, the owner authorized local implementation of the agent
protocol, bounded investigation loop, deterministic mock, local Meta Llama 3.1
8B Ollama adapter, CLI, tests and documentation. This newly authored work uses
the unchanged reviewed-source tools and independent mathematical verifier.
No pre-hackathon solver/code/results/assets were imported. Host-rendered edits
retain deterministic origin even when selected by a model. Mock traces are
explicitly not model inference or Llama/Muse performance.

The optional OpenAI client SDK and dependencies were installed in the existing
virtual environment to exercise the already-installed local Llama model. The
adapter follows official Ollama OpenAI-compatible/tool-calling documentation;
no hosted Meta endpoint or Muse behavior is invented. Local loopback inference
was executed, including incomplete investigations; see [Milestone 4 validation](milestone4_validation.md)
for actual outcomes. No real API credentials, hosted model requests, purchases,
model downloads, commits, pushes or deployments were authorized or performed.
