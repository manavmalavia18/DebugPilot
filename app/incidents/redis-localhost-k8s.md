# Redis connection refused in Kubernetes

## Symptoms
- CrashLoopBackOff on API pod
- `Connection refused` to `localhost:6379` or `127.0.0.1:6379`
- App works locally with docker-compose but fails in cluster

## Root cause
The app uses `REDIS_HOST=localhost`. Inside a Kubernetes pod, `localhost` refers to the pod itself, not the Redis Service running elsewhere in the cluster.

## Fix
Set `REDIS_HOST` to the Redis Service DNS name, e.g. `redis` (same namespace) or `redis.default.svc.cluster.local`.

Update the Deployment env vars or Helm values and redeploy.

## Debug commands
```bash
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs deployment/<api-deployment> --previous
kubectl get svc
kubectl run -it --rm redis-test --image=redis:alpine -- redis-cli -h redis ping
```

## Prevention
- Mirror K8s service names in docker-compose for local dev
- Never hardcode `localhost` for inter-service communication in cluster manifests
