"""Tiny HTTP service for demonstrating Kubernetes probes and Pod identity.

No Kubernetes client or external Python dependencies are required. The app runs
unchanged on a laptop and in a container; Kubernetes injects Pod metadata.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

STATIC_PAGE = Path(__file__).parent / "static" / "index.html"
START_MONOTONIC = time.monotonic()
START_UTC = datetime.now(timezone.utc).isoformat()
COUNTER_LOCK = threading.Lock()
REQUEST_COUNT = 0
LOG = logging.getLogger("kuberescue")


def startup_delay_seconds() -> float:
    """Optional delay to demonstrate readiness without changing liveness."""
    try:
        return max(0.0, float(os.environ.get("STARTUP_DELAY_SECONDS", "0")))
    except ValueError:
        LOG.warning("Invalid STARTUP_DELAY_SECONDS; defaulting to zero")
        return 0.0


READY_AFTER = START_MONOTONIC + startup_delay_seconds()


def pod_info() -> dict[str, Any]:
    global REQUEST_COUNT
    with COUNTER_LOCK:
        count = REQUEST_COUNT
    return {
        "application": "KubeRescue",
        "version": os.environ.get("APP_VERSION", "dev"),
        "pod": os.environ.get("POD_NAME", os.environ.get("HOSTNAME", "local")),
        "node": os.environ.get("POD_NODE_NAME", "local"),
        "namespace": os.environ.get("POD_NAMESPACE", "local"),
        "started_at": START_UTC,
        "uptime_seconds": round(time.monotonic() - START_MONOTONIC, 1),
        "requests_served": count,
        "ready": time.monotonic() >= READY_AFTER,
    }


class RescueHandler(BaseHTTPRequestHandler):
    server_version = "KubeRescue/1.0"
    sys_version = ""

    def do_GET(self) -> None:
        global REQUEST_COUNT
        with COUNTER_LOCK:
            REQUEST_COUNT += 1
        path = urlsplit(self.path).path
        if path == "/healthz":
            self.send_json({"status": "alive"})
        elif path == "/readyz":
            ready = time.monotonic() >= READY_AFTER
            self.send_json({"status": "ready" if ready else "starting"}, 200 if ready else 503)
        elif path == "/api/info":
            self.send_json(pod_info())
        elif path == "/":
            self.send_bytes(STATIC_PAGE.read_bytes(), "text/html; charset=utf-8")
        else:
            self.send_json({"error": "not found"}, 404)

    def do_HEAD(self) -> None:
        # HEAD isn't a probe requirement, but a clear 405 is useful to clients.
        self.send_response(405)
        self.send_header("Allow", "GET")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_json(self, obj: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        self.send_bytes(body, "application/json; charset=utf-8", status)

    def send_bytes(self, body: bytes, media_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-KubeRescue-Pod", os.environ.get("POD_NAME", "local"))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format: str, *args: object) -> None:
        LOG.info("%s %s", self.address_string(), format % args)


class RescueServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(port: int = 8080) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    httpd = RescueServer(("0.0.0.0", port), RescueHandler)

    def stop_server(_signum: int, _frame: object) -> None:
        LOG.info("Shutdown signal received")
        # shutdown() must be called in another thread to avoid deadlock.
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, stop_server)
        signal.signal(signal.SIGINT, stop_server)
    LOG.info("KubeRescue listening on port %s", port)
    try:
        httpd.serve_forever(poll_interval=0.2)
    finally:
        httpd.server_close()
        LOG.info("KubeRescue stopped")


if __name__ == "__main__":
    serve(int(os.environ.get("PORT", "8080")))
