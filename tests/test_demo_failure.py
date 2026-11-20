"""Unit-test the recovery proof independently of a Kubernetes installation."""

import importlib.util
from pathlib import Path
import unittest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "demo_failure.py"
spec = importlib.util.spec_from_file_location("demo_failure", SCRIPT_PATH)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def pod(name, uid, ready=True, deleting=False):
    metadata = {"name": name, "uid": uid}
    if deleting:
        metadata["deletionTimestamp"] = "2026-01-01T00:00:00Z"
    return {"metadata": metadata, "status": {"conditions": [
        {"type": "Ready", "status": "True" if ready else "False"}
    ]}}


class RecoveryLogicTests(unittest.TestCase):
    def setUp(self):
        self.original = [pod("a", "uid-a"), pod("b", "uid-b"), pod("c", "uid-c")]
        self.original_uids = {"uid-a", "uid-b", "uid-c"}

    def test_ready_pod(self):
        self.assertTrue(demo.ready(pod("x", "id")))

    def test_terminating_pod_is_not_ready(self):
        self.assertFalse(demo.ready(pod("x", "id", deleting=True)))

    def test_not_ready_pod_is_excluded(self):
        self.assertFalse(demo.ready(pod("x", "id", ready=False)))

    def test_original_pods_do_not_count_as_recovery(self):
        self.assertFalse(demo.recovered(self.original, self.original_uids, "uid-a", 3))

    def test_only_two_ready_is_not_recovery(self):
        replacement = [pod("b", "uid-b"), pod("c", "uid-c"), pod("d", "uid-d", ready=False)]
        self.assertFalse(demo.recovered(replacement, self.original_uids, "uid-a", 3))

    def test_old_uid_still_visible_is_not_recovery(self):
        pods = [*self.original, pod("d", "uid-d")]
        self.assertFalse(demo.recovered(pods, self.original_uids, "uid-a", 3))

    def test_new_pod_uid_and_all_ready_is_recovery(self):
        pods = [pod("b", "uid-b"), pod("c", "uid-c"), pod("d", "uid-d")]
        self.assertTrue(demo.recovered(pods, self.original_uids, "uid-a", 3))


if __name__ == "__main__":
    unittest.main()
