#!/usr/bin/env python3
"""Prove Deployment self-healing by UID, not by merely counting ready Pods.

This script *only* targets the `kind-kuberescue` context, making it suitable for
local demos and CI. It never changes the user's kubectl current context.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from typing import Any

CONTEXT = "kind-kuberescue"
NAMESPACE = "kuberescue"
SELECTOR = "app=kuberescue"


def kubectl(*args: str) -> str:
    result = subprocess.run(
        ["kubectl", "--context", CONTEXT, "-n", NAMESPACE, *args],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"kubectl failed with code {result.returncode}")
    return result.stdout


def deployment_replicas() -> int:
    deployment = json.loads(kubectl("get", "deployment", "kuberescue", "-o", "json"))
    return int(deployment["spec"]["replicas"])


def pods() -> list[dict[str, Any]]:
    data = json.loads(kubectl("get", "pods", "-l", SELECTOR, "-o", "json"))
    return data["items"]


def ready(pod: dict[str, Any]) -> bool:
    conditions = pod.get("status", {}).get("conditions", [])
    return pod.get("metadata", {}).get("deletionTimestamp") is None and any(
        c.get("type") == "Ready" and c.get("status") == "True" for c in conditions
    )


def recovered(current: list[dict[str, Any]], original_uids: set[str], deleted_uid: str, desired: int) -> bool:
    """Deleted UID vanished, ready count restored, and a genuinely new UID arrived."""
    ready_now = [p for p in current if ready(p)]
    current_uids = {p["metadata"]["uid"] for p in current}
    return (len(ready_now) == desired and deleted_uid not in current_uids
            and bool(current_uids - original_uids))


def demo(timeout: float) -> None:
    if timeout <= 0:
        raise ValueError("--timeout must be positive")
    desired = deployment_replicas()
    if desired < 2:
        raise RuntimeError("Expected at least two replicas for this demonstration")
    original = pods()
    ready_original = [p for p in original if ready(p)]
    if len(ready_original) != desired:
        raise RuntimeError(f"Deployment must start ready: {len(ready_original)}/{desired} ready")
    original_uids = {p["metadata"]["uid"] for p in original}
    victim = sorted(ready_original, key=lambda p: p["metadata"]["name"])[0]
    victim_name, victim_uid = victim["metadata"]["name"], victim["metadata"]["uid"]

    print(f"Context: {CONTEXT} (explicitly pinned; safe local lab)", flush=True)
    print(f"Initial ready: {len(ready_original)}/{desired}; Pod UIDs recorded", flush=True)
    print(f"Deleting Pod {victim_name} (UID {victim_uid}) ...", flush=True)
    kubectl("delete", "pod", victim_name, "--wait=false")
    started = time.monotonic()
    last_message = ""
    while time.monotonic() - started < timeout:
        current = pods()
        ready_count = sum(ready(p) for p in current)
        message = f"Ready: {ready_count}/{desired}; visible Pod objects: {len(current)}"
        if message != last_message:
            print(message, flush=True)
            last_message = message
        if recovered(current, original_uids, victim_uid, desired):
            replacement = sorted(
                (p for p in current if p["metadata"]["uid"] not in original_uids),
                key=lambda p: p["metadata"]["name"],
            )[0]
            elapsed = time.monotonic() - started
            print(f"PASS: {replacement['metadata']['name']} has a NEW UID", flush=True)
            print(f"Self-healing verified: {desired}/{desired} ready after {elapsed:.1f}s", flush=True)
            return
        time.sleep(1)
    raise TimeoutError(f"FAIL: No verified recovery after {timeout:g}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=180.0, help="Recovery timeout in seconds")
    args = parser.parse_args()
    try:
        demo(args.timeout)
    except (RuntimeError, TimeoutError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
