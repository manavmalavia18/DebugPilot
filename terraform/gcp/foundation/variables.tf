variable "gcp_project_id" {
  type        = string
  description = "GCP project ID (set via TF_VAR_gcp_project_id / GitHub GCP_PROJECT_ID)"
}

variable "gcp_region" {
  type    = string
  default = "us-central1"
}

variable "project_name" {
  type    = string
  default = "debugpilot"
}
