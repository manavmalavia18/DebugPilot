# Terraform state lock error

## Symptoms
- `Error acquiring the state lock`
- `ConditionalCheckFailedException` or lock ID shown in error
- `terraform apply` / `plan` blocked

## Root cause
A previous Terraform run was interrupted (Ctrl+C, CI timeout, crash) and did not release the remote state lock in S3/DynamoDB or GCS.

## Fix
1. Confirm no other `terraform apply` is actually running (CI, teammate)
2. If stale, force-unlock with the lock ID from the error:
   `terraform force-unlock <LOCK_ID>`
3. Re-run `terraform plan` before apply

⚠ Only force-unlock when you are sure no other operation holds the lock.

## Debug commands
```bash
terraform plan
# note lock ID from error output
terraform force-unlock <LOCK_ID>
```

## Prevention
- Use remote backend with locking (S3 + DynamoDB or GCS)
- Avoid parallel applies on same state
- Set reasonable CI timeouts
