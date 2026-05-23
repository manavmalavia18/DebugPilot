#!/bin/bash
set -e

echo "🚀 Starting JobRadar infrastructure..."

echo "📦 Creating EKS cluster..."
eksctl create cluster \
  --name jobradar \
  --region us-east-1 \
  --nodegroup-name workers \
  --node-type t2.micro \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed

echo "🐳 Logging into ECR..."
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS \
  --password-stdin 565273632019.dkr.ecr.us-east-1.amazonaws.com

echo "🔨 Building and pushing Docker image..."
docker build -t jobradar-api:latest .
docker tag jobradar-api:latest \
  565273632019.dkr.ecr.us-east-1.amazonaws.com/jobradar-api:latest
docker push \
  565273632019.dkr.ecr.us-east-1.amazonaws.com/jobradar-api:latest

echo "⎈ Deploying with Helm..."
helm upgrade --install jobradar ./charts/jobradar \
  --set api.image=565273632019.dkr.ecr.us-east-1.amazonaws.com/jobradar-api:latest \
  --set api.imagePullPolicy=Always

echo "✅ JobRadar is live!"
kubectl get services