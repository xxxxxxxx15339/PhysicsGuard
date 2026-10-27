"""Private worker for reviewed fixtures only; not an arbitrary-source endpoint.

This script rechecks pinned originals and the restricted candidate AST itself.
Resource limits and a subprocess are guards, not filesystem/network isolation.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    import contextlib
    import importlib.util
    import json
    import os
    import resource

    if os.geteuid() == 0:
        raise RuntimeError("root execution is unsupported")
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    import numpy as np
    from physicsguard.experiments.runner import execute_solver
    from physicsguard.schemas.repairs import SourceSnapshot
    from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification
    from physicsguard.repair.policy import check_candidate
    from physicsguard.repair.sources import REVIEWED_HASHES, read_source, source_hash

    root, name, expected = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    original = read_source(root / "original", name)
    snapshot = SourceSnapshot(name, source_hash(original), original)
    if REVIEWED_HASHES.get(name) != snapshot.sha256:
        raise ValueError("worker original is not reviewed")
    candidate = read_source(root / "candidate", name)
    if source_hash(candidate) != expected:
        raise ValueError("worker candidate hash mismatch")
    if candidate != original:
        check_candidate(snapshot, candidate)
    spec = importlib.util.spec_from_file_location("_physicsguard_reviewed_candidate", root / "candidate" / name)
    module = importlib.util.module_from_spec(spec)
    with open(os.devnull, "w") as sink:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            spec.loader.exec_module(module)  # Only here, in the bounded child after full source checks.
        print(json.dumps({"ready": True}), flush=True)
        while True:
            line = sys.stdin.buffer.readline(1024**2 + 1)
            if not line:
                return
            if len(line) > 1024**2:
                raise ValueError("request exceeds protocol limit")
            request = json.loads(line)
            cfg = request["config"]
            case = ExperimentCase("worker-request", physics=PhysicsSpecification(
                speed=cfg["speed"], x_min=cfg["x_min"], x_max=cfg["x_max"]),
                n_cells=cfg["n_cells"], cfl=cfg["cfl"], final_time=cfg["final_time"], max_steps=cfg["max_steps"])
            if source_hash(read_source(root / "candidate", name)) != expected:
                raise ValueError("candidate changed during execution")
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                result = execute_solver(module.solve_advection, "worker", case, np.asarray(request["initial"]))
            print(result.to_json().replace("\n", ""), flush=True)


if __name__ == "__main__":
    main()
