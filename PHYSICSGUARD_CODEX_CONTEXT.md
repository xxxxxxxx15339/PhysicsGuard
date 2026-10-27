# PhysicsGuard — Complete Context Handoff for Codex

> **This is a project handoff, not a request to implement the project.**
> Read and understand the context, inspect the existing repository if available, and return an architecture/roadmap summary. **Do not create, modify, or delete source files, install packages, run network operations, make commits, push to GitHub, or start implementation until I give you a separate, explicit implementation task.**

## 1. Who I am and what we are building

I am a computer-science/AI engineering student participating in the **Meta Global AI Developer Hackathon**, taking place **October 26 to November 4, 2026**. I have relevant academic/research experience in numerical methods for partial differential equations, finite-volume solvers, ENO/WENO/TENO shock-capturing, machine learning, JAX, Python, and scientific benchmarking.

Our new hackathon project is called **PhysicsGuard**.

**One-sentence pitch:** PhysicsGuard is an AI-assisted scientific debugging agent that finds, explains, proposes repairs for, and experimentally verifies numerical errors in scientific simulation software.

**User problem:** Researchers and engineers may obtain plausible-looking simulation plots even when the implementation violates physical/mathematical requirements: discrete conservation, boundary conditions, stability restrictions, or comparison with a known solution. Conventional unit tests and static checks often do not reveal these scientific failures. PhysicsGuard combines an LLM's hypothesis generation and investigation planning with a deterministic numerical verification engine. The product must show concrete evidence rather than claim that a fix works on the model's authority.

We discussed alternative concepts (StencilForge, SolverMedic, CircuitLens) and selected **PhysicsGuard** because it presents an accessible engineering need, an agentic workflow, and a compelling before-and-after demo.

### Important: existing experience is NOT submission code

I have worked on a separate pre-hackathon WENO/TENO research project. You may use this as **domain background** to understand numerical PDEs, but **do not copy its repository, code, experimental results, trained models, plots, or implementation into PhysicsGuard**. Anything claimed as our hackathon contribution must be newly built within the event period, or clearly identified as an authorized third-party dependency/asset. Pre-existing concepts and academic publications may be cited. Never portray old research results as PhysicsGuard results.

## 2. Hackathon requirements — hard constraints

From the organizers' rules and official kickoff slides provided to the project:

- **New work only:** Everything presented as the team's contribution must be developed during **Oct 26–Nov 4, 2026**. Make new work attributable and obvious.
- **Demo only newly developed functionality:** In the demo, clearly distinguish our new functionality from third-party models, packages, and pre-existing assets. Ambiguous provenance can cause disqualification.
- **Public GitHub repository** is mandatory for submission. Ensure it can be opened while signed out.
- **Team size:** 1 to 4 members; solo participation is valid. One person submits for the team and adds all team members.
- **Exactly one track:** **Indie Developer** is the intended track. Do not enter in the Startup track simultaneously.
- **Theme:** **Push the Frontier** is the intended problem statement. It explicitly welcomes substantial AI applications to engineering, science, and technical problems.
- **Meta AI must have a meaningful role**, more substantial than a superficial chatbot or API call; verify the model/API capabilities from current official documentation before coding against them.
- **Required submission:** a working **3-minute demo video**, public repository, and submission through the Cerebral Valley platform.
- **Deadline:** **Wednesday, Nov 4, 2026, 9:00 PM Eastern Time** (the event timezone; check current offsets if converting). Plan to finish ahead of the deadline.
- **Disallowed material/projects:** Do not infringe intellectual-property rights or use unauthorized code, images, datasets, or assets. Avoid disallowed/overdone project types (AI-generated medical advice, basic RAG, simple image analyzers, Streamlit apps, dashboards as the primary feature, generic education chatbots, job screeners, nutrition coaches, personality analyzers, sports analyzers/coaches). PhysicsGuard must clearly be an engineering problem-solving tool, not just a dashboard/chatbot.
- **Eligibility:** at least 18 and of legal age where the participant resides; do not claim compliance on behalf of team members without verifying their details.

**Judging rubric from event slides:** 30% impact, 25% Meta AI tooling, 20% technical depth, 25% demo. **Impact + demonstration = 55%**. Build a real and understandable workflow, not a large but unfinished system.

**Bonus prize targeting:** Best Agentic Use-Case ($5k in the provided slides) is a plausible secondary target, but do not assume that satisfying an agentic description guarantees eligibility or scoring. A best-open-weights bonus is distinct from merely calling a hosted model.

**Resources from kickoff slides:** $150 in Meta Model API credits per eligible builder, and conditional partner credits (Baseten, Modal, Fireworks). Claim links were announced in the Discord #resources channel. Do not assume credits are already claimed or that credentials are available.

## 3. Current development status — do not hallucinate progress

**As of October 27, 2026, this repository is a scaffold ONLY.** We explicitly decided to create the structure without implementing application code. The structure ZIP was produced at this stage. Implementation files in the ZIP are empty placeholders, not working features; the README simply says that implementation has not started. There is no verified Meta integration, solver, diagnostic, API, frontend, or deployed application yet. Do not describe any of these as completed.

I want to work **architecture-first, milestone-by-milestone**. For this initial handoff, **read, summarize, and plan only**. Wait for an explicit subsequent instruction such as "Implement Milestone 1" before writing any implementation.

## 4. Proposed user experience and boundaries

The central product workflow is:

1. A user selects or submits a *supported numerical simulation* and scenario (MVP uses built-in, controlled simulation modules; arbitrary untrusted repository execution is not an MVP feature).
2. PhysicsGuard runs a deterministic diagnostic suite on a baseline scenario and stores raw evidence.
3. A Meta-powered agent inspects test failures and solver metadata/source within the permitted scope, forms hypotheses, and selects targeted follow-up experiments.
4. The agent proposes a narrowly scoped, **structured** repair with an explanation tied to evidence.
5. A separate verification engine validates the proposal, applies it in an isolated and reversible candidate context, reruns diagnostics and regression tests, and computes before/after metrics.
6. The UI shows the original failure, hypothesis, proposed change, test evidence, repaired result, uncertainty, and honest success/failure status.

**Central principle: the LLM suggests; mathematical tests verify.** Never present a model explanation as proof. If the repair fails, surface that transparently.

### MVP boundaries

- **IN:** 1D periodic linear advection, an independently tested simple finite-volume baseline, a small set of controlled fault scenarios, mathematical tests, a reversible allowlisted repair pathway, the agent's reasoning/tool calls, a basic FastAPI service, a custom HTML/CSS/JS interface, complete automated tests, a reproducible demo.
- **OPTIONAL LATER:** inviscid Burgers, further independent benchmark cases, multiple defect categories, broader structured source inspection, validated fixes for a second solver.
- **OUT FOR INITIAL MVP:** full 3D CFD, Navier–Stokes, unstructured meshes, general arbitrary code execution, proving all PDE solvers correct, fine-tuning foundation models, training new large models, replacing existing numerical verification with chat responses, or deploying a multi-tenant execution service.

We may expand scope only after meeting the prior milestone's acceptance criteria.

## 5. Layered architecture and separation of responsibilities

```
Web UI (HTML/CSS/JavaScript)
    |
    v
FastAPI HTTP API and orchestration
    |                                \
    v                                 v
Agent layer (Meta Model API)     Scientific engine (NumPy)
    |                                 |
    +---------- structured proposals--+
                    |
                    v
          Repair & validation gate
                    |
                    v
          Evidence and result records
```

**Web UI:** starts controlled scenarios, shows run status, displays real numerical measurements and charts, compares before/after outcomes, and exposes agent actions. A dashboard alone is not the product; the real agentic debugging workflow is.

**FastAPI:** validates requests, dispatches finite, controlled experiments, responds with typed JSON records, enforces timeouts and scopes, and does not trust user-supplied paths or code.

**Agent:** uses Meta's authorized model interface (candidate: Muse Spark, subject to live verification) to interpret diagnostics, choose tests, and propose a structured repair. It should use defined tools rather than invent run results. Store tool-call and proposal traces for demo transparency; filter secrets. Do not hard-code a fake "AI found the bug" result.

**Scientific engine:** implements and runs deterministic numerical solvers. It owns all simulation calculations and benchmark ground truths.

**Diagnostics:** independent computations of conservation residuals, stability-condition compliance, and error norms; reports the hypotheses/assumptions under which each assertion is valid.

**Repair:** only permit a documented, allowlisted range of changes at first, ideally validated parameter/configuration/operation replacements. Never run arbitrary generated Python in the API process. Proposed changes must be reviewable and reversible; refuse unsafe or malformed instructions. Separate agent recommendation from the gate that accepts a repair.

**Experiment/evidence storage:** record test-case ID, parameters, grid spacing, timestep, CFL, initial condition, solver variant, seed if relevant, numeric metrics, fix proposal, verdict and errors. Use JSON initially; database not required for MVP.

## 6. Exact existing repository scaffold

The initial ZIP contains the following relative structure (empty placeholder files unless noted):

```text
physicsguard/
├── .github/
│   └── workflows/
│       └── .gitkeep
├── docs/
│   ├── architecture.md
│   ├── hackathon_provenance.md
│   └── demo_plan.md
├── src/
│   └── physicsguard/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── main.py
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── model_client.py
│       │   └── planner.py
│       ├── numerics/
│       │   ├── __init__.py
│       │   ├── advection.py
│       │   └── fluxes.py
│       ├── diagnostics/
│       │   ├── __init__.py
│       │   ├── accuracy.py
│       │   └── conservation.py
│       ├── repair/
│       │   ├── __init__.py
│       │   ├── proposals.py
│       │   └── validator.py
│       ├── experiments/
│       │   ├── __init__.py
│       │   ├── runner.py
│       │   └── scenarios.py
│       └── schemas/
│           ├── __init__.py
│           └── results.py
├── web/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
│   ├── test_numerics.py
│   ├── test_diagnostics.py
│   ├── test_agent.py
│   └── test_api.py
├── examples/
│   └── .gitkeep
├── artifacts/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

Do not rename or reorganize this structure without explaining why and receiving approval. Empty placeholder files are intentional. The README and `.gitignore` are the only contentful text files in the scaffold. Do not assume a GitHub repository has already been created or pushed.

## 7. Scientific requirements for the first experiment

### Governing PDE

One-dimensional, source-free, periodic linear advection:

\[
\partial_t u + \partial_x(a u)=0, \qquad a\in\mathbb{R}\text{ constant}.
\]

On uniform finite-volume cells \(I_i\) of width \(\Delta x\), track cell averages \(\bar u_i(t)\):

\[
\frac{d\bar u_i}{dt}=-\frac{\hat f_{i+1/2}-\hat f_{i-1/2}}{\Delta x}.
\]

For a **consistent shared interface flux** and periodic boundaries, the discrete total mass

\[
M(t)=\Delta x\sum_i\bar u_i(t)
\]

is conserved up to floating-point rounding and time-integration error (for standard conservative explicit integration, the algebraic flux sum cancels at each stage). We must explicitly test the relevant conditions instead of assuming them.

A simple *first-order upwind* reference is sufficient for the first milestone. A good starting point is positive constant advection speed with conservative upwind interface flux and an explicit timestep satisfying the scheme's CFL restriction. More advanced reconstructions are future work and not necessary for the first demonstration.

### Verified diagnostics to build progressively

- **Mass conservation** on a source-free periodic domain: \(|M(t)-M(0)|\), with scale-aware tolerances. This is not the correct invariant test for systems with nonzero sources or open boundary fluxes unless modified to include them.
- **Analytical solution comparison:** for periodic linear advection, \(u(x,t)=u_0((x-at)\bmod L)\). Compare *cell averages* to matching exact/reference cell averages, not a pointwise field mislabeled as a cell-average reference.
- **Accuracy:** \(L_1=N^{-1}\sum_i|e_i|\), \(L_2=\sqrt{N^{-1}\sum_i e_i^2}\), and \(L_\infty=\max_i|e_i|\), clearly identifying the normalization convention.
- **CFL:** compute \(|a|\Delta t/\Delta x\); reject inadmissible cases for a chosen scheme, rather than labeling all CFL>1 cases universally unstable.
- **Total variation:** \(TV(u)=\sum_i|u_{i+1}-u_i|\) with periodic wrap if used. Non-increase is a property of specific schemes under specific conditions, not a universal property of every PDE, solver, or Euler system.
- **Boundedness / positivity:** report only where mathematically justified (e.g. monotonicity-preserving upwind advection with suitable data/CFL). Never claim that positivity tests alone prove general solver correctness.
- **Reproducibility:** fixed explicit numerical parameters and clear test inputs.

### Controlled defect scenarios

The first memorable demo should use a solver variant containing an **unphysical extra source term** (mass drift), which is a detectable defect in the intended *source-free periodic advection* model. The agent should identify a likely nonconservative contribution and propose a specific removal/replacement within an allowlisted repair mechanism. The verifier should rerun tests and show the mass error drops substantially while other tests remain acceptable.

Possible next defects, only when time permits: incorrect periodic boundary indexing, wrong flux direction/sign, inconsistent interface flux, or a timestep violating the chosen numerical scheme's CFL constraint. Build defect fixtures to exercise real discovery; do not just display canned before/after numbers.

Remember that injecting a known fault is a demonstration fixture, **not** proof that the system can find arbitrary unknown bugs. Be clear about evaluated scope and limitations.

## 8. Tech stack and coding principles

Proposed stack (subject to setup validation when implementation begins):

- Python 3.11+; `src/` package layout.
- NumPy for deterministic 1D numerics.
- pytest for scientific-unit and end-to-end tests.
- FastAPI + Pydantic for API and typed records.
- Custom HTML/CSS/JavaScript for a lightweight interface; avoid Streamlit given the hackathon's anti-project list.
- Meta Model API / compatible SDK, with model identifier and tool-calling format **verified from Meta official documentation at implementation time**. Do not invent an endpoint, SDK schema, model name, or access entitlement.
- Secret configuration via environment variables; never commit real keys; `.env.example` documents names without values.
- GitHub public repo for competition submission, but create or push it only when I explicitly approve.

**Code style:** small functions with clear inputs and outputs; type annotations; minimal dependencies; deterministic tests; docstrings explaining physical assumptions and units; no hidden global mutable numerical state; clear separation of solver, diagnostics, LLM, orchestration, and UI; error responses rather than silently substituting fake success.

**Security:** no arbitrary LLM-generated Python execution in-process, no arbitrary shell command execution via model tools, no uncontrolled user-provided filesystem paths, no unrestricted remote Git access, bounded loops and timeouts, scrub API tokens from logs, no write-to-production/deploy/credential changes without authorization. If a later phase truly requires execution of untrusted candidate code, propose a resource-restricted, network-isolated process/container and seek authorization first.

## 9. Suggested milestones and exit criteria

**Milestone 0 — Architecture and planning (current)**
- Confirm repo tree; map modules; define minimal data contracts; identify mathematical assumptions and risks.
- No source code changes until I explicitly authorize Milestone 1.

**Milestone 1 — Deterministic solver + tests**
- Implement periodic 1D advection in `numerics/`.
- Tests: constant solution, mass conservation, transport of smooth initial condition, reasonable convergence/accuracy behavior, parameter/CFL validation, no NaNs.
- Exit: all documented numerical tests pass; known results reproducible without LLM/API.

**Milestone 2 — Diagnostics + controlled failures**
- Implement mass/accuracy/CFL diagnostics and a deliberately faulty case with real measurable violations.
- Exit: correct implementation passes, faulty implementation fails, and the diagnostic clearly identifies which assumption/test is violated.

**Milestone 3 — Safe repair and verification loop**
- Build structured proposal schema and allowlisted candidate edits; repeat tests and compare to baseline.
- Exit: tests reject a wrong repair and accept a genuinely improved fix; all repairs reversible and logged.

**Milestone 4 — Genuine Meta AI agent**
- Implement current official model API and tool-calling; agent obtains real diagnostics, reasons over failures, selects follow-up tests, and proposes repair actions.
- Exit: actual model invocations shown in sanitized trace; no fake tool results; deterministic verification remains independent; graceful handling of no access/credits.

**Milestone 5 — FastAPI + custom UI**
- User can run a scenario and inspect real input, baseline output, failed invariants, AI investigation trace, proposed fix, independent verification, and before/after comparison.
- Exit: interactive repeatable demo, no phantom success statuses.

**Milestone 6 — Submission and polish**
- Public repository with licenses and source attribution, clean new-work provenance, setup instructions, tests, and a real 3-minute demo video.
- Exit: full demo replays on a fresh environment and repo works for a reviewer.

**Tentative timebox:** Oct 27 foundation; Oct 28–29 deterministic numerics; Oct 30–31 agent and verification; Nov 1–2 UI and integrated demo; Nov 3 video and cleanup; Nov 4 submission buffer. These are planning targets, not work already finished.

## 10. What makes this a serious agentic product

The key is a **closed-loop, evidence-based agent**:

1. Initial invariant check returns raw measured violations.
2. Model proposes a hypothesis with confidence/uncertainty and a discriminating test.
3. Test engine executes the selected valid test and supplies results back to the model.
4. Model proposes a structured repair (one of the permitted choices).
5. Independent verifier reruns regression tests and computes metrics.
6. Only verified successful proposals get an accepted status; failed and uncertain proposals are visible.

A rule-based defect detector with an LLM-generated explanation is **not** enough to claim the model autonomously discovered a fix. Honest attribution is necessary. We should assess at least a few distinct seeded defects or held-out variations before making robustness claims.

A good 3-minute demo shows: problem and consequences; deliberately flawed numerical experiment; scientific diagnostic failure; real Meta model reasoning/tool use; applied controlled repair; evidence-rich before/after output; limitations and contribution list.

## 11. Provenance and academic grounding

- Keep a dated implementation history from the hackathon window; document which code/components/assets were built in the event.
- In `docs/hackathon_provenance.md`, list original work separately from external dependencies and earlier academic inspiration.
- Never reuse old project plots/checkpoints as hackathon evidence.
- Prefer primary numerical-method references for physics/math claims. Relevant starting references to confirm/cite in the appropriate documentation:
  - Jiang & Shu (1996), *Efficient Implementation of Weighted ENO Schemes*, Journal of Computational Physics, DOI: `10.1006/jcph.1996.0130` (WENO background).
  - Fu, Hu & Adams (2016), *A family of high-order targeted ENO schemes for compressible-fluid simulations*, Journal of Computational Physics, DOI: `10.1016/j.jcp.2015.10.037` (TENO background).
  - Stevens & Colonius (2020), *Enhancement of shock-capturing methods via machine learning*, Theoretical and Computational Fluid Dynamics, DOI: `10.1007/s00162-020-00531-1` (ML-enhanced solver context).
- These papers are scientific background and are **not** claims that PhysicsGuard was already implemented or published.
- Verify every dependency's license and every external link used in final docs; do not invent references, prizes, API availability, evaluation metrics, or experiment results.

## 12. How I want you (Codex) to collaborate

- **Start from what is in the repository, not from assumptions.** Empty files mean not implemented.
- Be precise, mathematical, and direct. Explain design choices, alternatives, and scientific validity assumptions.
- Prefer a small working, testable milestone over broad unvalidated scope.
- For each implementation phase, first state the files expected to change, acceptance criteria, tests, and any major tradeoffs. Then implement **only** the phase that I authorize.
- Do not silently change the project track, theme, numerical model, frontend stack, or new-work constraints.
- Do not claim a test passed unless you executed it and saw the result. Report commands and observable outcomes; distinguish skipped tests from passed tests.
- Do not claim an agent fixed a scientific bug unless the measured validation supports it.
- Avoid overengineering, premature ML training, unnecessary infrastructure, and invented functionality.
- Ask for one necessary piece of information only when you truly cannot proceed safely; otherwise make narrow and transparent assumptions in the implementation plan.
- External side effects (publish, push, deploy, credentials, paid API calls) require explicit authorization.

## 13. YOUR INSTRUCTIONS FOR THIS FIRST HANDOFF

**Read-only task. Do not begin implementation.**

1. Inspect the actual repository layout and existing README (if present).
2. Tell me what PhysicsGuard aims to do and how the agent, solver, diagnostics, repair gate, API and UI fit together.
3. Confirm what exists now versus what is only planned.
4. Restate hackathon eligibility/compliance constraints, the development window, deadline and scoring priorities.
5. Present a concrete Milestone 1 design, including function/data contracts and tests, but **no code and no file modifications**.
6. Identify the highest-risk assumptions (e.g., actual Meta API access, numerical correctness, executing model-proposed changes safely, provenance, demo timing).
7. Stop and wait for my next explicit instruction.

**Success for this first interaction is shared understanding, not lines of code.**
