# JobRadar — AI-Powered Job Intelligence Platform

> A production-grade DevOps project demonstrating multi-cloud Kubernetes deployment, GitOps, Infrastructure as Code, and AI-powered job matching.

**Live URLs:**
- API: https://jobradar.manavmalavia.org
- Grafana: https://jobradar-grafana.manavmalavia.org
- ArgoCD: https://jobradar-argocd.manavmalavia.org

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        GitHub                                │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐  │
│  │  CI/CD   │    │ Terraform│    │     Helm Charts       │  │
│  │ Pipeline │    │   IaC    │    │  charts/jobradar/     │  │
│  └────┬─────┘    └────┬─────┘    └──────────┬───────────┘  │
└───────┼───────────────┼───────────────────── ┼─────────────┘
        │               │                      │
        ▼               ▼                      ▼
   ECR / GCR       AWS EKS                  ArgoCD
   (images)        GCP GKE               (GitOps sync)
                      │
              ┌───────┴────────┐
              │   Kubernetes   │
              │                │
         ┌────┴────┐    ┌──────┴──────┐
         │ default │    │  monitoring │
         │ jobradar│    │ Prometheus  │
         │   api   │    │  Grafana    │
         │  redis  │    │             │
         └────┬────┘    └─────────────┘
              │
      Nginx Ingress + TLS
              │
     manavmalavia.org (Cloudflare)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Application** | Python, FastAPI, SQLModel, SQLite |
| **Caching** | Redis |
| **Background Jobs** | Celery, Flower |
| **AI** | Anthropic Claude API |
| **Monitoring** | Prometheus, Grafana |
| **Container** | Docker (multi-platform amd64 + arm64) |
| **Orchestration** | Kubernetes, Helm |
| **GitOps** | ArgoCD |
| **IaC** | Terraform |
| **CI/CD** | GitHub Actions |
| **Registry** | AWS ECR, GCP Artifact Registry |
| **Cloud (Primary)** | AWS EKS |
| **Cloud (Failover)** | GCP GKE |
| **Ingress** | Nginx Ingress Controller |
| **TLS** | cert-manager + Let's Encrypt |
| **DNS / CDN** | Cloudflare |

---

## Features

- **AI Job Matching** — paste your CV, Claude scores every job against it with a match percentage, reason, and missing skills
- **Cover Letter Generation** — one-click AI-generated cover letters tailored to each job
- **Async Job Fetching** — Celery background tasks fetch jobs from Remotive API without blocking the user
- **Redis Caching** — TTL-based caching on job searches to reduce API calls
- **Real-time Monitoring** — Prometheus scrapes metrics every 15 seconds, Grafana dashboards show request rate, latency, and pod resource usage
- **Zero Downtime Deploys** — Kubernetes rolling updates, HPA scales pods based on CPU

---

## CI/CD Pipeline

Every pull request triggers:

```
test → lint → (on merge) build image → push to ECR + GCR
                                    → CI Bot updates values.yaml with commit SHA
                                    → ArgoCD detects change → deploys automatically
```

### Workflows

| Workflow | Trigger | Action |
|----------|---------|--------|
| **CI** | Every PR + push to main | Test, lint, build, push image |
| **Terraform AWS** | Manual | Plan / Apply / Destroy AWS infrastructure |
| **Terraform GCP** | Manual | Plan / Apply / Destroy GCP infrastructure |
| **Deploy** | Manual | Force ArgoCD sync |

---

## Infrastructure as Code

Infrastructure is split into two layers:

```
terraform/
  aws/
    bootstrap/   ← ECR repository (always on, never destroyed)
    cluster/     ← VPC, EKS, Prometheus, Grafana, ArgoCD, Ingress
  gcp/
    cluster/     ← VPC Network, GKE, Artifact Registry
```

### Spinning up AWS infrastructure

```bash
# GitHub Actions → Terraform AWS → Run workflow → apply
# Takes ~8 minutes, creates:
#   VPC + 2 public subnets across 2 AZs
#   EKS cluster (3x t3.small nodes)
#   Prometheus + Grafana (kube-prometheus-stack)
#   ArgoCD (auto-deploys app from Git)
#   Nginx Ingress + cert-manager (HTTPS)
```

### Tearing down

```bash
# GitHub Actions → Terraform AWS → Run workflow → destroy
# All resources deleted, billing stops
# ECR repo preserved (bootstrap layer)
```

---

## GitOps Flow

ArgoCD watches `charts/jobradar/values.yaml` on the `main` branch. The CI pipeline updates the image tag in `values.yaml` after every build:

```
PR merged to main
      ↓
CI builds Docker image → pushes to ECR with commit SHA tag
CI Bot updates values.yaml: image: .../jobradar-api:<sha>
CI Bot commits to main
      ↓
ArgoCD detects values.yaml changed (polls every 3 min)
      ↓
helm upgrade → rolling update → zero downtime
```

---

## Kubernetes Resources

```
default namespace:
  Deployment: jobradar-api (FastAPI + Celery)
  Deployment: redis
  Service: jobradar-api (ClusterIP)
  HPA: jobradar-api (min:1, max:5, cpu:50%)
  ServiceMonitor: jobradar-api (Prometheus scraping)
  Ingress: jobradar-ingress (TLS)

monitoring namespace:
  Prometheus (kube-prometheus-stack)
  Grafana
  AlertManager
  node-exporter (DaemonSet)
  kube-state-metrics

argocd namespace:
  ArgoCD server + components
  Application: jobradar

ingress-nginx namespace:
  Nginx Ingress Controller (LoadBalancer)

cert-manager namespace:
  cert-manager
  ClusterIssuer: letsencrypt-prod
```

---

## Local Development

### Prerequisites

- Python 3.12+
- Docker
- Redis

### Setup

```bash
git clone https://github.com/manavmalavia18/JobTracker
cd JobTracker

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# copy and fill in your keys
cp .env.example .env

# start redis
docker run -d -p 6379:6379 redis:alpine

# start the API
uvicorn app.main:app --reload

# start celery worker (separate terminal)
celery -A app.celery_app worker --loglevel=info

# start flower dashboard (separate terminal)
celery -A app.celery_app flower --port=5555
```

API docs available at: `http://localhost:8000/docs`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/jobs` | List jobs (with optional title/location filter) |
| POST | `/jobs/fetch` | Fetch jobs from Remotive API |
| POST | `/jobs/fetch-async` | Fetch jobs as background task |
| GET | `/tasks/{task_id}` | Check background task status |
| POST | `/match` | AI-match jobs against CV text |
| POST | `/cover-letter/{job_id}` | Generate AI cover letter |
| GET | `/metrics` | Prometheus metrics |
| GET | `/health-stats` | Uptime + job count |

---

## Monitoring

Prometheus scrapes `/metrics` from the jobradar-api pod every 15 seconds.

Grafana dashboards available at `https://jobradar-grafana.manavmalavia.org`:
- Kubernetes / Compute Resources / Cluster
- Kubernetes / Compute Resources / Pod
- JobRadar API (request rate, latency, error rate)

Default credentials: `admin / jobradar123`

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for job matching and cover letters |
| `REDIS_HOST` | Redis hostname (default: localhost) |
| `REDIS_PORT` | Redis port (default: 6379) |

---

## Project Structure

```
JobTracker/
├── app/
│   ├── main.py           # FastAPI app, routes, middleware
│   ├── models.py         # SQLModel Job model
│   ├── database.py       # SQLite + SQLModel engine
│   ├── services.py       # Remotive API fetcher
│   ├── cache.py          # Redis TTL caching
│   ├── ai.py             # Claude API: score_job, generate_cover_letter
│   ├── celery_app.py     # Celery configuration
│   ├── tasks.py          # Background tasks
│   └── logging_config.py
├── charts/jobradar/      # Helm chart
│   ├── Chart.yaml
│   ├── values.yaml       # Image tag updated by CI Bot
│   └── templates/
│       ├── api-deployment.yaml
│       ├── redis-deployment.yaml
│       ├── hpa.yaml
│       └── servicemonitor.yaml
├── terraform/
│   ├── aws/
│   │   ├── bootstrap/    # ECR (always on)
│   │   └── cluster/      # EKS + full stack
│   └── gcp/              # GKE + Artifact Registry
├── k8s/ingress/          # Ingress rules + ClusterIssuer
├── .github/workflows/
│   ├── ci.yaml           # Test + build + push
│   ├── deploy.yaml       # Manual ArgoCD sync
│   ├── terraform-aws.yml # Manual AWS infra
│   └── terraform-gcp.yml # Manual GCP infra
├── tests/
│   └── test_api.py
├── Dockerfile
├── docker-compose.yaml
└── requirements.txt
```

---

## Key Design Decisions

**Continuous Delivery over Continuous Deployment** — images are built and pushed automatically, but cluster apply requires a manual trigger. This controls costs since the cluster is spun up on demand.

**Bootstrap / Cluster split in Terraform** — ECR lives in a separate `bootstrap` folder that is never destroyed. The cluster can be torn down and recreated freely without losing the image registry.

**GitOps with ArgoCD** — the cluster state is always derived from Git. If someone manually changes a resource, ArgoCD self-heals it back to match the Git state. Every deployment is a Git commit with a full audit trail.

**ClusterIP services with Nginx Ingress** — using one LoadBalancer (Nginx Ingress) instead of a LoadBalancer per service saves ~$36/month and prevents leftover ELBs blocking Terraform destroy.

**Multi-platform Docker builds** — the Mac M2 is ARM64, AWS EC2 is AMD64. Using `docker buildx` with `--platform linux/amd64,linux/arm64` ensures the image runs on both.

---

## Author

Manav Malavia — [manavmalavia.org](https://manavmalavia.org) — [GitHub](https://github.com/manavmalavia18)
