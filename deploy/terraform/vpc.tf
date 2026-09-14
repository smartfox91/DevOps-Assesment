# Data source for Availability Zones
data "aws_availability_zones" "available" {
  state = "available"
}

# 1. Custom VPC (Task 2 Requirement)
resource "aws_vpc" "custom_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "respondio-video-archive-vpc-${var.environment}"
  }
}

# 2. Private Subnet 1 (AZ A)
resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.custom_vpc.id
  cidr_block        = var.private_subnet_1_cidr
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "respondio-private-subnet-1-${var.environment}"
    Type = "Private"
  }
}

# 3. Private Subnet 2 (AZ B) - High Availability Multi-AZ
resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.custom_vpc.id
  cidr_block        = var.private_subnet_2_cidr
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "respondio-private-subnet-2-${var.environment}"
    Type = "Private"
  }
}

# 4. Route Table for Private Subnets
resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.custom_vpc.id

  tags = {
    Name = "respondio-private-rt-${var.environment}"
  }
}

# Subnet 1 Association
resource "aws_route_table_association" "private_assoc_1" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private_rt.id
}

# Subnet 2 Association
resource "aws_route_table_association" "private_assoc_2" {
  subnet_id      = aws_subnet.private_subnet_2.id
  route_table_id = aws_route_table.private_rt.id
}

# 5. S3 VPC Gateway Endpoint (Vital for zero data-processing charges!)
resource "aws_vpc_endpoint" "s3_gateway" {
  vpc_id            = aws_vpc.custom_vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private_rt.id]

  tags = {
    Name = "respondio-s3-gateway-endpoint-${var.environment}"
  }
}

# 6. Security Group for Lambda in Private Subnets
resource "aws_security_group" "lambda_sg" {
  name        = "respondio-lambda-sg-${var.environment}"
  description = "Security group for Video Archiver Lambda running in private subnets"
  vpc_id      = aws_vpc.custom_vpc.id

  egress {
    description = "Allow outbound to S3 VPC endpoint and local VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "respondio-lambda-sg-${var.environment}"
  }
}
