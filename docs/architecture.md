# KubeRescue — Architecture and engineering decisions

## Scope

One dependency-free Python HTTP service, one Deployment, one ClusterIP Service, and a three-node `kind` cluster. No cloud credentials are required.

## Control loop

1. The Deployment declares three desired Pods.
2. Its ReplicaSet watches actual Pods and attempts to maintain the desired count.
3. Deleting a Pod removes one managed instance; the controller creates a new Pod to replace it.
4. kubelet checks each container's health and readiness; Service endpoints include eligible ready Pods.
5. The failure script compares Pod UIDs before and after. A replacement is a **new object** with a new UID.

## Why multiple probes?

| Probe | URL | What it demonstrates |
| --- | --- | --- |
| Startup | `/healthz` | Let the process initialize before regular checks run. |
| Liveness | `/healthz` | Restart the container if it is unable to respond for repeated checks. |
| Readiness | `/readyz` | Remove an unready Pod from Service endpoints without requiring a container restart. |

The demo supports optional `STARTUP_DELAY_SECONDS` for readiness testing without changing liveness. Because the process is fully responsive as soon as it starts, the startup probe is intentionally simple.

## Workload defaults

- 3 replicas; rolling update `maxUnavailable: 1`, `maxSurge: 1`.
- Placement preferences spread Pods by hostname where possible; this is *soft*, not a strict anti-affinity rule.
- Resource requests: `25m` CPU and `32Mi` RAM per replica; limits: `250m` CPU, `128Mi` RAM.
- UID/GID 10001; `readOnlyRootFilesystem: true`; `allowPrivilegeEscalation: false`; `capabilities.drop: ALL`; `seccompProfile: RuntimeDefault`.
- ClusterIP Service on TCP port 80, forwarding to container port 8080.
- Pod name, namespace and node supplied by Kubernetes' Downward API, without ServiceAccount API access.

## Deliberate choices and trade-offs

**Python standard library vs. Flask/FastAPI:** minimizing dependencies keeps the learning focus on orchestration rather than framework setup. The server is for demo workloads, not production traffic.

**kind vs. cloud Kubernetes:** reproducible, local, and free. Two `kind` workers show node placement, but they run on the same Docker host. Physical fault tolerance is not demonstrated.

**Deleting a Pod vs. crashing a container:** a Pod deletion triggers ReplicaSet reconciliation and yields a new UID. A container crash generally causes a restart *inside the same Pod*, a different mechanism. This lab demonstrates the first case explicitly and documents probes for the second.

**No in-app Kubernetes API client:** the app should remain unprivileged. Orchestrator observability is handled by `kubectl`, not a broadly privileged ServiceAccount.

**Local Docker image loading:** the images are tagged `v1` and `v2` and loaded with `kind load docker-image`; the Deployment uses `IfNotPresent`. No registry is required.

**No external authentication:** the demo is bound to localhost through `kubectl port-forward`; don't expose it to the Internet without a dedicated security design.

## Extension ideas

- Add an automated HPA exercise with metrics-server and controlled CPU load.
- Add a NetworkPolicy-enabled cluster (using a CNI that supports NetworkPolicy).
- Add observability with OpenTelemetry and Prometheus.
- Add failure injection for a container restart and record restart counts.
- Create a GitHub release containing screenshots and CI test evidence after a successful workflow run.
