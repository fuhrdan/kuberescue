$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
function Assert-OK([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed (exit code $LASTEXITCODE)" }
}
Write-Host 'Building a new image with APP_VERSION=v2...'
& docker build --build-arg APP_VERSION=v2 -t kuberescue:v2 $root
Assert-OK 'Docker build v2'
& kind load docker-image kuberescue:v2 --name kuberescue
Assert-OK 'Load v2 image'
& kubectl --context kind-kuberescue -n kuberescue set image deployment/kuberescue 'web=kuberescue:v2'
Assert-OK 'Update Deployment image'
& kubectl --context kind-kuberescue -n kuberescue rollout status deployment/kuberescue --timeout=180s
Assert-OK 'Rolling update'
& kubectl --context kind-kuberescue -n kuberescue get pods -l 'app=kuberescue' -o wide
Assert-OK 'List updated Pods'
Write-Host 'Rolling deployment complete (version v2). Run setup.ps1 to return to v1.'
