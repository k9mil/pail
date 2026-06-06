import io
from collections.abc import Iterator
from typing import Any

from botocore.exceptions import ClientError


def make_client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code}}, "operation")


class FakePaginator:
    def __init__(self, objects: dict[tuple[str, str], bytes]) -> None:
        self.objects = objects

    def paginate(self, *, Bucket: str, Prefix: str = "") -> Iterator[dict[str, Any]]:
        keys = sorted(
            key
            for (bucket, key) in self.objects
            if bucket == Bucket and key.startswith(Prefix)
        )
        yield {"Contents": [{"Key": key} for key in keys]}


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

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
        self.objects[(Bucket, Key)] = Body
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if (Bucket, Key) not in self.objects:
            raise make_client_error("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

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
