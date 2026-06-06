from typing import Any

from botocore.exceptions import ClientError

from pail.protocols import S3Client


class Store:
    def __init__(self, bucket: str, client: S3Client) -> None:
        self.bucket = bucket
        self.client = client

    def put_if_absent(self, key: str, body: bytes) -> bool:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                IfNoneMatch="*",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "PreconditionFailed":
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
            if error.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(
            Bucket=self.bucket,
            Key=key,
        )

    def list_keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        token: str | None = None

        params: dict[str, Any] = {
            "Bucket": self.bucket,
            "Prefix": prefix,
        }

        while True:
            if token is not None:
                params["ContinuationToken"] = token

            response = self.client.list_objects_v2(**params)
            keys.extend(item["Key"] for item in response.get("Contents", []))

            if not response.get("IsTruncated"):
                break

            token = response.get("NextContinuationToken")
        return keys
