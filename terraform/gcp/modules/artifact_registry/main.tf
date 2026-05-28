resource "google_artifact_registry_repository" "api" {
  location      = var.gcp_region
  repository_id = var.project_name
  format        = "DOCKER"
  labels        = { project = var.project_name }
  lifecycle {
    prevent_destroy = true
  }

}
