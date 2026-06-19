from collections.abc import Callable
from typing import Any

type CompleteFn = Callable[[str, dict[str, Any] | None], None]
type FailFn = Callable[[str], None]


class Message:
    def __init__(
        self,
        message_id: str,
        payload: dict[str, Any],
        on_complete: CompleteFn,
        on_fail: FailFn,
    ) -> None:
        self.id = message_id
        self.payload = payload
        self.on_complete = on_complete
        self.on_fail = on_fail

    def complete(self, result: dict[str, Any] | None = None) -> None:
        self.on_complete(self.id, result)

    def fail(self) -> None:
        self.on_fail(self.id)
