# PHYSICSGUARD — MASTER RESEARCH-TO-IMPLEMENTATION PROMPT FOR CODEX

> Historical architecture/audit prompt. Current update, Oct 27, 2026: Milestones 1
> and 2 have since been separately authorized and implemented locally. README and
> `docs/milestone2_validation.md` describe actual capabilities and limitations.

Date: October 27, 2026. Hackathon submission deadline: November 4, 2026, 9:00 PM ET.

## YOUR ROLE

You are the lead scientific software-engineering collaborator for **PhysicsGuard**, a new project in the Meta Global AI Developer Hackathon 2026. Your job is to study the five research papers attached to this Codex workspace, inspect the existing PhysicsGuard scaffold, build an independently verified numerical-debugging agent, and provide real measured experimental evidence. Be skeptical, precise, and production-minded. Do not conflate a solver that runs with a solver that is physically correct.

**Execution guardrail:** In this initial run, perform the repository/paper/license audit and produce a revised architecture and milestone plan **only**. Do not write implementation code, install packages, call paid APIs, or push commits until I explicitly authorize a milestone in a subsequent instruction. Once authorized, implement only that milestone, run tests, and stop. Do NOT automatically build all stages.

## HACKATHON CONTEXT AND STRICT CONSTRAINTS

- Track: Indie Developer. Theme: Push the Frontier.
- Only show and claim project features implemented **during Oct 26–Nov 4, 2026**.
- The submitted repository must be public. Demo video: 3 minutes. One person submits for the team, maximum 4 people.
- Judging rubric (as provided by organizers): impact 30%, creative use of Meta AI 25%, technical depth 20%, demo 25%.
- Do not build an overdone basic RAG/chatbot/dashboard, nor a sports analyzer/coach.
- Preserve a dated git history. Track third-party dependencies, attribution, licenses, and the provenance of every borrowed asset. Do not claim existing research algorithms are ours, or that imported upstream code was developed at this event.
- A permissive license does **not** automatically guarantee compliance with a hackathon rule requiring new work. Default to new, independently written implementation inspired by published methods.
- Use upstream code as **read-only reference by default**. Before copying even a small code portion, inspect the exact repository/file license, attribution obligations, embedded third-party notices, whether the rules allow reused code, and get explicit permission from the project owner. If uncertain, DO NOT COPY; implement independently. Cite the idea.
- Do not publish upstream datasets, proprietary files, checkpoint weights, diagrams, or assets without verifying redistributability. Academic paper licenses are distinct from repository source-code licenses.

## EXPECTED LOCAL INPUTS

Read the repository's `AGENTS.md`, `PHYSICSGUARD_CODEX_CONTEXT.md`, current `README.md`, and the existing file tree. All current Python/HTML/CSS/JS implementation files may be empty placeholders. Keep the existing structure and extend only when justified.

The five attached source papers should be made available in `papers/` (or another clearly identified local location). Find by filename or arXiv ID:

1. `2610.30292v1.pdf` — **GAV: A scientific experimentation environment for PDE agents**, Li & Mou (2026), arXiv:2610.30292.
2. `2606.10752v1.pdf` — **AutoPDE: Reliable Agentic PDE Solving via Explicitly Represented Solver Strategies**, Dong et al. (2026), arXiv:2606.10752.
3. `2026.findings-emnlp.57.pdf` — **DiffPDE: Masked Diffusion Language Models as PDE Solver**, Guo et al. (Findings of EMNLP 2026).
4. `2602.17607v1.pdf` — **AutoNumerics: An Autonomous, PDE-Agnostic Multi-Agent Pipeline for Scientific Computing**, Du, Sun & Yang (2026), arXiv:2602.17607.
5. The PDF whose name starts `adv intell discov - 2026 - Fan - ChatCFD` — **ChatCFD: A Large Language Model-Driven Agent for End-to-End Computational Fluid Dynamics Automation with Structured Knowledge and Reasoning**, Fan et al. (2026), DOI: 10.1002/aidi.202500174.

Keep these PDFs in a local `papers/` folder for private study; do not commit or redistribute them in the public submission unless their redistribution terms are checked. When allowed to modify the repository, add a suitable `.gitignore` entry. If a file is missing, state it explicitly; DO NOT pretend to have read it. Inspect equations, main method sections, figures and experimental protocols directly; cite section/page references in your research notes. When literature evidence and our inference differ, label the difference.

## VERIFIED RESEARCH INTERPRETATION — WHAT TO TAKE / WHAT TO SKIP

**GAV (primary scientific testing influence).** Relevant paper: Sections 3.1–3.3 (MMS construction, private verifier, agent-directed experimentation). Its full framework learns a distribution over continuous reference solutions; this is far too expensive for our short hackathon. ADOPT: generate valid diagnostic problems from analytical/manufactured profiles, an interactive experiment-selection interface, isolated reference access, agent-visible *aggregate* feedback, a held-out final evaluation. SKIP: neural generative model training, Navier–Stokes/Vlasov–Poisson research infrastructure, specialized learned guidance. Our problem is **repairing existing solvers**, not learning to generate new solvers.

**AutoPDE (primary structure/strategy influence).** Relevant paper: Section 5 and the DIAGNOSIS / METHOD / solve-control strategy record. ADOPT: explicit typed PDE specification and solver strategy, numerical assumptions, cheap pilot solves, distinguish implementation bugs from discretization/strategy mismatch. SKIP: general ten-family FEM planner, heavyweight adaptive method synthesis. Do not confuse its solver-generation objective with our debugger objective.

**DiffPDE (primary repair influence).** Relevant paper: Section 4, localized re-masking/infilling and iterative repair. ADOPT: suspected-code localization, small patches, preservation of correct surrounding code, multi-step edit/verify history. SKIP: training masked diffusion LMs and ID-GRPO; Meta Muse Spark can propose localized diffs. Do **not** call that a reproduction of DiffPDE's diffusion algorithm.

**AutoNumerics (primary execution influence).** Relevant paper: Section 2.2 coarse-to-fine and Section 2.3 verification. ADOPT: rapid low-resolution checks first, second-stage rigorous high-resolution and refinement tests, multiple independent diagnostics. SKIP: dispatcher of many model agents, generating solvers for hundreds of PDE families. IMPORTANT: PDE residuals alone are insufficient for identifying all mathematically wrong implementations, particularly when computed using the same incorrect discrete operator.

**ChatCFD (primary reliability influence).** Relevant paper: Sections 2.4 and 3: structured error locator, file/change histories, execution success vs physical fidelity. ADOPT: source localization plus history, traceable actions, reporting whether results meet physics criteria. SKIP: OpenFOAM dependency, RAG vector DB, end-to-end CFD case-file generation. Distinguish ChatCFD's existing contribution from ours.

### REFERENCE REPOSITORIES — READ-ONLY BY DEFAULT

- GAV: https://github.com/PotatoJnny/PDE-GAV — visibly states MIT license; inspect `LICENSE`, `THIRD_PARTY_NOTICES.md`, `sdk/`, `plugins/`, `engine/`, `tests/` for architectural ideas. Prefer own implementation rather than copying the Controller.
- ChatCFD: https://github.com/ConMoo/ChatCFD — repository `LICENSE.txt` indicates GNU GPL v3. **Do not copy implementation into PhysicsGuard by default**; license compatibility and competition new-work rules require additional decisions. Read the architecture only.
- AutoNumerics: https://github.com/Daviddjddu/Autonumerics — repository exists; a top-level license was **not verified**. Treat code as all-rights-reserved until a valid license/permission is established. Read methodology only.
- DiffPDE: https://github.com/GU0vvx/DiffPDE — URL is given by its paper, but its live repository and license were **not independently retrievable at research time**. Verify before using any code; otherwise paper-only inspiration.
- AutoPDE: the paper is verified, but a canonical reusable code repository/license was **not verified**. Do not guess a link or copy code.

Use packages such as NumPy, SciPy, FastAPI, Pydantic, pytest according to their individual licenses; treat these as external dependencies, not features newly built by us. Record each in `docs/third_party.md` (plus source links and version pins). Add `docs/research_inspirations.md` mapping specific design decisions to the relevant paper section.

## PRODUCT POSITIONING

**PhysicsGuard — An AI scientific debugging agent that tests, localizes, patches and independently verifies hidden numerical defects in an existing PDE solver.**

The user provides/selects an existing solver plus a trusted physical specification. PhysicsGuard designs and executes discriminating scientific tests, interprets measurements, proposes localized repairs, and evaluates whether the repair restores correctness and generalizes beyond the diagnostic cases. It must report `verified`, `rejected`, `inconclusive`, or `not tested`; never claim formal mathematical proof based only on finite tests.

Our differentiation is the **combination** of active experimental design, fault localization, minimal repairs, and a separate hidden verifier. DO NOT claim these components or their combination are unprecedented without supporting evidence.

## SELECTED MVP / PRODUCT SCOPE

### First PDE: 1D source-free periodic linear advection

Equation: u_t + a u_x = 0, constant real velocity a on periodic interval [x_L, x_R].

Implement a mathematically correct first-order finite-volume upwind reference solver with Forward Euler, positive and negative a, and a=0, with a time step satisfying |a| dt / dx <= 1. Accept cell-average initial conditions. For smooth test profiles, compute reference *cell averages* (not just point samples), including proper periodic shift u(x,t) = u_0(x-at). Finish at requested T without overshoot. Write NumPy code independently, with no import from earlier WENO-NN research projects.

Invariants/tests under their assumptions:
- periodic conservative finite-volume mass M^n = dx sum_i U_i^n (tolerance scaled to floating precision and accumulated operations);
- exact preservation of constant solutions;
- for monotone first-order upwind with CFL in [0,1], maximum principle/TVD where applicable;
- transport-direction and analytical L1 cell-average error;
- expected first-order global convergence on smooth data under controlled dt/dx and adequate resolution;
- deterministic replay; distinct effects of changing a, dx, dt and periodic phase.

Do not use mass conservation as an all-purpose bug detector: a wrong-sign conservative flux can also conserve mass. Do not demand TVD for arbitrary schemes or shocks without checking assumptions. Diagnose numerical error vs discretization error properly.

### Second PDE (after advection works): 1D inviscid Burgers

Equation: u_t + (u^2/2)_x = 0. Use a conservative Godunov-type method with a stable CFL policy. Tests should include correct shock propagation and entropy selection; use exact Riemann solutions where available or a separately validated reference, rather than comparing to a naive smooth solution after shock formation. Defer if integration threatens milestone completion.

### OPTIONAL manufactured solutions (only after compatible source-term interface exists)

For specified differentiable u*(x,t), construct s = u*_t + (f(u*))_x, together with corresponding IC/BC, and verify a solver that **explicitly accepts source terms**. Never apply nonzero-source MMS to a source-free-only solver or mix pointwise and cell-average semantics. For advection, we can initially use source-free travelling-wave profiles, which already have exact references.

## PHYSICSBUGBENCH — NEW HACKATHON BENCHMARK

Introduce a `benchmarks/` or `src/physicsguard/benchmark/` module as appropriate; keep clear separation among benchmark mutation generators, development experiments, and held-out scoring.

Target 12–20 varied, realistically subtle injected defects, *not* 20 aliases of one mass-source bug, with at least two clean (bug-free) controls. Potential mutation classes:
- flux sign/direction;
- wrong interface neighbor indexing;
- periodic wrap mistake;
- wrong velocity sign handling;
- incorrect spatial scaling (dx);
- incorrect final-step / CFL handling;
- state mutation / accidental in-place aliasing;
- spurious source in a source-free PDE;
- nonconservative local flux construction;
- incorrect Burgers flux or entropy selection (later);
- code that executes but fails grid refinement;
- simultaneous coupled defects for harder cases (later).

IMPORTANT: each mutation must be classified by **known actual mathematical symptoms**, not assumption. Some incorrect schemes remain mass conserving, some have only phase error, some fail only negative velocity. Validate mutations experimentally and keep defect labels out of the investigator's context.

Partition examples into: development/public examples for agent iteration; fully hidden test seeds and defect details for final scoring. Prevent the agent from reading the answer labels, ground-truth code, hidden exact solutions, and hidden runner implementation. A fixed seed must not be treated as the only evidence of generalization. Include clean controls to measure false positive edits.

## ARCHITECTURE — MODULES AND TYPED CONTRACTS

Preserve the existing project file layout and implement these conceptual contracts (refine names based on repository conventions; avoid making many pointless layers):

- `PDESpec`: PDE family, equation coefficients, domain, BC/IC kinds, source-term presence, expected invariants and restrictions.
- `SolverStrategy`: scheme, reconstruction, flux method, time integrator, CFL policy, grid handling, known limitations; explicit inspectable record (AutoPDE-inspired).
- `SolverAdapter`: narrow interface that maps a numerical implementation and one `ExperimentSpec` into arrays, snapshots, metrics and runtime; initially only trusted example projects and allowlisted files.
- `ExperimentSpec`: PDE parameters, profile, grid size, time horizon, numerical-control settings, selected diagnostic, random seed; validate before execution.
- `ExperimentResult`: arrays/metadata, status, runtime, stdout/stderr, scientific measurements; reproducible JSON serialization.
- `DiagnosticReport`: invariant name, assumptions, measured deviation, numerical tolerance, pass/fail/uncertain, confidence **only when empirically justified**, and candidate bug hypotheses.
- `DiagnosisHypothesis`: suspected component/path/line range, cause, discriminating follow-up test, justification.
- `RepairProposal`: exact candidate path/span/diff, rationale, scope, expected effect, provenance/model identity.
- `VerificationReport`: before/after performance, held-out check results, regressions, patch decision, evidence and limitations.

Suggested areas: existing `numerics/`, `diagnostics/`, `experiments/`, `agent/`, `repair/`, `schemas/`, `api/`, `tests/`; add `benchmarks/`, `verification/`, or `sandbox/` only as needed. Avoid a multi-service distributed deployment.

### Key boundaries

1. Only deterministic scientific-engine components compute metrics and judgments. The model may interpret and propose, not assign itself a pass.
2. Development tests can be selected by the investigator; hidden verification tests cannot.
3. Code patch proposal != code patch approval != scientifically verified improvement. Distinct statuses and logs.
4. Maintain immutable original code, run repairs in ephemeral copies, generate `diff` output, and permit easy rollback.
5. No raw execution of arbitrary model-supplied code in the FastAPI server or host environment.

## TOOL-USING META AI AGENT

Use Meta **Muse Spark 1.3** (`muse-spark-1.3`) with the real Meta Model API at `https://api.meta.ai/v1`, authentication via `MODEL_API_KEY` only from environment variables. Verify exact current request/response/structured-output/tool-calling formats in https://dev.meta.ai/docs/overview and https://dev.meta.ai/docs/models before coding. Prefer official or OpenAI-compatible supported SDK, not hypothetical parameters.

Design one stateful tool-using investigator, not five overlapping LLM agents. Potential tools (tool names can be adapted):
- `inspect_solver()` — read allowlisted source and strategy metadata;
- `get_physics_spec()` — return independent trusted physical specification;
- `run_experiment(experiment_spec)` — validate and execute controlled test;
- `get_diagnostics(run_id)` — measured violations plus assumptions;
- `compare_runs(left_id,right_id)` — differential evidence;
- `propose_patch(path, diff)` — submit a structured localized patch for validation;
- `verify_patch(patch_id)` — invoke separate verifier, not the model;
- `get_public_history()` — investigator actions, hypotheses, measurements.

Make tool usage real. Support at most a bounded number of rounds, calls and compute resources; output parseable structured records. Keep full transcript (minus secrets and private verifier labels). Model's follow-up experiments should vary deliberately based on prior outcomes. Use honest error handling for API unavailable / quota exhausted; a deterministic offline mode is for development only and must be labeled as NOT a Meta AI demonstration.

### Security / execution

Initially work with restricted, known Python files in a project-owned corpus; do not support uploading arbitrary public code until an isolated sandbox is ready. Eventually use a container or equivalent restricted sandbox with resource/time/memory/output limits, no network, least privileges, read-only dependencies, ephemeral writable copy, path traversal defense, and explicit exec capability. Do not rely on AST analysis alone as a full sandbox. Never execute copied untrusted repos blindly. Secrets never enter prompts or logs.

## REPAIR / VERIFICATION POLICY

- Investigate -> localized candidate patch -> diff review -> isolated test -> independent verifier -> final decision.
- Validator checks target paths, patch scope, syntax, basic interface compatibility and any policy limits before executing.
- Allow human confirmation of applying patches in a user-controlled repository. The verifier's decision is about tested properties, not full mathematical proof.
- First release may restrict edit operations to a small allowlisted set. If repairs are entirely hardcoded, document that honestly and do NOT claim general code-repair autonomy. The prize-level target is model-proposed, code-specific patches tested on *unseen* defects.
- Keep separate pre/post held-out experiments; do not repeatedly reveal hidden case parameters in model feedback.
- Fail safely on invalid results, NaN/Inf, timeouts, divergence, nondeterminism, inappropriate method assumptions, or degraded previously passing tests.
- Show false positives and rejected repairs, not only cherry-picked successes.

## EXPERIMENTAL EVALUATION DESIGN

Evaluate at least these baselines under matched execution/time/token budgets:
1. Deterministic PhysicsGuard invariant tests alone (no Meta model).
2. Direct one-shot Meta LLM code review without diagnostic tools.
3. Meta agent using experiments/diagnostics but no repair.
4. Full PhysicsGuard agent using experiment selection, localized patch proposals and independent verification.

Report:
- bug detection recall and precision / clean-control false-positive rate;
- bug localization top-1/top-3 (if meaningful);
- proportion of proposed repairs that parse and execute;
- **held-out verified repair success rate** and new regression rate;
- experiments, model calls, median latency, compute time, and estimated API spend per case;
- attempted, successful, rejected and inconclusive outcomes, with at least one failure analysis;
- seed, code commit, configuration and model version.

Do not invent performance numbers. Separate known injected defects from completely unseen solvers; state evaluation limitations. No leakage of defect identity or held-out oracle answers into agent input.

## IMPLEMENTATION ORDER (TIME-BOXED)

**Milestone 0 — Today:** Confirm papers/repository contents and licenses; create `docs/research_inspirations.md`, `docs/third_party.md`, an architecture decision record, and typed interface proposal. Refine scientific criteria before implementing.

**Milestone 1 — Today:** Original first-order upwind finite-volume advection solver and trusted analytical reference cell averages; actual tests for constant state, mass conservation, sign of a, a=0, smooth convergence, invalid CFL, final time, deterministic replay. Add only NumPy and pytest, plus dependencies required for packaging. Report measured values from local runs.

**Milestone 2 — Oct 28:** Diagnostics and a collection of 8–12 validated mutations with clean controls, expandable to 12–20. Demonstrate at least two classes of flaws not detectable by simple mass checks.

**Milestone 3 — Oct 29:** Independent experiment runner, restricted patch representation, localize suspicious code, verification on new test cases, artifacts/logs. No arbitrary-source execution.

**Milestone 4 — Oct 30–31:** Real Meta Muse Spark tool-use integration and measurable investigator behavior; use real model responses. Prove at least some chosen tests depend on previous observations. Evaluate plain LLM baseline.

**Milestone 5 — Nov 1–2:** One coherent app/demo: select defective code -> agent examines -> test -> highlights defect -> proposes diff -> verifies -> compare plots. FastAPI/web only after backend loop works.

**Milestone 6 — Nov 3–4:** Evaluate on held-out benchmark, license/provenance audit, public repository, 3-minute demo, submission. Freeze risky features in time.

If behind schedule, cut Burgers/MMS/fancy UI before cutting truthful AI integration or independent verification. Do not overextend to OpenFOAM or 3D CFD.

## SCIENTIFIC NUANCES / EDGE CASES

- For periodic finite-volume methods, mass conservation follows interface-flux telescoping when the *same* numerical face flux is used by adjacent cells. A scheme can be mass conservative but inconsistent/unstable.
- Enforce consistent center-values vs finite-volume cell averages in both initial data and exact references. Use analytic integration where practical or accurate quadrature with checked convergence.
- CFL restrictions apply to specific numerical schemes/time integrators; they are not universal across all solvers. For linear first-order upwind + Forward Euler, |a| dt/dx <= 1 gives monotonicity.
- When comparing empirical convergence, control all confounding discretization parameters, including time-step scaling and reference accuracy. Smooth profiles matter.
- PDE residual computed by the same wrong discrete operator may be misleading. Combine independent references, consistency checks, invariants and metamorphic comparisons.
- A proposed Burgers patch must respect entropy admissibility; mass conservation alone is insufficient.
- Manufactured solutions for nonzero forcing require that the code under test supports the corresponding forced equation.
- Distinguish an implementation error from reasonable but inaccurate low-order numerical diffusion; don't 'fix' legitimate method limitations by hiding them.

## DELIVERABLES FROM THIS CODEX TURN

1. A 1–2 page repository and literature audit with citations to exact paper pages/sections and any missing sources.
2. A clear architecture decision record that maps each adopted paper idea to a PhysicsGuard module, plus explicit non-goals.
3. A license/provenance audit listing every upstream repo and `verified`, `incompatible/caution`, or `unknown` status; no copied code without permission.
4. A precise typed-interface plan with file-by-file proposed changes and scientifically justified acceptance criteria for Milestone 1.
5. A minimal proposal for the first code milestone, but **do not implement yet**. Wait for my explicit “Start Milestone 1” instruction.
6. A concise list of follow-on milestones, with no automatic implementation.

**Always make small, reviewable diffs, preserve existing project work, and report what was actually tested.** Never silently publish to GitHub or spend on API calls. Stop after the planning/audit handoff and ask the project owner to review. When later authorized to start a milestone, stop after that milestone.

## ACADEMIC REFERENCES

- Li, M., & Mou, W. (2026). GAV: A scientific experimentation environment for PDE agents. https://arxiv.org/abs/2610.30292
- Dong, H., et al. (2026). AutoPDE: Reliable Agentic PDE Solving via Explicitly Represented Solver Strategies. https://arxiv.org/abs/2606.10752
- Guo, W., et al. (2026). DiffPDE: Masked Diffusion Language Models as PDE Solver. Findings of EMNLP 2026. https://aclanthology.org/2026.findings-emnlp.57/
- Du, J., Sun, Y., & Yang, H. (2026). AutoNumerics: An Autonomous, PDE-Agnostic Multi-Agent Pipeline for Scientific Computing. https://arxiv.org/abs/2602.17607
- Fan, E., et al. (2026). ChatCFD: A Large Language Model-Driven Agent for End-to-End Computational Fluid Dynamics Automation with Structured Knowledge and Reasoning. Advanced Intelligent Discovery. https://doi.org/10.1002/aidi.202500174
- Meta Model API. https://dev.meta.ai/docs/overview
- Meta hackathon official landing page. https://dev.meta.ai/events/global-hackathon

End of handoff.
