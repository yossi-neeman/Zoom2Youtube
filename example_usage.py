#!/usr/bin/env python3
"""
Example usage of the Zoom Recording Downloader
"""

import os
from zoom_downloader import ZoomRecordingDownloader


def example_1_download_all():
    """Example 1: Download all recordings from the last 30 days"""
    print("=== Example 1: Download all recordings ===\n")

    downloader = ZoomRecordingDownloader(
        account_id=os.getenv('ZOOM_ACCOUNT_ID'),
        client_id=os.getenv('ZOOM_CLIENT_ID'),
        client_secret=os.getenv('ZOOM_CLIENT_SECRET')
    )

    downloader.download_all_recordings(output_dir='recordings')


def example_2_list_recordings():
    """Example 2: List all recordings without downloading"""
    print("=== Example 2: List recordings ===\n")

    downloader = ZoomRecordingDownloader(
        account_id=os.getenv('ZOOM_ACCOUNT_ID'),
        client_id=os.getenv('ZOOM_CLIENT_ID'),
        client_secret=os.getenv('ZOOM_CLIENT_SECRET')
    )

    recordings = downloader.get_recordings(from_date='2024-01-01', to_date='2024-12-31')

    for idx, meeting in enumerate(recordings, 1):
        print(f"{idx}. {meeting.get('topic', 'Untitled')}")
        print(f"   Date: {meeting.get('start_time', 'N/A')}")
        print(f"   Duration: {meeting.get('duration', 0)} minutes")
        print(f"   Recording count: {len(meeting.get('recording_files', []))}")
        print()


def example_3_specific_date_range():
    """Example 3: Download recordings from a specific date range"""
    print("=== Example 3: Download from specific date range ===\n")

    downloader = ZoomRecordingDownloader(
        account_id=os.getenv('ZOOM_ACCOUNT_ID'),
        client_id=os.getenv('ZOOM_CLIENT_ID'),
        client_secret=os.getenv('ZOOM_CLIENT_SECRET')
    )

    # Download recordings from January 2024
    downloader.download_all_recordings(
        output_dir='recordings/january_2024',
        from_date='2024-01-01',
        to_date='2024-01-31'
    )


def example_4_selective_download():
    """Example 4: Download only specific recordings (e.g., only videos)"""
    print("=== Example 4: Selective download ===\n")

    downloader = ZoomRecordingDownloader(
        account_id=os.getenv('ZOOM_ACCOUNT_ID'),
        client_id=os.getenv('ZOOM_CLIENT_ID'),
        client_secret=os.getenv('ZOOM_CLIENT_SECRET')
    )

    recordings = downloader.get_recordings()

    for meeting in recordings:
        meeting_topic = meeting.get('topic', 'Unknown')
        print(f"Processing: {meeting_topic}")

        recording_files = meeting.get('recording_files', [])

        for rec_file in recording_files:
            # Only download MP4 video files
            if rec_file.get('file_type') == 'MP4':
                download_url = rec_file.get('download_url')
                if download_url:
                    safe_topic = meeting_topic.replace('/', '_')
                    filename = f"{safe_topic}.mp4"
                    downloader.download_recording(
                        download_url=download_url,
                        output_path='recordings/videos_only',
                        filename=filename
                    )


def example_5_meeting_details():
    """Example 5: Get detailed information about recordings"""
    print("=== Example 5: Detailed recording information ===\n")

    downloader = ZoomRecordingDownloader(
        account_id=os.getenv('ZOOM_ACCOUNT_ID'),
        client_id=os.getenv('ZOOM_CLIENT_ID'),
        client_secret=os.getenv('ZOOM_CLIENT_SECRET')
    )

    recordings = downloader.get_recordings()

    for meeting in recordings:
        print(f"Meeting: {meeting.get('topic', 'Untitled')}")
        print(f"Meeting ID: {meeting.get('id')}")
        print(f"UUID: {meeting.get('uuid')}")
        print(f"Host: {meeting.get('host_email', 'N/A')}")
        print(f"Start Time: {meeting.get('start_time')}")
        print(f"Duration: {meeting.get('duration')} minutes")
        print(f"Total Size: {meeting.get('total_size', 0)} bytes")
        print(f"Recording Count: {meeting.get('recording_count', 0)}")

        print("\nRecording Files:")
        for rec_file in meeting.get('recording_files', []):
            print(f"  - Type: {rec_file.get('recording_type')}")
            print(f"    Format: {rec_file.get('file_type')}")
            print(f"    Size: {rec_file.get('file_size', 0)} bytes")
            print(f"    Extension: {rec_file.get('file_extension')}")

        print("\n" + "="*50 + "\n")


if __name__ == '__main__':
    # Check if credentials are set
    required_vars = [
        os.getenv('ZOOM_ACCOUNT_ID'),
        os.getenv('ZOOM_CLIENT_ID'),
        os.getenv('ZOOM_CLIENT_SECRET')
    ]
    if not all(required_vars):
        print("Error: Missing Zoom credentials!")
        print("Please set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, and ZOOM_CLIENT_SECRET")
        exit(1)

    # Run examples
    print("Choose an example to run:")
    print("1. Download all recordings from last 30 days")
    print("2. List all recordings (no download)")
    print("3. Download from specific date range")
    print("4. Download only video files (selective)")
    print("5. Show detailed recording information")

    choice = input("\nEnter choice (1-5): ").strip()

    examples = {
        '1': example_1_download_all,
        '2': example_2_list_recordings,
        '3': example_3_specific_date_range,
        '4': example_4_selective_download,
        '5': example_5_meeting_details
    }

    example_func = examples.get(choice)
    if example_func:
        example_func()
    else:
        print("Invalid choice!")
