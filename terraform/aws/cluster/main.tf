terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
    helm = { source = "hashicorp/helm", version = "~> 2.0" }
    argocd = { source = "oboukili/argocd", version = "~> 6.0" }
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

provider "argocd" {
  server_addr = "localhost:8080"
  username    = "admin"
  password    = var.argocd_password
  insecure    = true
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

resource "helm_release" "monitoring" {
  name             = "monitoring"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = "monitoring"
  create_namespace = true
  timeout          = 300

  set { name = "grafana.adminPassword", value = var.grafana_password }
  set { name = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues", value = "false" }

  depends_on = [null_resource.kubeconfig]
}

resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  namespace        = "argocd"
  create_namespace = true
  timeout          = 300
  depends_on       = [null_resource.kubeconfig]
}

resource "null_resource" "argocd_portforward" {
  provisioner "local-exec" {
    command = "kubectl port-forward svc/argocd-server -n argocd 8080:443 > /tmp/argocd-pf.log 2>&1 & echo $! > /tmp/argocd-pf.pid && sleep 15"
  }
  depends_on = [helm_release.argocd]
}

resource "argocd_application" "jobradar" {
  metadata {
    name      = "jobradar"
    namespace = "argocd"
  }
  spec {
    source {
      repo_url        = "https://github.com/manavmalavia18/JobTracker"
      path            = "charts/jobradar"
      target_revision = "HEAD"
    }
    destination {
      server    = "https://kubernetes.default.svc"
      namespace = "default"
    }
    sync_policy {
      automated { prune = true, self_heal = true }
    }
  }
  depends_on = [null_resource.argocd_portforward]
}
