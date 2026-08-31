#!/usr/bin/env python3
"""
YouTube Video Uploader
Uploads videos to YouTube using the YouTube Data API v3
"""

import os
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload


class YouTubeUploader:
    def __init__(self, client_secrets_file='client_secrets.json'):
        """
        Initialize YouTube uploader.

        Args:
            client_secrets_file: Path to OAuth 2.0 client secrets JSON file
        """
        self.client_secrets_file = client_secrets_file
        self.credentials = None
        self.youtube = None
        self.scopes = [
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube'
        ]

    def authenticate(self):
        """
        Authenticate with YouTube using OAuth 2.0.
        Uses saved credentials if available, otherwise starts OAuth flow.
        """
        token_file = 'youtube_token.pickle'

        # Load saved credentials if they exist
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                self.credentials = pickle.load(token)

        # If credentials don't exist or are invalid, get new ones
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                print("Refreshing YouTube access token...")
                self.credentials.refresh(Request())
            else:
                print("Starting YouTube OAuth authentication...")
                print("A browser window will open for you to authorize the app.")

                if not os.path.exists(self.client_secrets_file):
                    raise FileNotFoundError(
                        f"Client secrets file not found: {self.client_secrets_file}\n"
                        "Please download it from Google Cloud Console."
                    )

                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file,
                    self.scopes
                )
                self.credentials = flow.run_local_server(port=8080)

            # Save credentials for future use
            with open(token_file, 'wb') as token:
                pickle.dump(self.credentials, token)

        # Build YouTube service
        self.youtube = googleapiclient.discovery.build(
            'youtube', 'v3', credentials=self.credentials
        )

        print("✓ Successfully authenticated with YouTube API")
        return self.youtube

    def upload_video(self, video_file, title, description='',
                     category='22', privacy='private', tags=None,
                     playlist_id=None, thumbnail_file=None):
        """
        Upload a video to YouTube.

        Args:
            video_file: Path to the video file to upload
            title: Video title
            description: Video description (optional)
            category: YouTube category ID (default: 22 = People & Blogs)
            privacy: Privacy status ('public', 'private', or 'unlisted')
            tags: List of tags for the video (optional)
            playlist_id: YouTube playlist ID to add video to (optional)
            thumbnail_file: Path to thumbnail image file (optional)

        Returns:
            Video ID of uploaded video
        """
        if not self.youtube:
            self.authenticate()

        if not os.path.exists(video_file):
            raise FileNotFoundError(f"Video file not found: {video_file}")

        print(f"\nUploading video: {os.path.basename(video_file)}")
        print(f"Title: {title}")
        print(f"Privacy: {privacy}")

        # Prepare video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'categoryId': category
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': False
            }
        }

        if tags:
            body['snippet']['tags'] = tags

        # Create media upload
        media = MediaFileUpload(
            video_file,
            chunksize=1024*1024,  # 1MB chunks
            resumable=True
        )

        # Execute upload
        request = self.youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        response = None
        last_progress = 0

        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                if progress != last_progress:
                    print(f"Upload progress: {progress}%")
                    last_progress = progress

        video_id = response['id']
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        print(f"\n✓ Video uploaded successfully!")
        print(f"Video ID: {video_id}")
        print(f"Video URL: {video_url}")

        # Upload thumbnail if provided
        if thumbnail_file:
            try:
                self.set_thumbnail(video_id, thumbnail_file)
            except Exception as e:
                print(f"⚠ Warning: Failed to set thumbnail: {e}")

        # Add to playlist if provided
        if playlist_id:
            try:
                self.add_to_playlist(video_id, playlist_id)
            except Exception as e:
                print(f"⚠ Warning: Failed to add to playlist: {e}")

        return video_id

    def set_thumbnail(self, video_id, thumbnail_file):
        """
        Set a custom thumbnail for a video.

        Args:
            video_id: YouTube video ID
            thumbnail_file: Path to thumbnail image file
        """
        if not self.youtube:
            self.authenticate()

        if not os.path.exists(thumbnail_file):
            raise FileNotFoundError(f"Thumbnail file not found: {thumbnail_file}")

        print(f"Setting thumbnail for video {video_id}...")

        request = self.youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_file)
        )

        response = request.execute()
        print("✓ Thumbnail set successfully!")

        return response

    def list_playlists(self):
        """
        List all playlists for the authenticated user.

        Returns:
            List of playlist dictionaries with id, title, and item count
        """
        if not self.youtube:
            self.authenticate()

        print("Fetching your playlists...")

        request = self.youtube.playlists().list(
            part='snippet,contentDetails',
            mine=True,
            maxResults=50
        )

        response = request.execute()
        playlists = []

        for item in response.get('items', []):
            playlist = {
                'id': item['id'],
                'title': item['snippet']['title'],
                'description': item['snippet'].get('description', ''),
                'item_count': item['contentDetails']['itemCount']
            }
            playlists.append(playlist)

        return playlists

    def add_to_playlist(self, video_id, playlist_id):
        """
        Add a video to a playlist.

        Args:
            video_id: YouTube video ID
            playlist_id: YouTube playlist ID

        Returns:
            Response from API
        """
        if not self.youtube:
            self.authenticate()

        print(f"Adding video to playlist...")

        request = self.youtube.playlistItems().insert(
            part='snippet',
            body={
                'snippet': {
                    'playlistId': playlist_id,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    }
                }
            }
        )

        response = request.execute()
        print("✓ Video added to playlist successfully!")

        return response

    def create_playlist(self, title, description='', privacy='private'):
        """
        Create a new playlist.

        Args:
            title: Playlist title
            description: Playlist description (optional)
            privacy: Privacy status ('public', 'private', or 'unlisted')

        Returns:
            Playlist ID
        """
        if not self.youtube:
            self.authenticate()

        print(f"Creating playlist: {title}")

        request = self.youtube.playlists().insert(
            part='snippet,status',
            body={
                'snippet': {
                    'title': title,
                    'description': description
                },
                'status': {
                    'privacyStatus': privacy
                }
            }
        )

        response = request.execute()
        playlist_id = response['id']

        print(f"✓ Playlist created successfully!")
        print(f"Playlist ID: {playlist_id}")
        print(f"Playlist URL: https://www.youtube.com/playlist?list={playlist_id}")

        return playlist_id


def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python youtube_uploader.py <video_file> [title] [description]")
        print("\nExample:")
        print("  python youtube_uploader.py video.mp4 'My Meeting' 'Meeting recording'")
        sys.exit(1)

    video_file = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(video_file)
    description = sys.argv[3] if len(sys.argv) > 3 else ''

    # Initialize uploader
    uploader = YouTubeUploader()

    try:
        # Upload video
        video_id = uploader.upload_video(
            video_file=video_file,
            title=title,
            description=description,
            privacy='private',  # Change to 'public' or 'unlisted' as needed
            tags=['zoom', 'meeting', 'recording']
        )

        print(f"\n✓ Upload complete! Video ID: {video_id}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error uploading video: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
