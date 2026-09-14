"""
Unit tests for Lambda handler logic (compression, recursion guards, and error cases).
"""

import hashlib
import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import zipfile

# Add lambda/ to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "lambda"))

import app


class TestLambdaHandler(unittest.TestCase):

    def setUp(self):
        self.mock_s3 = MagicMock()
        app.s3_client = self.mock_s3

    def test_empty_event(self):
        result = app.lambda_handler({}, None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("No records found", body["message"])

    def test_recursion_guard_skips_zip(self):
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "archives/video_metadata.zip"}
                    }
                }
            ]
        }
        result = app.lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["skipped_count"], 1)
        self.assertEqual(body["processed_count"], 0)
        self.mock_s3.get_object.assert_not_called()

    def test_skips_non_json_files(self):
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "videos/raw_footage.mp4"}
                    }
                }
            ]
        }
        result = app.lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["skipped_count"], 1)
        self.assertEqual(body["processed_count"], 0)
        self.mock_s3.get_object.assert_not_called()

    def test_successful_compression_and_cleanup(self):
        raw_json = json.dumps({"video_id": "vid-123", "score": 0.99}).encode("utf-8")
        original_sha256 = hashlib.sha256(raw_json).hexdigest()

        # Mock S3 GetObject
        mock_body = MagicMock()
        mock_body.read.return_value = raw_json
        self.mock_s3.get_object.return_value = {
            "ContentLength": len(raw_json),
            "Body": mock_body
        }

        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "metadata/video_123.json"}
                    }
                }
            ]
        }

        result = app.lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["processed_count"], 1)
        self.assertEqual(body["error_count"], 0)

        # Verify S3 PutObject was called with .zip key
        self.mock_s3.put_object.assert_called_once()
        put_kwargs = self.mock_s3.put_object.call_args[1]
        self.assertEqual(put_kwargs["Bucket"], "test-bucket")
        self.assertEqual(put_kwargs["Key"], "metadata/video_123.zip")

        # Verify uploaded zip contents
        uploaded_zip_bytes = put_kwargs["Body"]
        with zipfile.ZipFile(io.BytesIO(uploaded_zip_bytes), "r") as zf:
            self.assertEqual(zf.namelist(), ["video_123.json"])
            extracted_data = zf.read("video_123.json")
            self.assertEqual(hashlib.sha256(extracted_data).hexdigest(), original_sha256)

        # Verify original object was deleted
        self.mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="metadata/video_123.json"
        )


if __name__ == "__main__":
    unittest.main()

