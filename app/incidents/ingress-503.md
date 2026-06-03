# Ingress returns 503 Service Unavailable

## Symptoms
- Browser or curl to HTTPS hostname returns `503 Service Unavailable`
- DNS resolves but app is unreachable

## Root cause
Common causes:
1. Cluster is scaled down or destroyed (no running nodes)
2. Backend pods not ready or crashing
3. Ingress points to wrong Service name or port
4. Nginx ingress controller not running
5. TLS/cert issue causing routing failure

## Fix
1. Confirm cluster is running and nodes are Ready
2. Check pods: `kubectl get pods`
3. Verify Service endpoints: `kubectl get endpoints`
4. Compare Ingress backend service/port with actual Service manifest
5. Check ingress-nginx controller pods in `ingress-nginx` namespace

## Debug commands
```bash
kubectl get nodes
kubectl get pods -A
kubectl get ingress
kubectl describe ingress <ingress-name>
kubectl get svc
kubectl get endpoints
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

## Prevention
- Health check endpoint on app before marking pod Ready
- Document which hostnames require cluster to be up
