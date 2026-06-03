# GitHub Actions deploy / kubectl failure

## Symptoms
- Workflow fails at `aws eks update-kubeconfig` or `kubectl apply`
- `Unable to connect to the server` or `Unauthorized`
- `error: You must be logged in to the server`

## Root cause
Common causes:
1. AWS credentials missing or expired in GitHub Secrets
2. Wrong cluster name or region
3. IAM role/user lacks EKS access
4. kubectl context not configured before helm/kubectl steps
5. Cluster does not exist (destroyed or wrong account)

## Fix
1. Verify secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
2. Confirm cluster exists: `aws eks describe-cluster --name <name>`
3. Run `aws eks update-kubeconfig --name <name> --region <region>` in workflow before kubectl
4. Check IAM policy includes `eks:DescribeCluster` and appropriate RBAC (aws-auth / access entries)

## Debug commands
```bash
aws sts get-caller-identity
aws eks list-clusters --region <region>
aws eks update-kubeconfig --name <cluster> --region <region>
kubectl get nodes
```

## Prevention
- Use OIDC + IAM role for GitHub Actions instead of long-lived keys when possible
- Smoke-test kubeconfig step separately before full deploy job
