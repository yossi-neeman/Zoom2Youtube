#!/usr/bin/env python3
"""
Zoom Recording Downloader
Downloads Zoom cloud recordings using the Zoom API
"""

import os
import requests
from datetime import datetime, timedelta
from pathlib import Path


class ZoomRecordingDownloader:
    def __init__(self, account_id, client_id, client_secret):
        """
        Initialize the Zoom downloader with OAuth credentials.

        Args:
            account_id: Your Zoom Account ID
            client_id: Your Zoom OAuth Client ID
            client_secret: Your Zoom OAuth Client Secret
        """
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.base_url = "https://api.zoom.us/v2"

    def get_access_token(self):
        """Get OAuth access token using Server-to-Server OAuth"""
        auth_url = "https://zoom.us/oauth/token"
        url = (f"{auth_url}?grant_type=account_credentials"
               f"&account_id={self.account_id}")

        response = requests.post(
            url,
            auth=(self.client_id, self.client_secret),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            print("✓ Successfully authenticated with Zoom API")
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.text}")

    def get_recordings(self, user_id='me', from_date=None,
                       to_date=None):
        """
        Get list of cloud recordings for a user.

        Args:
            user_id: Zoom user ID or 'me' for authenticated user
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format)
        """
        if not self.access_token:
            self.get_access_token()

        # Default to last 30 days if no dates provided
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')

        url = f"{self.base_url}/users/{user_id}/recordings"
        params = {
            'from': from_date,
            'to': to_date,
            'page_size': 300
        }

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        all_recordings = []

        while url:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                meetings = data.get('meetings', [])
                all_recordings.extend(meetings)

                # Check for next page
                url = data.get('next_page_token')
                if url:
                    params['next_page_token'] = url
                    url = f"{self.base_url}/users/{user_id}/recordings"
                else:
                    url = None
            else:
                raise Exception(f"Failed to get recordings: {response.text}")

        print(f"✓ Found {len(all_recordings)} recording(s)")
        return all_recordings

    def download_recording(self, download_url, output_path, filename=None):
        """
        Download a single recording file.

        Args:
            download_url: The download URL from the recording object
            output_path: Directory to save the file
            filename: Optional custom filename
        """
        if not self.access_token:
            self.get_access_token()

        # Add access token to download URL
        url = f"{download_url}?access_token={self.access_token}"

        # Create output directory if it doesn't exist
        Path(output_path).mkdir(parents=True, exist_ok=True)

        # Get filename from URL if not provided
        if not filename:
            filename = download_url.split('/')[-1].split('?')[0]

        filepath = os.path.join(output_path, filename)

        print(f"Downloading: {filename}...")

        response = requests.get(url, stream=True)

        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            progress = (downloaded / total_size) * 100
                            print(f"Progress: {progress:.1f}%", end='\r')

            print(f"\n✓ Downloaded: {filepath}")
            return filepath
        else:
            raise Exception(f"Failed to download recording: {response.status_code}")

    def download_all_recordings(self, output_dir='recordings',
                                user_id='me', from_date=None,
                                to_date=None):
        """
        Download all recordings for a user within a date range.

        Args:
            output_dir: Directory to save recordings
            user_id: Zoom user ID or 'me'
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        """
        recordings = self.get_recordings(user_id, from_date, to_date)

        downloaded_files = []

        for meeting in recordings:
            meeting_topic = meeting.get('topic', 'Unknown')
            meeting_date = meeting.get('start_time', '').split('T')[0]
            meeting_id = meeting.get('id', '')

            # Create a folder for each meeting
            meeting_folder = os.path.join(
                output_dir,
                f"{meeting_date}_{meeting_topic}_{meeting_id}".replace('/', '_')
            )

            print(f"\n📹 Meeting: {meeting_topic} ({meeting_date})")

            recording_files = meeting.get('recording_files', [])

            for rec_file in recording_files:
                file_type = rec_file.get('file_type', 'unknown')
                recording_type = rec_file.get('recording_type', 'unknown')
                download_url = rec_file.get('download_url')

                if download_url:
                    # Create descriptive filename
                    file_extension = rec_file.get('file_extension', 'mp4')
                    filename = f"{recording_type}_{file_type}.{file_extension}"

                    try:
                        filepath = self.download_recording(
                            download_url,
                            meeting_folder,
                            filename
                        )
                        downloaded_files.append(filepath)
                    except Exception as e:
                        print(f"✗ Error downloading {filename}: {str(e)}")

        print(f"\n✓ Downloaded {len(downloaded_files)} file(s) total")
        return downloaded_files

    def download_todays_recording(self, output_dir='recordings',
                                  user_id='me'):
        """
        Download today's recording with user selection if multiple exist.
        Only downloads MP4 video files.
        If no recordings found today, searches previous 5 days.

        Args:
            output_dir: Directory to save recordings
            user_id: Zoom user ID or 'me'

        Returns:
            List of downloaded file paths
        """
        # Get today's date
        today_date = datetime.now()
        today = today_date.strftime('%Y-%m-%d')

        print(f"Searching for recordings from today ({today})...")

        # Fetch only today's recordings
        recordings = self.get_recordings(
            user_id=user_id,
            from_date=today,
            to_date=today
        )

        # Filter recordings that have MP4 files
        recordings_with_mp4 = []
        for meeting in recordings:
            recording_files = meeting.get('recording_files', [])
            has_mp4 = any(
                f.get('file_type') == 'MP4'
                for f in recording_files
            )
            if has_mp4:
                recordings_with_mp4.append(meeting)

        # If no recordings today, search previous 5 days
        if not recordings_with_mp4:
            print("\nNo recordings found for today.")
            print("Searching recordings from the previous 5 days...")
            
            # Calculate date range for previous 5 days
            five_days_ago = (today_date - timedelta(days=5)).strftime('%Y-%m-%d')
            yesterday = (today_date - timedelta(days=1)).strftime('%Y-%m-%d')
            
            recordings = self.get_recordings(
                user_id=user_id,
                from_date=five_days_ago,
                to_date=yesterday
            )
            
            # Filter recordings that have MP4 files
            for meeting in recordings:
                recording_files = meeting.get('recording_files', [])
                has_mp4 = any(
                    f.get('file_type') == 'MP4'
                    for f in recording_files
                )
                if has_mp4:
                    recordings_with_mp4.append(meeting)
            
            if not recordings_with_mp4:
                print(f"\nNo recordings with video files found in the last 5 days.")
                return []
            else:
                print(f"✓ Found {len(recordings_with_mp4)} recording(s) from the last 5 days")

        # If only one recording, download it automatically
        if len(recordings_with_mp4) == 1:
            selected_meeting = recordings_with_mp4[0]
            print(f"\nFound 1 recording: {selected_meeting.get('topic')}")
            print("Downloading automatically...\n")
        else:
            # Multiple recordings - show selection menu
            print(f"\nFound {len(recordings_with_mp4)} recording(s):\n")

            for idx, meeting in enumerate(recordings_with_mp4, 1):
                topic = meeting.get('topic', 'Unknown')
                start_time = meeting.get('start_time', '')
                duration = meeting.get('duration', 0)

                # Parse and format date and time
                if start_time:
                    try:
                        dt = datetime.strptime(
                            start_time,
                            '%Y-%m-%dT%H:%M:%SZ'
                        )
                        date_str = dt.strftime('%Y-%m-%d')
                        time_str = dt.strftime('%I:%M %p')
                        datetime_str = f"{date_str} {time_str}"
                    except Exception:
                        datetime_str = start_time
                else:
                    datetime_str = 'Unknown'

                print(f"[{idx}] {topic} - {datetime_str} (Duration: {duration} min)")

            # Prompt user for selection
            while True:
                try:
                    choice = input(
                        f"\nSelect recording to download (1-{len(recordings_with_mp4)}) "
                        "or 'q' to quit: "
                    ).strip()

                    if choice.lower() == 'q':
                        print("Download cancelled.")
                        return []

                    choice_num = int(choice)
                    if 1 <= choice_num <= len(recordings_with_mp4):
                        selected_meeting = recordings_with_mp4[choice_num - 1]
                        break
                    else:
                        print(
                            f"Invalid choice. Please enter a number "
                            f"between 1 and {len(recordings_with_mp4)}."
                        )
                except ValueError:
                    print("Invalid input. Please enter a number or 'q' to quit.")

        # Download only MP4 files from selected meeting
        meeting_topic = selected_meeting.get('topic', 'Unknown')
        meeting_date = selected_meeting.get('start_time', '').split('T')[0]
        meeting_id = selected_meeting.get('id', '')

        meeting_folder = os.path.join(
            output_dir,
            f"{meeting_date}_{meeting_topic}_{meeting_id}".replace('/', '_')
        )

        print(f"\n📹 Meeting: {meeting_topic} ({meeting_date})")

        recording_files = selected_meeting.get('recording_files', [])
        downloaded_files = []

        for rec_file in recording_files:
            file_type = rec_file.get('file_type', 'unknown')

            # Only download MP4 files
            if file_type != 'MP4':
                continue

            recording_type = rec_file.get('recording_type', 'unknown')
            download_url = rec_file.get('download_url')

            if download_url:
                file_extension = rec_file.get('file_extension', 'mp4')
                filename = f"{recording_type}_{file_type}.{file_extension}"

                try:
                    filepath = self.download_recording(
                        download_url,
                        meeting_folder,
                        filename
                    )
                    downloaded_files.append(filepath)
                except Exception as e:
                    print(f"✗ Error downloading {filename}: {str(e)}")

        if downloaded_files:
            print(f"\n✓ Downloaded {len(downloaded_files)} MP4 file(s)")
        else:
            print("\n✗ No MP4 files were downloaded")

        return downloaded_files


def main():
    """Download today's Zoom recordings (MP4 only)"""

    # Load credentials from environment variables
    ACCOUNT_ID = os.getenv('ZOOM_ACCOUNT_ID')
    CLIENT_ID = os.getenv('ZOOM_CLIENT_ID')
    CLIENT_SECRET = os.getenv('ZOOM_CLIENT_SECRET')

    if not all([ACCOUNT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("Error: Missing Zoom credentials!")
        print("Please set the following environment variables:")
        print("  - ZOOM_ACCOUNT_ID")
        print("  - ZOOM_CLIENT_ID")
        print("  - ZOOM_CLIENT_SECRET")
        return

    # Initialize downloader
    downloader = ZoomRecordingDownloader(ACCOUNT_ID, CLIENT_ID, CLIENT_SECRET)

    # Download today's recordings (MP4 only)
    downloader.download_todays_recording(
        output_dir='recordings',
        user_id='me'
    )


if __name__ == '__main__':
    main()
