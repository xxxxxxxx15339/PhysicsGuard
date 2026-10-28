"""Reviewed-source worker. Checks bind execution to bytes, not a reopened path.

This does not provide host filesystem/network isolation or arbitrary-code safety.
"""
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class SourceMismatch(ValueError):
    pass


def load_checked_code(root, name, expected):
    from physicsguard.schemas.repairs import SourceSnapshot
    from physicsguard.repair.policy import check_candidate
    from physicsguard.repair.sources import REVIEWED_HASHES, read_source, source_hash
    original = read_source(root / "original", name)
    snapshot = SourceSnapshot(name, source_hash(original), original)
    if REVIEWED_HASHES.get(name) != snapshot.sha256:
        raise SourceMismatch("worker original is not reviewed")
    candidate = read_source(root / "candidate", name)
    if source_hash(candidate) != expected:
        raise SourceMismatch("worker candidate hash mismatch")
    if candidate != original:
        try:
            check_candidate(snapshot, candidate)
        except (ValueError, SyntaxError) as error:
            raise SourceMismatch("worker source policy rejected candidate") from error
    # Compile EXACTLY the checked bytes; never ask an import loader to reopen them.
    return compile(candidate.encode("utf-8"), str(root / "candidate" / name), "exec")


def main():
    import contextlib
    import os
    import resource
    if os.geteuid() == 0:
        raise RuntimeError("root execution is unsupported")
    for kind, limit in ((resource.RLIMIT_CPU, 10), (resource.RLIMIT_AS, 2*1024**3),
                        (resource.RLIMIT_NOFILE, 64), (resource.RLIMIT_NPROC, 64),
                        (resource.RLIMIT_FSIZE, 1024**2), (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(kind, (limit, limit))
    import numpy as np
    from physicsguard.experiments.runner import execute_solver
    from physicsguard.schemas.results import ExperimentCase, PhysicsSpecification
    from physicsguard.repair.protocol import decode_frame, encode_frame, MAX_REQUEST, MAX_RESPONSE, MAX_REQUESTS
    from physicsguard.repair.sources import read_source, source_hash
    root, name, expected = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    code = load_checked_code(root, name, expected)
    namespace = {"__name__": "_physicsguard_reviewed_candidate", "__file__": str(root / "candidate" / name)}
    with open(os.devnull, "w") as sink:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            exec(code, namespace)  # Pinned/restricted reviewed code ONLY, in this bounded child.
        sys.stdout.buffer.write(encode_frame({"ready": True, "sha256": expected}, MAX_RESPONSE))
        sys.stdout.buffer.flush()
        for ordinal in range(1, MAX_REQUESTS+1):
            line = sys.stdin.buffer.readline(MAX_REQUEST+1)
            if not line:
                return
            request = decode_frame(line, MAX_REQUEST)
            if (set(request) != {"request_id", "sha256", "config", "initial"}
                    or type(request["request_id"]) is not int or request["request_id"] != ordinal
                    or request["sha256"] != expected):
                raise ValueError("request identity/configuration protocol mismatch")
            cfg = request["config"]
            case = ExperimentCase("worker-request", physics=PhysicsSpecification(
                speed=cfg["speed"], x_min=cfg["x_min"], x_max=cfg["x_max"]),
                n_cells=cfg["n_cells"], cfl=cfg["cfl"], final_time=cfg["final_time"], max_steps=cfg["max_steps"])
            if source_hash(read_source(root / "candidate", name)) != expected:
                raise SourceMismatch("candidate changed during execution")
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                result = execute_solver(namespace["solve_advection"], "worker", case, np.asarray(request["initial"]))
            response = {"request_id": ordinal, "sha256": expected, "result": result.to_dict()}
            sys.stdout.buffer.write(encode_frame(response, MAX_RESPONSE))
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        from physicsguard.repair.protocol import encode_frame, MAX_RESPONSE
        kind = "source_mismatch" if isinstance(error, SourceMismatch) else "resource_limit" if isinstance(error, MemoryError) else "protocol_error"
        sys.stdout.buffer.write(encode_frame({"ready": False, "kind": kind, "error": type(error).__name__}, MAX_RESPONSE))
        sys.stdout.buffer.flush()
        sys.exit(1)
