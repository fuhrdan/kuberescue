#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo 'Building a new image with APP_VERSION=v2...'
docker build --build-arg APP_VERSION=v2 -t kuberescue:v2 "$ROOT"
kind load docker-image kuberescue:v2 --name kuberescue
kubectl --context kind-kuberescue -n kuberescue set image deployment/kuberescue web=kuberescue:v2
kubectl --context kind-kuberescue -n kuberescue rollout status deployment/kuberescue --timeout=180s
kubectl --context kind-kuberescue -n kuberescue get pods -l app=kuberescue -o wide
printf '\nRolling deployment complete (version v2). Run setup.sh to return to v1.\n'
