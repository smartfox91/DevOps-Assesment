# 1. Package Lambda source code into Zip archive
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/app.py"
  output_path = "${path.module}/lambda_payload.zip"
}

# 2. IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_exec_role" {
  name = "respondio-lambda-exec-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "respondio-lambda-exec-role-${var.environment}"
  }
}

# 3. Attach AWSLambdaVPCAccessExecutionRole for VPC ENI management
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# 4. Custom Least-Privilege S3 Policy for Get, Put, Delete
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "respondio-lambda-s3-permissions"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.video_metadata.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.video_metadata.arn
      }
    ]
  })
}

# 5. AWS Lambda Function
# Configured with VPC Private Subnets, Security Group, and version publishing
resource "aws_lambda_function" "video_archiver" {
  function_name    = "respondio-video-archiver-${var.environment}"
  description      = "Compresses video processing JSON metadata to ZIP and cleans up original"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout

  # Task 2 Requirement: Each deployment creates a new immutable version for reliable rollbacks
  publish = true

  vpc_config {
    subnet_ids         = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      LOG_LEVEL        = "INFO"
      AWS_ENDPOINT_URL = var.floci_endpoint != "" ? var.floci_endpoint : ""
    }
  }

  tags = {
    Name        = "respondio-video-archiver-${var.environment}"
    Environment = var.environment
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_vpc_access,
    aws_iam_role_policy.lambda_s3_policy
  ]
}

# 6. Lambda Live Alias for Controlled Releases & Instant Rollbacks
resource "aws_lambda_alias" "live" {
  name             = "live"
  description      = "Production active alias pointing to the latest verified version"
  function_name    = aws_lambda_function.video_archiver.function_name
  function_version = aws_lambda_function.video_archiver.version
}

# 7. Permissions for S3 to invoke Lambda via Alias and Function
resource "aws_lambda_permission" "allow_s3_alias" {
  statement_id  = "AllowExecutionFromS3Alias"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.video_archiver.function_name
  qualifier     = aws_lambda_alias.live.name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.video_metadata.arn
}

resource "aws_lambda_permission" "allow_s3_function" {
  statement_id  = "AllowExecutionFromS3Function"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.video_archiver.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.video_metadata.arn
}
