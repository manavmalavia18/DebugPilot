output "cluster_name" { value = module.gke.cluster_name }
output "cluster_endpoint" { value = module.gke.cluster_endpoint }
output "artifact_registry_url" { value = module.artifact_registry.repository_url }
