output "cluster_name" {
  value = module.gke.cluster_name
}

output "cluster_endpoint" {
  value = module.gke.cluster_endpoint
}

output "artifact_registry_url" {
  value = module.artifact_registry.repository_url
}

output "api_image" {
  value = "${module.artifact_registry.repository_url}/jobradar-api:${var.api_image_tag}"
}

output "api_url" {
  value = "https://${var.hostname_prefix}.${var.domain_name}"
}

output "grafana_url" {
  value = "https://${var.hostname_prefix}-grafana.${var.domain_name}"
}

output "argocd_url" {
  value = "https://${var.hostname_prefix}-argocd.${var.domain_name}"
}
