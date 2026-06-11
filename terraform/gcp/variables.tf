variable "gcp_project_id" {
  type = string
}

variable "gcp_region" {
  type    = string
  default = "us-central1"
}

variable "project_name" {
  type    = string
  default = "debugpilot"
}

variable "gcp_zone" {
  type        = string
  default     = ""
  description = "Optional zonal cluster location (e.g. us-central1-a) to avoid regional stockouts."
}

variable "node_locations" {
  type        = list(string)
  default     = ["us-central1-a"]
  description = "Zones for regional GKE nodes; CI apply retries other zones on GCE_STOCKOUT."
}

variable "machine_type" {
  type    = string
  default = "e2-medium"
}

variable "db_tier" {
  type        = string
  default     = "db-g1-small"
  description = "Cloud SQL tier; db-g1-small is the smallest shared-core Postgres tier."
}

variable "db_deletion_protection" {
  type        = bool
  default     = true
  description = "GCP API guard against accidental Cloud SQL delete. CI destroy workflow stops Cloud SQL after cluster teardown."
}

variable "node_count" {
  type    = number
  default = 1
}

variable "node_count_min" {
  type    = number
  default = 1
}

variable "node_count_max" {
  type    = number
  default = 5
}

variable "grafana_password" {
  type      = string
  sensitive = true
  default   = "debugpilot123"
}

variable "cloudflare_api_token" {
  type      = string
  sensitive = true
}

variable "domain_name" {
  type    = string
  default = "manavmalavia.org"
}

# API host: debugpilot-gcp.manavmalavia.org (isolated from AWS debugpilot.manavmalavia.org)
variable "hostname_prefix" {
  type    = string
  default = "debugpilot-gcp"
}

variable "anthropic_api_key" {
  type        = string
  sensitive   = true
  default     = ""
  description = "Anthropic API key for debugpilot-secrets (set via TF_VAR_anthropic_api_key in CI)"
}

variable "argocd_password" {
  type      = string
  sensitive = true
  default   = "debugpilot123"
}

variable "argocd_password_bcrypt" {
  type      = string
  sensitive = true
  default   = "$2a$10$uaWjWzOi.bXRSaEflJkpH.JXqBpVMx.fwucnfPQtBvSJ1MuUJmhI6"
}

variable "argocd_github_webhook_secret" {
  type        = string
  sensitive   = true
  default     = ""
  description = "GitHub webhook HMAC secret (webhook.github.secret). Set via TF_VAR_argocd_github_webhook_secret or ARGOCD_GITHUB_WEBHOOK_SECRET in CI."
}

variable "github_client_id" {
  type        = string
  sensitive   = true
  default     = ""
  description = "GitHub OAuth App client ID (TF_VAR_github_client_id / GitHub secret)"
}

variable "github_client_secret" {
  type        = string
  sensitive   = true
  default     = ""
  description = "GitHub OAuth App client secret"
}

variable "jwt_secret" {
  type        = string
  sensitive   = true
  default     = ""
  description = "JWT signing secret for session cookies (openssl rand -hex 32)"
}

variable "api_image_tag" {
  type        = string
  default     = "latest"
  description = "Artifact Registry tag for debugpilot-api (override after CI push)"
}
