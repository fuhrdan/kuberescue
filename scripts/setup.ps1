# Create / update ONLY the local kind-kuberescue training cluster.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Assert-OK([string]$description) {
    if ($LASTEXITCODE -ne 0) { throw "$description failed (exit code $LASTEXITCODE)" }
}
foreach ($command in @('docker', 'kind', 'kubectl')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Missing prerequisite: $command"
    }
}
& docker info *> $null
Assert-OK 'Docker check (is Docker Desktop running?)'
$clusters = @(& kind get clusters)
Assert-OK 'kind cluster lookup'
if ($clusters -notcontains 'kuberescue') {
    Write-Host '[1/4] Creating local three-node kind cluster...'
    & kind create cluster --name kuberescue --config (Join-Path $root 'k8s/kind-config.yaml')
    Assert-OK 'kind create cluster'
} else {
    Write-Host '[1/4] Reusing local kind-kuberescue cluster'
}
Write-Host '[2/4] Building application image...'
& docker build --build-arg APP_VERSION=v1 -t kuberescue:v1 $root
Assert-OK 'Docker build'
Write-Host '[3/4] Loading image into kind...'
& kind load docker-image kuberescue:v1 --name kuberescue
Assert-OK 'kind image load'
Write-Host '[4/4] Applying Kubernetes resources...'
& kubectl --context kind-kuberescue apply -f (Join-Path $root 'k8s/namespace.yaml')
Assert-OK 'Namespace apply'
& kubectl --context kind-kuberescue apply -f (Join-Path $root 'k8s/deployment.yaml') -f (Join-Path $root 'k8s/service.yaml')
Assert-OK 'Deployment and Service apply'
& kubectl --context kind-kuberescue -n kuberescue set image deployment/kuberescue 'web=kuberescue:v1'
Assert-OK 'Image reset to v1'
& kubectl --context kind-kuberescue -n kuberescue rollout status deployment/kuberescue --timeout=180s
Assert-OK 'Deployment rollout'
& kubectl --context kind-kuberescue -n kuberescue get pods -l 'app=kuberescue' -o wide
Assert-OK 'Pod listing'
Write-Host "`nDone! In another PowerShell terminal run:"
Write-Host '  kubectl --context kind-kuberescue -n kuberescue port-forward svc/kuberescue 8080:80'
Write-Host 'Then visit http://localhost:8080'
