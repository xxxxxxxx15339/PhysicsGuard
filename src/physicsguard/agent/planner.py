"""Bounded JSON investigator orchestration; host verification owns decisions."""
from dataclasses import dataclass
import json

from physicsguard.repair.tools import RepairTools
from .boundary import public_response
from .instructions import SYSTEM_INSTRUCTION
from .model_client import ModelClient, BackendError
from .protocol import (
    AgentExplanation, BackendProvenance, InvestigationResult, TraceEvent, ToolRequest, ToolResponse,
    ProtocolError, dumps, parse_message, tool_descriptions,
)


@dataclass(frozen=True)
class AgentBudgets:
    max_turns: int = 16
    max_actions: int = 12
    max_experiments: int = 4
    max_verifications: int = 2
    max_invalid_responses: int = 2
    max_conversation_bytes: int = 120000
    max_cumulative_input_bytes: int = 1000000
    max_output_tokens: int = 8192
    max_tokens_per_turn: int = 1024

    def __post_init__(self):
        limits = {"max_turns": 32, "max_actions": 24, "max_experiments": 16,
                  "max_verifications": 8, "max_invalid_responses": 4,
                  "max_conversation_bytes": 120000, "max_cumulative_input_bytes": 2000000,
                  "max_output_tokens": 16384, "max_tokens_per_turn": 2048}
        if any(type(getattr(self, name)) is not int or not 1 <= getattr(self, name) <= limit
               for name, limit in limits.items()):
            raise ValueError("bounded positive integer agent budgets required")


def investigate(client: ModelClient, store, source_file: str, *, budgets=None) -> InvestigationResult:
    """Local host entry point. Only JSON strings are passed to the provider.

    Bytes conservatively bound input tokens without a provider tokenizer. Tool
    results omit nondeterministic runtimes, making mock traces replay exactly.
    No module imports, store, tools, callbacks or evaluator objects enter a client.
    """
    budgets = budgets or AgentBudgets()
    snapshot = store.inspect(source_file)
    initial_provenance = client.provenance
    tools = RepairTools(store)
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": dumps({"source_file": source_file,
                    "task": "Investigate this reviewed solver, select evidence-supported experiments and a permitted repair or abstain."})}]
    descriptions = dumps({"tools": tool_descriptions()})
    events, seen, call_ids = [], set(), set()
    run_ids, read_runs, proposals, evidence_ids = set(), set(), {}, set()
    actions = experiments = verifications = invalid = input_bytes = output_tokens = 0
    proposal = verification = explanation = None
    inspected = False
    cleaned = True
    termination = "turn_budget"

    def event(kind, data):
        events.append(TraceEvent(len(events), kind, data))

    def invalid_reply(reason="invalid_or_unavailable_response"):
        # Do not echo untrusted response text or exception details into traces.
        nonlocal invalid
        invalid += 1
        event("invalid_response", {"error": reason})
        messages.append({"role": "user", "content": dumps({
            "error": reason,
            "instruction": "Use exactly one described tool with allowed arguments, or the required final JSON explanation with observed evidence IDs. Choose your own experiment controls. Speed and domain bounds belong inside case.physics. Do not include solver implementation arguments, arrays or method overrides.",
            "example_experiment_arguments": {"source_file": source_file, "case": {
                "case_id": "chosen-observation", "physics": {"speed": 1.0},
                "n_cells": 64, "cfl": 0.8, "final_time": 0.23, "profile": "sine"}},
        })})

    for _ in range(budgets.max_turns):
        conversation = dumps({"messages": messages}, 2 * 1024**2)
        size = len(conversation.encode()) + len(descriptions.encode())
        if size > budgets.max_conversation_bytes:
            termination = "conversation_budget"
            break
        input_bytes += size
        if input_bytes > budgets.max_cumulative_input_bytes:
            termination = "input_budget"
            break
        if output_tokens >= budgets.max_output_tokens:
            termination = "output_token_budget"
            break
        try:
            requested_tokens = min(budgets.max_tokens_per_turn, budgets.max_output_tokens-output_tokens)
            reply = client.complete(conversation, descriptions, max_tokens=requested_tokens)
            output_tokens += reply.output_tokens
            if output_tokens > budgets.max_output_tokens or reply.output_tokens > requested_tokens:
                termination = "output_token_budget"
                break
            action = parse_message(reply.message_json)
            if isinstance(action, AgentExplanation):
                if (set(action.evidence_ids) - evidence_ids or evidence_ids and not action.evidence_ids
                        or action.stage == "final" and not action.abstain and not verification):
                    raise ProtocolError("unsupported final explanation")
                if action.stage == "hypothesis":
                    event("explanation", action.to_dict())
                    messages.append({"role": "assistant", "content": dumps(action.to_dict())})
                    invalid = 0
                    continue
                explanation = action
                event("explanation", action.to_dict())
                termination = "completed" if verification else "abstained"
                break
        except BackendError as error:
            if error.code == "invalid_model_response":
                # No usable usage record survived parsing. Charge the requested
                # output allowance conservatively rather than granting free retries.
                output_tokens += requested_tokens
                invalid_reply()
                if invalid < budgets.max_invalid_responses:
                    continue
                termination = "invalid_response_limit"
            else:
                event("backend_error", {"error": error.code})
                termination = error.code
            break
        except TimeoutError:
            event("backend_error", {"error": "model_timeout"})
            termination = "model_timeout"
            break
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
            # These codes reveal only the schema category, never model text,
            # argument values, host paths or detailed SDK errors.
            category = {"unexpected tool arguments": "unexpected_tool_arguments",
                        "unknown tool or arguments": "unknown_tool",
                        "unexpected experiment arguments": "unexpected_experiment_arguments",
                        "physical contract cannot be overridden": "physical_contract_override",
                        "exactly one sequential tool call required": "multiple_or_missing_calls",
                        "unsupported final explanation": "unsupported_evidence_reference"}.get(str(error), "invalid_or_unavailable_response")
            invalid_reply(category)
            if invalid < budgets.max_invalid_responses:
                continue
            termination = "invalid_response_limit"
            break

        if actions >= budgets.max_actions:
            termination = "action_budget"
            break
        actions += 1
        operation, arguments = action.operation, action.arguments
        event("tool_request", action.to_dict())
        signature = json.dumps([operation, arguments], sort_keys=True, allow_nan=False)
        if signature in seen or action.call_id in call_ids:
            termination = "duplicate_call"
            break
        seen.add(signature)
        call_ids.add(action.call_id)
        if arguments.get("source_file", source_file) != source_file:
            termination = "source_scope_violation"
            break
        if (operation == "run_scientific_experiment" and not inspected
                or "run_id" in arguments and arguments["run_id"] not in run_ids
                or operation in ("select_localized_edit", "propose_localized_patch") and arguments["run_id"] not in read_runs
                or operation == "verify_candidate_patch" and arguments["proposal_id"] not in proposals):
            termination = "unsupported_evidence_reference"
            break
        if operation == "run_scientific_experiment":
            if experiments >= budgets.max_experiments:
                termination = "experiment_budget"
                break
            experiments += 1
        if operation == "verify_candidate_patch":
            if verifications >= budgets.max_verifications:
                termination = "verification_budget"
                break
            verifications += 1
        messages.append(action.assistant_message())
        try:
            response = public_response(action, tools.call(operation, arguments))
        except (ValueError, TypeError, KeyError, OSError, RuntimeError, RecursionError):
            response = ToolResponse(action.call_id, operation, False,
                                    error="invalid_or_unavailable_operation")
        messages.append(response.tool_message())
        event("tool_response", response.to_dict())
        if not response.ok:
            # A failed context manager may have failed cleanup; do not assert it.
            if operation in ("run_scientific_experiment", "verify_candidate_patch"):
                cleaned = None
            termination = "tool_error"
            break
        invalid = 0
        result = response.result
        if operation == "inspect_solver_source":
            inspected = True
        elif operation == "run_scientific_experiment":
            # Successful dispatch returned after source_workspace.__exit__,
            # which checks copy integrity and raises on failed cleanup.
            run_ids.add(result["run_id"])
            if result["status"] != "completed":
                termination = "experiment_unavailable"
                break
        elif operation == "get_diagnostic_report":
            read_runs.add(arguments["run_id"])
            if "diagnostics" not in result:
                termination = "experiment_unavailable"
                break
            for diagnostic in result["diagnostics"]:
                evidence_ids.add(diagnostic["diagnostic_id"])
                evidence_ids.update(diagnostic["case_ids"])
        elif operation in ("select_localized_edit", "propose_localized_patch") and result:
            if (result["source_file"] != source_file or result["original_sha256"] != snapshot.sha256
                    or result["origin"] != "deterministic"):
                termination = "proposal_identity_mismatch"
                break
            proposals[result["proposal_id"]] = result
            proposal = result
        elif operation == "verify_candidate_patch":
            if result["proposal_id"] != arguments["proposal_id"]:
                termination = "verification_identity_mismatch"
                break
            verification = result
            proposal = proposals[result["proposal_id"]]
            cleaned = cleaned and result["workspaces_cleaned"]

    decision = verification["decision"] if verification else None
    if verification:
        # A later unverified proposal cannot inherit an earlier decision.
        proposal = proposals[verification["proposal_id"]]
    original_integrity = store.unchanged(snapshot) and (not verification or verification["original_integrity"])
    if decision:
        final = f"Independent host verifier: {decision}. This establishes only the tested repair contract; it is not a proof of general correctness."
    elif termination == "abstained":
        final = "Abstained without an accepted repair. Only the observed development evidence is available; no independent repair success was established."
    else:
        final = f"Investigation stopped ({termination}). No independent repair success was established."
    event("termination", {"reason": termination})
    provenance = client.provenance
    requests = provenance.successful_requests - initial_provenance.successful_requests
    provenance = BackendProvenance(provenance.backend, provenance.model, requests > 0, requests)
    return InvestigationResult(provenance, source_file, termination, explanation, proposal,
        decision, verification, original_integrity, cleaned, final, actions, verifications, output_tokens, tuple(events))
