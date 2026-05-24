variable "project_name" { type = string }
variable "cluster_version" { type = string }
variable "subnet_ids" { type = list(string) }
variable "node_instance_type" { type = string }
variable "node_count" { type = number }
variable "node_count_min" { type = number }
variable "node_count_max" { type = number }
