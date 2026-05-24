output "repository_url" {
  value = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${var.project_name}"
}
