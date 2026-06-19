import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fakes import FakeS3, ShuffledS3

from pail import Mode, Pail


def test_given_payload_when_enqueue_then_returns_ulid(pail: Pail) -> None:
    job_id = pail.enqueue({"scenario": "x"})
    assert len(job_id) == 26


def test_given_enqueued_job_when_claim_then_returns_it(pail: Pail) -> None:
    job_id = pail.enqueue({"scenario": "x", "n": 5})
    message = pail.claim()
    assert message is not None
    assert message.id == job_id
    assert message.payload == {"scenario": "x", "n": 5}


def test_given_empty_queue_when_claim_then_returns_none(pail: Pail) -> None:
    assert pail.claim() is None


def test_given_only_job_claimed_when_claim_again_then_returns_none(pail: Pail) -> None:
    pail.enqueue({"n": 1})
    pail.claim()
    assert pail.claim() is None


def test_given_two_jobs_when_claimed_then_distinct_ids(pail: Pail) -> None:
    pail.enqueue({"n": 1})
    pail.enqueue({"n": 2})
    first = pail.claim()
    second = pail.claim()
    assert first is not None
    assert second is not None
    assert first.id != second.id


def test_given_incomplete_job_when_result_then_none(pail: Pail) -> None:
    job_id = pail.enqueue({"n": 1})
    assert pail.result(job_id) is None


def test_given_unknown_id_when_result_then_none(pail: Pail) -> None:
    assert pail.result("missing") is None


def test_given_completed_job_when_result_then_returns_result(pail: Pail) -> None:
    pail.enqueue({"n": 1})
    message = pail.claim()
    assert message is not None
    message.complete({"ok": True})
    assert pail.result(message.id) == {"ok": True}


def test_given_completed_without_result_when_result_then_empty_dict(pail: Pail) -> None:
    pail.enqueue({"n": 1})
    message = pail.claim()
    assert message is not None
    message.complete()
    assert pail.result(message.id) == {}


def test_given_orphaned_run_when_claim_then_reclaims_and_returns(
    s3: FakeS3,
    pail: Pail,
) -> None:
    stale = datetime.now(UTC) - timedelta(seconds=60)
    s3.seed("bucket", "run/01ORPHAN", json.dumps({"n": 1}).encode(), stale)
    message = pail.claim()
    assert message is not None
    assert message.id == "01ORPHAN"
    assert message.payload == {"n": 1}


def test_given_fresh_run_when_claim_then_not_reclaimed(s3: FakeS3, pail: Pail) -> None:
    s3.seed("bucket", "run/01FRESH", json.dumps({"n": 1}).encode(), datetime.now(UTC))
    assert pail.claim() is None
    assert ("bucket", "run/01FRESH") in s3.objects


def test_given_directory_bucket_when_pail_then_mode_is_express() -> None:
    pail = Pail("jobs--use1-az4--x-s3", FakeS3())
    assert pail.mode == Mode.EXPRESS


def test_given_general_bucket_when_pail_then_mode_is_standard() -> None:
    pail = Pail("jobs", FakeS3())
    assert pail.mode == Mode.STANDARD


def test_given_unordered_list_when_claim_all_then_every_job_claimed() -> None:
    pail = Pail("bucket", ShuffledS3())
    ids = {pail.enqueue({"n": i}) for i in range(3)}
    claimed = set()
    message = pail.claim()
    while message is not None:
        claimed.add(message.id)
        message = pail.claim()
    assert claimed == ids


def test_given_empty_queue_when_stats_then_all_zero(pail: Pail) -> None:
    assert pail.stats() == (0, 0, 0, None)


def test_given_pending_jobs_when_stats_then_counts_pending(pail: Pail) -> None:
    pail.enqueue({"n": 1})
    pail.enqueue({"n": 2})
    stats = pail.stats()
    assert stats.pending == 2
    assert stats.running == 0
    assert stats.done == 0


def test_given_claimed_job_when_stats_then_counts_running(pail: Pail) -> None:
    pail.enqueue({"n": 1})
    pail.claim()
    stats = pail.stats()
    assert stats.pending == 0
    assert stats.running == 1


def test_given_completed_job_when_stats_then_counts_done(pail: Pail) -> None:
    pail.enqueue({"n": 1})
    message = pail.claim()
    assert message is not None
    message.complete({"ok": True})
    stats = pail.stats()
    assert stats.running == 0
    assert stats.done == 1


def test_given_pending_job_when_stats_then_oldest_pending_is_set(pail: Pail) -> None:
    pail.enqueue({"n": 1})
    oldest = pail.stats().oldest_pending
    assert oldest is not None
    assert oldest >= timedelta(0)


def test_given_empty_queue_when_work_once_then_returns_false(pail: Pail) -> None:
    assert pail.work_once(lambda payload: payload) is False


def test_given_job_when_work_once_then_completes_with_result(pail: Pail) -> None:
    job_id = pail.enqueue({"n": 2})
    did_work = pail.work_once(lambda payload: {"doubled": payload["n"] * 2})
    assert did_work is True
    assert pail.result(job_id) == {"doubled": 4}


def test_given_raising_handler_when_work_once_then_requeues(pail: Pail) -> None:
    pail.enqueue({"n": 1})

    def boom(payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError

    assert pail.work_once(boom) is True
    stats = pail.stats()
    assert stats.pending == 1
    assert stats.running == 0
