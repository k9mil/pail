from datetime import datetime
from enum import StrEnum
from typing import NamedTuple

from botocore.exceptions import ClientError

from pail.protocols import S3Client

LIST_OBJECTS_V2 = "list_objects_v2"


class S3Error(StrEnum):
    PRECONDITION_FAILED = "PreconditionFailed"
    NO_SUCH_KEY = "NoSuchKey"


class S3Field(StrEnum):
    CONTENTS = "Contents"
    KEY = "Key"
    BODY = "Body"
    LAST_MODIFIED = "LastModified"


class S3Object(NamedTuple):
    key: str
    last_modified: datetime


class Store:
    def __init__(self, bucket: str, client: S3Client) -> None:
        self.bucket = bucket
        self.client = client

    @staticmethod
    def error_code(error: ClientError) -> str:
        return error.response["Error"]["Code"]

    def put_if_absent(self, key: str, body: bytes) -> bool:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                IfNoneMatch="*",
            )
        except ClientError as error:
            if self.error_code(error) == S3Error.PRECONDITION_FAILED:
                return False
            raise
        return True

    def put(self, key: str, body: bytes) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
        )

    def get(self, key: str) -> bytes | None:
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=key,
            )
        except ClientError as error:
            if self.error_code(error) == S3Error.NO_SUCH_KEY:
                return None
            raise
        return response[S3Field.BODY].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(
            Bucket=self.bucket,
            Key=key,
        )

    def list_objects(self, prefix: str) -> list[S3Object]:
        objects: list[S3Object] = []
        paginator = self.client.get_paginator(LIST_OBJECTS_V2)

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            objects.extend(
                S3Object(item[S3Field.KEY], item[S3Field.LAST_MODIFIED])
                for item in page.get(S3Field.CONTENTS, [])
            )

        return objects
