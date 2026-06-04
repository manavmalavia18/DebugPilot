terraform {
  backend "s3" {
    bucket  = "debugpilot-terraform-state-565273632019"
    key     = "aws/cluster/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}