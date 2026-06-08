#!/bin/bash
# Stop managed databases to save compute cost while keeping incident history.
# Storage is still billed (~$2/mo per 20GB).
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_DB_ID="${AWS_DB_IDENTIFIER:-jobradar-postgres}"
GCP_PROJECT="${GCP_PROJECT_ID:-jobradar-497223}"
GCP_SQL="${GCP_SQL_INSTANCE:-debugpilot-postgres}"

pause_aws() {
  echo "⏸  Stopping AWS RDS: ${AWS_DB_ID} (${AWS_REGION})"
  if aws rds describe-db-instances \
    --db-instance-identifier "$AWS_DB_ID" \
    --region "$AWS_REGION" \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text 2>/dev/null | grep -q stopped; then
    echo "   Already stopped."
    return
  fi
  aws rds stop-db-instance \
    --db-instance-identifier "$AWS_DB_ID" \
    --region "$AWS_REGION" \
    --output text >/dev/null
  echo "   Stop requested (may take a few minutes)."
}

pause_gcp() {
  echo "⏸  Stopping Cloud SQL: ${GCP_SQL} (project ${GCP_PROJECT})"
  gcloud sql instances patch "$GCP_SQL" \
    --project="$GCP_PROJECT" \
    --activation-policy=NEVER \
    --quiet
  echo "   Cloud SQL stopped."
}

echo "💤 Pausing databases (cheap + keep history)"
echo ""
pause_aws || echo "   ⚠️  AWS RDS skip: ${AWS_DB_ID} not found"
echo ""
pause_gcp || echo "   ⚠️  Cloud SQL skip: ${GCP_SQL} not found"
echo ""
echo "✅ Done. Tear down the cluster separately (terraform/console) when ready."
