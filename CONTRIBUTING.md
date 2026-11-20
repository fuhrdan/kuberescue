# Contributing

KubeRescue is a learning-focused Kubernetes example. Keep contributions small and observable.

1. Open an issue with the concept to demonstrate and the expected behavior.
2. Run `python -m unittest discover -s tests -v` before opening a pull request.
3. For manifest or workflow changes, test in the dedicated `kind-kuberescue` local cluster when possible.
4. Add a meaningful automated test for new behavior and update the README.
5. Never commit kubeconfig, cluster credentials, secrets, or production endpoint information.

CI intentionally runs real Pod deletion and rollout tests against **only an isolated kind cluster**.
