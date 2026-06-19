import threading

from pail.store import Store


class Heartbeat:
    def __init__(self, store: Store, key: str, body: bytes, interval: float) -> None:
        self.store = store
        self.key = key
        self.body = body
        self.interval = interval
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def beat(self) -> None:
        self.store.put(self.key, self.body)

    def run(self) -> None:
        while not self.stopped.wait(self.interval):
            self.beat()

    def stop(self) -> None:
        self.stopped.set()
        self.thread.join()
