from typing import Any

from pail import Pail

BUCKET = "my-bucket"
ERROR = "ERROR"


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    print(f"building report {payload['report_id']}")
    raise RuntimeError(ERROR)


def main() -> None:
    pail = Pail.connect(BUCKET, max_retries=3)
    pail.enqueue({"report_id": "q2_revenue", "format": "pdf"})

    while pail.work_once(build_report):
        pass

    print(f"dlq depth is now {pail.stats().failed}")


if __name__ == "__main__":
    main()
