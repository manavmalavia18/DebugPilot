<h1 align="center">DebugPilot</h1>

<p align="center">
  <em>Paste a log. Get a diagnosis. Or don't paste at all — let your broken CI come to you.</em><br/>
  <sub>AI DevOps debugger · Claude + playbooks · multi-cloud · now with Kafka ears</sub>
</p>

<p align="center">
  <a href="https://debugpilot.manavmalavia.org">Live demo (AWS)</a> ·
  <a href="#-quick-start-local">Local setup</a> ·
  <a href="#-multi-cloud-infrastructure">Multi-cloud</a> ·
  <a href="#-dns-external-dns-and-failover-behavior">DNS</a>
</p>

<p align="center">
  <img src="docs/screenshots/analyze.png" alt="DebugPilot analyze screen — log input, AI diagnosis, and playbook match badge" width="720" />
</p>

---

## Table of contents

- [Overview](#-overview)
- [Why we added Kafka (the honest version)](#-why-we-added-kafka-the-honest-version)
- [Tech stack](#-tech-stack)
- [Multi-cloud infrastructure](#-multi-cloud-infrastructure)
- [Architecture](#-architecture)
- [How deployment works](#-how-deployment-works)
- [DNS, external-dns, and failover behavior](#-dns-external-dns-and-failover-behavior)
- [Quick start (local)](#-quick-start-local)
- [What an analysis returns](#-what-an-analysis-returns)
- [Project layout](#-project-layout)
- [Local development](#-local-development)
- [API reference](#-api-reference)
- [GitHub Actions](#-github-actions)
- [Operational runbooks](#-operational-runbooks)
- [Troubleshooting](#-troubleshooting)
- [Author](#-author)

---

## Overview

**DebugPilot** is a full-stack application for debugging infrastructure failures. Paste logs from **Kubernetes**, **Terraform**, **GitHub Actions**, or **Docker** and receive a structured diagnosis from **Claude**, enriched by markdown **playbooks** in `app/incidents/` (real incidents from multi-cloud deployments: Redis in K8s, ImagePullBackOff, Ingress 503, Terraform state lock, external-dns stale CNAME, and more).

The repository is both a **product** and a **platform showcase**: the same Helm chart and CI pipeline can run on **AWS EKS** or **GCP GKE**, with isolated DNS hostnames per cloud.

| Layer | Responsibility |
|--------|----------------|
| **Application** | FastAPI API, React ops UI, Postgres/SQLite history, semantic RAG playbooks, Redis analysis cache, Prometheus metrics |
| **Event pipeline** | GitHub webhooks → Kafka → consumer → auto-analyzed incidents in History |
| **Packaging** | Helm chart `charts/debugpilot`, multi-stage Docker image |
| **AWS** | EKS, ECR, VPC, ingress-nginx, external-dns, cert-manager, Argo CD, Strimzi Kafka |
| **GCP** | GKE, Artifact Registry, same platform components, separate hostnames, Strimzi Kafka |
| **Delivery** | GitHub Actions CI, GitOps sync, optional GitHub → Argo CD webhook |

---

## Why we added Kafka (the honest version)

We shipped a debugger that asks you to **copy-paste logs**. That works great in a demo. It works less great when you're the same person who just broke `main` at 11pm and you're alt-tabbing between GitHub Actions, `kubectl`, and a textarea.

So we asked a simple question: *what if the failure showed up in History before you went looking for it?*

### The pipeline

```
GitHub Actions fails
       │
       ▼
POST /webhooks/github  ──►  incidents.raw (Kafka)  ──►  debugpilot-consumer
       │                           │                         │
       │                           │                         ▼
       │                           └── incidents.dlq ◄──  Claude + playbooks
       │                              (if something breaks)      │
       ▼                                                         ▼
  202 accepted                                            History row appears
  (with github_actions badge)                             in the UI — no paste
```

**Why Kafka and not "just call analyze() in the webhook handler"?**

| Reason | What we were avoiding |
|--------|------------------------|
| **Decoupling** | GitHub expects a fast 202, not a 45s Claude round-trip |
| **Retries** | Consumer retries with backoff; poison messages land in `incidents.dlq` |
| **Backpressure** | Ten workflows fail at once? Queue absorbs the spike |
| **Future sources** | Alertmanager and Kubernetes events slot in without rewriting the API |
| **Dogfooding** | We run Strimzi on the same clusters we debug — ImagePullBackOff included |

### War stories we earned along the way

These are real, not resume fluff:

- **Strimzi 1.0** dropped `v1beta2` — we pinned the operator, bumped Kafka to **4.1.2**, and waited for CRDs like adults.
- **Incidents saved to the wrong user** — webhook actor `manavmalavia18` ≠ OAuth login `manavm18`. Fix: match by **GitHub numeric ID**, not username guessing.
- **Re-run ≠ new incident** — GitHub reuses the same `workflow_run.id` on "Re-run failed jobs". Fix: include `run_attempt` in the dedup key so attempt 2 is its own row.
- **The test workflow named `fail-on-purpose`** — yes, Claude correctly diagnosed our intentional `exit 1` as intentional. The pipeline works. You're welcome.

### Wire it up (GCP example)

1. **GitHub webhook** on your repo → `https://debugpilot-gcp.manavmalavia.org/webhooks/github`, event: **Workflow runs**
2. Secrets: `DEBUGPILOT_WEBHOOK_SECRET` (HMAC), `DEBUGPILOT_WEBHOOK_TOKEN` (PAT with `actions:read` for job logs)
3. Log into DebugPilot **once** with the GitHub account that triggers workflows — incidents map to your user by `github_id`
4. Run **Kafka Webhook Test** (manual dispatch) to prove the loop; watch History populate with a `github_actions` badge

Topics: `incidents.raw`, `incidents.dlq` · Bootstrap: `debugpilot-kafka-bootstrap.kafka.svc:9092`

---

## Tech stack

### Application layer

| Component | Technology | Role |
|-----------|------------|------|
| API | **Python 3.12**, **FastAPI** | REST endpoints, OpenAPI, static UI in production |
| AI | **Anthropic Claude** (`claude-sonnet-4-5`) | Log analysis with structured JSON output |
| Persistence | **SQLModel**, **Postgres** (RDS on EKS) or **SQLite** locally | Saved incident history |
| Cache | **Redis** (`redis:7-alpine` in Helm / compose) | Identical log + `source_hint` → cached JSON (default 7-day TTL); skips repeat Claude calls |
| Events | **Apache Kafka** via **Strimzi 1.0** | `incidents.raw` queue, `incidents.dlq` dead-letter; producer in API, consumer deployment in Helm |
| Webhooks | **GitHub `workflow_run`** HMAC | Failed Actions jobs → fetch logs via PAT → publish `IncidentEvent` |
| Metrics | **prometheus-fastapi-instrumentator** | `/metrics` for Prometheus scraping |
| UI | **React 19**, **Vite**, **Tailwind CSS 4** | Terminal-style ops console |
| HTTP client | **Axios** | Same-origin API in prod; `VITE_API_URL` for local dev |
| Testing | **pytest**, **ruff** | API tests and lint in CI |

### Container & build

| Component | Technology | Role |
|-----------|------------|------|
| Image | **Multi-stage Dockerfile** | Stage 1: `npm run build` → Stage 2: Python slim + `frontend/dist` |
| Registries | **AWS ECR**, **GCP Artifact Registry** | Same image tag pushed to both on `main` |
| Local | **docker-compose**, **start.sh** | Optional container or scripted dev environment |

### AWS platform (EKS)

| Component | Technology | Role |
|-----------|------------|------|
| Compute | **Amazon EKS 1.34**, managed node group (`t3.small`) | Kubernetes control plane and workers |
| Network | **VPC** (public subnets), **Internet Gateway** | Cluster networking |
| Registry | **ECR** `debugpilot-api` | Container images (bootstrap stack) |
| Ingress | **ingress-nginx** (NLB/ELB) | HTTP/S routing to services |
| DNS | **external-dns** + **Cloudflare** provider | Syncs Ingress hostnames → Cloudflare records |
| TLS | **cert-manager**, Let's Encrypt (`letsencrypt-prod`) | TLS secrets per hostname |
| GitOps | **Argo CD** | Syncs `charts/debugpilot` from GitHub `main` |
| Observability | **kube-prometheus-stack** | Prometheus + Grafana |
| IaC | **Terraform** (`terraform/aws/bootstrap`, `terraform/aws/cluster`) | Bootstrap vs cluster state split |

### GCP platform (GKE)

| Component | Technology | Role |
|-----------|------------|------|
| Compute | **Google GKE**, regional cluster | Parallel stack to AWS |
| Registry | **Artifact Registry** `debugpilot/debugpilot-api` | Same CI image tags as ECR |
| Network | **VPC** module (`terraform/gcp/modules/network`) | GKE networking |
| Ingress / DNS / TLS | Same pattern as AWS | **Different hostnames** (see below) |
| GitOps | **Argo CD** with `values-gcp.yaml` | Same chart, GCP-specific image registry path |
| IaC | **Terraform** (`terraform/gcp/foundation`, `terraform/gcp`) | Foundation (GAR, state) + cluster |

### CI/CD & GitOps

| Component | Technology | Role |
|-----------|------------|------|
| CI | **GitHub Actions** | Test, lint, Helm validate, buildx push amd64+arm64 |
| GitOps | **Argo CD** automated sync + self-heal | Cluster follows `charts/debugpilot` on `main` |
| Webhook | **GitHub → `/api/webhook`** | Near-instant refresh on push (vs ~3 min poll) |
| Deploy workflow | Manual dispatch | Optional rollout / image patch when not using Helm release |

---

## Multi-cloud infrastructure

DebugPilot is designed to run in **either** cloud without changing application code. Terraform and ingress manifests are **split by cloud** so AWS and GCP can coexist in the same Cloudflare zone without overwriting each other.

### Live endpoints

| Service | AWS (EKS) | GCP (GKE) |
|---------|-----------|-----------|
| **API** | https://debugpilot.manavmalavia.org | https://debugpilot-gcp.manavmalavia.org |
| **Grafana** | https://debugpilot-grafana.manavmalavia.org | https://debugpilot-gcp-grafana.manavmalavia.org |
| **Argo CD** | https://debugpilot-argocd.manavmalavia.org | https://debugpilot-gcp-argocd.manavmalavia.org |

### Isolation strategy

| Concern | AWS | GCP |
|---------|-----|-----|
| Terraform path | `terraform/aws/` | `terraform/gcp/` |
| Ingress manifests | `k8s/ingress/aws/` | `k8s/ingress/gcp/` |
| external-dns `txtOwnerId` | `debugpilot-aws` | `debugpilot-gcp` |
| DNS record prefix | `debugpilot`, `debugpilot-grafana`, … | `debugpilot-gcp`, `debugpilot-gcp-grafana`, … |
| Image registry | ECR | Artifact Registry |
| Helm values file | `charts/debugpilot/values.yaml` | `charts/debugpilot/values-gcp.yaml` |

CI pushes **one build** to **both** registries; each cluster’s Argo CD Application points at the registry and values file for that cloud.

### Terraform layout

```
terraform/
├── aws/
│   ├── bootstrap/          # ECR repository (long-lived)
│   └── cluster/            # VPC, EKS, Helm: ingress, external-dns, cert-manager,
│                           # monitoring, Argo CD, ingress YAML apply, Argo Application
└── gcp/
    ├── foundation/         # Artifact Registry, remote state bucket setup
    └── main.tf             # Network, GKE, same Helm platform pattern
```

### Typical bring-up order

**AWS**

1. `Terraform AWS Foundation` → ECR  
2. Merge to `main` → CI builds image and updates `values.yaml`  
3. `Terraform AWS Cluster` → **apply** → EKS + platform + Argo CD Application  
4. Verify DNS and `curl https://debugpilot.manavmalavia.org/health`

**GCP** (optional second region/cloud)

1. `Terraform GCP Foundation` → Artifact Registry + state  
2. `Terraform GCP Cluster` → **apply** → GKE + platform  
3. Verify https://debugpilot-gcp.manavmalavia.org  

You can run **one cloud or both**; destroying AWS does not remove GCP DNS records (separate `txtOwnerId` and hostnames).

### Greenfield after the rename (your flow)

1. Merge this branch, then create **new** remote state buckets matching `terraform/*/backend.tf` (`debugpilot-terraform-state-…`).
2. **AWS:** run `Terraform AWS Foundation` → apply (ECR `debugpilot-api`), then `Terraform AWS Cluster` → apply (new EKS cluster `debugpilot`).
3. **GCP:** create the GCS state bucket (see `terraform/gcp/README.md`), run `Terraform GCP Foundation` → apply, run CI on `main` (updates `values-gcp.yaml` when GAR exists), then `Terraform GCP Cluster` → apply.
4. Push to `main` so CI builds and tags `debugpilot-api` in both registries.
5. Delete stale Cloudflare `jobradar*` records. Add GitHub repo webhooks once per Argo URL (see [Argo CD GitHub webhook](#argocd-github-webhook)).

---

## Architecture

### Application flow

```mermaid
flowchart LR
  subgraph client [Client]
    UI[React UI]
  end
  subgraph api [FastAPI]
    Routes[REST + static dist]
    Analyzer[analyzer.py]
    Playbooks[incidents/*.md]
    Cache[(Redis)]
    AI[ai.py → Claude]
    DB[(Postgres / SQLite)]
  end
  UI --> Routes
  Routes --> Analyzer
  Analyzer --> Playbooks
  Analyzer --> Cache
  Cache -->|miss| AI
  AI --> Analyzer
  Analyzer -->|save optional| DB
```

### Event-driven ingestion (GitHub Actions → History)

```mermaid
sequenceDiagram
  participant GH as GitHub Actions
  participant WH as POST /webhooks/github
  participant K as Kafka incidents.raw
  participant C as debugpilot-consumer
  participant AI as Claude + playbooks
  participant H as History UI

  GH->>WH: workflow_run completed (failure)
  WH->>WH: verify HMAC, fetch job logs
  WH->>K: publish IncidentEvent
  WH-->>GH: 202 accepted
  K->>C: consume message
  C->>C: resolve user by github_id
  C->>AI: analyze_log()
  AI->>H: saved incident + github_actions badge
```

### Multi-cloud traffic (simplified)

```mermaid
flowchart TB
  subgraph users [Users]
    U[Browser]
  end
  subgraph dns [Cloudflare DNS]
    AWSrec[debugpilot.* records]
    GCPrec[debugpilot-gcp.* records]
  end
  subgraph aws [AWS EKS]
    AWSlb[NLB / ELB]
    AWSing[ingress-nginx]
    AWSpod[DebugPilot pod]
  end
  subgraph gcp [GCP GKE]
    GCPlb[Cloud LB]
    GCPing[ingress-nginx]
    GCPpod[DebugPilot pod]
  end
  U --> AWSrec --> AWSlb --> AWSing --> AWSpod
  U --> GCPrec --> GCPlb --> GCPing --> GCPpod
```

---

## How deployment works

```
┌─────────────┐     push to main      ┌──────────────┐
│  Developer  │ ───────────────────►  │  GitHub CI   │
└─────────────┘                       │  test, build │
                                      │  push ECR+GAR│
                                      │  commit tag  │
                                      └──────┬───────┘
                                             │
                    webhook (optional)       │  values.yaml
                                             ▼
                                      ┌──────────────┐
                                      │   Argo CD    │
                                      │  helm sync   │
                                      └──────┬───────┘
                                             ▼
                                      ┌──────────────┐
                                      │ debugpilot-api │
                                      │ debugpilot-consumer │
                                      │ redis · kafka  │
                                      └──────────────┘
```

| Phase | Tool | What happens |
|-------|------|----------------|
| **Build** | GitHub Actions CI | pytest, ruff, frontend build, Docker buildx, push to ECR + GAR |
| **Config git** | CI bot commit | Updates `charts/debugpilot/values.yaml` image digest on `main` |
| **Sync** | Argo CD | Renders Helm chart → applies API, **Redis**, Service, HPA, ServiceMonitor |
| **Platform** | Terraform (manual) | Cluster, ingress controller, external-dns, cert-manager, Argo CD install |
| **Edge** | Cloudflare + external-dns | Hostname → load balancer IP/CNAME per cloud |

**Day-to-day:** push application changes to `main` — CI and Argo CD handle the rest. Re-run Terraform only for infrastructure changes.

---

## DNS, external-dns, and failover behavior

DNS is the **edge** of the system: users hit Cloudflare hostnames that must point at the **current** cloud load balancer. This project uses **external-dns** in each cluster to reconcile Ingress hosts into Cloudflare.

### How records are created

1. **ingress-nginx** provisions a cloud load balancer (AWS ELB/NLB or GCP forwarding rule).
2. **Ingress** resources in `k8s/ingress/aws/` or `k8s/ingress/gcp/` annotate desired hostnames:

   ```yaml
   external-dns.alpha.kubernetes.io/hostname: debugpilot.manavmalavia.org
   external-dns.alpha.kubernetes.io/cloudflare-proxied: "false"
   ```

3. **external-dns** (Helm release in cluster) watches Ingress objects and creates/updates **CNAME** (AWS) or **A** (GCP) records in Cloudflare.
4. **TXT records** (`cname-debugpilot...`) record ownership (`txtOwnerId`: `debugpilot-aws` vs `debugpilot-gcp`) so each cluster only manages its own records.

### AWS vs GCP record shapes

| Cloud | Typical record type | Points to |
|-------|---------------------|-----------|
| **AWS** | CNAME | `*.elb.amazonaws.com` hostname from Ingress status |
| **GCP** | A | Static IP or LB IP for the GKE ingress |

Always verify with:

```bash
# AWS — compare Ingress vs DNS
kubectl get ingress debugpilot-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'
dig debugpilot.manavmalavia.org CNAME +short

# GCP
kubectl get ingress debugpilot-ingress -n default
dig debugpilot-gcp.manavmalavia.org +short
```

### Failover and recreation scenarios

“Failover” here means **recovering correct DNS after infrastructure changes** — not automatic multi-cloud active-active failover between AWS and GCP (those are **parallel stacks**, not hot standby).

| Scenario | What goes wrong | What to do |
|----------|-----------------|------------|
| **EKS recreated** | New ELB hostname; Cloudflare still has **old** CNAME | Run destroy workflow (deletes Ingress first, waits for external-dns), or delete stale CNAMEs and restart external-dns |
| **external-dns says “up to date” but DNS is wrong** | Records exist without matching TXT ownership from current cluster | Delete `debugpilot` / `debugpilot-grafana` / `debugpilot-argocd` CNAMEs + `cname-debugpilot*` TXT; restart external-dns deployment |
| **503 / NXDOMAIN** | DNS not pointing at live LB, or cert still issuing | Fix DNS first; wait for cert-manager; confirm pods Ready |
| **Destroy AWS, keep GCP** | AWS records should disappear; GCP `debugpilot-gcp*` unaffected | Confirm destroy workflow ran ingress cleanup; manually remove orphaned AWS records if needed |
| **Both clouds up** | No conflict if hostnames stay prefixed (`debugpilot` vs `debugpilot-gcp`) | Do not reuse the same hostname across clusters |

### Destroy-time DNS cleanup (AWS / GCP)

**Terraform AWS Cluster → destroy** and **Terraform GCP Cluster → destroy** run:

1. `kubectl delete -f k8s/ingress/{aws|gcp}/...` (app, Grafana, Argo CD ingresses)
2. Wait ~90s for external-dns to **delete** Cloudflare records
3. Detach the managed database (and VPC peering on GCP) from Terraform state — **data is kept**
4. `terraform destroy` (cluster, Helm, IAM, etc.)
5. **Stop** RDS / Cloud SQL to cut compute billing (~\$2/mo storage remains)

On **apply**, CI starts a stopped database and re-imports retained resources before recreating the cluster.

This prevents **stale CNAMEs** pointing at deleted load balancers after cluster teardown.

### Manual DNS recovery checklist

```bash
# 1. Confirm load balancer exists
kubectl get ingress -A

# 2. Check external-dns
kubectl logs -n external-dns deployment/external-dns --tail=50

# 3. Compare DNS
dig debugpilot.manavmalavia.org CNAME +short
dig debugpilot-gcp.manavmalavia.org +short

# 4. If stale — delete wrong records in Cloudflare, then:
kubectl rollout restart deployment/external-dns -n external-dns
```

Full playbook: [`app/incidents/external-dns-stale-cname.md`](app/incidents/external-dns-stale-cname.md)

---

## Quick start (local)

Run the full product on your laptop — **no Kubernetes required**.

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Node.js | 22+ |
| Anthropic API key | [console.anthropic.com](https://console.anthropic.com/) |
| Redis (optional) | 7+ — caches repeat analyses; omit `REDIS_URL` to call Claude every time |

### Steps

```bash
git clone https://github.com/manavmalavia18/JobTracker.git
cd JobTracker
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY
# Optional: REDIS_URL=redis://localhost:6379/0 (run Redis locally or use docker compose)

chmod +x start.sh
./start.sh
```

**With Redis (recommended for dev):** API + Redis in one command:

```bash
docker compose up --build
```

Uses `REDIS_URL=redis://redis:6379/0` from compose. UI still via `./start.sh` or http://localhost:8000 after building the frontend.

- UI: http://localhost:5173  
- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

Try a **sample log** in the UI, or:

```bash
curl http://localhost:8000/health
```

Stop with `Ctrl+C` in the terminal running `start.sh`.

---

## What an analysis returns

- **Category** — kubernetes, terraform, github_actions, docker, app, unknown  
- **Symptom**, **what failed**, **root cause**, **confidence**  
- **Debug commands** — prefer read-only; destructive steps listed in **warnings**  
- **Likely fix**, **prevention** tips  
- Optional **save** to history (Postgres in cluster, SQLite locally)

**Log uploads:** On AWS, files go to S3 (`debugpilot-log-uploads-<account_id>` from Terraform bootstrap). EKS node IAM allows `PutObject`/`GetObject`. Helm sets `UPLOADS_S3_BUCKET` in `values.yaml`. Locally, set `UPLOADS_LOCAL_DIR` when S3 is unset.

**Caching:** If `REDIS_URL` is set, the same log text and `source_hint` returns the cached analysis (no Claude tokens). `POST /analyze` includes `cached` (boolean) and `duration_ms` so the UI and metrics can show Redis vs Claude. Prometheus counters: `debugpilot_analysis_cache_hits_total`, `debugpilot_analysis_cache_misses_total`. Cache key includes model and `ANALYSIS_CACHE_VERSION` — bump that env var when changing prompts or playbooks. Default TTL: 7 days (`REDIS_CACHE_TTL_SECONDS`).

Playbooks under `app/incidents/` are retrieved with **semantic RAG** (fastembed + cosine similarity); only matches ≥70% (`RETRIEVAL_CONTEXT_MIN_SCORE`) are sent to Claude. Keyword fallback applies when embeddings are unavailable.

---

## Project layout

```
├── app/
│   ├── webhooks/github.py  # workflow_run → Kafka
│   ├── consumer.py         # incidents.raw → analyze → DB
│   └── events/             # schema, producer, user resolution
├── frontend/               # React UI (History badges per ingestion source)
├── charts/debugpilot/      # Helm — api, consumer, redis (values.yaml + values-gcp.yaml)
├── k8s/kafka/              # Strimzi Kafka + topic CRs
├── k8s/ingress/aws|gcp/    # Per-cloud Ingress + TLS
├── terraform/aws|gcp/      # Multi-cloud IaC + Strimzi operator
├── .github/workflows/      # CI, Deploy, Terraform, kafka-webhook-test
├── tests/
├── Dockerfile
└── start.sh
```

---

## Local development

| Mode | Command |
|------|---------|
| All-in-one script | `./start.sh` |
| API + Redis (compose) | `docker compose up --build` |
| API only | `uvicorn app.main:app --reload --port 8000` |
| UI dev server | `cd frontend && npm run dev` |
| Prod-like (UI from API) | `cd frontend && npm run build && uvicorn app.main:app --port 8000` |
| Tests | `pytest tests/ -v` |
| RAG eval (semantic) | `EVAL_INTEGRATION=1 pytest tests/test_eval_retrieval.py -v` |

### Redis (local & Kubernetes)

| Setting | Default | Purpose |
|---------|---------|---------|
| `REDIS_URL` | unset locally | e.g. `redis://localhost:6379/0` or `redis://redis:6379/0` in cluster |
| `REDIS_CACHE_TTL_SECONDS` | `604800` (7 days) | How long cached analyses live |
| `ANALYSIS_CACHE_VERSION` | `1` | Bump to invalidate cache after prompt/playbook changes |

In **Kubernetes**, Helm deploys a `redis` Service (`charts/debugpilot/templates/redis.yaml`) when `redis.enabled: true`. The API uses cluster DNS `redis://redis:6379/0` — not `localhost` (see playbook `redis-localhost-k8s.md` for misconfigured *other* apps).

Frontend dev uses `frontend/.env.development` (`VITE_API_URL=http://localhost:8000`). Production build uses **same-origin** `/analyze` (no localhost in the bundle).

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/auth/config` | Whether GitHub login is required |
| `GET` | `/auth/me` | Current user (session cookie) |
| `GET` | `/auth/github/login` | Start GitHub OAuth |
| `POST` | `/auth/logout` | Clear session |
| `POST` | `/uploads` | Upload `.log` / `.txt` (max 512 KB); stores in S3 (AWS) or local dir; returns `log_text` + `upload_id` |
| `POST` | `/analyze` | Analyze log text or `upload_id`; response adds `cached`, `duration_ms` (auth if OAuth configured) |
| `GET` | `/incidents` | List saved analyses |
| `GET` | `/incidents/{id}` | Get one analysis |
| `GET` | `/metrics` | Prometheus metrics |
| `POST` | `/webhooks/github` | GitHub `workflow_run` failures → Kafka (HMAC `X-Hub-Signature-256`) |
| `GET` | `/docs` | OpenAPI |

---

## GitHub Actions

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** | Push / PR → `main`, or **Run workflow** | Test, ruff, Helm lint, build & push image, update `values.yaml` / `values-gcp.yaml` |
| **Deploy** | Manual | Optional rollout / image patch (Argo CD–managed clusters) |
| **Terraform AWS Foundation** | Manual | ECR |
| **Terraform AWS Cluster** | Manual | plan / apply / destroy EKS |
| **Terraform GCP Foundation** | Manual | Artifact Registry + state |
| **Terraform GCP Cluster** | Manual | plan / apply / destroy GKE |
| **Kafka Webhook Test** | Manual dispatch | Intentionally fails to validate webhook → Kafka → History (remove after validation) |

### Repository secrets (Terraform / CI)

| Secret | Used by |
|--------|---------|
| `ARGOCD_GITHUB_WEBHOOK_SECRET` | Terraform AWS/GCP cluster apply — pins `webhook.github.secret` in Argo CD Helm so cluster rebuilds match the GitHub webhook |
| `ANTHROPIC_API_KEY` | Terraform cluster apply (K8s secret), local `.env` |
| `DEBUGPILOT_OAUTH_CLIENT_ID_AWS` | OAuth Client ID for AWS (`debugpilot.manavmalavia.org`) |
| `DEBUGPILOT_OAUTH_CLIENT_SECRET_AWS` | OAuth client secret for AWS |
| `DEBUGPILOT_OAUTH_CLIENT_ID_GCP` | OAuth Client ID for GCP (`debugpilot-gcp.manavmalavia.org`) |
| `DEBUGPILOT_OAUTH_CLIENT_SECRET_GCP` | OAuth client secret for GCP |
| `JWT_SECRET` | Session cookie signing — same value on both clouds (`openssl rand -hex 32`) |
| `DEBUGPILOT_WEBHOOK_SECRET` | HMAC secret for `POST /webhooks/github` (cannot use `GITHUB_` prefix) |
| `DEBUGPILOT_WEBHOOK_TOKEN` | GitHub PAT with `actions:read` — API fetches failed job logs |

### GitHub sign-in (abuse protection)

When `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are set on the API (via `debugpilot-secrets`), `/analyze` and `/incidents` require a GitHub login. Sessions use an httpOnly cookie (7 days).

| Cloud | OAuth callback URL |
|-------|-------------------|
| **AWS** | `https://debugpilot.manavmalavia.org/auth/github/callback` |
| **GCP** | `https://debugpilot-gcp.manavmalavia.org/auth/github/callback` |

Repo secret names cannot start with `GITHUB` (reserved). Use `DEBUGPILOT_OAUTH_*` above.

1. Create a [GitHub OAuth App](https://github.com/settings/developers) per hostname (**OAuth App**, device flow off).
2. Add the `DEBUGPILOT_OAUTH_*` secrets and `JWT_SECRET`, then run **Terraform GCP/AWS Cluster → apply**.
3. Or patch the cluster secret manually:

   ```bash
   kubectl -n default patch secret debugpilot-secrets --type merge -p '{
     "stringData": {
       "GITHUB_CLIENT_ID": "your-client-id",
       "GITHUB_CLIENT_SECRET": "your-client-secret",
       "JWT_SECRET": "your-openssl-hex-secret"
     }
   }'
   ```

4. Redeploy / restart API pods. `values-gcp.yaml` sets `publicBaseUrl` and `authCookieSecure: true`.

Local dev without OAuth: leave `GITHUB_CLIENT_ID` unset — API uses a built-in `dev` user (`AUTH_DISABLED` behavior). Set `AUTH_DISABLED=1` to force that mode even if OAuth env vars exist.

### Argo CD GitHub webhook

Terraform sets `configs.secret.githubSecret` when `ARGOCD_GITHUB_WEBHOOK_SECRET` (or `TF_VAR_argocd_github_webhook_secret` locally) is set. Use the **same** value you configured in GitHub.

| Cloud | Webhook payload URL |
|-------|---------------------|
| GCP | `https://debugpilot-gcp-argocd.manavmalavia.org/api/webhook` |
| AWS | `https://debugpilot-argocd.manavmalavia.org/api/webhook` |

**One-time per URL:** create the webhook in GitHub (push events, shared secret). After cluster destroy/recreate, run Terraform apply only — no `kubectl patch` if the secret and URL are unchanged.

Local apply:

```bash
export TF_VAR_argocd_github_webhook_secret='your-existing-secret'
```

---

## Operational runbooks

Markdown guides in `app/incidents/`:

| Playbook | Topic |
|----------|--------|
| `external-dns-stale-cname.md` | DNS drift after cluster recreate |
| `ingress-503.md` | Ingress up, backend unhealthy |
| `image-pull-backoff.md` | ECR/GAR image mismatch |
| `cert-manager-tls.md` | TLS / ACME issues |
| `terraform-state-lock.md` | State lock during apply |
| `redis-localhost-k8s.md` | Redis URL in K8s |
| `github-actions-kubeconfig.md` | CI cluster access |

---

## Troubleshooting

| Symptom | Likely cause | Pointer |
|---------|----------------|---------|
| `Could not resolve host` | Stale Cloudflare CNAME | [DNS section](#-dns-external-dns-and-failover-behavior) |
| **503** from nginx | No ready endpoints | `kubectl get pods -l app=debugpilot-api` |
| Argo CD **OutOfSync** | Git vs cluster drift | Sync in UI; check repo path |
| CORS / localhost from live site | Old frontend bundle | Use current `main` (same-origin API) |
| GCP works, AWS doesn’t | Separate hostnames / records | Verify `debugpilot` vs `debugpilot-gcp` records independently |
| Every analyze hits Claude | Redis missing or wrong URL | `kubectl get pods -l app=redis`; confirm `REDIS_URL=redis://redis:6379/0` on API deployment |
| Webhook 200 ignored | Run succeeded or wrong event type | Only `workflow_run` + `conclusion=failure` are queued |
| Incident in DB but not in UI | Wrong GitHub user mapping | Log in with the account that triggered the workflow |
| Re-run didn't create row | Same `run_id` deduped | Needs `run_attempt` in external_id (see [Why Kafka](#-why-we-added-kafka-the-honest-version)) |
| Consumer silent | Kafka not ready or env missing | `kubectl -n kafka get kafka`; check `KAFKA_BOOTSTRAP_SERVERS` on API + consumer |

---

## Author

**Manav Malavia** — [manavmalavia.org](https://manavmalavia.org) · [GitHub](https://github.com/manavmalavia18/JobTracker)

---

<p align="center">
  <sub>FastAPI · React · Claude · Kafka · Strimzi · Terraform · AWS EKS · GCP GKE · Helm · Argo CD</sub><br/>
  <sub><em>Built by someone who got tired of pasting their own CI logs.</em></sub>
</p>
