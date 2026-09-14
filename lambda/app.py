"""
Lambda Function: Video Metadata S3 Archiver
Author: Senior DevOps Candidate for respond.io

Responsibilities:
1. Receives S3 ObjectCreated events for newly uploaded video metadata files (.json).
2. Recursion Guard: Skips any file that is not .json or is already .zip to prevent infinite loops.
3. Streams and compresses the JSON object into a standard ZIP archive (DEFLATED).
4. Uploads the .zip archive to the same S3 bucket under the corresponding archive key.
5. Deletes the original .json object from S3 after successful upload.
6. Emits structured JSON logs with performance, compression ratio, and audit details.
"""

import io
import json
import logging
import os
import sys
import time
import urllib.parse
import zipfile
import boto3
from botocore.exceptions import ClientError

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
    json.dumps({
        "timestamp": "%(asctime)s",
        "level": "%(levelname)s",
        "module": "%(name)s",
        "message": "%(message)s"
    })
))
if not logger.handlers:
    logger.addHandler(handler)

# Initialize S3 client (supports AWS_ENDPOINT_URL for Floci / LocalStack local testing)
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL") or None
s3_client = boto3.client("s3", endpoint_url=ENDPOINT_URL)


def lambda_handler(event, context):
    """
    Main entry point for S3 ObjectCreated notifications.
    """
    start_time = time.time()
    records = event.get("Records", [])

    if not records:
        logger.warning(json.dumps({"event": "empty_event", "detail": "No Records in event payload"}))
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "No records found to process"})
        }

    processed = []
    skipped = []
    errors = []

    for record in records:
        s3_info = record.get("s3", {})
        bucket_name = s3_info.get("bucket", {}).get("name")
        raw_key = s3_info.get("object", {}).get("key", "")

        # S3 keys in event notifications are URL-encoded
        object_key = urllib.parse.unquote_plus(raw_key)

        if not bucket_name or not object_key:
            logger.warning(json.dumps({"error": "invalid_record", "record": record}))
            continue

        # =====================================================================
        # 1. RECURSION GUARD: Prevent Infinite Invocation Loops
        # =====================================================================
        # If this Lambda writes .zip files into the same bucket, any ObjectCreated
        # trigger could fire recursively unless filtered at both event and code level.
        if object_key.endswith(".zip"):
            logger.info(json.dumps({
                "action": "skip",
                "reason": "already_compressed_zip",
                "bucket": bucket_name,
                "key": object_key
            }))
            skipped.append(object_key)
            continue

        if not object_key.endswith(".json"):
            logger.info(json.dumps({
                "action": "skip",
                "reason": "non_json_extension",
                "bucket": bucket_name,
                "key": object_key
            }))
            skipped.append(object_key)
            continue

        # =====================================================================
        # 2. COMPRESS AND ARCHIVE
        # =====================================================================
        try:
            result = process_s3_object(bucket_name, object_key)
            processed.append(result)
        except Exception as exc:
            logger.error(json.dumps({
                "error": "processing_failed",
                "bucket": bucket_name,
                "key": object_key,
                "detail": str(exc)
            }), exc_info=True)
            errors.append({"key": object_key, "error": str(exc)})

    duration_ms = round((time.time() - start_time) * 1000, 2)
    summary = {
        "status": "success" if not errors else "partial_failure",
        "total_records": len(records),
        "processed_count": len(processed),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "duration_ms": duration_ms,
        "processed": processed,
        "errors": errors
    }
    logger.info(json.dumps({"summary": summary}))

    if errors:
        raise RuntimeError(f"Failed to process {len(errors)} object(s): {errors}")

    return {
        "statusCode": 200,
        "body": json.dumps(summary)
    }


def process_s3_object(bucket: str, key: str) -> dict:
    """
    Downloads original JSON, compresses into ZIP in-memory, uploads ZIP,
    and removes original JSON.
    """
    download_start = time.time()
    logger.info(json.dumps({"action": "fetch_object", "bucket": bucket, "key": key}))

    # 1. Fetch original JSON object
    response = s3_client.get_object(Bucket=bucket, Key=key)
    original_size = response["ContentLength"]
    content_bytes = response["Body"].read()
    download_time_ms = round((time.time() - download_start) * 1000, 2)

    # 2. Compress into ZIP buffer (DEFLATED)
    compress_start = time.time()
    zip_buffer = io.BytesIO()
    internal_filename = os.path.basename(key)

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(internal_filename, content_bytes)

    zip_bytes = zip_buffer.getvalue()
    compressed_size = len(zip_bytes)
    compress_time_ms = round((time.time() - compress_start) * 1000, 2)

    # Calculate compression ratio
    ratio = round((1 - (compressed_size / original_size)) * 100, 2) if original_size > 0 else 0.0

    # 3. Target ZIP object key
    if key.endswith(".json"):
        zip_key = key[:-5] + ".zip"
    else:
        zip_key = f"{key}.zip"

    upload_start = time.time()
    logger.info(json.dumps({
        "action": "upload_zip",
        "bucket": bucket,
        "zip_key": zip_key,
        "original_size_bytes": original_size,
        "compressed_size_bytes": compressed_size,
        "compression_ratio_pct": ratio
    }))

    # 4. Upload compressed ZIP back into the same S3 bucket
    s3_client.put_object(
        Bucket=bucket,
        Key=zip_key,
        Body=zip_bytes,
        ContentType="application/zip",
        Metadata={
            "original-filename": internal_filename,
            "original-size": str(original_size),
            "compression-type": "zip-deflated",
            "archived-by": "lambda-video-archiver"
        }
    )
    upload_time_ms = round((time.time() - upload_start) * 1000, 2)

    # 5. Delete original object only after confirmed successful ZIP upload
    delete_start = time.time()
    logger.info(json.dumps({"action": "delete_original", "bucket": bucket, "key": key}))
    s3_client.delete_object(Bucket=bucket, Key=key)
    delete_time_ms = round((time.time() - delete_start) * 1000, 2)

    return {
        "original_key": key,
        "archived_key": zip_key,
        "original_size_bytes": original_size,
        "compressed_size_bytes": compressed_size,
        "space_saved_bytes": original_size - compressed_size,
        "compression_ratio_pct": ratio,
        "timings_ms": {
            "download": download_time_ms,
            "compress": compress_time_ms,
            "upload": upload_time_ms,
            "delete": delete_time_ms
        }
    }

