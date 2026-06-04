export const SAMPLE_PRESETS = [
  {
    id: "redis-k8s",
    label: "Redis / K8s",
    source: "kubernetes",
    log: `Back-off restarting failed container api in pod debugpilot-api-7d8f9c-abc12_default
Last State: Terminated
Reason: Error
Exit Code: 1
Logs:
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379. Connection refused.`,
  },
  {
    id: "image-pull",
    label: "ImagePullBackOff",
    source: "kubernetes",
    log: `Failed to pull image "565273632019.dkr.ecr.us-east-1.amazonaws.com/debugpilot-api:badtag":
rpc error: code = NotFound desc = failed to pull and unpack image: manifest unknown
Pod status: ImagePullBackOff`,
  },
  {
    id: "ingress-503",
    label: "Ingress 503",
    source: "kubernetes",
    log: `curl https://debugpilot.manavmalavia.org/
HTTP/2 503 Service Unavailable
nginx ingress: no upstream endpoints available for service debugpilot-api`,
  },
  {
    id: "terraform-lock",
    label: "Terraform lock",
    source: "terraform",
    log: `Error: Error acquiring the state lock
Lock Info:
  ID:        a1b2c3d4-5678-90ab-cdef
  Path:      debugpilot/terraform.tfstate
  Operation: OperationTypeApply
  Who:       github-actions@runner
  Version:   1.7.0`,
  },
  {
    id: "github-actions",
    label: "GitHub Actions",
    source: "github_actions",
    log: `##[error]Unable to connect to the server: getting credentials: exec: executable aws not found
Run aws eks update-kubeconfig --name debugpilot --region us-east-1
error: You must be logged in to the server (Unauthorized)`,
  },
]
