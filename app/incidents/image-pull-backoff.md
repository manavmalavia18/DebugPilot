# ImagePullBackOff

## Symptoms
- Pod status `ImagePullBackOff` or `ErrImagePull`
- Events mention `Failed to pull image` or `manifest unknown`

## Root cause
Common causes:
1. Wrong image tag or typo in registry path
2. Image not pushed to ECR/GCR/Artifact Registry
3. Node architecture mismatch (arm64 image on amd64 nodes)
4. Missing registry credentials or wrong IAM permissions

## Fix
1. Verify the tag exists: `aws ecr describe-images` or check GCR/Artifact Registry
2. Confirm Helm values / deployment image matches CI-built SHA
3. Rebuild with `docker buildx --platform linux/amd64` for EKS/GKE nodes
4. Ensure `imagePullPolicy` and registry auth are configured if using private registries

## Debug commands
```bash
kubectl describe pod <pod-name>
kubectl get events --sort-by='.lastTimestamp'
aws ecr describe-images --repository-name <repo> --region <region>
```

## Prevention
- CI pushes image before updating Helm values / GitOps manifest
- Pin images by commit SHA, not only `:latest`
