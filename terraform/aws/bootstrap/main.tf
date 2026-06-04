terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_ecr_repository" "api" {
  name                 = "debugpilot-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = false
  image_scanning_configuration { scan_on_push = true }
  tags = {
    Name    = "debugpilot-api"
    Project = "debugpilot"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{ rulePriority = 1, description = "Keep last 10 images",
      selection = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 },
      action    = { type = "expire" }
    }]
  })
}

resource "aws_s3_bucket" "log_uploads" {
  bucket = "debugpilot-log-uploads-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "debugpilot-log-uploads"
    Project = "debugpilot"
  }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_public_access_block" "log_uploads" {
  bucket = aws_s3_bucket.log_uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "log_uploads" {
  bucket = aws_s3_bucket.log_uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "log_uploads" {
  bucket = aws_s3_bucket.log_uploads.id

  rule {
    id     = "expire-old-uploads"
    status = "Enabled"

    filter {}

    expiration {
      days = 30
    }
  }
}

output "log_uploads_bucket" {
  value = aws_s3_bucket.log_uploads.bucket
}

output "repository_url" {
  value = aws_ecr_repository.api.repository_url
}
