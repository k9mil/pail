import json
from datetime import UTC, datetime
from functools import partial
from typing import Any, Self, cast

import boto3
from ulid import ULID

from pail.heartbeat import Heartbeat
from pail.models import Message
from pail.protocols import S3Client
from pail.store import Store

QUEUE_PREFIX = "queue/"
RUN_PREFIX = "run/"
DONE_PREFIX = "done/"

S3 = "s3"

DEFAULT_VISIBILITY_TIMEOUT = 30.0
HEARTBEAT_DIVISOR = 3


class Pail:
    def __init__(
        self,
        bucket: str,
        client: S3Client,
        *,
        visibility_timeout: float = DEFAULT_VISIBILITY_TIMEOUT,
    ) -> None:
        self.store = Store(bucket, client)
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


def encode(value: dict[str, Any]) -> bytes:
    return json.dumps(value).encode()


def decode(body: bytes) -> dict[str, Any]:
    return json.loads(body)
