variable "gcp_project_id" { type = string }
variable "gcp_region" { type = string, default = "us-central1" }
variable "project_name" { type = string, default = "jobradar" }
variable "machine_type" { type = string, default = "e2-small" }
variable "node_count" { type = number, default = 2 }
variable "node_count_min" { type = number, default = 1 }
variable "node_count_max" { type = number, default = 5 }
variable "grafana_password" { type = string, sensitive = true, default = "jobradar123" }
variable "argocd_password" { type = string, sensitive = true }
