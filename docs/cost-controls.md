# Cost controls: cheap + keep history

Destroy the **cluster** (EKS/GKE) to stop the big bills. **Pause** the managed database to keep incident history for ~$2/mo storage.

## Monthly cost when idle

| Resource | Running | Paused cluster + paused DB |
|----------|---------|----------------------------|
| EKS/GKE + NAT/nodes | ~$100+/mo | $0 |
| RDS / Cloud SQL compute | ~$12–15/mo | $0 |
| RDS / Cloud SQL storage (20GB) | included | ~$2/mo |

## Workflow

### Shut down (save money, keep history)

```bash
./scripts/pause-db.sh              # 1. stop RDS + Cloud SQL (keeps data)
# 2. destroy cluster only — terraform / console / CI
#    Do NOT terraform destroy database resources (prevent_destroy + deletion_protection)
```

### Bring back

```bash
./scripts/resume-db.sh             # 1. start RDS + Cloud SQL (~5–10 min)
cd terraform/aws/cluster && terraform apply   # 2. AWS
# or: cd terraform/gcp && terraform apply       # 2. GCP
# CI on main deploys the app image after the cluster exists
```

## Identifiers (env overrides)

| Cloud | Default | Env var |
|-------|---------|---------|
| AWS RDS | `jobradar-postgres` | `AWS_DB_IDENTIFIER` |
| GCP Cloud SQL | `debugpilot-postgres` | `GCP_SQL_INSTANCE` |

## AWS

- RDS auto-starts after **7 days** stopped.
- Config: `terraform/aws/cluster/rds.tf`

## GCP

- Cloud SQL: `terraform/gcp/cloudsql.tf`, `DATABASE_URL` in secrets.
- GKE zones: `node_locations = ["us-central1-a", "us-central1-b"]` avoids `-c` stockouts.
