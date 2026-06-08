#!/bin/bash
# Start managed databases before bringing clusters back up.
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_DB_ID="${AWS_DB_IDENTIFIER:-jobradar-postgres}"
GCP_PROJECT="${GCP_PROJECT_ID:-jobradar-497223}"
GCP_SQL="${GCP_SQL_INSTANCE:-debugpilot-postgres}"

resume_aws() {
  echo "▶️  Starting AWS RDS: ${AWS_DB_ID} (${AWS_REGION})"
  aws rds start-db-instance \
    --db-instance-identifier "$AWS_DB_ID" \
    --region "$AWS_REGION" \
    --output text >/dev/null 2>&1 || true
  echo "   Waiting for RDS..."
  aws rds wait db-instance-available \
    --db-instance-identifier "$AWS_DB_ID" \
    --region "$AWS_REGION"
  echo "   RDS available."
}

resume_gcp() {
  echo "▶️  Starting Cloud SQL: ${GCP_SQL} (project ${GCP_PROJECT})"
  gcloud sql instances patch "$GCP_SQL" \
    --project="$GCP_PROJECT" \
    --activation-policy=ALWAYS \
    --quiet
  echo "   Waiting for Cloud SQL..."
  until [ "$(gcloud sql instances describe "$GCP_SQL" \
    --project="$GCP_PROJECT" \
    --format='value(state)')" = "RUNNABLE" ]; do
    sleep 10
  done
  echo "   Cloud SQL runnable."
}

echo "🔄 Resuming databases"
echo ""
resume_aws || echo "   ⚠️  AWS RDS skip: ${AWS_DB_ID} not found"
echo ""
resume_gcp || echo "   ⚠️  Cloud SQL skip: ${GCP_SQL} not found"
echo ""
echo "✅ Databases up. Run terraform apply / CI deploy for the cluster next."
