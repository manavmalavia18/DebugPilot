# cert-manager / TLS certificate not ready

## Symptoms
- Ingress exists but HTTPS fails or shows certificate errors
- cert-manager Certificate stuck in `Pending` or `False` Ready
- Challenge failures in cert-manager logs

## Root cause
Let's Encrypt HTTP-01 or DNS-01 challenge failed. Common issues:
1. ClusterIssuer misconfigured
2. Ingress not reachable from internet for HTTP-01
3. Cloudflare proxy blocking challenge
4. Wrong hostname on Ingress vs Certificate

## Fix
1. `kubectl get certificate, certificaterequest, challenge -A`
2. `kubectl describe certificate <name>`
3. Ensure `external-dns` hostname matches Ingress host
4. For Cloudflare: set DNS records to DNS-only (grey cloud) during cert issuance if using HTTP-01

## Debug commands
```bash
kubectl get clusterissuer
kubectl get certificate -A
kubectl describe certificate <name> -n <namespace>
kubectl logs -n cert-manager deployment/cert-manager
kubectl describe challenge -A
```

## Prevention
- Use consistent hostname annotations on Ingress
- Document DNS/proxy settings for your domain
