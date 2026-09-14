terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Test credentials when emulating via Floci
  access_key = var.floci_endpoint != "" ? "test" : null
  secret_key = var.floci_endpoint != "" ? "test" : null

  s3_use_path_style           = var.floci_endpoint != "" ? true : false
  skip_credentials_validation = var.floci_endpoint != "" ? true : false
  skip_metadata_api_check     = var.floci_endpoint != "" ? true : false
  skip_requesting_account_id  = var.floci_endpoint != "" ? true : false

  dynamic "endpoints" {
    for_each = var.floci_endpoint != "" ? [1] : []
    content {
      s3             = var.floci_endpoint
      lambda         = var.floci_endpoint
      ec2            = var.floci_endpoint
      iam            = var.floci_endpoint
      sts            = var.floci_endpoint
      cloudwatch     = var.floci_endpoint
      cloudwatchlogs = var.floci_endpoint
      ecr            = var.floci_endpoint
    }
  }

  default_tags {
    tags = {
      Project     = "respond.io-devops-assessment"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
