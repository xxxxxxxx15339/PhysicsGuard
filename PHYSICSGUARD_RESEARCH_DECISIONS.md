# PhysicsGuard — Research-informed implementation decisions

Date: October 27, 2026. Internal hackathon planning. Not a claim of novel research.

Current implementation update: Milestones 1 and 2 are implemented locally. The
owner's Milestone 2 scope approved six distinct faults and three correct controls;
the larger corpus below remains a future target. No Meta integration or repair
success is implied. See `docs/milestone2_validation.md` for measured evidence.

## Product
Investigate and repair pre-existing numerical PDE code through agent-chosen experiments, localized changes, and independent hidden scientific verification. Primary user: numerical computing researcher/engineering developer. The MVP is constrained to finite-volume 1D linear advection and, if time, inviscid Burgers.

## Source-to-feature map

| Paper | Scientific method verified in source | Adopt | Defer / reject |
|---|---|---|---|
| GAV (Li & Mou, arXiv 2610.30292; Sec. 3.1–3.3) | manufactured PDE/reference pairs; interactive test selection; verifier protects reference | experiment generator, private verifier, held-out test | learned continuous generative model, advanced guided sampling |
| AutoPDE (Dong et al., arXiv 2606.10752; Sec. 5) | independent numerical strategy record; diagnosis/method cards; cheap pilots | typed `PDESpec`, `SolverStrategy`, pilot diagnostics | general solver generation or multi-PDE FEM library |
| DiffPDE (Guo et al., EMNLP Findings 2026; Sec. 4) | targeted span infilling based on localization, multi-round repair | localized diff and edit history | diffusion model training and ID-GRPO |
| AutoNumerics (Du et al., arXiv 2602.17607; Sec. 2) | coarse-to-fine execution; error/residual verification | staged tests and independent diagnostics | many agents and broad PDE generation |
| ChatCFD (Fan et al., 2026; Sec. 2.4 and evaluation) | error localization, structured reflection, physical fidelity distinct from execution | traceable diagnosis and scientific-verification report | OpenFOAM stack and vector DB |

## Novelty caution
These are known research ideas. The proposed practical combination is not verified to be novel and must not be described as a first. The hackathon contribution is an independent implementation of a focused existing-code debugging product, plus empirical measurements demonstrating whether it actually works.

## Live repository review (October 27, 2026)

- https://github.com/PotatoJnny/PDE-GAV — exists, labelled MIT. Read-only architecture reference by default. Must check file-level license and THIRD_PARTY_NOTICES before reuse.
- https://github.com/ConMoo/ChatCFD — exists; LICENSE.txt states GNU GPL v3. Avoid direct code copying to prevent accidental copyleft obligations and ambiguity over new-work rule.
- https://github.com/Daviddjddu/Autonumerics — exists; no top-level license verified in public repo view. Do not copy code until authors' grant/license established.
- https://github.com/GU0vvx/DiffPDE — named by academic PDF, but live content/license not verified in audit. Treat as unavailable for code reuse until verified.
- AutoPDE official repo — not verified. Paper-only inspiration.

**Even MIT/GPL permissions do not override competition originality/new-work restrictions.** Safe default: learn from the paper and implement original code during competition. Use third-party libraries as dependencies with appropriate attribution, not as newly built features.

## Proposed minimum benchmark
- 12–20 distinct validated defect cases, at least two clean controls.
- Hold-out parameter combinations and mutation classes where feasible.
- Show counterexample that conserves mass but gets transport wrong.
- Give the agent only code/spec/public experiment feedback, not ground-truth defect or private verifier samples.
- Compare deterministic tests, one-shot Meta LLM review, agent with experiments only, and full repair-and-verification agent.
- Report verified repair successes and regressions, not only discovery rate.

## Scientific criteria
- source-free periodic FV advection conserves mass by flux telescoping.
- reference solution must compare appropriate cell averages.
- Forward Euler upwind monotonic CFL <= 1; not universal.
- separate valid diffusion of low-order method from actual implementation defect.
- residuals may be uninformative if they reuse the same buggy operator.
- MMS with nonzero source is in scope only after a forced-PDE interface exists.

## MVP priorities
1. Trusted solver plus tests.
2. Faulty mutations with distinct symptoms.
3. Agent-chosen test selection.
4. Targeted diff and held-out verifier.
5. Real Meta API, reliable demo and evidence.
6. Additional PDE/UI only if time.

Sources: primary user-provided PDFs named in the Codex master prompt, plus official Meta documentation and repositories linked above.
