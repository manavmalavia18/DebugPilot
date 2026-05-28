terraform {
  required_providers {
    aws  = { source = "hashicorp/aws", version = "~> 5.0" }
    helm = { source = "hashicorp/helm", version = "~> 2.0" }
    null = { source = "hashicorp/null", version = "~> 3.0" }
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

module "eks" {
  source             = "./modules/eks"
  project_name       = var.project_name
  cluster_version    = var.cluster_version
  subnet_ids         = module.vpc.public_subnet_ids
  node_instance_type = var.node_instance_type
  node_count         = var.node_count
  node_count_min     = var.node_count_min
  node_count_max     = var.node_count_max
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
  timeout          = 300

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

      txtOwnerId = "jobradar-aws"

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
  timeout          = 900

  set {
    name  = "grafana.adminPassword"
    value = var.grafana_password
  }

  set {
    name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
    value = "false"
  }

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

  depends_on = [null_resource.kubeconfig]
}

resource "null_resource" "ingress_rules" {
  provisioner "local-exec" {
    command = <<-EOT
      sleep 30
      kubectl apply -f ${path.module}/../../../k8s/ingress/aws/cluster-issuer.yaml
      kubectl apply -f ${path.module}/../../../k8s/ingress/aws/jobradar-ingress.yaml
      kubectl apply -f ${path.module}/../../../k8s/ingress/aws/grafana-ingress.yaml
      kubectl apply -f ${path.module}/../../../k8s/ingress/aws/argocd-ingress.yaml
    EOT
  }
  depends_on = [helm_release.cert_manager, helm_release.ingress_nginx]
}

resource "null_resource" "argocd_app" {
  provisioner "local-exec" {
    command = <<-EOT
      sleep 15
      kubectl apply -f - <<YAML
      apiVersion: argoproj.io/v1alpha1
      kind: Application
      metadata:
        name: jobradar
        namespace: argocd
      spec:
        project: default
        source:
          repoURL: https://github.com/manavmalavia18/JobTracker
          targetRevision: HEAD
          path: charts/jobradar
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
  depends_on = [helm_release.argocd]
}
