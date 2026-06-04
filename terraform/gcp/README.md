# GCP cluster (isolated from AWS)

Mirrors the AWS EKS stack: GKE, Artifact Registry, ingress-nginx, external-dns (Cloudflare), cert-manager, kube-prometheus-stack, ArgoCD, and GCP-only ingress hostnames.

**Does not modify** `terraform/aws/` or `k8s/ingress/aws/` (AWS production DNS). GCP manifests live under `k8s/ingress/gcp/`.

## URLs (GCP only)

| Service | URL |
|---------|-----|
| API | https://debugpilot-gcp.manavmalavia.org |
| Grafana | https://debugpilot-gcp-grafana.manavmalavia.org |
| ArgoCD | https://debugpilot-gcp-argocd.manavmalavia.org |

## Prerequisites

```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud auth application-default login

gcloud services enable container.googleapis.com artifactregistry.googleapis.com compute.googleapis.com

# Remote state bucket (once)
gcloud storage buckets create gs://debugpilot-terraform-state-PROJECT_NUMBER \
  --project=YOUR_GCP_PROJECT_ID --location=us-central1 --uniform-bucket-level-access
```

## Local apply

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your Cloudflare token
# Optional: argocd_github_webhook_secret, github_client_id/secret (GITHUB_OAUTH_CLIENT_ID_GCP in Actions), jwt_secret

cd terraform/gcp
terraform init
terraform plan
terraform apply
```

## Verify

```bash
gcloud container clusters get-credentials debugpilot \
  --region us-central1 --project YOUR_GCP_PROJECT_ID

kubectl get nodes
kubectl get pods -A
kubectl get ingress -A
```

Push an image to Artifact Registry before expecting the API pod to run (CI on `main` or `scripts/up.sh` option 2).
