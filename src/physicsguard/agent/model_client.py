"""Keyless mock and local Llama providers. No hosted adapter or fallback."""
from dataclasses import dataclass
import ipaddress
from time import monotonic
from typing import Protocol
from urllib.parse import urlsplit

from .protocol import BackendProvenance, MAX_MODEL_BYTES, ProtocolError, dumps, loads

DEFAULT_ENDPOINT = "http://127.0.0.1:11434/v1"
DEFAULT_MODEL = "llama3.1:8b"


class BackendError(RuntimeError):
    """Only static public error codes, never SDK exceptions/headers/bodies."""
    def __init__(self, code):
        if code not in {"optional_dependency_missing", "model_timeout", "model_unavailable",
                        "model_identity_mismatch", "invalid_model_response"}:
            code = "model_unavailable"
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Completion:
    message_json: str
    output_tokens: int = 0

    def __post_init__(self):
        if not isinstance(self.message_json, str) or len(self.message_json.encode()) > MAX_MODEL_BYTES:
            raise ProtocolError("model payload budget exceeded")
        if type(self.output_tokens) is not int or self.output_tokens < 0:
            raise ProtocolError("invalid output token accounting")


class ModelClient(Protocol):
    """Future providers implement this JSON-only boundary, not host callbacks."""
    @property
    def provenance(self) -> BackendProvenance: ...

    def complete(self, messages_json: str, tools_json: str, *, max_tokens: int) -> Completion: ...


def local_endpoint(value):
    """No DNS, proxies, credentials, redirects, queries or nonlocal origins."""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if host == "localhost":
            host = "127.0.0.1"
        address = ipaddress.ip_address(host)
        port = parsed.port or 11434
        if (parsed.scheme != "http" or not address.is_loopback or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment
                or parsed.path.rstrip("/") != "/v1" or not 1 <= port <= 65535):
            raise ValueError("loopback Ollama /v1 endpoint required")
        authority = f"[{host}]" if address.version == 6 else host
        return f"http://{authority}:{port}/v1"
    except (ValueError, TypeError) as error:
        raise ValueError("loopback Ollama /v1 endpoint required") from error


class OllamaClient:
    def __init__(self, *, endpoint=DEFAULT_ENDPOINT, model=DEFAULT_MODEL, timeout_seconds=45.0):
        self.endpoint = local_endpoint(endpoint)
        # A local proxy can also serve cloud models: pin this adapter to the
        # requested local Llama tag, rather than accepting a cloud model name.
        if model != DEFAULT_MODEL:
            raise ValueError("this adapter supports local llama3.1:8b only")
        if type(timeout_seconds) not in (int, float) or not 0.1 <= timeout_seconds <= 60:
            raise ValueError("request timeout must be between .1 and 60 seconds")
        self.model, self.timeout_seconds = model, timeout_seconds
        self.successful_requests = 0

    @property
    def provenance(self):
        return BackendProvenance("ollama", self.model, self.successful_requests > 0,
                                 self.successful_requests)

    def complete(self, messages_json, tools_json, *, max_tokens):
        # Imported only on explicit real-backend use; never read API-key env vars.
        try:
            import httpx
            from openai import OpenAI, APITimeoutError, APIError
        except ImportError:
            raise BackendError("optional_dependency_missing") from None
        messages = loads(messages_json, 131072)["messages"]
        tools = loads(tools_json)["tools"]
        started = monotonic()
        try:
            with httpx.Client(trust_env=False, follow_redirects=False,
                              timeout=httpx.Timeout(self.timeout_seconds)) as transport:
                with OpenAI(base_url=self.endpoint, api_key="ollama-local-placeholder",
                            organization="", project="", max_retries=0, http_client=transport) as client:
                    # stream=False controls the completion format; the raw HTTP
                    # response is still read incrementally with a byte cap.
                    with client.chat.completions.with_streaming_response.create(
                        model=self.model, messages=messages, tools=tools, stream=False,
                        temperature=0, max_tokens=max_tokens,
                    ) as response:
                        data = bytearray()
                        for chunk in response.iter_bytes(chunk_size=4096):
                            data.extend(chunk)
                            if monotonic() - started > self.timeout_seconds:
                                raise BackendError("model_timeout")
                            if len(data) > 2 * MAX_MODEL_BYTES:
                                raise BackendError("invalid_model_response")
            value = loads(bytes(data), 2 * MAX_MODEL_BYTES)
            if value.get("model") != self.model:
                raise BackendError("model_identity_mismatch")
            choices = value["choices"]
            if len(choices) != 1 or choices[0].get("finish_reason") not in ("stop", "tool_calls"):
                raise BackendError("invalid_model_response")
            message = choices[0]["message"]
            tokens = value["usage"]["completion_tokens"]
            if type(tokens) is not int or not 0 <= tokens <= max_tokens:
                raise BackendError("invalid_model_response")
            # Counts valid local inference responses, even if their arguments
            # or final explanations subsequently fail protocol validation.
            self.successful_requests += 1
            if message.get("tool_calls"):
                calls = [{"id": c["id"], "name": c["function"]["name"],
                          "arguments": c["function"]["arguments"]} for c in message["tool_calls"]]
                payload = dumps({"tool_calls": calls}, MAX_MODEL_BYTES)
            else:
                payload = dumps({"explanation": loads(message["content"], MAX_MODEL_BYTES)}, MAX_MODEL_BYTES)
            return Completion(payload, tokens)
        except BackendError:
            raise
        except (APITimeoutError, httpx.TimeoutException, TimeoutError):
            raise BackendError("model_timeout") from None
        except (APIError, httpx.HTTPError, OSError):
            raise BackendError("model_unavailable") from None
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            raise BackendError("invalid_model_response") from None


class MockClient:
    """Scripted public-evidence policy, never a model-performance measurement."""
    @property
    def provenance(self):
        return BackendProvenance("mock", None, False)

    def complete(self, messages_json, tools_json, *, max_tokens):
        messages = loads(messages_json, 131072)["messages"]
        source = loads(next(m["content"] for m in messages if m["role"] == "user"))["source_file"]
        calls = [m["tool_calls"][0] for m in messages if m["role"] == "assistant" and m.get("tool_calls")]
        responses = [loads(m["content"]) for m in messages if m["role"] == "tool"]
        pairs = [(c["function"]["name"], r["result"]) for c, r in zip(calls, responses) if r["ok"]]

        def action(name, **arguments):
            return Completion(dumps({"tool_calls": [{"id": f"mock-{len(calls)+1}",
                "name": name, "arguments": dumps(arguments)}]}, MAX_MODEL_BYTES))

        if not pairs:
            return action("inspect_solver_source", source_file=source)
        reports = [r for name, r in pairs if name == "get_diagnostic_report"]
        runs = [r for name, r in pairs if name == "run_scientific_experiment"]
        if len(reports) < len(runs):
            return action("get_diagnostic_report", run_id=runs[-1]["run_id"])
        if len(reports) < 2:
            sign = 1 if not reports else -1
            return action("run_scientific_experiment", source_file=source,
                          case={"case_id": f"investigate-{'positive' if sign > 0 else 'negative'}",
                                "physics": {"speed": sign}})
        failures = {d["diagnostic_id"] for report in reports for d in report["diagnostics"]
                    if d["status"] == "fail"}
        selected = [(name, r) for name, r in pairs if name in ("select_localized_edit", "propose_localized_patch")]
        if not selected and failures:
            for needed, operation in (
                ({"conservation", "translation", "periodic_wrap"}, "wrap_incoming_neighbor"),
                ({"space_scaling", "refinement"}, "normalize_time_by_cell_width"),
                ({"direction", "accuracy"}, "restore_signed_upwind"),
            ):
                # Selection requires public failures from one actual report,
                # never a fixture name/hash, label, expected line or private case.
                report = next((r for r in reports if needed <= {
                    d["diagnostic_id"] for d in r["diagnostics"] if d["status"] == "fail"}), None)
                if report:
                    index = reports.index(report)
                    hypothesis_recorded = any(m["role"] == "assistant" and m.get("content")
                        and '"stage":"hypothesis"' in m["content"] for m in messages)
                    if not hypothesis_recorded:
                        mechanism = {
                            "wrap_incoming_neighbor": "A periodic incoming-neighbor error is consistent with the measured mass, translation and wrapping failures.",
                            "normalize_time_by_cell_width": "Incorrect spatial normalization is consistent with failed scaling and refinement checks; diffusion alone does not establish this fault.",
                            "restore_signed_upwind": "A signed upwind-neighbor error is consistent with accuracy and propagation-direction failures for both tested velocity signs.",
                        }[operation]
                        return Completion(dumps({"explanation": {"summary": "Scripted hypothesis from observed public diagnostic failures; ask the host to check the corresponding source operation.",
                            "evidence_ids": sorted(needed), "hypothesis": mechanism,
                            "abstain": False, "stage": "hypothesis"}}, MAX_MODEL_BYTES))
                    return action("select_localized_edit", source_file=source,
                                  run_id=runs[index]["run_id"], operation_id=operation)
        proposal = selected[-1][1] if selected else None
        verified = [r for name, r in pairs if name == "verify_candidate_patch"]
        if proposal and not verified:
            return action("verify_candidate_patch", proposal_id=proposal["proposal_id"])
        evidence = sorted(failures) if failures else sorted({
            d["diagnostic_id"] for r in reports for d in r["diagnostics"] if d["status"] == "pass"})
        hypothesis = proposal["hypothesis"]["explanation"] if proposal else None
        summary = (f"Host verifier returned {verified[-1]['decision']} for the host-rendered candidate."
                   if verified else "Abstain: no evidence-supported permitted repair selected; finite tests do not prove correctness.")
        return Completion(dumps({"explanation": {"summary": summary, "evidence_ids": evidence,
            "hypothesis": hypothesis, "abstain": not bool(verified)}}, MAX_MODEL_BYTES))
