"""Integration-style HTTP tests using only Python's standard library."""

import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

from app import main


class AppHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = main.RescueServer(("127.0.0.1", 0), main.RescueHandler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=3) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def test_healthz_is_live(self):
        code, headers, body = self.request("/healthz")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body), {"status": "alive"})
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_readyz_when_started(self):
        with mock.patch.object(main, "READY_AFTER", time.monotonic() - 1):
            code, _, body = self.request("/readyz")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["status"], "ready")

    def test_readyz_returns_503_when_not_ready(self):
        with mock.patch.object(main, "READY_AFTER", time.monotonic() + 60):
            code, _, body = self.request("/readyz")
        self.assertEqual(code, 503)
        self.assertEqual(json.loads(body)["status"], "starting")

    def test_healthz_does_not_depend_on_readiness(self):
        with mock.patch.object(main, "READY_AFTER", time.monotonic() + 60):
            code, _, _ = self.request("/healthz")
        self.assertEqual(code, 200)

    def test_api_info_shape(self):
        code, _, body = self.request("/api/info")
        self.assertEqual(code, 200)
        info = json.loads(body)
        self.assertEqual(info["application"], "KubeRescue")
        self.assertIn("pod", info)
        self.assertIn("node", info)
        self.assertIn("namespace", info)
        self.assertIn("started_at", info)
        self.assertGreaterEqual(info["uptime_seconds"], 0)
        self.assertGreaterEqual(info["requests_served"], 1)

    def test_api_uses_environment_metadata(self):
        with mock.patch.dict("os.environ", {"APP_VERSION": "test-42", "POD_NAME": "replica-1", "POD_NODE_NAME": "worker-1", "POD_NAMESPACE": "test-ns"}):
            info = json.loads(self.request("/api/info")[2])
        self.assertEqual(info["version"], "test-42")
        self.assertEqual(info["pod"], "replica-1")
        self.assertEqual(info["node"], "worker-1")
        self.assertEqual(info["namespace"], "test-ns")

    def test_homepage_contains_ui(self):
        code, headers, body = self.request("/")
        self.assertEqual(code, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b"Kube", body)
        self.assertIn(b"/api/info", body)

    def test_unknown_route_is_404(self):
        code, _, body = self.request("/does-not-exist")
        self.assertEqual(code, 404)
        self.assertEqual(json.loads(body)["error"], "not found")

    def test_query_strings_do_not_break_routes(self):
        code, _, _ = self.request("/healthz?probe=1")
        self.assertEqual(code, 200)

    def test_response_has_pod_header(self):
        with mock.patch.dict("os.environ", {"POD_NAME": "pod-xyz"}):
            _, headers, _ = self.request("/api/info")
        self.assertEqual(headers["X-KubeRescue-Pod"], "pod-xyz")

    def test_invalid_startup_delay_is_safe(self):
        with mock.patch.dict("os.environ", {"STARTUP_DELAY_SECONDS": "not-a-number"}):
            self.assertEqual(main.startup_delay_seconds(), 0.0)

    def test_negative_delay_clamped_to_zero(self):
        with mock.patch.dict("os.environ", {"STARTUP_DELAY_SECONDS": "-10"}):
            self.assertEqual(main.startup_delay_seconds(), 0.0)


if __name__ == "__main__":
    unittest.main()
