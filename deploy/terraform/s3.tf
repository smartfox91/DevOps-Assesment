# 1. Video Processing Metadata S3 Bucket
resource "aws_s3_bucket" "video_metadata" {
  bucket        = var.bucket_name
  force_destroy = true # Convenient for sandbox testing; set false in prod

  tags = {
    Name        = var.bucket_name
    Purpose     = "video-processing-metadata-archive"
    Environment = var.environment
  }
}

# 2. Bucket Versioning
resource "aws_s3_bucket_versioning" "metadata_versioning" {
  bucket = aws_s3_bucket.video_metadata.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 3. Server-Side Encryption (AES256)
resource "aws_s3_bucket_server_side_encryption_configuration" "metadata_encryption" {
  bucket = aws_s3_bucket.video_metadata.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 4. Block Public Access
resource "aws_s3_bucket_public_access_block" "metadata_public_block" {
  bucket = aws_s3_bucket.video_metadata.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 5. S3 Event Notification to trigger Lambda
# Filtered specifically on .json suffix to prevent recursion with .zip files
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.video_metadata.id

  lambda_function {
    lambda_function_arn = aws_lambda_alias.live.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".json"
  }

  depends_on = [
    aws_lambda_permission.allow_s3_alias,
    aws_lambda_permission.allow_s3_function
  ]
}
