#!/bin/bash
# =============================================================================
# LocalStack Initialization Script
# =============================================================================
# This script runs when LocalStack container starts

set -e

echo "Initializing LocalStack resources..."

# Wait for LocalStack to be ready
sleep 2

# =============================================================================
# S3 Buckets
# =============================================================================
echo "Creating S3 buckets..."

# Raw documents bucket
awslocal s3 mb s3://biomedical-raw-documents 2>/dev/null || true
awslocal s3api put-bucket-versioning \
    --bucket biomedical-raw-documents \
    --versioning-configuration Status=Enabled

# Processed chunks bucket
awslocal s3 mb s3://biomedical-processed-chunks 2>/dev/null || true

# Configure CORS for buckets (needed for potential web uploads)
awslocal s3api put-bucket-cors --bucket biomedical-raw-documents --cors-configuration '{
    "CORSRules": [
        {
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
            "AllowedHeaders": ["*"],
            "MaxAgeSeconds": 3000
        }
    ]
}'

echo "S3 buckets created successfully"

# =============================================================================
# SQS Queues
# =============================================================================
echo "Creating SQS queues..."

# Dead Letter Queue (create first)
awslocal sqs create-queue \
    --queue-name ingestion-dlq \
    --attributes '{
        "MessageRetentionPeriod": "1209600",
        "VisibilityTimeout": "300"
    }' 2>/dev/null || true

# Get DLQ ARN
DLQ_ARN=$(awslocal sqs get-queue-attributes \
    --queue-url http://localhost:4566/000000000000/ingestion-dlq \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' \
    --output text)

# Main ingestion queue with DLQ
awslocal sqs create-queue \
    --queue-name ingestion-queue \
    --attributes '{
        "VisibilityTimeout": "300",
        "MessageRetentionPeriod": "86400",
        "ReceiveMessageWaitTimeSeconds": "20",
        "RedrivePolicy": "{\"deadLetterTargetArn\": \"'$DLQ_ARN'\", \"maxReceiveCount\": 3}"
    }' 2>/dev/null || true

# Embedding queue (for async embedding generation)
awslocal sqs create-queue \
    --queue-name embedding-queue \
    --attributes '{
        "VisibilityTimeout": "600",
        "MessageRetentionPeriod": "86400"
    }' 2>/dev/null || true

echo "SQS queues created successfully"

# =============================================================================
# Secrets Manager
# =============================================================================
echo "Creating secrets..."

# Database credentials (for local development)
awslocal secretsmanager create-secret \
    --name biomedical/database \
    --secret-string '{
        "username": "biomedical",
        "password": "dev_password",
        "host": "postgres",
        "port": 5432,
        "database": "knowledge_platform"
    }' 2>/dev/null || true

# API keys placeholder
awslocal secretsmanager create-secret \
    --name biomedical/api-keys \
    --secret-string '{
        "default_api_key": "dev-api-key-12345"
    }' 2>/dev/null || true

echo "Secrets created successfully"

# =============================================================================
# Verification
# =============================================================================
echo ""
echo "=== LocalStack Resources ==="
echo ""
echo "S3 Buckets:"
awslocal s3 ls

echo ""
echo "SQS Queues:"
awslocal sqs list-queues --query 'QueueUrls' --output table

echo ""
echo "Secrets:"
awslocal secretsmanager list-secrets --query 'SecretList[].Name' --output table

echo ""
echo "LocalStack initialization complete!"
