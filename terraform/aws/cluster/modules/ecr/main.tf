resource "aws_ecr_repository" "api" {
  name                 = "${var.project_name}-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration { scan_on_push = true }
  tags = { Name = "${var.project_name}-api", Project = var.project_name }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{ rulePriority = 1, description = "Keep last 10 images",
      selection = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 },
      action = { type = "expire" }
    }]
  })
}
