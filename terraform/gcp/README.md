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
# Optional: argocd_github_webhook_secret (same value as GitHub repo webhook + ARGOCD_GITHUB_WEBHOOK_SECRET in Actions)

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

## Cloud SQL (incident history)

GCP now provisions **Cloud SQL Postgres** (private IP) and sets `DATABASE_URL` in `debugpilot-secrets`, matching AWS RDS.

**One-time (project owner / Console):** enable Cloud SQL APIs before the first cluster apply. The GitHub Actions service account cannot enable project services.

```bash
gcloud services enable sqladmin.googleapis.com servicenetworking.googleapis.com
```

Or: GCP Console → **APIs & Services** → **Library** → enable **Cloud SQL Admin API** and **Service Networking API**.

## Cost controls

See [docs/cost-controls.md](../../docs/cost-controls.md).

**One-step shutdown:** GitHub Actions → **Terraform GCP Cluster** → `destroy` — tears down GKE, then stops Cloud SQL (history kept, ~$2/mo).

**One-step bring-back:** same workflow → `apply` — starts Cloud SQL, recreates cluster, wires `DATABASE_URL`.

If GKE fails with `GCE_STOCKOUT` in `us-central1-c`, use `node_locations` in `terraform.tfvars` (see `terraform.tfvars.example`).
