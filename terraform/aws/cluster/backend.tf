terraform {
  backend "s3" {
    bucket  = "jobradar-terraform-state-565273632019"
    key     = "aws/cluster/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}