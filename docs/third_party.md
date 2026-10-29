# Third-party dependencies and provenance

## Milestone 1 environment

The validation environment on October 27, 2026 used CPython 3.13.11, NumPy 2.4.3,
pytest 9.0.1, setuptools 80.9.0, and pip 25.3. These packages already existed;
no external dependency downloads were needed. Python 3.11 is the declared minimum,
but execution on Python 3.11/3.12 was not available in this environment.

| Component | Role | Inspected license information | Source |
| --- | --- | --- | --- |
| NumPy 2.4.3 | Sole runtime dependency, array arithmetic | Installed metadata: `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`; the main installed license credits NumPy Developers, 2005–2025. Bundled components retain their own notices. | [Source](https://github.com/numpy/numpy), [main license](https://numpy.org/doc/stable/license.html) |
| pytest 9.0.1 | Scientific test runner | Installed metadata/license: MIT; copyright 2004 Holger Krekel and others. | [Source and license](https://github.com/pytest-dev/pytest/blob/main/LICENSE) |
| setuptools 80.9.0 | Build backend | Installed metadata declares MIT for setuptools; vendored components have separate licenses. Build tooling is not copied into the PhysicsGuard runtime package. | [Source](https://github.com/pypa/setuptools) |
| Python 3.13.11 | Runtime and standard-library dataclasses/Fraction | External runtime; not redistributed by this project. | [Python license](https://docs.python.org/3.13/license.html) |

`pyproject.toml` allows `numpy>=1.26,<3` and `pytest>=8`. For direct dependency
pins matching the measured environment, use Python 3.13.11 and:

```sh
python -m pip install -e '.[dev]' 'numpy==2.4.3' 'pytest==9.0.1'
```

This pins the numerical/test dependencies, not all transitive/build packages.
A complete release lock and distribution-specific notice audit remain future
work. Preserve applicable licenses/notices when redistributing dependencies;
no dependency source is vendored here. FastAPI, Pydantic, model SDKs, and other
future components have not been added by Milestone 1.

Milestone 2 uses the same dependencies plus Python's standard-library dataclasses,
JSON, timing and seeded random utilities. No new runtime/test dependency, copied
upstream code, license change or additional redistributed paper asset was added.
The same local Python/NumPy/pytest versions were used for Milestone 2 validation.

## Research repositories: read-only references

Audit observations from October 27, 2026. No upstream source, prompts, datasets,
weights, figures, or other assets were incorporated into PhysicsGuard.

| Repository | Observed license/access status | Reuse boundary |
| --- | --- | --- |
| [PDE-GAV](https://github.com/PotatoJnny/PDE-GAV) | Accessible; MIT for original code, copyright 2026 PDE Agent Verifier Solver contributors. [Third-party notices](https://github.com/PotatoJnny/PDE-GAV/blob/main/THIRD_PARTY_NOTICES.md) identify AIDE/MIT and ERA/Apache-2.0; additional bundled notices exist. | No blanket clearance for all bundled code/assets. Independently implement ideas. |
| [ChatCFD](https://github.com/ConMoo/ChatCFD) | Redirects to `tianhanz/ChatCFD`; [LICENSE.txt](https://github.com/tianhanz/ChatCFD/blob/main/LICENSE.txt) contains GPLv3 terms. Exact file-level/version-grant scope needs review before reuse. | No copying; any derived-code distribution requires a separate compatibility decision. |
| [AutoNumerics](https://github.com/Daviddjddu/Autonumerics) | Accessible; no top-level license observed; recursive retrieval was incomplete. | No established reuse grant. Paper-only inspiration. |
| [DiffPDE](https://github.com/GU0vvx/DiffPDE) | Accessible; Apache-2.0 for original contributions. [Notices](https://github.com/GU0vvx/DiffPDE/blob/main/THIRD_PARTY_NOTICES.md) cover dLLM-RL adaptations and identify externally loaded CodePDE resources without a verified license grant. | No copying; top-level license does not clear external CodePDE/model/data resources. |
| AutoPDE implementation | No canonical implementation repository/license verified. | Paper-only inspiration. |

Permission under a software license does not establish compliance with competition
new-work requirements. Recheck the exact revision, file notices, asset terms,
attribution requirements, and owner authorization before any future reuse.

## Paper copies and publication

GAV and AutoPDE identify CC BY 4.0; ACL's policy covers published DiffPDE under
CC BY 4.0. ChatCFD's publisher states a Creative Commons Attribution license.
These grants are distinct from source-code licenses and do not automatically
clear separately credited third-party figures.

AutoNumerics uses [arXiv's non-exclusive distribution license](https://arxiv.org/licenses/nonexclusive-distrib/1.0/license.html).
That grant permits arXiv distribution; it is not a general republication license.
Study copies should remain outside the public submission. Existing PDFs are
present in historical commit `23e467c`, although absent from the approved
baseline's tracked tree; `.gitignore` alone cannot remove history. See
[provenance](hackathon_provenance.md) for the outstanding release review.

PhysicsGuard's own project license has not yet been selected. This document is
an audit record, not a claim that all release obligations have been completed.

## Milestone 4 optional local client

The `ollama` extra adds `openai>=1.40,<3`; it is optional and unused in mock CI.
Local validation installed OpenAI SDK 2.54.0 and HTTPX 0.28.1, with their runtime
dependencies, in the repository virtual environment. No SDK source is vendored.
The OpenAI-compatible client targets local Ollama, not a hosted OpenAI/Meta API.
The existing local model is `llama3.1:8b`, reported as 8.0B/Q4_K_M GGUF. Model
weights are not downloaded by PhysicsGuard or redistributed in the repository.
Runtime model/license and full transitive redistribution review remain release
tasks; using the SDK does not establish Meta hosted API access. See the exact
environment/provenance and official references in [Milestone 4 validation](milestone4_validation.md).
