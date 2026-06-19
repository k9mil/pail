import io
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, NamedTuple

from botocore.exceptions import ClientError


def make_client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code}}, "operation")


class Stored(NamedTuple):
    body: bytes
    last_modified: datetime


class FakePaginator:
    def __init__(self, objects: dict[tuple[str, str], Stored]) -> None:
        self.objects = objects

    def paginate(self, *, Bucket: str, Prefix: str = "") -> Iterator[dict[str, Any]]:
        items = sorted(
            (key, stored.last_modified)
            for (bucket, key), stored in self.objects.items()
            if bucket == Bucket and key.startswith(Prefix)
        )
        yield {
            "Contents": [
                {"Key": key, "LastModified": last_modified}
                for key, last_modified in items
            ],
        }


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], Stored] = {}

    def seed(self, bucket: str, key: str, body: bytes, last_modified: datetime) -> None:
        self.objects[(bucket, key)] = Stored(body, last_modified)

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        IfNoneMatch: str | None = None,
    ) -> dict[str, Any]:
        if IfNoneMatch == "*" and (Bucket, Key) in self.objects:
            raise make_client_error("PreconditionFailed")
        self.objects[(Bucket, Key)] = Stored(Body, datetime.now(UTC))
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if (Bucket, Key) not in self.objects:
            raise make_client_error("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)].body)}

    def delete_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self.objects.pop((Bucket, Key), None)
        return {}

    def get_paginator(self, operation_name: str, /) -> FakePaginator:
        return FakePaginator(self.objects)


class RaisingS3(FakeS3):
    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        IfNoneMatch: str | None = None,
    ) -> dict[str, Any]:
        raise make_client_error("AccessDenied")
