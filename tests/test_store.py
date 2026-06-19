import pytest
from botocore.exceptions import ClientError
from fakes import RaisingS3

from pail.store import Store


def test_given_no_object_when_put_if_absent_then_creates(store: Store) -> None:
    created = store.put_if_absent("queue/a", b"payload")
    assert created is True
    assert store.get("queue/a") == b"payload"


def test_given_existing_object_when_put_if_absent_then_rejects(store: Store) -> None:
    store.put_if_absent("queue/a", b"first")
    created = store.put_if_absent("queue/a", b"second")
    assert created is False
    assert store.get("queue/a") == b"first"


def test_given_object_when_put_then_overwrites(store: Store) -> None:
    store.put("done/a", b"one")
    store.put("done/a", b"two")
    assert store.get("done/a") == b"two"


def test_given_missing_object_when_get_then_returns_none(store: Store) -> None:
    assert store.get("nope") is None


def test_given_object_when_delete_then_gone(store: Store) -> None:
    store.put("run/a", b"x")
    store.delete("run/a")
    assert store.get("run/a") is None


def test_given_keys_under_prefix_when_list_objects_then_sorted(store: Store) -> None:
    store.put("queue/b", b"1")
    store.put("queue/a", b"2")
    store.put("run/c", b"3")
    assert [obj.key for obj in store.list_objects("queue/")] == ["queue/a", "queue/b"]


def test_given_object_when_list_objects_then_timestamp_is_utc(store: Store) -> None:
    store.put("queue/a", b"1")
    [obj] = store.list_objects("queue/")
    assert obj.last_modified.tzinfo is not None


def test_given_unexpected_error_when_put_if_absent_then_reraises() -> None:
    store = Store("bucket", RaisingS3())
    with pytest.raises(ClientError, match="AccessDenied"):
        store.put_if_absent("queue/a", b"x")


def test_given_client_error_when_error_code_then_returns_code(store: Store) -> None:
    error = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
    assert store.error_code(error) == "NoSuchKey"
