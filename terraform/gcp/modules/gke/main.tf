resource "google_container_cluster" "main" {
  name                     = var.project_name
  location                 = var.gcp_region
  network                  = var.network
  subnetwork               = var.subnetwork
  initial_node_count       = 1
  remove_default_node_pool = true
  deletion_protection      = false
}

resource "google_container_node_pool" "workers" {
  name       = "workers"
  location   = var.gcp_region
  cluster    = google_container_cluster.main.name
  node_count = var.node_count

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
