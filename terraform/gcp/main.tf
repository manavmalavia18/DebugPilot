terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
    helm   = { source = "hashicorp/helm", version = "~> 2.0" }
    null   = { source = "hashicorp/null", version = "~> 3.0" }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "helm" {
  kubernetes {
    config_path    = "~/.kube/config"
    config_context = "gke_${var.gcp_project_id}_${var.gcp_region}_${var.project_name}"
  }
}

module "network" {
  source       = "./modules/network"
  project_name = var.project_name
  gcp_region   = var.gcp_region
}

module "gke" {
  source         = "./modules/gke"
  project_name   = var.project_name
  gcp_region     = var.gcp_region
  network        = module.network.network
  subnetwork     = module.network.subnetwork
  machine_type   = var.machine_type
  node_count     = var.node_count
  node_count_min = var.node_count_min
  node_count_max = var.node_count_max
}

module "artifact_registry" {
  source         = "./modules/artifact_registry"
  project_name   = var.project_name
  gcp_project_id = var.gcp_project_id
  gcp_region     = var.gcp_region
}

resource "null_resource" "kubeconfig" {
  provisioner "local-exec" {
    command = "gcloud container clusters get-credentials ${var.project_name} --region=${var.gcp_region} --project=${var.gcp_project_id}"
  }

  depends_on = [module.gke]
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

  set {
    name  = "controller.publishService.enabled"
    value = "true"
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

      policy     = "upsert-only"
      txtOwnerId = "jobradar-gcp"

      # The external-dns chart rendered invalid probe fields with enabled=false.
      # Null removes the probes and prevents the GKE pod from being killed by /healthz failures.
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
  timeout          = 900

  values = [
    yamlencode({
      grafana = {
        adminPassword = var.grafana_password

        readinessProbe = {
          initialDelaySeconds = 60
        }

        livenessProbe = {
          initialDelaySeconds = 120
        }
      }

      prometheus = {
        prometheusSpec = {
          serviceMonitorSelectorNilUsesHelmValues = false

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

  values = [
    yamlencode({
      configs = {
        secret = {
          argocdServerAdminPassword      = var.argocd_password_bcrypt
          argocdServerAdminPasswordMtime = "2024-01-01T00:00:00Z"
        }
      }

      server = {
        livenessProbe = {
          initialDelaySeconds = 120
        }

        readinessProbe = {
          initialDelaySeconds = 60
        }
      }

      repoServer = {
        livenessProbe = {
          initialDelaySeconds = 120
        }

        readinessProbe = {
          initialDelaySeconds = 60
        }
      }
    })
  ]

  depends_on = [null_resource.kubeconfig]
}

resource "null_resource" "ingress_rules" {
  provisioner "local-exec" {
    command = <<-EOT
      sleep 30
      kubectl apply -f ${path.module}/../../k8s/ingress/gcp/cluster-issuer.yaml
      kubectl apply -f ${path.module}/../../k8s/ingress/gcp/jobradar-ingress.yaml
      kubectl apply -f ${path.module}/../../k8s/ingress/gcp/grafana-ingress.yaml
      kubectl apply -f ${path.module}/../../k8s/ingress/gcp/argocd-ingress.yaml
    EOT
  }

  depends_on = [
    helm_release.cert_manager,
    helm_release.ingress_nginx
  ]
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
          helm:
            valueFiles:
              - values-gcp.yaml
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