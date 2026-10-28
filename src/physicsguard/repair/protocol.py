"""Bounded finite JSON frames for reviewed solver IPC; no executable payloads."""
import json
import math

MAX_REQUEST = 1024**2
MAX_RESPONSE = 2 * 1024**2
MAX_REQUESTS = 64


class ProtocolError(ValueError):
    pass


def decode_frame(payload, limit):
    if not isinstance(payload, (bytes, str)) or len(payload) > limit:
        raise ProtocolError("protocol frame size/type limit exceeded")
    def finite_float(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError("nonfinite protocol number")
        return value
    def reject_constant(text):
        raise ValueError("nonstandard JSON constant")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    try:
        value = json.loads(payload, parse_float=finite_float, parse_constant=reject_constant,
                           object_pairs_hook=unique_object)
        if not isinstance(value, dict):
            raise ValueError("object frame required")
        return value
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ProtocolError("malformed or nonfinite JSON frame") from error


def encode_frame(value, limit):
    try:
        encoded = (json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n").encode()
    except (ValueError, TypeError, RecursionError) as error:
        raise ProtocolError("unserializable protocol frame") from error
    if len(encoded) > limit:
        raise ProtocolError("protocol frame size limit exceeded")
    return encoded
