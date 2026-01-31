output "raw_documents_bucket_name" {
  description = "Name of the raw documents S3 bucket"
  value       = aws_s3_bucket.raw_documents.id
}

output "raw_documents_bucket_arn" {
  description = "ARN of the raw documents S3 bucket"
  value       = aws_s3_bucket.raw_documents.arn
}

output "processed_chunks_bucket_name" {
  description = "Name of the processed chunks S3 bucket"
  value       = aws_s3_bucket.processed_chunks.id
}

output "processed_chunks_bucket_arn" {
  description = "ARN of the processed chunks S3 bucket"
  value       = aws_s3_bucket.processed_chunks.arn
}

output "s3_access_policy_arn" {
  description = "ARN of the S3 access IAM policy"
  value       = aws_iam_policy.s3_access.arn
}
