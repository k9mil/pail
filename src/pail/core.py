import json
from typing import Any, Self, cast

import boto3
from ulid import ULID

from pail.models import Message
from pail.protocols import S3Client
from pail.store import Store

QUEUE_PREFIX = "queue/"
RUN_PREFIX = "run/"
DONE_PREFIX = "done/"

S3 = "S3"


class Pail:
    def __init__(self, bucket: str, client: S3Client) -> None:
        self.store = Store(bucket, client)

    @classmethod
    def connect(
        cls,
        bucket: str,
        *,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str | None = None,
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
        )

    def enqueue(self, payload: dict[str, Any]) -> str:
        message_id = str(ULID())
        self.store.put_if_absent(
            QUEUE_PREFIX + message_id,
            encode(payload),
        )

        return message_id

    def claim(self) -> Message | None:
        for key in self.store.list_keys(QUEUE_PREFIX):
            message_id = key.removeprefix(QUEUE_PREFIX)
            body = self.store.get(key)

            if body is None:
                continue

            claimed = self.store.put_if_absent(
                RUN_PREFIX + message_id,
                body,
            )
            self.store.delete(key)

            if claimed:
                return Message(
                    message_id,
                    decode(body),
                    self.complete,
                )
        return None

    def result(self, message_id: str) -> dict[str, Any] | None:
        body = self.store.get(DONE_PREFIX + message_id)

        if body is None:
            return None

        return decode(body)

    def complete(self, message_id: str, result: dict[str, Any] | None) -> None:
        self.store.put(
            DONE_PREFIX + message_id,
            encode(result or {}),
        )
        self.store.delete(RUN_PREFIX + message_id)


def encode(value: dict[str, Any]) -> bytes:
    return json.dumps(value).encode()


def decode(body: bytes) -> dict[str, Any]:
    return json.loads(body)
