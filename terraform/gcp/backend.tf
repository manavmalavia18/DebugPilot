terraform {
  backend "gcs" {
    bucket = "jobradar-terraform-state-497223"
    prefix = "gcp/cluster"
  }
}
