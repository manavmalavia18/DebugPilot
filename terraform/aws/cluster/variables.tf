variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_account_id" {
  type = string
}

variable "project_name" {
  type    = string
  default = "debugpilot"
}

variable "cluster_version" {
  type    = string
  default = "1.34"
}

variable "node_instance_type" {
  type    = string
  default = "t3.small"
}

variable "node_count" {
  type    = number
  default = 4
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

variable "github_client_id" {
  type        = string
  sensitive   = true
  default     = ""
  description = "GitHub OAuth App client ID"
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
  description = "JWT signing secret for session cookies"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_deletion_protection" {
  type        = bool
  default     = true
  description = "AWS API guard against accidental RDS delete. CI destroy workflow stops RDS after cluster teardown."
}

variable "db_skip_final_snapshot" {
  type        = bool
  default     = false
  description = "If true, terraform destroy can drop RDS without snapshot (only when prevent_destroy is removed)."
}

variable "argocd_github_webhook_secret" {
  type        = string
  sensitive   = true
  default     = ""
  description = "GitHub webhook HMAC secret (webhook.github.secret). Set via TF_VAR_argocd_github_webhook_secret or ARGOCD_GITHUB_WEBHOOK_SECRET in CI."
}
