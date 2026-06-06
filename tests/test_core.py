from pail import Pail


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
