locals {
  cluster_location = var.gcp_zone != "" ? var.gcp_zone : var.gcp_region
}

resource "google_container_cluster" "main" {
  name                     = var.project_name
  location                 = local.cluster_location
  network                  = var.network
  subnetwork               = var.subnetwork
  node_locations           = var.gcp_zone == "" && length(var.node_locations) > 0 ? var.node_locations : null
  initial_node_count       = 1
  remove_default_node_pool = true

  timeouts {
    create = "60m"
    update = "60m"
    delete = "60m"
  }
  deletion_protection = false
}

resource "google_container_node_pool" "workers" {
  name           = "workers"
  location       = local.cluster_location
  cluster        = google_container_cluster.main.name
  node_locations = var.gcp_zone == "" && length(var.node_locations) > 0 ? var.node_locations : null
  node_count     = var.node_count

  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
  }

  node_config {
    machine_type = var.machine_type
    disk_size_gb = 20
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    labels       = { project = var.project_name }
  }

  autoscaling {
    min_node_count = var.node_count_min
    max_node_count = var.node_count_max
  }
}
