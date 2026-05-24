variable "aws_region" { type = string, default = "us-east-1" }
variable "aws_account_id" { type = string }
variable "project_name" { type = string, default = "jobradar" }
variable "cluster_version" { type = string, default = "1.34" }
variable "node_instance_type" { type = string, default = "t3.small" }
variable "node_count" { type = number, default = 3 }
variable "node_count_min" { type = number, default = 1 }
variable "node_count_max" { type = number, default = 5 }
variable "grafana_password" { type = string, sensitive = true, default = "jobradar123" }
variable "argocd_password" { type = string, sensitive = true }
