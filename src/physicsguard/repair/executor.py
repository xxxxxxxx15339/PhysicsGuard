"""Bounded child execution of reviewed, narrow fixture edits only.

No arbitrary uploaded/model source is supported. The worker has a sanitized
environment and resource limits, but it shares the host UID/filesystem/network.
This is deliberately NOT advertised as an untrusted-code sandbox.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
from time import monotonic, perf_counter

import numpy as np

from physicsguard.diagnostics.suite import diagnose_solver
from physicsguard.experiments.runner import _NonfiniteOutput, validate_cases
from physicsguard.numerics import AdvectionResult
from physicsguard.schemas.repairs import ProcessRun
from .sources import read_source, source_hash

MAX_MESSAGE = 2 * 1024**2


class WorkerTimeout(TimeoutError):
    pass


class FixtureWorker:
    def __init__(self, workspace: Path, name: str, *, timeout_seconds=2.0, startup_seconds=5.0):
        if (not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool)
                or not 0.01 <= timeout_seconds <= 10 or not 0.1 <= startup_seconds <= 10):
            raise ValueError("bounded positive worker timeouts are required")
        self.root, self.name = Path(workspace).absolute(), name
        self.timeout = timeout_seconds
        self.process = None
        self.buffer = bytearray()
        self.requests = 0
        self.failure = None
        self.failure_status = None
        self.startup_seconds = startup_seconds

    def __enter__(self):
        if sys.platform != "linux" or os.geteuid() == 0:
            raise RuntimeError("reviewed worker requires non-root Linux with POSIX resource limits")
        digest = source_hash(read_source(self.root / "candidate", self.name))
        environment = {"PATH": os.defpath, "LANG": "C.UTF-8", "OPENBLAS_NUM_THREADS": "1",
                       "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        self.process = subprocess.Popen(
            [sys.executable, "-I", "-u", str(Path(__file__).with_name("_worker.py")),
             str(self.root), self.name, digest], cwd=self.root, env=environment,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            start_new_session=True, close_fds=True, bufsize=0)
        os.set_blocking(self.process.stdin.fileno(), False)
        os.set_blocking(self.process.stdout.fileno(), False)
        try:
            ready = self._read(monotonic() + self.startup_seconds)
            if ready != {"ready": True}:
                raise RuntimeError("worker startup protocol failed")
            return self
        except Exception:
            self.close()
            raise

    def _expired(self):
        self.failure_status = "timeout"
        self.failure = "Hard wall-clock limit exceeded; child process group terminated"
        self.close()
        raise WorkerTimeout(self.failure)

    def _read(self, deadline):
        while b"\n" not in self.buffer:
            remaining = deadline - monotonic()
            if remaining <= 0:
                self._expired()
            readable, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not readable:
                self._expired()
            data = os.read(self.process.stdout.fileno(), 65536)
            if not data:
                code = self.process.poll()
                self.failure_status = "resource_limit" if code in (-signal.SIGKILL, -signal.SIGXCPU) else "execution_error"
                self.failure = "Worker exited before producing execution evidence"
                raise RuntimeError(self.failure)
            self.buffer.extend(data)
            if len(self.buffer) > MAX_MESSAGE:
                self.failure_status = "execution_error"
                self.close()
                raise RuntimeError("worker response exceeds protocol limit")
        line, _, remainder = self.buffer.partition(b"\n")
        self.buffer = bytearray(remainder)
        return json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite protocol data")))

    def __call__(self, initial, config):
        if self.failure:
            raise RuntimeError(self.failure)
        self.requests += 1
        deadline = monotonic() + self.timeout
        encoded = (json.dumps({"initial": initial.tolist(), "config": asdict(config)}, allow_nan=False) + "\n").encode()
        if len(encoded) > MAX_MESSAGE // 2:
            raise ValueError("worker request exceeds protocol limit")
        view = memoryview(encoded)
        while view:
            remaining = deadline - monotonic()
            if remaining <= 0:
                self._expired()
            _, writable, _ = select.select([], [self.process.stdin], [], remaining)
            if not writable:
                self._expired()
            written = os.write(self.process.stdin.fileno(), view)
            view = view[written:]
        response = self._read(deadline)
        if response.get("status") != "success":
            if response.get("error_kind") == "nonfinite_output":
                raise _NonfiniteOutput(response.get("error", "confirmed nonfinite child output"))
            if (response.get("error") or "").startswith("MemoryError"):
                self.failure_status, self.failure = "resource_limit", "Child memory resource exhausted"
                raise RuntimeError(self.failure)
            raise RuntimeError(response.get("error", "child execution failed"))
        edges = config.cell_edges()
        return AdvectionResult(config, edges, edges[:-1]+np.diff(edges)/2,
            np.asarray(response["initial_averages"]), np.asarray(response["final_averages"]),
            np.asarray(response["time_steps"]))

    def close(self):
        if self.process is None:
            return
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.process.wait(timeout=2)
        for stream in (self.process.stdin, self.process.stdout):
            if stream and not stream.closed:
                stream.close()

    def __exit__(self, *exception):
        self.close()


def run_source_diagnostics(workspace: Path, name: str, cases, *, timeout_seconds=2.0,
                           startup_seconds=5.0, audience="evaluator_only") -> ProcessRun:
    """Parent computes diagnostics; only reviewed solver calls cross the pipe."""
    cases = validate_cases(cases)  # Invalid callers raise before a child exists.
    started = perf_counter()
    worker = FixtureWorker(workspace, name, timeout_seconds=timeout_seconds, startup_seconds=startup_seconds)
    try:
        with worker:
            report = diagnose_solver(worker, name, cases, audience=audience)
        status = worker.failure_status or "completed"
        return ProcessRun(status, report, perf_counter()-started, worker.requests, worker.failure)
    except WorkerTimeout as error:
        return ProcessRun("timeout", None, perf_counter()-started, worker.requests, str(error))
    except (OSError, RuntimeError, ValueError) as error:
        status = "unsupported" if sys.platform != "linux" or os.geteuid() == 0 else (worker.failure_status or "execution_error")
        return ProcessRun(status, None, perf_counter()-started, worker.requests, str(error))
