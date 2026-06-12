terraform {
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    helm   = { source = "hashicorp/helm", version = "~> 2.0" }
    null   = { source = "hashicorp/null", version = "~> 3.0" }
    random = { source = "hashicorp/random", version = "~> 3.0" }
    tls    = { source = "hashicorp/tls", version = "~> 4.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "helm" {
  kubernetes {
    config_path    = "~/.kube/config"
    config_context = "arn:aws:eks:${var.aws_region}:${var.aws_account_id}:cluster/${var.project_name}"
  }
}

module "vpc" {
  source       = "./modules/vpc"
  project_name = var.project_name
}

data "aws_s3_bucket" "log_uploads" {
  bucket = "debugpilot-log-uploads-${var.aws_account_id}"
}

module "eks" {
  source             = "./modules/eks"
  project_name       = var.project_name
  cluster_version    = var.cluster_version
  subnet_ids         = module.vpc.public_subnet_ids
  node_instance_type = var.node_instance_type
  node_count         = var.node_count
  node_count_min     = var.node_count_min
  node_count_max     = var.node_count_max
  uploads_bucket_arn = data.aws_s3_bucket.log_uploads.arn
}

module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
}

resource "null_resource" "kubeconfig" {
  provisioner "local-exec" {
    command = "aws eks update-kubeconfig --name ${var.project_name} --region ${var.aws_region}"
  }
  depends_on = [module.eks]
}

resource "helm_release" "ingress_nginx" {
  name             = "ingress-nginx"
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  timeout          = 300

  set {
    name  = "controller.service.type"
    value = "LoadBalancer"
  }

  depends_on = [null_resource.kubeconfig]
}


resource "helm_release" "external_dns" {
  name             = "external-dns"
  repository       = "https://kubernetes-sigs.github.io/external-dns/"
  chart            = "external-dns"
  namespace        = "external-dns"
  create_namespace = true
  timeout          = 600

  values = [
    yamlencode({
      provider = {
        name = "cloudflare"
      }

      sources = ["ingress"]

      domainFilters = [
        var.domain_name
      ]

      policy = "sync"

      txtOwnerId = "debugpilot-aws"

      livenessProbe  = null
      readinessProbe = null

      env = [
        {
          name  = "CF_API_TOKEN"
          value = var.cloudflare_api_token
        }
      ]
    })
  ]

  depends_on = [helm_release.ingress_nginx]
}

resource "helm_release" "cert_manager" {
  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  namespace        = "cert-manager"
  create_namespace = true
  timeout          = 300

  set {
    name  = "crds.enabled"
    value = "true"
  }

  depends_on = [null_resource.kubeconfig]
}

resource "helm_release" "monitoring" {
  name             = "monitoring"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = "monitoring"
  create_namespace = true
  timeout          = 1800

  values = [
    yamlencode({
      alertmanager = {
        enabled = false
      }

      grafana = {
        adminPassword = var.grafana_password
      }

      prometheus = {
        prometheusSpec = {
          serviceMonitorSelectorNilUsesHelmValues = false

          resources = {
            requests = {
              cpu    = "200m"
              memory = "512Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "1Gi"
            }
          }

          startupProbe = {
            failureThreshold = 120
          }
        }
      }
    })
  ]

  depends_on = [null_resource.kubeconfig]
}

resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  namespace        = "argocd"
  create_namespace = true
  timeout          = 300

  set {
    name  = "configs.secret.argocdServerAdminPassword"
    value = var.argocd_password_bcrypt
  }

  set {
    name  = "configs.secret.argocdServerAdminPasswordMtime"
    value = "2024-01-01T00:00:00Z"
  }

  dynamic "set" {
    for_each = var.argocd_github_webhook_secret != "" ? [1] : []
    content {
      name  = "configs.secret.githubSecret"
      value = var.argocd_github_webhook_secret
    }
  }

  depends_on = [null_resource.kubeconfig]
}

resource "null_resource" "ingress_rules" {
  triggers = {
    cluster_issuer = filesha256("${path.module}/../../../k8s/ingress/aws/cluster-issuer.yaml")
    grafana        = filesha256("${path.module}/../../../k8s/ingress/aws/grafana-ingress.yaml")
    argocd         = filesha256("${path.module}/../../../k8s/ingress/aws/argocd-ingress.yaml")
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command = <<-EOT
      set -euo pipefail

      echo "Waiting for ingress-nginx controller..."
      kubectl wait --namespace ingress-nginx \
        --for=condition=ready pod \
        --selector=app.kubernetes.io/component=controller \
        --timeout=600s

      echo "Waiting for ingress-nginx admission webhook..."
      for i in $(seq 1 60); do
        if kubectl get endpoints ingress-nginx-controller-admission -n ingress-nginx \
          -o jsonpath='{.subsets[0].addresses[0].ip}' 2>/dev/null | grep -q .; then
          break
        fi
        sleep 5
      done

      kubectl apply -f ${path.module}/../../../k8s/ingress/aws/cluster-issuer.yaml
      kubectl apply -f ${path.module}/../../../k8s/ingress/aws/grafana-ingress.yaml
      kubectl apply -f ${path.module}/../../../k8s/ingress/aws/argocd-ingress.yaml
    EOT
  }
  depends_on = [helm_release.cert_manager, helm_release.ingress_nginx]
}

resource "null_resource" "debugpilot_ingress" {
  triggers = {
    manifest = filesha256("${path.module}/../../../k8s/ingress/aws/debugpilot-ingress.yaml")
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command = <<-EOT
      set -euo pipefail

      echo "Waiting for Argo CD to deploy debugpilot-api..."
      for i in $(seq 1 60); do
        kubectl get deployment debugpilot-api -n default >/dev/null 2>&1 && break
        sleep 10
      done
      kubectl wait --for=condition=available deployment/debugpilot-api -n default --timeout=600s

      kubectl apply -f ${path.module}/../../../k8s/ingress/aws/debugpilot-ingress.yaml
    EOT
  }

  depends_on = [null_resource.ingress_rules, null_resource.argocd_app]
}

resource "null_resource" "debugpilot_secrets" {
  count = var.anthropic_api_key != "" ? 1 : 0

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    environment = {
      ANTHROPIC_API_KEY     = var.anthropic_api_key
      GITHUB_CLIENT_ID      = var.github_client_id
      GITHUB_CLIENT_SECRET  = var.github_client_secret
      JWT_SECRET            = var.jwt_secret
      DATABASE_URL          = local.database_url
      GITHUB_WEBHOOK_SECRET = var.github_webhook_secret
      GITHUB_WEBHOOK_TOKEN  = var.github_webhook_token
    }
    command = <<-EOT
      EXTRA_ARGS=""
      if [ -n "$GITHUB_CLIENT_ID" ]; then
        EXTRA_ARGS="$EXTRA_ARGS --from-literal=GITHUB_CLIENT_ID=$GITHUB_CLIENT_ID"
      fi
      if [ -n "$GITHUB_CLIENT_SECRET" ]; then
        EXTRA_ARGS="$EXTRA_ARGS --from-literal=GITHUB_CLIENT_SECRET=$GITHUB_CLIENT_SECRET"
      fi
      if [ -n "$JWT_SECRET" ]; then
        EXTRA_ARGS="$EXTRA_ARGS --from-literal=JWT_SECRET=$JWT_SECRET"
      fi
      if [ -n "$DATABASE_URL" ]; then
        EXTRA_ARGS="$EXTRA_ARGS --from-literal=DATABASE_URL=$DATABASE_URL"
      fi
      if [ -n "$GITHUB_WEBHOOK_SECRET" ]; then
        EXTRA_ARGS="$EXTRA_ARGS --from-literal=GITHUB_WEBHOOK_SECRET=$GITHUB_WEBHOOK_SECRET"
      fi
      if [ -n "$GITHUB_WEBHOOK_TOKEN" ]; then
        EXTRA_ARGS="$EXTRA_ARGS --from-literal=GITHUB_WEBHOOK_TOKEN=$GITHUB_WEBHOOK_TOKEN"
      fi
      kubectl create secret generic debugpilot-secrets \
        --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
        $EXTRA_ARGS \
        --dry-run=client -o yaml | kubectl apply -f -
    EOT
  }

  depends_on = [null_resource.kubeconfig, aws_db_instance.postgres]

  triggers = {
    api_key_hash = sha256(var.anthropic_api_key)
    auth_hash    = sha256("${var.github_client_id}:${var.jwt_secret}")
    db_hash      = sha256(local.database_url)
    webhook_hash = sha256("${var.github_webhook_secret}:${var.github_webhook_token}")
  }
}

resource "helm_release" "strimzi_operator" {
  name             = "strimzi-kafka-operator"
  repository       = "https://strimzi.io/charts/"
  chart            = "strimzi-kafka-operator"
  version          = "1.0.0"
  namespace        = "kafka"
  create_namespace = true
  timeout          = 600

  values = [
    yamlencode({
      resources = {
        requests = {
          cpu    = "100m"
          memory = "256Mi"
        }
        limits = {
          cpu    = "500m"
          memory = "512Mi"
        }
      }
    })
  ]

  set {
    name  = "watchNamespaces[0]"
    value = "kafka"
  }

  depends_on = [null_resource.kubeconfig]
}

resource "null_resource" "strimzi_kafka" {
  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      echo "Waiting for Strimzi CRDs to become established..."
      for crd in kafkas.kafka.strimzi.io kafkatopics.kafka.strimzi.io kafkanodepools.kafka.strimzi.io; do
        kubectl wait --for=condition=Established "crd/$crd" --timeout=300s
      done
      echo "Waiting for kafka.strimzi.io/v1 API..."
      for attempt in $(seq 1 60); do
        if kubectl api-resources --api-group=kafka.strimzi.io 2>/dev/null | grep -q '^kafkas '; then
          break
        fi
        echo "Kafka API not listed yet (attempt $attempt/60)..."
        sleep 5
      done
      if ! kubectl wait --for=condition=Available deployment/strimzi-cluster-operator -n kafka --timeout=600s; then
        echo "Strimzi operator not Available yet; continuing with manifest apply..."
        kubectl get pods -n kafka -o wide || true
      fi
      kubectl apply -f ${path.module}/../../../k8s/kafka/
      echo "Waiting for Kafka cluster debugpilot to become ready..."
      kubectl wait kafka/debugpilot -n kafka --for=condition=Ready --timeout=900s
    EOT
  }

  depends_on = [helm_release.strimzi_operator]

  triggers = {
    kafka_manifest  = filesha256("${path.module}/../../../k8s/kafka/kafka.yaml")
    topic_manifest  = filesha256("${path.module}/../../../k8s/kafka/kafka-topics.yaml")
    strimzi_version = helm_release.strimzi_operator.version
  }
}

resource "null_resource" "argocd_app" {
  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command = <<-EOT
      set -euo pipefail
      sleep 15
      kubectl apply -f - <<YAML
      apiVersion: argoproj.io/v1alpha1
      kind: Application
      metadata:
        name: debugpilot
        namespace: argocd
      spec:
        project: default
        source:
          repoURL: https://github.com/manavmalavia18/JobTracker
          targetRevision: HEAD
          path: charts/debugpilot
          helm:
            valueFiles:
              - values-aws.yaml
        destination:
          server: https://kubernetes.default.svc
          namespace: default
        syncPolicy:
          automated:
            prune: true
            selfHeal: true
      YAML
    EOT
  }
  depends_on = [
    helm_release.argocd,
    null_resource.debugpilot_secrets,
    null_resource.strimzi_kafka,
  ]
}
