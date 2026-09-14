"""
Generates realistic video processing metadata JSON files for testing.
Simulates high-throughput on-premises video processing engines.
"""

import json
import os
import sys

def generate_video_metadata(target_size_mb: float = 10.0) -> bytes:
    """
    Generates a realistic video processing result JSON structure
    until it reaches approximately target_size_mb.
    """
    base_structure = {
        "video_id": "vid-respondio-2026-09-84729",
        "pipeline_version": "v3.8.2-prod",
        "source": "on-premises-transcoder-cluster",
        "video_metadata": {
            "format": "mp4",
            "codec": "H.265 / HEVC",
            "resolution": "3840x2160",
            "fps": 60,
            "duration_seconds": 3600,
            "bitrate_kbps": 45000,
            "color_space": "BT.2020",
            "audio_channels": 6
        },
        "frames_analysis": []
    }

    target_bytes = int(target_size_mb * 1024 * 1024)

    # Reusable frame sample structure
    frame_template = {
        "frame_number": 0,
        "timestamp_ms": 16.66,
        "scene_id": "scene-0012",
        "detected_objects": [
            {"label": "person", "confidence": 0.984, "bbox": [120, 45, 340, 890]},
            {"label": "microphone", "confidence": 0.921, "bbox": [140, 120, 160, 210]},
            {"label": "laptop", "confidence": 0.895, "bbox": [310, 400, 520, 680]},
            {"label": "coffee_cup", "confidence": 0.742, "bbox": [530, 410, 560, 470]}
        ],
        "sentiment_score": 0.85,
        "face_recognition": [
            {"face_id": "actor-01", "emotion": "focused", "gaze_vector": [0.12, -0.05, 0.98]}
        ],
        "audio_transcript_segment": "Welcome back to the respond.io live technical demonstration."
    }

    current_data = base_structure
    frames_list = []
    
    # Calculate rough size of single frame in JSON
    frame_sample_bytes = len(json.dumps(frame_template).encode('utf-8'))
    needed_frames = max(1, target_bytes // (frame_sample_bytes + 2))

    for i in range(needed_frames):
        f = frame_template.copy()
        f["frame_number"] = i
        f["timestamp_ms"] = round(i * 16.666, 2)
        frames_list.append(f)

    current_data["frames_analysis"] = frames_list
    json_bytes = json.dumps(current_data, indent=2).encode("utf-8")

    # If slightly under or over, adjust padding
    if len(json_bytes) < target_bytes:
        padding_needed = target_bytes - len(json_bytes)
        current_data["_debug_padding"] = "X" * (padding_needed - 30)
        json_bytes = json.dumps(current_data, indent=2).encode("utf-8")

    return json_bytes

if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else "sample_video_metadata_10mb.json"
    size_mb = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    print(f"Generating ~{size_mb} MB mock video metadata JSON...")
    data = generate_video_metadata(size_mb)
    with open(out_path, "wb") as f:
        f.write(data)
    actual_mb = len(data) / (1024 * 1024)
    print(f"Created {out_path} ({actual_mb:.2f} MB, {len(data):,} bytes)")

