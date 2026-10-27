# Milestone 1 validation

Recorded October 27, 2026, from actual local computation. This validates the
deterministic advection foundation; no debugging/repair/model benchmark was run.

## Environment and commands

- Python: CPython 3.13.11, Linux x86_64.
- NumPy: 2.4.3; pytest: 9.0.1.
- Scientific suite: `python -m pytest -q` — **149 passed**.
- Warnings are treated as errors by the project pytest configuration.
- Offline packaging: `python -m pip wheel` with `--no-index --no-deps
  --no-build-isolation --no-cache-dir` built `physicsguard-0.1.0-py3-none-any.whl`
  in a temporary output directory. No external dependencies were downloaded.
- Both Python examples in README executed against that wheel under isolated
  Python (`-I`), using the already-installed NumPy. Required numerical modules
  were present and no research PDFs were included. This is a packaging/import
  smoke check, not a fresh-environment dependency installation test.

Tests for later components remain placeholders and contribute no test cases.
Python 3.11/3.12 and other NumPy versions/platforms were not exercised. Reproduction
instructions and the full convergence command are in [README](../README.md).

## Measured smooth transport

Domain `[0,1)`, initial profile `1 + 0.2*sin(2*pi*x)` integrated over each cell,
constant `a=+1` or `a=-1`, CFL 0.8, final time 0.3. Reference values are exact
cell averages at that time. Normalization: `L1=mean(abs(e))`,
`L2=sqrt(mean(e**2))`, `Linf=max(abs(e))`.

| Speed | Cells | Steps | Max CFL | L1 | L2 | Linf | Absolute mass drift |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| +1 | 64 | 24 | 0.8 | 2.334902656e-3 | 2.592383451e-3 | 3.661799071e-3 | 0.0 |
| +1 | 128 | 48 | 0.8 | 1.172653801e-3 | 1.302423462e-3 | 1.841706414e-3 | 0.0 |
| +1 | 256 | 96 | 0.8 | 5.876657871e-4 | 6.527475760e-4 | 9.231216688e-4 | 0.0 |
| -1 | 64 | 24 | 0.8 | 2.334902656e-3 | 2.592383451e-3 | 3.661799071e-3 | 0.0 |
| -1 | 128 | 48 | 0.8 | 1.172653801e-3 | 1.302423462e-3 | 1.841706414e-3 | 0.0 |
| -1 | 256 | 96 | 0.8 | 5.876657871e-4 | 6.527475760e-4 | 9.231216688e-4 | 0.0 |

Both speed signs gave L1 orders 0.993585 and 0.996709, and L2 orders 0.993081
and 0.996601 under successive doubling. The measured mass drift is exactly zero
under the recorded float64 mass reduction for these six runs; this does not imply
zero rounding error for every initial state or platform.

## Acceptance criteria exercised

| Property | Test requirement |
| --- | --- |
| Constant state | Unchanged for signed/zero speeds and CFL 0.2, 0.8, 1.0. |
| Direction and periodicity | Hand-calculated face-balance updates and exact CFL-1 cell shifts, including wrap and a one-cell domain. |
| Mass | Smooth, discontinuous, and zero-mean profiles over multiple steps; tolerance `50*eps64*(steps+1)*max(1, dx*sum(abs(U0)))` in these nondimensional cases. |
| Per-step properties | Mass, original bounds, and non-increasing periodic TV checked over 80 individual updates under admissible CFLs. |
| Exact reference | Cosine-primitive integration, known half/full-period integrals, nonuniform cells, and independent 32-point Gauss-Legendre quadrature. |
| Smooth convergence | N=64,128,256 at CFL 0.8; decreasing errors; L1/L2 orders in (0.8,1.2); finest-grid L1 below 1e-3. |
| Clock handling | Partial last step, no accumulated-clock extra step, tiny positive duration, target-time sum, positive steps, and CFL compliance to rounding. |
| Stationary cases | Zero speed/duration gives unchanged independent arrays with zero updates. |
| Metamorphic checks | Linearity, cyclic grid-shift equivariance, and consistent domain/velocity rescaling. |
| Data and errors | Reproducible replay; no input aliasing; read-only results; finite output; invalid input/shape/CFL/grid/budget and numerical overflow rejected. |

The independent primitive test oracle reduces travel modulo the period before
subtracting neighboring primitive values. A multi-period case exposed cancellation
in unreduced arguments; quadrature confirmed this reference-rounding issue. The
original comparison tolerance was retained, and the quadrature case is now a
regression test. No acceptance threshold was relaxed to conceal a solver failure.

## Limits

This is a first-order, uniform-grid, source-free scalar advection solver. No WENO,
TENO, Burgers, source-term MMS, fault corpus, diagnostic reporting API, LLM,
candidate repair execution, held-out verifier, or UI workflow is validated here.
Overflow in intermediate physical flux arithmetic explicitly fails. Finite tests
provide evidence under stated assumptions, not universal mathematical proof.
