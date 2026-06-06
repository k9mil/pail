import pytest
from fakes import FakeS3

from pail import Pail
from pail.store import Store


@pytest.fixture
def s3() -> FakeS3:
    return FakeS3()


@pytest.fixture
def store(s3: FakeS3) -> Store:
    return Store("bucket", s3)


@pytest.fixture
def pail(s3: FakeS3) -> Pail:
    return Pail("bucket", s3)
