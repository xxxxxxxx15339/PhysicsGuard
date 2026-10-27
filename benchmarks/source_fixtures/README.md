# Standalone reviewed solver source fixtures

These four source modules were newly authored for Milestones 2.2/3 during the
hackathon. They derive the direct first-order upwind cell-average difference from
the supported source-free periodic advection specification. They share existing
`AdvectionResult` and `_time_steps` contracts, but do not call or replace themselves
with the trusted solver. No external repository or pre-hackathon code was copied.
They deliberately share a simple scaffold; they are not independent external
scientific projects or unseen defects.

The source text and neutral identifiers may be shown to an investigator. **This
README, evaluator labels and expected locations must not be included in that
interface.** Public source/hashes are not secrets or a secure holdout boundary.

| Source | Evaluator ground truth | Supported localized region |
| --- | --- | --- |
| solver_01.py | Stable conservative transport against physical velocity | `advance`, line 8, signed upstream offset |
| solver_02.py | Missing dx division produces incorrect speed | `advance`, line 9, update coefficient |
| solver_03.py | Positive-velocity incoming seam uses self instead of periodic neighbor | `advance`, line 12, seam value |
| solver_04.py | Correct reference control for this fixture scaffold | No repair should be proposed |

The original files are never modified during evaluation. The source store pins
reviewed original hashes; candidates must change exactly one permitted assignment
expression in a disposable copy. The proposer reads source and actual development
diagnostics, never this table, expected line locations or a reference patch.
Its explicit deterministic rules recognize these supported patterns; that is
not AI-driven or general-purpose fault localization.

Run from the repository root after an editable install:

```sh
python -m benchmarks.source_repair.evaluate --output artifacts/source-repair-evaluator.json
```

The [source evaluator](../source_repair/evaluate.py) joins ground truth only after
investigation. Known-source detection/localization/proposal/repair metrics are
separate from additional parameter cases, correct controls, negative proposals
and unseen patterns (unevaluated). Full reports include source/diffs/hashes,
before/after diagnostics and additional-case results. Only developer-facing
evidence and verification summaries cross the future tool interface.

Workers support non-root Linux only. They recheck reviewed hashes/restricted ASTs,
use controlled cwd/environment and resource limits, and are killed on wall timeout.
They share the host filesystem/network/UID and are **not an arbitrary-code
sandbox**. Meta-origin source execution is disabled. A real private verifier
requires OS-enforced access separation; these public definitions are not hidden.

See [full measured validation and limits](../../docs/milestone3_validation.md).
