"""Bounded reviewed-fixture execution; no arbitrary-code sandbox or upload API."""
from dataclasses import asdict
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
from time import monotonic, perf_counter
from math import fsum

import numpy as np
from physicsguard.diagnostics.suite import diagnose_solver
from physicsguard.experiments.runner import _NonfiniteOutput, validate_cases
from physicsguard.numerics import AdvectionResult
from physicsguard.numerics._validation import real_vector
from physicsguard.schemas.repairs import ProcessRun
from physicsguard.schemas.results import SolverExecutionResult, ExperimentCase, PhysicsSpecification, SolverStrategy
from .protocol import ProtocolError, decode_frame, encode_frame, MAX_REQUEST, MAX_RESPONSE, MAX_REQUESTS
from .sources import REVIEWED_HASHES, read_source, source_hash

MAX_MESSAGE = MAX_RESPONSE


class WorkerFailure(RuntimeError):
    def __init__(self, message, status="protocol_error"):
        super().__init__(message)
        self.status = status


class WorkerTimeout(WorkerFailure, TimeoutError):
    pass


class FixtureWorker:
    def __init__(self, workspace, name, *, expected_sha256=None, timeout_seconds=2.0, startup_seconds=5.0):
        if (type(timeout_seconds) not in (int, float) or not 0.01 <= timeout_seconds <= 10
                or type(startup_seconds) not in (int, float) or not 0.1 <= startup_seconds <= 10):
            raise ValueError("bounded positive worker timeouts are required")
        self.root, self.name = Path(workspace).absolute(), name
        self.expected = REVIEWED_HASHES.get(name) if expected_sha256 is None else expected_sha256
        if self.expected is None:
            raise ValueError("worker source is not allowlisted")
        self.timeout, self.startup_seconds = timeout_seconds, startup_seconds
        self.process, self.buffer, self.requests = None, bytearray(), 0
        self.failure, self.failure_status = None, None

    def __enter__(self):
        if sys.platform != "linux" or os.geteuid() == 0:
            raise WorkerFailure("reviewed worker requires non-root Linux", "unsupported")
        if source_hash(read_source(self.root / "candidate", self.name)) != self.expected:
            raise WorkerFailure("candidate bytes differ from the authorized hash", "source_mismatch")
        environment = {"PATH": os.defpath, "LANG": "C.UTF-8", "OPENBLAS_NUM_THREADS": "1",
                       "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        try:
            self.process = subprocess.Popen([sys.executable, "-I", "-u", str(Path(__file__).with_name("_worker.py")),
                str(self.root), self.name, self.expected], cwd=self.root, env=environment,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                start_new_session=True, close_fds=True, bufsize=0)
            os.set_blocking(self.process.stdin.fileno(), False)
            os.set_blocking(self.process.stdout.fileno(), False)
            ready = self._read(monotonic()+self.startup_seconds)
            if ready != {"ready": True, "sha256": self.expected}:
                self._abort(ready.get("kind", "protocol_error"), "worker startup/identity rejected")
            return self
        except BaseException as error:
            self._close_preserving(error)
            raise

    def _abort(self, status, message):
        if status not in {"timeout", "resource_limit", "unsupported", "execution_error", "protocol_error", "source_mismatch"}:
            status = "protocol_error"
        self.failure_status, self.failure = status, message
        error = WorkerTimeout(message, status) if status == "timeout" else WorkerFailure(message, status)
        self._close_preserving(error)
        raise error

    def _deadline(self, deadline):
        remaining = deadline-monotonic()
        if remaining <= 0:
            self._abort("timeout", "Hard wall-clock limit exceeded; child process group terminated")
        return remaining

    def _read(self, deadline):
        try:
            while b"\n" not in self.buffer:
                readable, _, _ = select.select([self.process.stdout], [], [], self._deadline(deadline))
                if not readable:
                    self._abort("timeout", "Hard wall-clock limit exceeded; child process group terminated")
                try:
                    data = os.read(self.process.stdout.fileno(), 65536)
                except BlockingIOError:
                    continue
                if not data:
                    code = self.process.wait(timeout=1)
                    status = "resource_limit" if code in (-signal.SIGKILL, -signal.SIGXCPU) else "execution_error"
                    self._abort(status, "Worker exited before producing execution evidence")
                self.buffer.extend(data)
                if len(self.buffer) > MAX_RESPONSE:
                    self._abort("protocol_error", "worker response exceeds protocol limit")
            line, _, remainder = self.buffer.partition(b"\n")
            self.buffer = bytearray(remainder)
            return decode_frame(bytes(line), MAX_RESPONSE)
        except WorkerFailure:
            raise
        except ProtocolError:
            self._abort("protocol_error", "malformed/nonfinite worker JSON response")
        except (OSError, ValueError, subprocess.TimeoutExpired):
            self._abort("protocol_error", "worker pipe/lifecycle failed")

    def __call__(self, initial, config):
        if self.failure:
            raise WorkerFailure(self.failure, self.failure_status)
        if self.requests >= MAX_REQUESTS:
            self._abort("protocol_error", "worker request budget exhausted")
        ordinal, deadline = self.requests+1, monotonic()+self.timeout
        try:
            encoded = encode_frame({"request_id": ordinal, "sha256": self.expected,
                                    "initial": initial.tolist(), "config": asdict(config)}, MAX_REQUEST)
            view = memoryview(encoded)
            while view:
                _, writable, _ = select.select([], [self.process.stdin], [], self._deadline(deadline))
                if not writable:
                    self._abort("timeout", "Hard wall-clock limit exceeded; child process group terminated")
                try:
                    written = os.write(self.process.stdin.fileno(), view)
                except BlockingIOError:
                    continue
                if not written:
                    raise OSError("worker pipe closed")
                view = view[written:]
            self.requests = ordinal
            response = self._read(deadline)
            if response.get("kind"):
                self._abort(response["kind"], "worker rejected source or request")
            if (set(response) != {"request_id", "sha256", "result"}
                    or type(response["request_id"]) is not int or response["request_id"] != ordinal
                    or response["sha256"] != self.expected):
                raise ProtocolError("reply identity mismatch")
            result = response["result"]
            if not isinstance(result, dict) or set(result) != set(SolverExecutionResult.__dataclass_fields__):
                raise ProtocolError("invalid worker result schema")
            values = dict(result["case"])
            values["physics"] = PhysicsSpecification(**values["physics"])
            values["strategy"] = SolverStrategy(**values["strategy"])
            if ExperimentCase(**values).config() != config or result["solver_id"] != "worker":
                raise ProtocolError("worker returned another numerical configuration")
            if type(result["elapsed_seconds"]) not in (int, float) or result["elapsed_seconds"] < 0:
                raise ProtocolError("invalid worker elapsed time")
            status = result["status"]
            if status == "error":
                if result["error_kind"] not in ("nonfinite_output", "execution_error") or not isinstance(result["error"], str) or len(result["error"]) > 4096:
                    raise ProtocolError("invalid execution error record")
                if result["error_kind"] == "nonfinite_output":
                    raise _NonfiniteOutput(result["error"])
                if result["error"].startswith("MemoryError"):
                    self._abort("resource_limit", "Child memory resource exhausted")
                raise RuntimeError(result["error"])
            if status != "success" or result["error"] is not None or result["error_kind"] is not None:
                raise ProtocolError("invalid success status")
            for key in ("initial_averages", "final_averages", "time_steps"):
                if not isinstance(result[key], list):
                    raise ProtocolError("worker arrays must be JSON lists")
            if (len(result["initial_averages"]) != config.n_cells or len(result["final_averages"]) != config.n_cells
                    or len(result["time_steps"]) > config.max_steps):
                raise ProtocolError("worker result shape limit exceeded")
            start = real_vector(result["initial_averages"], "worker initial")
            final = real_vector(result["final_averages"], "worker final")
            steps = real_vector(result["time_steps"], "worker timesteps", minimum_size=0)
            if not np.array_equal(start, initial):
                raise ProtocolError("worker initial state changed")
            if (np.any(steps <= 0) or config.speed == 0 and len(steps)
                    or config.final_time == 0 and len(steps)
                    or config.speed != 0 and config.final_time > 0
                    and abs(fsum(steps)-config.final_time) > 8*np.spacing(config.final_time)):
                raise ProtocolError("inconsistent worker time schedule")
            edges = config.cell_edges()
            return AdvectionResult(config, edges, edges[:-1]+np.diff(edges)/2, start, final, steps)
        except _NonfiniteOutput:
            raise
        except WorkerFailure:
            raise
        except (ProtocolError, ValueError, TypeError, KeyError, OSError, OverflowError) as error:
            self._abort("protocol_error", f"invalid worker response/transport: {type(error).__name__}")

    def close(self):
        if self.process is None:
            return
        try:
            # A failed group leader may already have exited while children remain.
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait(timeout=2)
        finally:
            for stream in (self.process.stdin, self.process.stdout):
                if stream and not stream.closed:
                    stream.close()

    def _close_preserving(self, error):
        try:
            self.close()
        except (OSError, subprocess.TimeoutExpired) as cleanup:
            self.failure_status = self.failure_status or "execution_error"
            error.add_note(f"Worker cleanup failed: {type(cleanup).__name__}")

    def __exit__(self, kind, error, traceback):
        if error is not None:
            self._close_preserving(error)
        else:
            self.close()


def run_source_diagnostics(workspace, name, cases, *, expected_sha256=None, timeout_seconds=2.0,
                           startup_seconds=5.0, audience="evaluator_only"):
    """Host-only reviewed execution. Caller input failures raise before startup."""
    cases = validate_cases(cases)
    started = perf_counter()
    worker = FixtureWorker(workspace, name, expected_sha256=expected_sha256,
                           timeout_seconds=timeout_seconds, startup_seconds=startup_seconds)
    try:
        with worker:
            report = diagnose_solver(worker, name, cases, audience=audience)
        return ProcessRun(worker.failure_status or "completed", report, perf_counter()-started, worker.requests, worker.failure)
    except WorkerFailure as error:
        return ProcessRun(error.status, None, perf_counter()-started, worker.requests, str(error))
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        return ProcessRun(worker.failure_status or "execution_error", None, perf_counter()-started, worker.requests, str(error))
