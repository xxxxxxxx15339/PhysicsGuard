"""Host-owned explicit projection. Providers never receive dispatcher objects."""
from .protocol import ToolResponse, ProtocolError, dumps, loads


def _fields(value, fields):
    if type(value) is not dict:
        raise ProtocolError("object result required")
    return {key: value[key] for key in fields}


def _verification(value):
    result = _fields(value, ("proposal_id", "origin", "decision", "original_integrity", "workspaces_cleaned"))
    decision = result["decision"]
    if decision not in ("ACCEPTED", "REJECTED", "INCONCLUSIVE"):
        raise ProtocolError("invalid verifier decision")
    result["reasons"] = [{"ACCEPTED": "Host verification accepted the candidate",
                          "REJECTED": "Host verification rejected the candidate",
                          "INCONCLUSIVE": "Host verification lacks sufficient evidence"}[decision]]
    result["stages"] = _fields(value["stages"],
        ("source", "execution", "science", "additional_cases", "regressions"))
    if any(v not in ("pending", "pass", "fail", "inconclusive", "unsupported") for v in result["stages"].values()):
        raise ProtocolError("invalid verifier stages")
    if any(type(result[k]) is not bool for k in ("original_integrity", "workspaces_cleaned")):
        raise ProtocolError("invalid lifecycle flags")
    return result


def _case(value):
    result = _fields(value, ("case_id", "n_cells", "cfl", "final_time", "profile", "offset", "amplitude", "mode", "phase", "max_steps"))
    result["physics"] = _fields(value["physics"], ("speed", "x_min", "x_max", "equation", "boundary", "source_free", "state", "length_unit", "time_unit", "field_unit"))
    result["strategy"] = _fields(value["strategy"], ("method", "time_integrator", "grid", "monotone_cfl_limit"))
    return result


def public_response(request, reply):
    """Drop runtime noise, bulky arrays and all non-allowlisted host fields.

    Public diagnostic measurements/assumptions/criteria remain actual host data.
    Error text is never echoed: it may contain paths or private case details.
    """
    reply = loads(dumps(reply, 2 * 1024**2), 2 * 1024**2)
    if type(reply.get("ok")) is not bool or not reply["ok"]:
        return ToolResponse(request.call_id, request.operation, False,
                            error="invalid_or_unavailable_operation")
    value, operation = reply["result"], request.operation
    if operation == "inspect_solver_source":
        result = _fields(value, ("source_file", "sha256"))
        result["lines"] = [_fields(line, ("line", "text")) for line in value["lines"]]
    elif operation == "run_scientific_experiment":
        result = _fields(value, ("run_id", "status"))
        result["error"] = "execution_evidence_unavailable" if value.get("error") else None
    elif operation == "get_diagnostic_report":
        if value.get("audience") == "evaluator_only":
            raise ProtocolError("evaluator evidence refused")
        if "diagnostics" not in value:
            result = {"status": "unavailable", "error": "execution_evidence_unavailable"}
        else:
            # Cases are the caller's development inputs, not verifier inputs.
            result = {"solver_id": value["solver_id"], "cases": [_case(c) for c in value["cases"]],
                      "executions": [], "diagnostics": []}
            for run in value["executions"]:
                result["executions"].append({"case_id": run.get("case_id") or run["case"]["case_id"],
                    "status": run["status"], "error_kind": run.get("error_kind"),
                    "error": "execution_evidence_unavailable" if run.get("error") else None,
                    "max_cfl": run.get("max_cfl")})
            for diagnostic in value["diagnostics"]:
                item = _fields(diagnostic, ("diagnostic_id", "description", "assumptions", "applicable", "status",
                    "measurements", "units", "acceptance_criteria", "tolerance", "tolerance_justification", "case_ids"))
                item["evidence_errors"] = ["evidence_unavailable"] if diagnostic.get("evidence_errors") else []
                result["diagnostics"].append(item)
    elif operation in ("select_localized_edit", "propose_localized_patch"):
        result = None if value is None else _fields(value, (
            "proposal_id", "source_file", "original_sha256", "proposed_sha256", "hypothesis",
            "line_number", "old_line", "new_line", "unified_diff", "expected_effect", "origin"))
        if result:
            result["hypothesis"] = _fields(value["hypothesis"], ("mechanism", "function", "start_line", "end_line", "explanation", "evidence_ids", "evidence_case_ids"))
    elif operation == "verify_candidate_patch":
        result = _verification(value)
    else:
        result = [_verification(record) for record in value]
    return ToolResponse(request.call_id, operation, True, result)
