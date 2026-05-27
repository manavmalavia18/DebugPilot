variable "project_name" {
  type = string
}

variable "gcp_region" {
  type = string
}

variable "network" {
  type = string
}

variable "subnetwork" {
  type = string
}

variable "machine_type" {
  type    = string
  default = "e2-small"
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
