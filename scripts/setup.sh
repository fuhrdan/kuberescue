#!/usr/bin/env bash
# Creates / updates only the named kind-kuberescue lab cluster.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for cmd in kind kubectl docker; do
  command -v "$cmd" >/dev/null || { echo "Missing dependency: $cmd" >&2; exit 1; }
done
docker info >/dev/null 2>&1 || { echo "Docker isn't running." >&2; exit 1; }

if ! kind get clusters | grep -qx kuberescue; then
  echo '[1/4] Creating local three-node kind cluster...'
  kind create cluster --name kuberescue --config "$ROOT/k8s/kind-config.yaml"
else
  echo '[1/4] Reusing existing local kind cluster kuberescue'
fi

echo '[2/4] Building Python application image...'
docker build --build-arg APP_VERSION=v1 -t kuberescue:v1 "$ROOT"
echo '[3/4] Loading image into kind nodes...'
kind load docker-image kuberescue:v1 --name kuberescue

echo '[4/4] Applying Kubernetes resources...'
kubectl --context kind-kuberescue apply -f "$ROOT/k8s/namespace.yaml"
kubectl --context kind-kuberescue apply -f "$ROOT/k8s/deployment.yaml" -f "$ROOT/k8s/service.yaml"
# Idempotent re-runs after a v2 demo should switch back to v1.
kubectl --context kind-kuberescue -n kuberescue set image deployment/kuberescue web=kuberescue:v1
kubectl --context kind-kuberescue -n kuberescue rollout status deployment/kuberescue --timeout=180s
kubectl --context kind-kuberescue -n kuberescue get pods -l app=kuberescue -o wide
printf '\nDone! Open another terminal and run:\n  kubectl --context kind-kuberescue -n kuberescue port-forward svc/kuberescue 8080:80\nVisit http://localhost:8080\n'
