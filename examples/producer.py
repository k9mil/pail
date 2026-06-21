import time

from pail import Pail

BUCKET = "my-bucket"
POLL_SECONDS = 2


def main() -> None:
    pail = Pail.connect(BUCKET)

    job_id = pail.enqueue({"report_id": "q2_revenue", "format": "pdf"})
    print(f"enqueued {job_id}")

    result = pail.result(job_id)
    while result is None:
        time.sleep(POLL_SECONDS)
        result = pail.result(job_id)

    print(f"result ready: {result}")


if __name__ == "__main__":
    main()
