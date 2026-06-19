import json
from typing import Any


def encode(value: dict[str, Any]) -> bytes:
    return json.dumps(value).encode()


def decode(body: bytes) -> dict[str, Any]:
    return json.loads(body)
