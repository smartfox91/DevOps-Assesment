# Variables for local emulation against Floci (http://localhost:4566)
aws_region          = "us-east-1"
environment         = "local"
bucket_name         = "respondio-video-metadata-archive-local"
floci_endpoint      = "http://localhost:4566"
vpc_cidr            = "10.0.0.0/16"
private_subnet_1_cidr = "10.0.1.0/24"
private_subnet_2_cidr = "10.0.2.0/24"
lambda_memory_size  = 512
lambda_timeout      = 60
