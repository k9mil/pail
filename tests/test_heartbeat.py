from datetime import UTC, datetime, timedelta

from fakes import FakeS3

from pail.heartbeat import Heartbeat
from pail.store import Store


def test_given_beat_when_called_then_writes_body(store: Store) -> None:
    heartbeat = Heartbeat(store, "run/a", b"payload", 10)
    heartbeat.beat()
    assert store.get("run/a") == b"payload"


def test_given_stale_object_when_beat_then_refreshes_timestamp(
    s3: FakeS3,
    store: Store,
) -> None:
    s3.seed("bucket", "run/a", b"payload", datetime.now(UTC) - timedelta(seconds=100))
    heartbeat = Heartbeat(store, "run/a", b"payload", 10)
    heartbeat.beat()
    [obj] = store.list_objects("run/")
    assert (datetime.now(UTC) - obj.last_modified).total_seconds() < 1


def test_given_started_heartbeat_when_stop_then_thread_ends(store: Store) -> None:
    heartbeat = Heartbeat(store, "run/a", b"payload", 10)
    heartbeat.start()
    heartbeat.stop()
    assert heartbeat.thread.is_alive() is False
