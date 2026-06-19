from typing import Any

from pail.models import Message


def test_given_message_when_created_then_exposes_id_and_payload() -> None:
    message = Message("01ABC", {"n": 1}, lambda *_: None, lambda *_: None)
    assert message.id == "01ABC"
    assert message.payload == {"n": 1}


def test_given_message_when_complete_then_callback_receives_id_and_result() -> None:
    captured: dict[str, Any] = {}

    def on_complete(message_id: str, result: dict[str, Any] | None) -> None:
        captured["id"] = message_id
        captured["result"] = result

    message = Message("01ABC", {"n": 1}, on_complete, lambda *_: None)
    message.complete({"ok": True})
    assert captured == {"id": "01ABC", "result": {"ok": True}}


def test_given_message_when_complete_without_result_then_callback_receives_none() -> (
    None
):
    captured: dict[str, Any] = {}

    def on_complete(message_id: str, result: dict[str, Any] | None) -> None:
        captured["result"] = result

    message = Message("01ABC", {}, on_complete, lambda *_: None)
    message.complete()
    assert captured["result"] is None


def test_given_message_when_fail_then_callback_receives_id() -> None:
    captured: dict[str, Any] = {}

    def on_fail(message_id: str) -> None:
        captured["id"] = message_id

    message = Message("01ABC", {"n": 1}, lambda *_: None, on_fail)
    message.fail()
    assert captured == {"id": "01ABC"}
