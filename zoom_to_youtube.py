#!/usr/bin/env python3
"""
Zoom to YouTube - Complete workflow
Downloads today's Zoom recording and uploads to YouTube
"""

import os
from datetime import datetime
from zoom_downloader import ZoomRecordingDownloader
from youtube_uploader import YouTubeUploader
from PIL import Image, ImageDraw, ImageFont
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    RTL_SUPPORT = True
except ImportError:
    RTL_SUPPORT = False
    print("⚠ Warning: bidi libraries not installed. Hebrew text may not display correctly.")


def create_thumbnail(text, output_path='thumbnail.jpg',
                     template_path='graphics_template.jpg'):
    """
    Create thumbnail by overlaying text on template image.

    Args:
        text: Text to overlay on the template
        output_path: Path to save thumbnail
        template_path: Path to template image

    Returns:
        Path to created thumbnail
    """
    if not os.path.exists(template_path):
        print(f"⚠ Warning: Template not found: {template_path}")
        print("Creating thumbnail without template...")
        # Fallback to simple thumbnail
        img = Image.new('RGB', (1280, 720), color=(45, 55, 72))
    else:
        # Load template image
        img = Image.open(template_path)
        # Resize to YouTube standard if needed
        if img.size != (1280, 720):
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(img)

    # Try to use a font that supports Hebrew
    font_size = 180  # Font size for thumbnail text
    try:
        # Try David Libre and other Hebrew-supporting fonts (in order of preference)
        font_paths = [
            '/Library/Fonts/DavidLibre-Regular.ttf',  # David Libre (preferred)
            '/Library/Fonts/DavidLibre.ttf',
            '/Library/Fonts/David Libre.ttf',
            '/System/Library/Fonts/Supplemental/DavidLibre-Regular.ttf',
            '~/Library/Fonts/DavidLibre-Regular.ttf',
            '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',  # Fallback
            '/Library/Fonts/Arial Unicode.ttf',
        ]
        
        # Expand home directory
        font_paths = [os.path.expanduser(p) for p in font_paths]
        
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    # Test if font supports Hebrew by checking if it has Hebrew glyphs
                    print(f"Using font: {os.path.basename(font_path)}")
                    break
                except Exception as e:
                    print(f"Tried {font_path}: {e}")
                    continue
        
        if not font:
            print("⚠ Warning: No Hebrew font found, text may not display correctly")
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Font loading error: {e}")
        font = ImageFont.load_default()

    # Get image dimensions
    width, height = img.size

    # Process RTL text (Hebrew/Arabic) if support is available
    display_text = text
    if RTL_SUPPORT:
        try:
            # Reshape Arabic/Hebrew text and apply BiDi algorithm
            reshaped_text = arabic_reshaper.reshape(text)
            display_text = get_display(reshaped_text)
            print(f"✓ Applied RTL text processing")
        except Exception as e:
            print(f"⚠ RTL processing failed: {e}, using original text")
            display_text = text
    else:
        print("⚠ Using text without RTL processing (install python-bidi for Hebrew support)")

    # Draw text in center of the black rectangle
    # The black rectangle spans horizontally across the middle of the image
    # For 1280x720 image:
    black_rect_top = 420
    black_rect_bottom = 655
    black_rect_height = black_rect_bottom - black_rect_top
    
    # Calculate text size
    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center horizontally on the entire image
    x = (width - text_width) // 2
    
    # Position text so its center is at y=420
    text_center_y = 420
    y = text_center_y - (text_height // 2)

    # Draw text with outline for better visibility
    outline_color = 'black'
    text_color = 'black'
    outline_width = 3

    # Draw outline
    for adj_x in range(-outline_width, outline_width + 1):
        for adj_y in range(-outline_width, outline_width + 1):
            draw.text((x + adj_x, y + adj_y), display_text, font=font, fill=outline_color)

    # Draw main text
    draw.text((x, y), display_text, fill=text_color, font=font)

    # Save thumbnail
    img.save(output_path, 'JPEG', quality=95)
    print(f"✓ Thumbnail created: {output_path}")

    return output_path


def main():
    """Main workflow: Download from Zoom and upload to YouTube"""

    print("=" * 70)
    print("Zoom to YouTube - Automated Upload")
    print("=" * 70)
    print()

    # Step 1: Download from Zoom
    print("STEP 1: Downloading from Zoom")
    print("-" * 70)

    ZOOM_ACCOUNT_ID = os.getenv('ZOOM_ACCOUNT_ID')
    ZOOM_CLIENT_ID = os.getenv('ZOOM_CLIENT_ID')
    ZOOM_CLIENT_SECRET = os.getenv('ZOOM_CLIENT_SECRET')

    if not all([ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET]):
        print("Error: Missing Zoom credentials!")
        print("Please set the following environment variables:")
        print("  - ZOOM_ACCOUNT_ID")
        print("  - ZOOM_CLIENT_ID")
        print("  - ZOOM_CLIENT_SECRET")
        return

    # Download today's recording
    zoom_downloader = ZoomRecordingDownloader(
        ZOOM_ACCOUNT_ID,
        ZOOM_CLIENT_ID,
        ZOOM_CLIENT_SECRET
    )

    downloaded_files = zoom_downloader.download_todays_recording(
        output_dir='recordings',
        user_id='me'
    )

    if not downloaded_files:
        print("\nNo files to upload. Exiting.")
        return

    # Step 2: Upload to YouTube
    print("\n" + "=" * 70)
    print("STEP 2: Uploading to YouTube")
    print("-" * 70)

    # Get video file (should be the first/only MP4)
    video_file = downloaded_files[0]

    # Extract meeting info
    filename = os.path.basename(video_file)
    folder_name = os.path.basename(os.path.dirname(video_file))

    # Parse date from folder
    # Format: YYYY-MM-DD_MeetingName_MeetingID
    parts = folder_name.split('_', 1)
    date_str = parts[0] if parts else datetime.now().strftime('%Y-%m-%d')

    print(f"\nVideo file: {video_file}")
    print(f"Date: {date_str}")

    # Prompt for custom video title
    print("\n" + "=" * 70)
    default_title = parts[1].rsplit('_', 1)[0] if len(parts) > 1 else 'Zoom Recording'
    title = input(f"Enter video title [default: {default_title}]: ").strip()
    if not title:
        title = default_title

    description = ""  # Empty description as requested

    print(f"Using title: {title}")

    # Prompt for privacy setting
    print("\nPrivacy options:")
    print("  1. Private (only you can see)")
    print("  2. Unlisted (anyone with link can see)")
    print("  3. Public (everyone can see)")

    while True:
        privacy_choice = input("\nSelect privacy (1-3) [default: 1]: ").strip() or '1'
        if privacy_choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")

    privacy_map = {
        '1': 'private',
        '2': 'unlisted',
        '3': 'public'
    }
    privacy = privacy_map[privacy_choice]

    # Initialize YouTube uploader
    youtube_uploader = YouTubeUploader(client_secrets_file='client_secrets.json')

    # Get or create playlist
    playlist_id = None
    use_playlist = input("\nAdd to playlist? (y/n) [default: n]: ").strip().lower()

    if use_playlist == 'y':
        print("\nFetching your playlists...")
        try:
            playlists = youtube_uploader.list_playlists()

            if playlists:
                print("\nYour playlists:")
                for idx, pl in enumerate(playlists, 1):
                    print(f"  [{idx}] {pl['title']} ({pl['item_count']} videos)")

                print(f"  [0] Create new playlist")

                while True:
                    choice = input(f"\nSelect playlist (0-{len(playlists)}) or 'n' to skip: ").strip()

                    if choice.lower() == 'n':
                        break

                    try:
                        choice_num = int(choice)
                        if choice_num == 0:
                            # Create new playlist
                            pl_name = input("Enter new playlist name: ").strip()
                            if pl_name:
                                playlist_id = youtube_uploader.create_playlist(
                                    title=pl_name,
                                    description="Zoom meeting recordings",
                                    privacy=privacy
                                )
                            break
                        elif 1 <= choice_num <= len(playlists):
                            playlist_id = playlists[choice_num - 1]['id']
                            print(f"Selected: {playlists[choice_num - 1]['title']}")
                            break
                        else:
                            print(f"Invalid choice. Please enter 0-{len(playlists)}.")
                    except ValueError:
                        print("Invalid input. Please enter a number or 'n'.")
            else:
                print("\nNo playlists found. Create one?")
                create = input("Create new playlist? (y/n): ").strip().lower()
                if create == 'y':
                    pl_name = input("Enter playlist name: ").strip()
                    if pl_name:
                        playlist_id = youtube_uploader.create_playlist(
                            title=pl_name,
                            description="Zoom meeting recordings",
                            privacy=privacy
                        )
        except Exception as e:
            print(f"⚠ Warning: Could not fetch playlists: {e}")

    # Create thumbnail
    thumbnail_path = None
    use_thumbnail = input("\nGenerate thumbnail? (y/n) [default: y]: ").strip().lower()

    if use_thumbnail != 'n':
        # Prompt for thumbnail text
        thumbnail_text = input("Enter thumbnail text: ").strip()
        
        if thumbnail_text:
            try:
                thumbnail_path = create_thumbnail(
                    thumbnail_text,
                    'temp_thumbnail.jpg',
                    'graphics_template.jpg'
                )
            except Exception as e:
                print(f"⚠ Warning: Could not create thumbnail: {e}")
                print("Continuing without thumbnail...")
        else:
            print("No thumbnail text provided, skipping thumbnail...")

    try:
        # Upload video
        video_id = youtube_uploader.upload_video(
            video_file=video_file,
            title=title,
            description=description,
            privacy=privacy,
            tags=['zoom', 'meeting', 'recording', date_str],
            playlist_id=playlist_id,
            thumbnail_file=thumbnail_path
        )

        # Clean up thumbnail
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

        print("\n" + "=" * 70)
        print("✓ WORKFLOW COMPLETE!")
        print("=" * 70)
        print(f"\nVideo uploaded to YouTube:")
        print(f"https://www.youtube.com/watch?v={video_id}")
        print()

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nTo fix this:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
        print("2. Create a project and enable YouTube Data API v3")
        print("3. Create OAuth 2.0 credentials (Desktop app)")
        print("4. Download the JSON file and save it as 'client_secrets.json'")
        return

    except Exception as e:
        print(f"\nError uploading to YouTube: {e}")
        return


if __name__ == '__main__':
    main()
