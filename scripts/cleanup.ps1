$ErrorActionPreference = 'Stop'
# Removes only the kind cluster explicitly named kuberescue.
& kind delete cluster --name kuberescue
if ($LASTEXITCODE -ne 0) { throw "kind delete cluster failed" }
