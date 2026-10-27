# PhysicsGuard — Persistent Codex Instructions

> Copy this file to the repository root as `AGENTS.md`. This is repository guidance, not permission to implement the application.

## Project and status

PhysicsGuard is a NEW project for the Meta Global AI Developer Hackathon, Oct 26–Nov 4, 2026. Intended entry: **Indie Developer** track, **Push the Frontier** theme. It is an AI-assisted debugging agent for scientific numerical simulations: run mathematical diagnostics, have a real Meta-powered agent reason over failures and propose narrowly scoped repairs, and independently verify each candidate fix by rerunning simulations. **The mathematical verification engine, not the LLM, determines whether a repair works.**

As of Oct 27, 2026, **Milestones 1 and 2 are implemented locally**: the trusted
advection solver, deterministic scientific diagnostics, bounded experiment runner,
and PhysicsBugBench fault/control evaluation exist. See the milestone validation
documents for executed evidence. Model integration, repairs, API, UI workflow
and deployment remain unimplemented. Do not imply otherwise.

Before working, read `README.md` and the relevant architecture/provenance documents under `docs/` if they have content. The complete historical handoff is in `PHYSICSGUARD_CODEX_CONTEXT.md` if placed in the root (or supplied in chat).

## Hackathon requirements

- Only newly developed work from Oct 26–Nov 4 may be presented as hackathon contribution. Do not reuse pre-hackathon WENO/TENO project code/results/plots/models.
- Submission: public GitHub repo, attributable new code/features, working 3-minute video, deadline Nov 4, 9 PM ET.
- Do not claim a Meta API integration exists unless it has been built and tested; verify current official docs before choosing API endpoints/model IDs.
- Avoid disallowed/overdone categories: generic dashboards, basic RAG, Streamlit apps, sports analyzers/coaches, medical advice, etc.
- Judging weights: impact 30%, Meta AI use 25%, technical depth 20%, demo 25%. Keep the product demo understandable and evidence-based.
- Track/theme changes, publication, remote pushes, deployment, paid API usage and credentials require separate approval.

## Architecture boundaries

- `src/physicsguard/numerics/`: deterministic PDE solvers; first MVP is periodic 1D source-free linear advection.
- `diagnostics/`: conservation and accuracy checks, then CFL/TV/boundedness checks only under valid assumptions.
- `experiments/`: controlled repeatable scenarios, numerical parameters and evidence.
- `agent/`: current official Meta AI integration; hypothesis generation, test selection, structured repair planning, traceable actual tool outputs.
- `repair/`: schema validation, restricted reversible proposals, independent acceptance gate. Never execute arbitrary AI-generated Python in the API process.
- `schemas/`: typed request, proposal and result records.
- `api/`: small FastAPI orchestration endpoints.
- `web/`: custom HTML/CSS/JS demonstration, not a chatbot/dashboard-only product.
- `tests/`: deterministic scientific tests, negative cases, and agent-tool contract tests.

## Numerical requirements

Model: `∂_t u + ∂_x(a u) = 0`, constant speed, periodic domain. Finite-volume state is cell averages. The flux-form semidiscrete equation is `d ubar_i/dt = -(F_{i+1/2}-F_{i-1/2})/dx`. For source-free periodic flux-form updates, total discrete mass `dx * sum(ubar_i)` must remain invariant within floating-point tolerance. Use a simple first-order upwind method initially. Check CFL for the chosen method. Compare numerical *cell averages* against properly constructed exact/reference cell averages. State precise norms and assumptions. Do not treat TVD, boundedness, positivity or conservation as universal for arbitrary PDEs/BCs.

First planned demo: a controlled solver defect introduces an unphysical extra source, producing a measurable mass-conservation failure; the agent proposes a restricted change and the independent gate tests it. Controlled defects are demo fixtures, not evidence of general automatic code repair.

## Engineering principles

Python 3.11+, NumPy, pytest, FastAPI/Pydantic, custom static web interface, model SDK verified at integration time. Small typed functions, explicit physics assumptions, deterministic tests, reproducible parameters, minimal dependencies, no invented results, no fake model traces. Keys in environment variables only. Isolate and bound any future untrusted execution; never execute generated code directly in the service. If a test has not been run, report it as unverified.

## Current collaboration rule

**A context handoff or planning request is read-only.** Do not modify files or write implementation until the user explicitly authorizes a specific milestone. For implementation requests, outline changed files, acceptance criteria and tests, then work only on the approved milestone. Do not commit, push, deploy, access private credentials or spend API credits without separate permission.

Milestones: (0) architecture and contracts; (1) deterministic advection solver/tests; (2) diagnostics/fault fixtures; (3) restricted repair/verification; (4) actual Meta agent/tool calling; (5) FastAPI/UI; (6) provenance, demo, public submission. Avoid broadening scope before passing the prior milestone.
