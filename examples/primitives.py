import time
from typing import Any

from pail import Pail

BUCKET = "my-bucket"
POLL_SECONDS = 5


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    report_id = payload["report_id"]
    return {"report_id": report_id, "url": f"reports/{report_id}.pdf"}


def main() -> None:
    pail = Pail.connect(BUCKET)

    while True:
        message = pail.claim()
        if message is None:
            time.sleep(POLL_SECONDS)
            continue

        print(f"claimed {message.id}")
        try:
            result = build_report(message.payload)
        except Exception:
            message.fail()
            print(f"failed {message.id}, returned to queue")
        else:
            message.complete(result)
            print(f"completed {message.id}")


if __name__ == "__main__":
    main()
