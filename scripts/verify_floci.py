"""
Comprehensive End-to-End Verification Harness for Floci Emulation
Author: Senior DevOps Candidate for respond.io

This script performs complete automated verification of Tasks 1 and 2:
1. Verifies connectivity to the local Floci AWS emulator (localhost:4566).
2. Creates an S3 test bucket (matching the IaC configuration).
3. Generates a realistic 10 MB video processing result JSON payload.
4. Uploads the JSON file to S3.
5. Triggers the Lambda archiver with the S3 ObjectCreated event.
6. Asserts:
   a. The .zip archive is uploaded to S3.
   b. The uncompressed content matches the original SHA-256 digest exactly (zero corruption).
   c. The original .json file is deleted from S3.
   d. The compression ratio is evaluated (~75-85% reduction).
7. Tests the Recursion Guard:
   - Simulates an event for the .zip file to guarantee no infinite loop occurs.
8. Tests Non-JSON filtering:
   - Confirms non-JSON files are ignored.
"""

import hashlib
import io
import json
import os
import sys
import time
import urllib.request
import zipfile
import boto3
from botocore.exceptions import ClientError

# Add lambda/ to sys.path so we can directly invoke the handler for testing
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "lambda"))

import app  # Lambda handler

# Set stdout to utf-8 if supported
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FLOCI_ENDPOINT = os.getenv("FLOCI_ENDPOINT", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
TEST_BUCKET = os.getenv("TEST_BUCKET", "respondio-video-metadata-archive-local")

def check_floci_health():
    """Verify Floci emulator is online."""
    print(f"\n[1/6] Checking Floci health at {FLOCI_ENDPOINT}...")
    try:
        req = urllib.request.Request(f"{FLOCI_ENDPOINT}/_floci/health")
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status == 200:
                print("  [OK] Floci emulator is ONLINE and healthy.")
                return True
    except Exception as e:
        print(f"  [FAIL] Failed to reach Floci at {FLOCI_ENDPOINT}: {e}")
        print("    Please run 'floci start' before running this script.")
        return False

def get_s3_client():
    """Returns a boto3 S3 client configured for Floci."""
    return boto3.client(
        "s3",
        endpoint_url=FLOCI_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )

def setup_test_bucket(s3):
    """Creates the test bucket if it does not exist."""
    print(f"\n[2/6] Ensuring test S3 bucket exists: s3://{TEST_BUCKET}...")
    try:
        s3.head_bucket(Bucket=TEST_BUCKET)
        print("  [OK] Bucket already exists.")
    except ClientError:
        try:
            s3.create_bucket(Bucket=TEST_BUCKET)
            print("  [OK] Successfully created bucket.")
        except Exception as e:
            print(f"  [FAIL] Failed to create bucket: {e}")
            sys.exit(1)

def run_verification():
    print("=" * 70)
    print(" respond.io Senior DevOps Assessment: Floci Verification Suite")
    print("=" * 70)

    if not check_floci_health():
        sys.exit(1)

    s3 = get_s3_client()
    setup_test_bucket(s3)

    # 3. Generate 10MB test JSON payload
    print("\n[3/6] Generating ~10 MB realistic video processing result JSON...")
    sys.path.insert(0, CURRENT_DIR)
    from generate_mock_data import generate_video_metadata
    
    start_gen = time.time()
    raw_json_bytes = generate_video_metadata(target_size_mb=10.0)
    original_size = len(raw_json_bytes)
    original_sha256 = hashlib.sha256(raw_json_bytes).hexdigest()
    print(f"  [OK] Generated payload: {original_size:,} bytes ({original_size / (1024*1024):.2f} MB) in {time.time()-start_gen:.2f}s")
    print(f"  [OK] Original SHA-256: {original_sha256}")

    # 4. Upload original JSON to S3
    test_key = "video_processing_results/cluster-01/camera-front-001.json"
    print(f"\n[4/6] Uploading original JSON to s3://{TEST_BUCKET}/{test_key}...")
    s3.put_object(
        Bucket=TEST_BUCKET,
        Key=test_key,
        Body=raw_json_bytes,
        ContentType="application/json"
    )
    print("  [OK] Upload complete.")

    # 5. Trigger Lambda Handler with simulated S3 ObjectCreated event
    print("\n[5/6] Triggering Lambda Archiver function...")
    s3_event = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": AWS_REGION,
                "eventTime": "2026-09-14T12:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {
                        "name": TEST_BUCKET,
                        "arn": f"arn:aws:s3:::{TEST_BUCKET}"
                    },
                    "object": {
                        "key": test_key,
                        "size": original_size
                    }
                }
            }
        ]
    }

    # Ensure app uses the Floci endpoint
    app.ENDPOINT_URL = FLOCI_ENDPOINT
    app.s3_client = s3

    exec_start = time.time()
    response = app.lambda_handler(s3_event, None)
    exec_duration = time.time() - exec_start

    print(f"  [OK] Lambda execution finished with status {response['statusCode']} in {exec_duration:.3f}s")
    body = json.loads(response["body"])
    print(f"  Execution summary: {json.dumps(body['processed'][0], indent=4)}")

    # 6. Assertions
    print("\n[6/6] Running validation assertions...")
    expected_zip_key = "video_processing_results/cluster-01/camera-front-001.zip"

    # Assertion A: Original JSON must be deleted
    original_exists = True
    try:
        s3.head_object(Bucket=TEST_BUCKET, Key=test_key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            original_exists = False
    assert not original_exists, f"Assertion Failed: Original object {test_key} still exists in S3!"
    print(f"  [OK] PASSED: Original object '{test_key}' was deleted from S3.")

    # Assertion B: Compressed ZIP must exist
    zip_obj = s3.get_object(Bucket=TEST_BUCKET, Key=expected_zip_key)
    compressed_bytes = zip_obj["Body"].read()
    compressed_size = len(compressed_bytes)
    ratio = (1 - (compressed_size / original_size)) * 100
    print(f"  [OK] PASSED: Compressed ZIP '{expected_zip_key}' exists in S3.")
    print(f"    - Original Size:   {original_size:,} bytes ({original_size / (1024*1024):.2f} MB)")
    print(f"    - Compressed Size: {compressed_size:,} bytes ({compressed_size / (1024*1024):.2f} MB)")
    print(f"    - Space Reduction: {ratio:.2f}% saved!")

    # Assertion C: Data Integrity (Decompress & compare SHA-256)
    with zipfile.ZipFile(io.BytesIO(compressed_bytes), "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 1, f"Expected 1 file inside zip, found: {namelist}"
        decompressed_data = zf.read(namelist[0])
        decompressed_sha256 = hashlib.sha256(decompressed_data).hexdigest()
        assert decompressed_sha256 == original_sha256, "Assertion Failed: Decompressed SHA-256 mismatch!"
    print(f"  [OK] PASSED: Data integrity verified. Extracted SHA-256 matches original.")

    # Assertion D: Recursion Guard Test (Simulate S3 event with .zip file)
    print("\n  [Bonus Test] Recursion Guard Verification...")
    recursive_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": TEST_BUCKET},
                    "object": {"key": expected_zip_key}
                }
            }
        ]
    }
    rec_res = app.lambda_handler(recursive_event, None)
    rec_body = json.loads(rec_res["body"])
    assert rec_body["skipped_count"] == 1, "Recursion guard failed to skip .zip file!"
    assert rec_body["processed_count"] == 0, "Recursion guard should not process .zip file!"
    print("  [OK] PASSED: Recursion guard successfully blocked re-invocation on .zip file.")

    # Assertion E: Non-JSON Filter Test
    non_json_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": TEST_BUCKET},
                    "object": {"key": "videos/sample.mp4"}
                }
            }
        ]
    }
    nj_res = app.lambda_handler(non_json_event, None)
    nj_body = json.loads(nj_res["body"])
    assert nj_body["skipped_count"] == 1, "Non-JSON filter failed!"
    print("  [OK] PASSED: Non-JSON files (.mp4) are safely filtered out.")

    print("\n" + "=" * 70)
    print(" ALL VERIFICATION CHECKS PASSED SUCCESSFULLY! ")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
