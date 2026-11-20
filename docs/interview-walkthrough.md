# KubeRescue — 5-minute interview demonstration

## Short introduction (30 seconds)

> I built KubeRescue to demonstrate Kubernetes beyond simply deploying YAML. It's a small Python service with three replicas, live health probes, least-privilege container settings, rolling updates, and an automated recovery test. The GitHub Actions workflow starts a real kind cluster and proves recovery on every pull request.

## Live walkthrough

1. **Show `k8s/deployment.yaml` (45 sec):** explain replicas, selectors, probe types, resource requests and limits, and update strategy.
2. **Inspect real pods (30 sec):** `kubectl --context kind-kuberescue -n kuberescue get pods -o wide` — identify desired vs. actual state and worker placement.
3. **Show the app (45 sec):** `kubectl --context kind-kuberescue -n kuberescue port-forward svc/kuberescue 8080:80`; visit `http://localhost:8080` and show the responding Pod's metadata.
4. **Inject a failure (60 sec):** `python scripts/demo_failure.py` — explain how the script records Pod UIDs, deletes one Pod and validates that a *new* UID appears and the ready count returns to three.
5. **Review CI (30 sec):** show `.github/workflows/ci.yml` — unit tests, real cluster deployment, Pod deletion/recovery and v2 rollout. If CI has not been executed yet, say so.
6. **Explain trade-offs (30 sec):** kind nodes share a physical Docker host; `port-forward` selects a Pod and is not a Service load-balancing benchmark; no claims of enterprise-grade availability.

## Strong interview answers

**Why did you use a Deployment?** Its controller maintains a desired number of interchangeable, stateless Pods through a ReplicaSet and supports controlled rolling updates.

**What is the difference between readiness and liveness?** Readiness decides whether a Pod should receive Service traffic; liveness tells kubelet when to restart an unhealthy container. Neither guarantees the application is correct, so probes should represent suitable checks.

**How did you prove Kubernetes replaced the Pod?** Before deletion I saved the set of Pod UIDs. After deletion I required the old UID to disappear, all desired replicas to be Ready, and at least one new UID to appear. This guards against a misleading count-only test.

**What's the biggest limitation?** This is a single-host kind lab. It demonstrates control-plane behavior and Pod replacement but not independent infrastructure failure domains or production-grade SLOs.

## How to describe the project on a resume

> Built a reproducible Kubernetes self-healing lab using Python, Docker and kind; configured a secure three-replica Deployment with HTTP health probes and rolling updates, and automated failure/recovery verification in GitHub Actions by tracking Pod UIDs.
