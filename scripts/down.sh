#!/bin/bash
set -e

echo "🛑 DebugPilot teardown"
echo ""
echo "Which cloud do you want to tear down?"
echo "  [1] AWS only"
echo "  [2] GCP only"
echo "  [3] Both"
read -p "Enter choice (1/2/3): " choice

teardown_aws() {
  echo ""
  echo "🔍 Checking AWS cluster..."
  if eksctl get cluster --name debugpilot --region us-east-1 &>/dev/null; then
    echo "⎈ Uninstalling Helm on AWS..."
    kubectl config use-context Debugpilot@debugpilot.us-east-1.eksctl.io || true
    helm uninstall debugpilot || true

    echo "💀 Deleting EKS cluster..."
    eksctl delete cluster \
      --name debugpilot \
      --region us-east-1
    echo "✅ AWS torn down. Billing stopped."
  else
    echo "⚠️  No AWS cluster found — skipping."
  fi
}

teardown_gcp() {
  echo ""
  echo "🔍 Checking GCP cluster..."
  if gcloud container clusters describe debugpilot \
    --region=us-central1 &>/dev/null; then
    echo "⎈ Uninstalling Helm on GCP..."
    gcloud container clusters get-credentials debugpilot \
      --region=us-central1 --quiet
    helm uninstall debugpilot || true

    echo "☁️  Deleting GKE cluster..."
    gcloud container clusters delete debugpilot \
      --region=us-central1 \
      --quiet
    echo "✅ GCP torn down. Billing stopped."
  else
    echo "⚠️  No GCP cluster found — skipping."
  fi
}

case $choice in
  1) teardown_aws ;;
  2) teardown_gcp ;;
  3) teardown_aws; teardown_gcp ;;
  *) echo "Invalid choice. Exiting." ; exit 1 ;;
esac

echo ""
echo "✅ Done."