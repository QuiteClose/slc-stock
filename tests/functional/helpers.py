import json
import os
import socket
import subprocess
import time
import urllib.request
import urllib.error
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from slc_stock.models import Base, Quote


DB_PATH = "/tmp/slc_stock_test.db"
DB_URL = f"sqlite:///{DB_PATH}"

SEED_QUOTES = [
    {"symbol": "CSCO", "date": date(2026, 2, 9), "open": 59.10, "high": 60.20, "low": 58.80, "close": 59.75, "volume": 18_000_000, "adjusted": True, "provider": "yfinance"},
    {"symbol": "CSCO", "date": date(2026, 2, 10), "open": 59.80, "high": 60.50, "low": 59.40, "close": 60.10, "volume": 17_500_000, "adjusted": True, "provider": "yfinance"},
    {"symbol": "CSCO", "date": date(2026, 2, 11), "open": 60.15, "high": 61.00, "low": 59.90, "close": 60.85, "volume": 19_200_000, "adjusted": True, "provider": "yfinance"},
    {"symbol": "CSCO", "date": date(2026, 2, 12), "open": 60.90, "high": 61.30, "low": 60.10, "close": 60.50, "volume": 16_800_000, "adjusted": True, "provider": "yfinance"},
    {"symbol": "CSCO", "date": date(2026, 2, 13), "open": 60.55, "high": 61.50, "low": 60.00, "close": 61.20, "volume": 20_100_000, "adjusted": True, "provider": "yfinance"},
    {"symbol": "AAPL", "date": date(2026, 2, 13), "open": 230.00, "high": 232.50, "low": 229.00, "close": 231.80, "volume": 55_000_000, "adjusted": True, "provider": "yfinance"},
]


class Server:
    """Context manager that starts the Flask app on a random free port."""

    _WAIT_SEC = 3

    def __init__(self):
        self.proc = None
        self.host = None
        self.port = None

    def _find_free_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        self.host, self.port = sock.getsockname()
        sock.close()

    def _clean_db(self):
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)

    def seed(self, quotes=None):
        """Insert Quote rows into the test DB before the server starts."""
        rows = quotes if quotes is not None else SEED_QUOTES
        engine = create_engine(DB_URL, echo=False)
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        now = datetime.now(UTC)
        for q in rows:
            session.add(Quote(
                symbol=q["symbol"],
                date=q["date"],
                open=q["open"],
                high=q["high"],
                low=q["low"],
                close=q["close"],
                volume=q["volume"],
                adjusted=q.get("adjusted", True),
                provider=q["provider"],
                fetched_at=now,
            ))
        session.commit()
        session.close()
        engine.dispose()

    def _start_server(self):
        self._find_free_port()
        env = os.environ.copy()
        env["DATABASE_URL"] = DB_URL
        self.proc = subprocess.Popen(
            [
                "python", "-m", "flask",
                "--app", "slc_stock.app:create_app",
                "run",
                "--host", self.host,
                "--port", str(self.port),
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        tries = int(self._WAIT_SEC / 0.1)
        for _ in range(tries):
            try:
                check = socket.create_connection((self.host, self.port), timeout=0.25)
                check.close()
                break
            except (OSError, ConnectionRefusedError):
                time.sleep(0.1)
        else:
            raise RuntimeError(f"Server failed to start on {self.host}:{self.port}")

    def __enter__(self):
        self._clean_db()
        self._start_server()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
        self._clean_db()

    def url(self, path=""):
        if self.proc is None:
            raise RuntimeError("URL unknown until server is started")
        return f"http://{self.host}:{self.port}{path}"

    def api_get(self, path):
        """HTTP GET against the running server. Returns (status, body_dict)."""
        req = urllib.request.Request(self.url(path))
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
                return resp.status, body
        except urllib.error.HTTPError as exc:
            body = json.loads(exc.read().decode())
            return exc.code, body

    def api_post(self, path, data=None):
        """HTTP POST against the running server. Returns (status, body_dict)."""
        payload = json.dumps(data or {}).encode() if data else b""
        req = urllib.request.Request(
            self.url(path), data=payload, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
                return resp.status, body
        except urllib.error.HTTPError as exc:
            body = json.loads(exc.read().decode())
            return exc.code, body
