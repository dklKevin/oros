# =============================================================================
# Messaging Module
# =============================================================================
# Creates SQS queues for async processing

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# =============================================================================
# Dead Letter Queue
# =============================================================================
resource "aws_sqs_queue" "ingestion_dlq" {
  name = "${local.name_prefix}-ingestion-dlq"

  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 300

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-ingestion-dlq"
    Type = "dlq"
  })
}

# =============================================================================
# Ingestion Queue
# =============================================================================
resource "aws_sqs_queue" "ingestion" {
  name = "${local.name_prefix}-ingestion-queue"

  visibility_timeout_seconds = 300     # 5 minutes
  message_retention_seconds  = 86400   # 1 day
  receive_wait_time_seconds  = 20      # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingestion_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-ingestion-queue"
    Type = "processing"
  })
}

# =============================================================================
# Embedding Queue
# =============================================================================
resource "aws_sqs_queue" "embedding" {
  name = "${local.name_prefix}-embedding-queue"

  visibility_timeout_seconds = 600    # 10 minutes (embeddings take longer)
  message_retention_seconds  = 86400  # 1 day
  receive_wait_time_seconds  = 20     # Long polling

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-embedding-queue"
    Type = "processing"
  })
}

# =============================================================================
# Queue Policies
# =============================================================================
data "aws_iam_policy_document" "sqs_access" {
  statement {
    sid    = "AllowSQSAccess"
    effect = "Allow"

    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ChangeMessageVisibility",
    ]

    resources = [
      aws_sqs_queue.ingestion.arn,
      aws_sqs_queue.ingestion_dlq.arn,
      aws_sqs_queue.embedding.arn,
    ]
  }
}

resource "aws_iam_policy" "sqs_access" {
  name        = "${local.name_prefix}-sqs-access-policy"
  description = "Policy for accessing SQS queues"
  policy      = data.aws_iam_policy_document.sqs_access.json

  tags = var.tags
}

# =============================================================================
# CloudWatch Alarms
# =============================================================================
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${local.name_prefix}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Dead letter queue has messages"

  dimensions = {
    QueueName = aws_sqs_queue.ingestion_dlq.name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog" {
  alarm_name          = "${local.name_prefix}-queue-backlog"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 100
  alarm_description   = "Ingestion queue backlog is high"

  dimensions = {
    QueueName = aws_sqs_queue.ingestion.name
  }

  tags = var.tags
}
