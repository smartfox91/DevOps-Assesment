variable "aws_region" {
  type        = string
  description = "AWS region for provisioning resources"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
  default     = "production"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the custom VPC"
  default     = "10.0.0.0/16"
}

variable "private_subnet_1_cidr" {
  type        = string
  description = "CIDR block for Private Subnet 1 (AZ A)"
  default     = "10.0.1.0/24"
}

variable "private_subnet_2_cidr" {
  type        = string
  description = "CIDR block for Private Subnet 2 (AZ B)"
  default     = "10.0.2.0/24"
}

variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket for video processing metadata"
  default     = "respondio-video-metadata-archive"
}

variable "floci_endpoint" {
  type        = string
  description = "Custom endpoint URL if deploying to Floci / LocalStack (e.g. http://localhost:4566). Leave empty for real AWS."
  default     = ""
}

variable "lambda_memory_size" {
  type        = number
  description = "Memory allocated to Lambda function in MB"
  default     = 512
}

variable "lambda_timeout" {
  type        = number
  description = "Timeout for Lambda function in seconds"
  default     = 60
}

variable "lambda_package_type" {
  type        = string
  description = "Lambda package type: Image (Docker) or Zip"
  default     = "Zip"
}
