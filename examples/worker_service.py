import time
from typing import Any

from pail import Pail

BUCKET = "my-bucket"
SIMULATION_SECONDS = 2


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    report_id = payload["report_id"]
    print(f"building report {report_id}")
    time.sleep(SIMULATION_SECONDS)
    return {"report_id": report_id, "url": f"reports/{report_id}.pdf"}


def main() -> None:
    pail = Pail.connect(BUCKET)
    pail.work(build_report)


if __name__ == "__main__":
    main()
