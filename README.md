<div align="center">

<img src="https://github.com/user-attachments/assets/d54337b3-3a03-4746-9401-66bccfb05d45" alt="pail" width="480">

# pail

**A brokerless, durable job queue that lives in a single S3 bucket.**

[Install](#install) · [Usage](#usage) · [How it works](#how-it-works) · [When to use it](#when-to-use-it) · [Contributing](#contributing)

</div>

> [!WARNING]
> The pail product is early and evolving. APIs may change between versions.

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

A worker claims a job, runs its own compute, and completes it:

```python
while True:
    msg = pail.claim()
    if msg is None:
        time.sleep(2)
        continue
    result = run(msg.payload)
    msg.complete(result)
```

Anyone can poll the result by id:

```python
pail.result(job_id)
```

## How it works

Everything rests on one S3 feature: conditional writes. `IfNoneMatch="*"` turns a `PutObject` into a compare-and-swap, so exactly one of N racing workers wins a job. No locks, no coordinator, no leader election.

A job is one JSON object whose prefix is its state:

```
queue/{id}  pending
run/{id}    in flight
done/{id}   finished
```

Ids are [ULIDs](https://github.com/ulid/spec), so listings return jobs oldest-first. State is a plain object, so a frontend can poll `done/{id}` directly through a presigned URL, no status API required. Enable bucket versioning and every transition is retained as a free audit trail.

## When to use it

Reach for pail when you want a queue for long-running work plus live status, without the setup. A typical case is a long-running export or report where the frontend needs to show the user when it's done. Doing that the usual way means standing up SQS for the queue, DynamoDB for status, and a status endpoint or event notifications to surface it. pail is one bucket instead.

It is not built for high-throughput, low-latency queues (use AWS SQS or Redis), managed compute (AWS Batch), or multi-step orchestration with rollbacks (AWS Step Functions, Temporal).

## Contributing

Issues and PRs welcome. The codebase is small and fully typed: `uv sync`, then `uvx ruff check` and `uvx ty check` should pass clean.
