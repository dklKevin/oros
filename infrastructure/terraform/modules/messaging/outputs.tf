output "ingestion_queue_url" {
  description = "URL of the ingestion SQS queue"
  value       = aws_sqs_queue.ingestion.url
}

output "ingestion_queue_arn" {
  description = "ARN of the ingestion SQS queue"
  value       = aws_sqs_queue.ingestion.arn
}

output "ingestion_dlq_url" {
  description = "URL of the ingestion DLQ"
  value       = aws_sqs_queue.ingestion_dlq.url
}

output "ingestion_dlq_arn" {
  description = "ARN of the ingestion DLQ"
  value       = aws_sqs_queue.ingestion_dlq.arn
}

output "embedding_queue_url" {
  description = "URL of the embedding SQS queue"
  value       = aws_sqs_queue.embedding.url
}

output "embedding_queue_arn" {
  description = "ARN of the embedding SQS queue"
  value       = aws_sqs_queue.embedding.arn
}

output "sqs_access_policy_arn" {
  description = "ARN of the SQS access IAM policy"
  value       = aws_iam_policy.sqs_access.arn
}
