output "cluster_name" { value = aws_eks_cluster.main.name }
output "cluster_endpoint" { value = aws_eks_cluster.main.endpoint }
output "cluster_certificate" { value = aws_eks_cluster.main.certificate_authority[0].data }
output "oidc_issuer_url" { value = aws_eks_cluster.main.identity[0].oidc[0].issuer }
