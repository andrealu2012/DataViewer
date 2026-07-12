"""Background worker that asks the RealDataView server for stock quotes."""

from typing import List

import requests
from PyQt6.QtCore import QMutex, QThread, pyqtSignal


class StockDataClientWorker(QThread):
    data_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, stock_codes: List[str], base_url: str, timeout_seconds: float = 8):
        super().__init__()
        self.stock_codes = stock_codes
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.mutex = QMutex()
        self._is_running = False

    def run(self):
        self.mutex.lock()
        self._is_running = True
        self.mutex.unlock()

        try:
            response = requests.post(
                f"{self.base_url}/api/quotes",
                json={"codes": self.stock_codes},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()

            self.mutex.lock()
            is_running = self._is_running
            self.mutex.unlock()

            if is_running:
                self.data_ready.emit(payload)
        except Exception as exc:
            self.error_occurred.emit(f"{type(exc).__name__}: {exc}")

    def stop(self, wait_ms: int = 1000):
        self.mutex.lock()
        self._is_running = False
        self.mutex.unlock()
        if wait_ms > 0:
            self.wait(wait_ms)
