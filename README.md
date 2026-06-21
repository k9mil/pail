<div align="center">

<img src="https://github.com/user-attachments/assets/650bf5ff-d4d3-4e88-9c38-2d70d35038f3" alt="pail" width="720">

# *pail*

**A brokerless, durable job queue that lives in a single S3 bucket.**

[Install](#install) · [Usage](#usage) · [How it works](#how-it-works) · [When to use it](#when-to-use-it) · [Contributing](#contributing)

</div>

> [!WARNING]
> The pail product is _extremely_ early and evolving. APIs may change between versions, and the project is expected to improve significantly in the near future.

## Overview

pail turns an S3 bucket into a durable job queue with first-class, queryable job state. It replaces the usual three-service stack (a queue like SQS, a status and result store like DynamoDB, and an API to expose status) with a single bucket.

You enqueue work, your own workers claim and process it, and anyone can read a job's status or result by reading an object, over a presigned URL or CDN, with no backend in the loop. Runs on AWS S3 and Cloudflare R2.

## Install

```bash
uv add pail
```

Then point it at a bucket:

```python
from pail import Pail

pail = Pail.connect("my-bucket")
```

## Usage

pail is bring-your-own-worker: a queue, fully decoupled from compute. Producer and worker share only the bucket.

The producer enqueues and gets an id back:

```python
job_id = pail.enqueue({"scenario": "market_crash", "agents": 10_000})
```

A worker is just a function. Hand it to pail and it runs the loop for you, including retries and a dead-letter queue: a job that raises is returned to the queue, retried, and parked in the DLQ if it never succeeds, never silently lost.

```python
def run(payload):
    return {"price": simulate(payload["agents"])}

pail.work(run)
```

Running on ephemeral compute like a Fargate task or a cron container? Process one job and exit:

```python
pail.work_once(run)
```

The id from `enqueue` is the handle. Whoever holds it, the producer or a frontend you passed it to, polls the result straight from the bucket while the worker stays oblivious to it. It returns `None` until the job is done, then the worker's return value:

```python
pail.result(job_id)
```

That is the whole API: `enqueue`, `work`, `result`. No broker to run, no status table to provision, no endpoint to wire up. If you want the raw primitives, `claim` / `complete` / `fail` are there too.

### More examples

Runnable versions of these patterns (a producer, a long-running worker, a one-shot worker, the raw primitives, retries and the DLQ) live in [`examples/`](examples).

## How it works

Everything rests on one S3 feature: conditional writes. `IfNoneMatch="*"` turns a `PutObject` into a compare-and-swap, so exactly one of N racing workers wins a job. No locks, no coordinator, no leader election.

A job is one JSON object whose prefix is its state:

```
queue/{id}  pending
run/{id}    in-flight
done/{id}   finished
dlq/{id}    dlq
```

Ids are [ULIDs](https://github.com/ulid/spec), so listings return jobs oldest-first. State is a plain object, so a frontend can poll `done/{id}` directly through a presigned URL, no status API required. Enable bucket versioning and every transition is retained as a free audit trail.

Delivery is **at-least-once**: a dead worker's job is retried, never lost, but it can run more than once. A job's `id` is stable across retries, so use it as your idempotency key. A job that keeps failing is retried up to `max_retries` times (default 3) and then parked in `dlq/` for inspection instead of looping forever, set `max_retries=None` to retry without a ceiling.

### Standard and express

pail reads its mode from the bucket name: a general-purpose bucket is standard, and an [S3 Express One Zone](https://aws.amazon.com/s3/storage-classes/express-one-zone/) directory bucket, whose name ends in `--x-s3`, is express. The queue logic is the same on both. Use express if you want cheaper requests and single-digit-millisecond latency and can accept single-AZ durability and unordered claims (it returns a pending job, not necessarily the oldest). Otherwise use standard.

## When to use it

Reach for pail when you want a queue for long-running work plus live status, without the setup. A typical case is a long-running export or report where the frontend needs to show the user when it's done. Doing that the usual way means standing up SQS for the queue, DynamoDB for status, and a status endpoint or event notifications to surface it. pail is one bucket instead.

It is not built for high-throughput, low-latency queues (use AWS SQS or Redis), managed compute (AWS Batch), or multi-step orchestration with rollbacks (AWS Step Functions, Temporal).

## Contributing

Issues and PRs welcome. The codebase is small and fully typed: `uv sync`, then `uvx ruff check` and `uvx ty check` should pass clean.
