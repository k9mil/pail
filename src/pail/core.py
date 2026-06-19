import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import partial
from typing import Any, NamedTuple, Self, cast

import boto3
from ulid import ULID

from pail.codec import decode, encode
from pail.heartbeat import Heartbeat
from pail.models import Message
from pail.protocols import S3Client
from pail.store import Store

QUEUE_PREFIX = "queue/"
RUN_PREFIX = "run/"
DONE_PREFIX = "done/"

S3 = "s3"

DEFAULT_POLL_INTERVAL = 5.0
DEFAULT_VISIBILITY_TIMEOUT = 30.0
HEARTBEAT_DIVISOR = 3
DIRECTORY_SUFFIX = "--x-s3"


type Handler = Callable[[dict[str, Any]], dict[str, Any] | None]


class Mode(StrEnum):
    STANDARD = "standard"
    EXPRESS = "express"


class Stats(NamedTuple):
    pending: int
    running: int
    done: int
    oldest_pending: timedelta | None


class Pail:
    def __init__(
        self,
        bucket: str,
        client: S3Client,
        *,
        visibility_timeout: float = DEFAULT_VISIBILITY_TIMEOUT,
    ) -> None:
        self.store = Store(bucket, client)
        self.mode = Mode.EXPRESS if bucket.endswith(DIRECTORY_SUFFIX) else Mode.STANDARD
        self.visibility_timeout = visibility_timeout
        self.heartbeat_interval = visibility_timeout / HEARTBEAT_DIVISOR

    @classmethod
    def connect(
        cls,
        bucket: str,
        *,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str | None = None,
        visibility_timeout: float = DEFAULT_VISIBILITY_TIMEOUT,
    ) -> Self:
        client = boto3.client(
            S3,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        return cls(
            bucket,
            cast("S3Client", client),
            visibility_timeout=visibility_timeout,
        )

    def enqueue(self, payload: dict[str, Any]) -> str:
        message_id = str(ULID())
        self.store.put_if_absent(
            QUEUE_PREFIX + message_id,
            encode(payload),
        )

        return message_id

    def claim(self) -> Message | None:
        self.reclaim()

        for obj in self.store.list_objects(QUEUE_PREFIX):
            message_id = obj.key.removeprefix(QUEUE_PREFIX)
            body = self.store.get(obj.key)

            if body is None:
                continue

            claimed = self.store.put_if_absent(
                RUN_PREFIX + message_id,
                body,
            )

            if claimed:
                self.store.delete(obj.key)
                heartbeat = Heartbeat(
                    self.store,
                    RUN_PREFIX + message_id,
                    body,
                    self.heartbeat_interval,
                )
                heartbeat.start()
                return Message(
                    message_id,
                    decode(body),
                    partial(self.complete, heartbeat=heartbeat),
                    partial(self.fail, heartbeat=heartbeat),
                )
        return None

    def reclaim(self) -> None:
        now = datetime.now(UTC)

        for obj in self.store.list_objects(RUN_PREFIX):
            if (now - obj.last_modified).total_seconds() <= self.visibility_timeout:
                continue

            message_id = obj.key.removeprefix(RUN_PREFIX)
            body = self.store.get(obj.key)

            if body is None:
                continue

            if self.store.put_if_absent(QUEUE_PREFIX + message_id, body):
                self.store.delete(obj.key)

    def result(self, message_id: str) -> dict[str, Any] | None:
        body = self.store.get(DONE_PREFIX + message_id)

        if body is None:
            return None

        return decode(body)

    def stats(self) -> Stats:
        queue = self.store.list_objects(QUEUE_PREFIX)
        oldest = min(
            (obj.last_modified for obj in queue),
            default=None,
        )

        return Stats(
            pending=len(queue),
            running=len(self.store.list_objects(RUN_PREFIX)),
            done=len(self.store.list_objects(DONE_PREFIX)),
            oldest_pending=datetime.now(UTC) - oldest if oldest is not None else None,
        )

    def complete(
        self,
        message_id: str,
        result: dict[str, Any] | None,
        *,
        heartbeat: Heartbeat,
    ) -> None:
        heartbeat.stop()
        self.store.put(
            DONE_PREFIX + message_id,
            encode(result or {}),
        )
        self.store.delete(RUN_PREFIX + message_id)

    def fail(self, message_id: str, *, heartbeat: Heartbeat) -> None:
        heartbeat.stop()
        body = self.store.get(RUN_PREFIX + message_id)

        if body is None:
            return

        if self.store.put_if_absent(QUEUE_PREFIX + message_id, body):
            self.store.delete(RUN_PREFIX + message_id)

    def work_once(self, handler: Handler) -> bool:
        message = self.claim()

        if message is None:
            return False

        try:
            message.complete(handler(message.payload))
        except Exception:
            message.fail()

        return True

    def work(
        self,
        handler: Handler,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        while True:
            if not self.work_once(handler):
                time.sleep(poll_interval)
