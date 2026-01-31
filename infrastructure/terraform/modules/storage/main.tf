# =============================================================================
# Storage Module
# =============================================================================
# Creates S3 buckets for document storage

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# =============================================================================
# Raw Documents Bucket
# =============================================================================
resource "aws_s3_bucket" "raw_documents" {
  bucket = "${local.name_prefix}-raw-documents-${var.aws_account_id}"

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-raw-documents"
    Type = "raw-documents"
  })
}

resource "aws_s3_bucket_versioning" "raw_documents" {
  bucket = aws_s3_bucket.raw_documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_documents" {
  bucket = aws_s3_bucket.raw_documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw_documents" {
  bucket = aws_s3_bucket.raw_documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_documents" {
  bucket = aws_s3_bucket.raw_documents.id

  rule {
    id     = "archive-old-versions"
    status = "Enabled"

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

# =============================================================================
# Processed Chunks Bucket
# =============================================================================
resource "aws_s3_bucket" "processed_chunks" {
  bucket = "${local.name_prefix}-processed-chunks-${var.aws_account_id}"

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-processed-chunks"
    Type = "processed-chunks"
  })
}

resource "aws_s3_bucket_versioning" "processed_chunks" {
  bucket = aws_s3_bucket.processed_chunks.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed_chunks" {
  bucket = aws_s3_bucket.processed_chunks.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "processed_chunks" {
  bucket = aws_s3_bucket.processed_chunks.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# IAM Policy for S3 Access
# =============================================================================
data "aws_iam_policy_document" "s3_access" {
  statement {
    sid    = "AllowS3Access"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]

    resources = [
      aws_s3_bucket.raw_documents.arn,
      "${aws_s3_bucket.raw_documents.arn}/*",
      aws_s3_bucket.processed_chunks.arn,
      "${aws_s3_bucket.processed_chunks.arn}/*",
    ]
  }
}

resource "aws_iam_policy" "s3_access" {
  name        = "${local.name_prefix}-s3-access-policy"
  description = "Policy for accessing S3 buckets"
  policy      = data.aws_iam_policy_document.s3_access.json

  tags = var.tags
}
