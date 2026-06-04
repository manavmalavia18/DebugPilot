data "tls_certificate" "eks_oidc" {
  url = module.eks.oidc_issuer_url
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks_oidc.certificates[0].sha1_fingerprint]
  url             = module.eks.oidc_issuer_url
}

locals {
  oidc_provider_host = replace(module.eks.oidc_issuer_url, "https://", "")
}

resource "aws_iam_role" "api_uploads" {
  name = "${var.project_name}-api-uploads"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.eks.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_provider_host}:aud" = "sts.amazonaws.com"
          "${local.oidc_provider_host}:sub" = "system:serviceaccount:default:debugpilot-api"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "api_uploads_s3" {
  name = "${var.project_name}-api-uploads-s3"
  role = aws_iam_role.api_uploads.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject"]
      Resource = "${data.aws_s3_bucket.log_uploads.arn}/*"
    }]
  })
}

resource "null_resource" "api_uploads_service_account" {
  provisioner "local-exec" {
    command = <<-EOT
      kubectl apply -f - <<YAML
      apiVersion: v1
      kind: ServiceAccount
      metadata:
        name: debugpilot-api
        namespace: default
        annotations:
          eks.amazonaws.com/role-arn: ${aws_iam_role.api_uploads.arn}
      YAML
    EOT
  }

  depends_on = [null_resource.kubeconfig, aws_iam_role.api_uploads]

  triggers = {
    role_arn = aws_iam_role.api_uploads.arn
  }
}

output "api_uploads_role_arn" {
  value = aws_iam_role.api_uploads.arn
}
