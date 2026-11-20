#!/usr/bin/env bash
set -euo pipefail
# Removes only the kind cluster explicitly named kuberescue.
kind delete cluster --name kuberescue
