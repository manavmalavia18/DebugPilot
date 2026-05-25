# GCP cluster (isolated from AWS)

Mirrors the AWS EKS stack: GKE, Artifact Registry, ingress-nginx, external-dns (Cloudflare), cert-manager, kube-prometheus-stack, ArgoCD, and GCP-only ingress hostnames.

**Does not modify** `terraform/aws/` or `k8s/ingress/aws/` (AWS production DNS). GCP manifests live under `k8s/ingress/gcp/`.

## URLs (GCP only)

| Service | URL |
|---------|-----|
| API | https://jobradar-gcp.manavmalavia.org |
| Grafana | https://jobradar-gcp-grafana.manavmalavia.org |
| ArgoCD | https://jobradar-gcp-argocd.manavmalavia.org |

## Prerequisites

```bash
gcloud auth login
gcloud config set project jobradar-497223
gcloud auth application-default login

gcloud services enable container.googleapis.com artifactregistry.googleapis.com compute.googleapis.com

# Remote state bucket (once)
gcloud storage buckets create gs://jobradar-terraform-state-497223 \
  --project=jobradar-497223 --location=us-central1 --uniform-bucket-level-access
```

## Local apply

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your Cloudflare token

cd terraform/gcp
terraform init
terraform plan
terraform apply
```

## Verify

```bash
gcloud container clusters get-credentials jobradar \
  --region us-central1 --project jobradar-497223

kubectl get nodes
kubectl get pods -A
kubectl get ingress -A
```

Push an image to Artifact Registry before expecting the API pod to run (CI on `main` or `scripts/up.sh` option 2).
