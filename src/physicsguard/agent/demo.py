"""Local investigation demo: python -m physicsguard.agent.demo --backend mock."""
import argparse
from collections import Counter
import os
from pathlib import Path
import re
from uuid import uuid4

from physicsguard.repair.sources import default_source_store
from .model_client import MockClient, OllamaClient, DEFAULT_MODEL
from .planner import AgentBudgets, investigate


def save_trace(result, name=None):
    """Create a private, strict JSON artifact; never overwrite another file."""
    name = name or f"milestone4-{result.provenance.backend}-{result.source_file[:-3]}-{uuid4().hex[:12]}.json"
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,120}\.json", name):
        raise ValueError("trace must be a JSON basename under artifacts/")
    folder = Path.cwd() / "artifacts"
    if folder.is_symlink():
        raise ValueError("artifact directory must not be a symlink")
    folder.mkdir(exist_ok=True)
    data = result.to_json() + "\n"
    descriptor = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=descriptor)
        with os.fdopen(output, "w", encoding="utf-8") as stream:
            stream.write(data)
    finally:
        os.close(descriptor)
    return folder / name


def print_result(result):
    p = result.provenance
    print(f"backend: {p.backend}\nmodel: {p.model or 'none'}\nmodel_inference: {str(p.model_inference).lower()}")
    print(f"successful local inference responses: {p.successful_requests}")
    selector = "Model-selected" if p.backend == "ollama" and p.model_inference else "Mock-selected"
    for event in result.events:
        data = event.data
        if event.kind == "tool_request":
            print(f"{selector} tool: {data['operation']} {data['arguments']}")
        elif event.kind == "tool_response" and data["ok"] and data["operation"] == "run_scientific_experiment":
            print("  experiment result:", data["result"])
        elif event.kind == "explanation" and data.get("stage") == "hypothesis":
            print(f"{selector} hypothesis:", data["hypothesis"], "evidence:", data["evidence_ids"])
        elif event.kind == "tool_response" and data["ok"] and data["operation"] == "get_diagnostic_report":
            report = data["result"]
            if "diagnostics" in report:
                print("  diagnostic statuses:", dict(sorted(Counter(d["status"] for d in report["diagnostics"]).items())))
                for d in report["diagnostics"]:
                    if d["diagnostic_id"] in ("accuracy", "conservation", "direction"):
                        print(f"  {d['diagnostic_id']}: {d['status']} {d['measurements']}")
        elif event.kind in ("backend_error", "invalid_response"):
            print(f"{event.kind}: {data['error']}")
    print("Investigator hypothesis:", result.explanation.hypothesis if result.explanation else "unavailable")
    if result.proposal:
        print("Host-rendered proposal (origin: deterministic):")
        print(result.proposal["unified_diff"])
    else:
        print("Proposed patch: none")
    print("Independent verifier decision:", result.verifier_decision or "not requested / unavailable")
    print("Original integrity:", result.original_integrity)
    print("Workspace cleanup:", result.workspaces_cleaned if result.workspaces_cleaned is not None else "unverified")
    print("Termination:", result.termination)
    if result.explanation:
        print("Investigator explanation (cited narrative):", result.explanation.summary)
    print(result.final_explanation)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("mock", "ollama"), required=True)
    parser.add_argument("--source", default="solver_01.py")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--max-actions", type=int, default=12)
    parser.add_argument("--max-turns", type=int, default=16)
    parser.add_argument("--max-verifications", type=int, default=2)
    parser.add_argument("--trace", help="new JSON basename under artifacts/; existing files are refused")
    args = parser.parse_args(argv)
    try:
        budgets = AgentBudgets(max_actions=args.max_actions, max_turns=args.max_turns,
                               max_verifications=args.max_verifications)
        client = MockClient() if args.backend == "mock" else OllamaClient(
            model=args.model, timeout_seconds=args.timeout)
        result = investigate(client, default_source_store(), args.source, budgets=budgets)
        path = save_trace(result, args.trace)
    except (ValueError, OSError):
        parser.error("invalid configuration, unavailable reviewed source, or unwritable/existing trace destination")
    print_result(result)
    print("Strict JSON trace:", path)
    return 0 if result.termination in ("completed", "abstained") else 2


if __name__ == "__main__":
    raise SystemExit(main())
