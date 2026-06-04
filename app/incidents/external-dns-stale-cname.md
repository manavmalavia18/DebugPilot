# ExternalDNS stale CNAME after cluster recreate

## Symptoms
- `curl: (6) Could not resolve host` or site unreachable after EKS recreate
- `dig debugpilot.manavmalavia.org CNAME +short` shows an old ELB hostname
- `kubectl get ingress` shows a **different** (new) ELB address
- external-dns logs: `All records are already up to date` but DNS is wrong

## Root cause
Recreating the cluster creates a new AWS load balancer. Cloudflare CNAME records
still point at the **old** ELB. external-dns may not update them if:
1. CNAMEs exist without matching TXT ownership records (`txtOwnerId: debugpilot-aws`)
2. Cluster was destroyed without deleting Ingress resources first
3. DNS records were created manually or by a previous cluster instance

## Fix
1. Compare desired vs actual:
   ```bash
   kubectl get ingress debugpilot-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'
   dig debugpilot.manavmalavia.org CNAME +short
   ```
2. In Cloudflare, delete stale AWS CNAME records:
   - `debugpilot`, `debugpilot-grafana`, `debugpilot-argocd`
   - Related TXT records (`cname-debugpilot*`) if present
3. Restart external-dns to recreate records:
   ```bash
   kubectl rollout restart deployment/external-dns -n external-dns
   kubectl logs -n external-dns deployment/external-dns --tail=30 -f
   ```
4. Verify:
   ```bash
   dig debugpilot.manavmalavia.org CNAME +short
   curl https://debugpilot.manavmalavia.org/health
   ```

## Debug commands
```bash
kubectl get ingress -A
kubectl get pods -n external-dns
kubectl logs -n external-dns deployment/external-dns --tail=50
dig debugpilot.manavmalavia.org CNAME +short
dig debugpilot-grafana.manavmalavia.org CNAME +short
dig debugpilot-argocd.manavmalavia.org CNAME +short
```

## Prevention
- Always run **Terraform AWS → destroy** (not orphan the cluster) before recreating
- The destroy workflow deletes AWS Ingress manifests and waits for external-dns
  to remove Cloudflare records before tearing down EKS
- After **apply**, confirm `dig` CNAME matches `kubectl get ingress` ADDRESS
- Do not edit AWS CNAME records manually in Cloudflare unless re-syncing afterward
