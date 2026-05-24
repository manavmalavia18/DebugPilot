#!/bin/bash
set -e

echo "🚀 JobRadar deployment"
echo ""
echo "Which cloud do you want to deploy to?"
echo "  [1] AWS only"
echo "  [2] GCP only"
echo "  [3] Both"
read -p "Enter choice (1/2/3): " choice

deploy_aws() {
  echo ""
  echo "🔍 Checking if AWS cluster exists..."
  if eksctl get cluster --name jobradar --region us-east-1 &>/dev/null; then
    echo "✅ Cluster already exists — skipping creation."
  else
    echo "📦 Creating EKS cluster..."
    eksctl create cluster \
      --name jobradar \
      --region us-east-1 \
      --nodegroup-name workers \
      --node-type t3.small \
      --nodes 2 \
      --nodes-min 1 \
      --nodes-max 3 \
      --managed
  fi

  echo "🐳 Logging into ECR..."
  aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS \
    --password-stdin 565273632019.dkr.ecr.us-east-1.amazonaws.com

  echo "🔨 Building and pushing image to ECR..."
  eval $(minikube docker-env --unset) 2>/dev/null || true
  docker buildx create --name multiplatform \
    --driver docker-container --use 2>/dev/null || \
    docker buildx use multiplatform
  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag 565273632019.dkr.ecr.us-east-1.amazonaws.com/jobradar-api:latest \
    --push .

  echo "🔀 Switching kubectl to AWS..."
  kubectl config use-context Jobradar@jobradar.us-east-1.eksctl.io

  echo "⎈ Deploying with Helm to AWS..."
  helm upgrade --install jobradar ./charts/jobradar \
    --set api.image=565273632019.dkr.ecr.us-east-1.amazonaws.com/jobradar-api:latest \
    --set api.replicas=1

  echo "⏳ Waiting for pods..."
  kubectl wait --for=condition=ready pod \
    -l app=jobradar-api --timeout=120s

  echo "✅ AWS live!"
  kubectl get services
}

deploy_gcp() {
  echo ""
  echo "🔍 Checking if GCP cluster exists..."
  if gcloud container clusters describe jobradar \
    --region=us-central1 &>/dev/null; then
    echo "✅ Cluster already exists — skipping creation."
  else
    echo "📦 Creating GKE cluster..."
    gcloud container clusters create jobradar \
      --region=us-central1 \
      --num-nodes=2 \
      --machine-type=e2-small \
      --disk-size=20
  fi

  echo "🐳 Configuring Docker for GCR..."
  gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

  echo "🔨 Building and pushing image to GCR..."
  eval $(minikube docker-env --unset) 2>/dev/null || true
  docker buildx create --name multiplatform \
    --driver docker-container --use 2>/dev/null || \
    docker buildx use multiplatform
  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag us-central1-docker.pkg.dev/jobradar-497223/jobradar/jobradar-api:latest \
    --push .

  echo "🔀 Switching kubectl to GCP..."
  gcloud container clusters get-credentials jobradar \
    --region=us-central1 --quiet

  echo "⎈ Deploying with Helm to GCP..."
  helm upgrade --install jobradar ./charts/jobradar \
    --set api.image=us-central1-docker.pkg.dev/jobradar-497223/jobradar/jobradar-api:latest \
    --set api.replicas=1

  echo "⏳ Waiting for pods..."
  kubectl wait --for=condition=ready pod \
    -l app=jobradar-api --timeout=120s

  echo "✅ GCP live!"
  kubectl get services
}

case $choice in
  1) deploy_aws ;;
  2) deploy_gcp ;;
  3) deploy_aws; deploy_gcp ;;
  *) echo "Invalid choice. Exiting." ; exit 1 ;;
esac

echo ""
echo "✅ Deployment complete."