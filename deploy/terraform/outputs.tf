output "vpc_id" {
  description = "Custom VPC ID"
  value       = aws_vpc.custom_vpc.id
}

output "private_subnet_1_id" {
  description = "Private Subnet 1 (AZ A)"
  value       = aws_subnet.private_subnet_1.id
}

output "private_subnet_2_id" {
  description = "Private Subnet 2 (AZ B)"
  value       = aws_subnet.private_subnet_2.id
}

output "s3_gateway_endpoint_id" {
  description = "S3 VPC Gateway Endpoint ID"
  value       = aws_vpc_endpoint.s3_gateway.id
}

output "s3_bucket_name" {
  description = "Video Metadata S3 Bucket Name"
  value       = aws_s3_bucket.video_metadata.id
}

output "lambda_function_arn" {
  description = "ARN of the Video Archiver Lambda Function"
  value       = aws_lambda_function.video_archiver.arn
}

output "lambda_function_version" {
  description = "Published Immutable Version of the Lambda"
  value       = aws_lambda_function.video_archiver.version
}

output "lambda_live_alias_arn" {
  description = "Live Alias ARN pointing to published release"
  value       = aws_lambda_alias.live.arn
}
