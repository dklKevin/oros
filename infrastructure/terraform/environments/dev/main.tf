# =============================================================================
# Development Environment
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment for remote state (recommended for team development)
  # backend "s3" {
  #   bucket         = "biomedical-platform-terraform-state"
  #   key            = "dev/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "biomedical-platform-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# =============================================================================
# Networking
# =============================================================================
module "networking" {
  source = "../../modules/networking"

  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones

  # Cost savings for dev - disable NAT Gateway and some VPC endpoints
  enable_nat_gateway   = false
  enable_vpc_endpoints = false

  tags = local.common_tags
}

# =============================================================================
# Storage
# =============================================================================
module "storage" {
  source = "../../modules/storage"

  project_name   = var.project_name
  environment    = var.environment
  aws_account_id = data.aws_caller_identity.current.account_id

  tags = local.common_tags
}

# =============================================================================
# Database
# =============================================================================
module "database" {
  source = "../../modules/database"

  project_name      = var.project_name
  environment       = var.environment
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.rds_security_group_id

  # Cost-optimized settings for dev
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  multi_az          = false

  tags = local.common_tags
}

# =============================================================================
# Messaging
# =============================================================================
module "messaging" {
  source = "../../modules/messaging"

  project_name = var.project_name
  environment  = var.environment

  tags = local.common_tags
}

# =============================================================================
# Outputs
# =============================================================================
output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "database_endpoint" {
  description = "Database endpoint"
  value       = module.database.db_instance_endpoint
}

output "database_credentials_secret" {
  description = "Database credentials secret ARN"
  value       = module.database.db_credentials_secret_arn
}

output "raw_documents_bucket" {
  description = "Raw documents S3 bucket name"
  value       = module.storage.raw_documents_bucket_name
}

output "processed_chunks_bucket" {
  description = "Processed chunks S3 bucket name"
  value       = module.storage.processed_chunks_bucket_name
}

output "ingestion_queue_url" {
  description = "Ingestion SQS queue URL"
  value       = module.messaging.ingestion_queue_url
}
