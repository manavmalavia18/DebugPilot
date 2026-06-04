output "cluster_name" {
  value = module.gke.cluster_name
}

output "cluster_endpoint" {
  value = module.gke.cluster_endpoint
}

output "artifact_registry_url" {
  value = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${var.project_name}"
}

output "api_image" {
  value = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${var.project_name}/debugpilot-api:${var.api_image_tag}"
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
