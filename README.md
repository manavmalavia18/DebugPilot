# DebugPilot — AI DevOps Incident Debugger

Paste Kubernetes, Terraform, GitHub Actions, or Docker errors and get structured diagnosis, safe debug commands, and fixes grounded in real deployment incidents.

**Live URLs (when cluster is up):**
- App: https://jobradar.manavmalavia.org
- Grafana: https://jobradar-grafana.manavmalavia.org
- ArgoCD: https://jobradar-argocd.manavmalavia.org

> Rename the GitHub repo when ready — Helm/k8s resource names still use `jobradar` until you update ingress and charts.

---

## What it does

- Paste infra logs → AI analyzes root cause
- Keyword-matched playbooks from `app/incidents/` (Redis/K8s, ImagePullBackOff, Ingress 503, Terraform lock, etc.)
- Structured output: symptom, fix, debug commands, prevention
- Saves analysis history to SQLite
- Terminal-style ops console UI

---

## Local development

### Quick start

```bash
./start.sh
```

Opens the UI at http://localhost:5173 and API at http://localhost:8000. Requires `.env` with `ANTHROPIC_API_KEY`.

### Manual start

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend (hot reload)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### All-in-one (built UI served from API)

```bash
cd frontend && npm install && npm run build
cd .. && uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/analyze` | Analyze log text with Claude |
| GET | `/incidents` | List saved analyses |
| GET | `/incidents/{id}` | Get one saved analysis |
| GET | `/metrics` | Prometheus metrics |

---

## Infrastructure

Multi-cloud Kubernetes deployment with Terraform, Helm, ArgoCD, Prometheus, and GitHub Actions CI/CD.

**CI pipeline (on push/PR to main):**
- Python tests + frontend production build
- Ruff lint
- Helm chart lint + template render
- Docker multi-stage build (React UI + FastAPI) → push to ECR + GAR on main

**Deploy workflow (optional):**
- Re-sync secret or restart `jobradar-api` after image/key changes
- Patches deployment image when ArgoCD owns the app (no Helm conflict)

**Cluster lifecycle (AWS/GCP):**
- **Destroy** — workflow deletes Ingress resources first so external-dns removes Cloudflare CNAMEs before the cluster is torn down
- **Apply** — after apply, confirm DNS matches the new load balancer:
  ```bash
  kubectl get ingress jobradar-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{"\n"}'
  dig jobradar.manavmalavia.org CNAME +short
  ```
  See `app/incidents/external-dns-stale-cname.md` if they differ.

```
terraform/          AWS EKS + GCP GKE
charts/jobradar/    Helm chart (API deployment)
k8s/ingress/        TLS ingress for AWS + GCP
.github/workflows/  CI, deploy, terraform
```

### Kubernetes secret

`ANTHROPIC_API_KEY` must be in **GitHub repository secrets**. **Terraform AWS/GCP apply** creates `debugpilot-secrets` automatically.

Deploy workflow is optional (key rotation or forced restart). Manual create:

```bash
kubectl create secret generic debugpilot-secrets \
  --from-literal=ANTHROPIC_API_KEY=your-key
```

---

## Project structure

```
app/
├── main.py           # FastAPI + static UI
├── ai.py             # Claude integration
├── analyzer.py       # log analysis + incident matching
├── models.py
├── database.py
└── incidents/        # seed debugging playbooks
frontend/             # React + Tailwind UI
charts/jobradar/      # Helm chart
terraform/            # AWS + GCP IaC
tests/
```

---

## Author

Manav Malavia — [manavmalavia.org](https://manavmalavia.org)
