variable "project_name" {
  type = string
}

variable "gcp_region" {
  type = string
}

variable "gcp_zone" {
  type    = string
  default = ""
}

variable "node_locations" {
  type    = list(string)
  default = []
}

variable "network" {
  type = string
}

variable "subnetwork" {
  type = string
}

variable "machine_type" {
  type    = string
  default = "e2-medium"
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
