terraform {
  backend "gcs" {
    bucket = "debugpilot-terraform-state-497223"
    prefix = "gcp/foundation"
  }
}
