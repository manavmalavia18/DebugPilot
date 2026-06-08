resource "random_password" "db" {
  length  = 24
  special = false
}

resource "google_project_service" "sqladmin" {
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "servicenetworking" {
  service            = "servicenetworking.googleapis.com"
  disable_on_destroy = false
}

resource "google_compute_global_address" "sql_private_range" {
  name          = "${var.project_name}-sql-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = module.network.network
}

resource "google_service_networking_connection" "sql_private_vpc" {
  network                 = module.network.network
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.sql_private_range.name]

  depends_on = [google_project_service.servicenetworking]
}

resource "google_sql_database_instance" "postgres" {
  name             = "${var.project_name}-postgres"
  database_version = "POSTGRES_16"
  region           = var.gcp_region

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"

    ip_configuration {
      ipv4_enabled    = false
      private_network = module.network.network
    }

    backup_configuration {
      enabled = false
    }
  }

  deletion_protection = var.db_deletion_protection

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.sql_private_vpc,
  ]

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_sql_database" "debugpilot" {
  name     = "debugpilot"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "debugpilot" {
  name     = "debugpilot"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db.result
}

locals {
  database_url = "postgresql+psycopg2://${google_sql_user.debugpilot.name}:${urlencode(random_password.db.result)}@${google_sql_database_instance.postgres.private_ip_address}:5432/${google_sql_database.debugpilot.name}"
}
