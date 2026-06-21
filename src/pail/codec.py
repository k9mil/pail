import json
from typing import Any, NamedTuple


class Envelope(NamedTuple):
    payload: dict[str, Any]
    attempts: int


def encode(value: dict[str, Any]) -> bytes:
    return json.dumps(value).encode()


def decode(body: bytes) -> dict[str, Any]:
    return json.loads(body)


def wrap(payload: dict[str, Any], attempts: int = 0) -> bytes:
    return encode({"payload": payload, "attempts": attempts})


def unwrap(body: bytes) -> Envelope:
    data = decode(body)
    return Envelope(data["payload"], data["attempts"])
