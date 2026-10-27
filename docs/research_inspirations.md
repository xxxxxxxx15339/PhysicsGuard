# Research inspirations and implementation boundaries

Recorded October 27, 2026. These are known research mechanisms informing an
independent implementation, not claims of novelty or reproductions of the systems.
Local study PDFs exist for AutoPDE, DiffPDE, and AutoNumerics. GAV was reviewed via
its public paper; ChatCFD via publisher full text and the author preprint. Diagrams,
equations, methods, experimental protocols, and limitations were inspected during
the architecture review. No paper images or upstream implementation code are used
as application assets.

| Source | Evidence and assumptions | PhysicsGuard adaptation | Current state |
| --- | --- | --- | --- |
| [GAV](https://arxiv.org/abs/2610.30292), §§3.1–3.3, pp. 4–6, Eq. 2, Fig. 1, Appendix C.2 | Matching PDE/reference construction, private references, error/runtime feedback, and separate final evaluation. MMS requires compatible PDE operators, forcing, and BCs. Its theory assumes independent evaluation and additional distribution/convexity conditions. | Independently calculated references; later agent-directed experiments and held-out verification. No learned generator or transfer of theoretical guarantees to code patches. | Source-free analytical travelling waves implemented; active experiments and private verifier planned. |
| [AutoPDE](https://arxiv.org/abs/2606.10752), §5, pp. 5–6, Fig. 4, Appendix H, p. 16 | Explicit diagnosis/method/control records and measured pilot solves. Evaluation is based on a FEM backend. | Explicit numerical configuration now; later separate physics/strategy records and cheap pilot experiments. Expected first-order diffusion is a method limitation, not automatically a bug. | Numerical controls implemented; agent strategy workflow planned. |
| [DiffPDE](https://aclanthology.org/2026.findings-emnlp.57/), §4.1, p. 1172, §4.3, Appendix A, p. 1180 | Localized infilling with preserved context. Documented deterministic localization is traceback-anchored; global repairs remain a limitation. | Later evidence-linked source spans, localized diffs, and edit/verify histories. Silent numerical errors require additional experimental evidence. No diffusion training, ID-GRPO, or claimed equivalent speedup. | Planned. |
| [AutoNumerics](https://arxiv.org/abs/2602.17607), §§2.2–2.3, pp. 2–3, Eq. 1, Fig. 1 | Coarse-to-fine execution and analytical/residual metrics. Regular-domain evaluation and high-order/high-dimensional failures limit generalization. | Multiple grid resolutions and independent scientific signals. Later staged execution; no assumption that fine-grid failure is always a stability issue. Candidate-computed residuals cannot serve as the sole oracle. | Deterministic refinement/accuracy/invariant tests implemented; execution pipeline planned. |
| [ChatCFD](https://doi.org/10.1002/aidi.202500174), §2.4, p. 6, §3.2, pp. 9–10, Fig. 2 | Structured localization, modification histories, and separation of execution success from physical fidelity. Physical fidelity includes conditions/model checks and flow-feature comparisons. | Separate execution and scientific outcomes, quantitative advection checks, and later traceable repair histories. No OpenFOAM/RAG stack or claim of reproducing its fidelity evaluation. | Quantitative numerical tests implemented; investigation/history/reporting planned. |

Page references above use the respective paper's printed pages (DiffPDE uses
proceedings pagination; ChatCFD uses publisher pagination). The ChatCFD preprint
has different pagination. Research results are not PhysicsGuard benchmarks.

## Mathematical foundation

The implemented solver follows the standard conservative finite-volume balance
and signed upwind flux, derived directly from constant-speed linear advection.
The exact reference follows analytic integration of a periodic travelling sine
wave over each cell. These established methods do not depend on any of the five
systems' source code. No forcing interface, Burgers solver, learned numerical
method, model integration, or benchmark result is implied by this milestone.

## Milestone 2 application of the research

The earlier table describes Milestone 1's state. The separately authorized
Milestone 2 now implements these original adaptations:

- **GAV §§3.1–3.3, pp. 4–6; Appendix C.2:** analytical references remain owned by
  diagnostics, and measured development feedback is separated from final scoring.
  `experiments/scenarios.py`, `diagnostics/accuracy.py` and the evaluator implement
  that evidence boundary. No learned generator, source-term MMS, interactive
  model-directed testing or inherited theoretical guarantee is claimed. GAV's
  primary arXiv HTML was reread for this phase.
- **AutoPDE §5, pp. 5–6, Fig. 4:** `PhysicsSpecification`, `SolverStrategy` and
  `ExperimentCase` separate physical requirements from numerical assumptions.
  These are experiment contracts for debugging existing code, not a solver
  generation system. The local supplied PDF's strategy/pilot sections were read.
- **AutoNumerics §§2.2–2.3, pp. 2–3:** `diagnostics/suite.py` runs inexpensive
  coarse cases before refinement and metamorphic probes. Multiple independent
  measurements replace reliance on execution success or a reused discrete
  residual. No agent team, fresh solver generation or assumption that every
  fine-grid failure is a stability problem is adopted. Sections were read from
  the local supplied PDF.
- **DiffPDE §§4.1, 4.3, p. 1172; Appendix A, p. 1180:** localized repair remains
  deferred. Each diagnostic now links to its supporting experiment IDs, while
  benchmark fault locations/answers stay out of investigator evidence. A failed
  measurement alone does not justify a source span. The local PDF was consulted;
  no diffusion model or source-editing implementation is used.

The smooth upwind truncation envelope and square-pulse BV translation bound are
independent mathematical derivations described in [validation](milestone2_validation.md).
None of the measured PhysicsBugBench results is taken from these papers.
