"""Typed evidence contracts. No benchmark labels or model decisions belong here."""

from dataclasses import asdict, dataclass, field
import json
from typing import Literal

from physicsguard.numerics import AdvectionConfig
from physicsguard.numerics._validation import finite_real, positive_integer


class JsonRecord:
    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        """Strict JSON: NaN/Infinity are unavailable evidence, never JSON numbers."""
        return json.dumps(self.to_dict(), allow_nan=False, sort_keys=True, indent=2)


@dataclass(frozen=True)
class PhysicsSpecification(JsonRecord):
    speed: float = 1.0
    x_min: float = 0.0
    x_max: float = 1.0
    equation: Literal["u_t + (a*u)_x = 0"] = "u_t + (a*u)_x = 0"
    boundary: Literal["periodic"] = "periodic"
    source_free: bool = True
    state: Literal["cell_averages"] = "cell_averages"
    length_unit: str = "length"
    time_unit: str = "time"
    field_unit: str = "u"

    def __post_init__(self):
        cfg = AdvectionConfig(speed=self.speed, x_min=self.x_min, x_max=self.x_max)
        for name in ("speed", "x_min", "x_max"):
            object.__setattr__(self, name, getattr(cfg, name))
        if (self.equation, self.boundary, self.state, self.source_free) != (
            "u_t + (a*u)_x = 0", "periodic", "cell_averages", True
        ) or not isinstance(self.source_free, bool):
            raise ValueError("only source-free periodic cell-average linear advection is supported")
        if not all(isinstance(x, str) and x for x in
                   (self.length_unit, self.time_unit, self.field_unit)):
            raise ValueError("units must be nonempty strings")


@dataclass(frozen=True)
class SolverStrategy(JsonRecord):
    """Declared assumptions, supplied independently of the candidate code."""
    method: str = "first_order_upwind"
    time_integrator: str = "forward_euler"
    grid: str = "uniform"
    monotone_cfl_limit: float = 1.0

    def __post_init__(self):
        if not all(isinstance(value, str) and value for value in
                   (self.method, self.time_integrator, self.grid)):
            raise ValueError("strategy names must be nonempty strings")
        limit = finite_real(self.monotone_cfl_limit, "monotone_cfl_limit")
        if limit <= 0:
            raise ValueError("monotone_cfl_limit must be positive")
        object.__setattr__(self, "monotone_cfl_limit", limit)

    @property
    def supports_upwind_checks(self) -> bool:
        return (self.method, self.time_integrator, self.grid, self.monotone_cfl_limit) == (
            "first_order_upwind", "forward_euler", "uniform", 1.0)


@dataclass(frozen=True)
class ExperimentCase(JsonRecord):
    case_id: str
    physics: PhysicsSpecification = field(default_factory=PhysicsSpecification)
    strategy: SolverStrategy = field(default_factory=SolverStrategy)
    n_cells: int = 64
    cfl: float = 0.8
    final_time: float = 0.23
    profile: Literal["sine", "square", "constant"] = "sine"
    offset: float = 1.0
    amplitude: float = 0.2
    mode: int = 1
    phase: float = 0.37
    max_steps: int = 20_000

    def __post_init__(self):
        if not isinstance(self.case_id, str) or not self.case_id:
            raise ValueError("case_id must be nonempty")
        if not isinstance(self.physics, PhysicsSpecification) or not isinstance(self.strategy, SolverStrategy):
            raise ValueError("typed physics and strategy records are required")
        cfg = self.config()
        for name in ("n_cells", "cfl", "final_time", "max_steps"):
            object.__setattr__(self, name, getattr(cfg, name))
        for name in ("offset", "amplitude", "phase"):
            object.__setattr__(self, name, finite_real(getattr(self, name), name))
        object.__setattr__(self, "mode", positive_integer(self.mode, "mode"))
        if self.profile not in ("sine", "square", "constant"):
            raise ValueError("unsupported profile")

    def config(self) -> AdvectionConfig:
        return AdvectionConfig(n_cells=self.n_cells, speed=self.physics.speed,
                               x_min=self.physics.x_min, x_max=self.physics.x_max,
                               cfl=self.cfl, final_time=self.final_time, max_steps=self.max_steps)


@dataclass(frozen=True)
class SolverExecutionResult(JsonRecord):
    solver_id: str
    case: ExperimentCase
    status: Literal["success", "error"]
    elapsed_seconds: float
    initial_averages: tuple[float, ...] = ()
    final_averages: tuple[float, ...] = ()
    time_steps: tuple[float, ...] = ()
    max_cfl: float | None = None
    error: str | None = None
    error_kind: Literal["nonfinite_output", "execution_error"] | None = None


@dataclass(frozen=True)
class DiagnosticResult(JsonRecord):
    diagnostic_id: str
    description: str
    assumptions: tuple[str, ...]
    applicable: bool
    status: Literal["pass", "fail", "inconclusive"]
    measurements: dict[str, float | list[float] | None]
    units: dict[str, str]
    acceptance_criteria: str
    tolerance: float | None
    tolerance_justification: str
    evidence_errors: tuple[str, ...] = ()
    case_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiagnosticReport(JsonRecord):
    solver_id: str
    cases: tuple[ExperimentCase, ...]
    executions: tuple[SolverExecutionResult, ...]
    diagnostics: tuple[DiagnosticResult, ...]
    elapsed_seconds: float
    audience: Literal["investigator", "evaluator_only"] = "evaluator_only"

    @property
    def detected(self) -> bool:
        """Evidence of a failed property, with no assertion of fault location."""
        return any(d.status == "fail" for d in self.diagnostics)

    @property
    def inconclusive_count(self) -> int:
        return sum(d.status == "inconclusive" for d in self.diagnostics)
