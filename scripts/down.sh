#!/bin/bash
set -e

echo "🛑 Tearing down JobRadar infrastructure..."

echo "⎈ Uninstalling Helm release..."
helm uninstall jobradar || true

echo "💀 Deleting EKS cluster..."
eksctl delete cluster \
  --name jobradar \
  --region us-east-1

echo "✅ Everything torn down. No more charges."