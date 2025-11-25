import os
import re
import time
import random
import logging
import asyncio
import datetime
import argparse
import requests
import subprocess
import signal
from pathlib import Path  # Added for robust path handling

import yt_dlp

from mutagen.id3 import ID3, TIT2, TPE1, TALB, TXXX
from mutagen import MutagenError

from .utils import extract_id_from_url, sanitize_name
from .vlc_manager import VLCManager
from .music_library import MusicLibrary

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - line %(lineno)d - %(message)s'
)

BUFFER_SIZE = 20
MIN_SONGS_TO_START = 3

async def extract_video_info(video_url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            logging.info(f"Extracted info for {video_url}: {info_dict.get('title')}")
            return info_dict
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error extracting info for {video_url}: {e}")
        return None

async def download_audio(video_url, playlist_name, music_library):
    # Ensure we use the base folder from the library instance
    playlist_folder = os.path.join(music_library.base_folder, playlist_name)

    # We download using the ID and the raw title to ensure uniqueness during download
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(playlist_folder, '%(id)s_%(title)s.%(ext)s'),  # Do not sanitize the title here
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
        'quiet': True
    }
    try:
        start_time = datetime.datetime.now()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            end_time = datetime.datetime.now()

            video_id = info_dict.get('id')
            title = info_dict.get('title')
            artist = info_dict.get('uploader')
            album = playlist_name

            if not music_library.song_exists(playlist_name, video_id):
                # The file currently exists on disk with the RAW (unsanitized) title
                raw_file_path = os.path.join(playlist_folder, f"{video_id}_{title}.mp3")

                if os.path.exists(raw_file_path):
                    logging.info(f"File downloaded successfully: {raw_file_path}")

                    # CRITICAL FIX:
                    # We pass the SANITIZED title to the library.
                    # The library's add_song method will take our 'raw_file_path'
                    # and rename it to match the sanitized title.
                    clean_title = sanitize_name(title)

                    music_library.add_song(
                        playlist_name=playlist_name,
                        video_id=video_id,
                        title=clean_title,
                        file_path=raw_file_path
                    )

                    # Now we calculate the new path (post-rename) to apply metadata
                    final_path = os.path.join(playlist_folder, f"{video_id}_{clean_title}.mp3")

                    try:
                        audio = ID3(final_path)
                        audio.add(TIT2(encoding=3, text=title)) # Keep original title in metadata
                        if artist:
                            audio.add(TPE1(encoding=3, text=artist))
                        audio.add(TALB(encoding=3, text=album))  # Set album as playlist name
                        audio.add(TXXX(encoding=3, desc='YouTubeID', text=video_id))
                        audio.add(TXXX(encoding=3, desc='PlaylistName', text=playlist_name))  # Save playlist info in metadata
                        audio.save()
                    except (MutagenError, FileNotFoundError) as e:
                        logging.error(f"Metadata error for {final_path}: {e}")
                        return None

                    logging.info(f"Downloaded and processed: {clean_title}")
                    logging.info(f"Saved as: {final_path} with metadata - Title: {title}, Artist: {artist}, Album: {album}, YouTubeID: {video_id}")

                    return final_path  # Return the file path instead of adding directly to VLC playlist
                else:
                    logging.error(f"Expected file not found: {raw_file_path}")
                    return None
            else:
                return None
    except (yt_dlp.utils.DownloadError, FileNotFoundError) as e:
        logging.error(f"Error processing {video_url}: {e}")
        return None
    except MutagenError as e:
        logging.error(f"Mutagen error while processing {file_path}: {e}")
        return None

async def maintain_buffer(videos, playlist_name, music_library, vlc_manager, current_song_index):
    buffer = []  # Local buffer to track which songs need to be added to the VLC playlist

    if vlc_manager.vlc_process is None or vlc_manager.vlc_process.poll() is not None:
        return  # Exit if VLC is not running

    n_songs = vlc_manager.get_playlist_length()
    songs_ahead = n_songs - current_song_index

    # Ensure the buffer has the right number of songs ahead
    while songs_ahead < BUFFER_SIZE and videos:
        next_video_url = videos.pop(0)
        info_dict = await extract_video_info(next_video_url)
        video_id = info_dict.get('id', None) if info_dict else None
        title = sanitize_name(info_dict.get('title', None)) if info_dict else None

        if video_id and title:
            # Check if the song is already in the buffer or playlist
            song_in_playlist = any(video_id in path for path in vlc_manager.playlist)
            song_in_buffer = any(video_id in path for path in buffer)

            if not music_library.song_exists(playlist_name, video_id) and not song_in_playlist and not song_in_buffer:
                file_path = await download_audio(next_video_url, playlist_name, music_library)
                if file_path:
                    buffer.append(file_path)  # Add the downloaded song to the buffer
            else:
                logging.info(f"Song {title} already exists or is already queued. Skipping download.")
                paths = music_library.get_song_paths_by_id(video_id, playlist_name)
                if paths and not song_in_playlist and not song_in_buffer:
                    buffer.append(paths[0])  # Add existing song path to the buffer

        songs_ahead = len(buffer) + n_songs - current_song_index

    # Add songs from buffer to VLC playlist in the correct order
    while buffer:
        song_to_add = buffer.pop(0)
        if song_to_add not in vlc_manager.playlist:  # Double check to avoid duplicates
            await vlc_manager.add_to_playlist(song_to_add)


async def player_loop(vlc_manager, current_song_index):
    current_song = None
    if vlc_manager.vlc_process and vlc_manager.vlc_process.poll() is None:
        try:
            await vlc_manager.update_current_song_index()
            new_song, new_song_index = await vlc_manager.get_current_song()
            if new_song_index != current_song_index:
                current_song = new_song
                current_song_index = new_song_index
                logging.info(f"Currently playing: {current_song} (Index: {current_song_index})")
            else:
                pass
                #logging.info(f"No change in the current song.")
            return current_song_index  # Return the updated song index
        except requests.RequestException as e:
            logging.error(f"Error checking VLC status: {e}")
            return -1

async def main_loop(videos, playlist_name, music_library, vlc_manager, alarm_time, test_mode):
    alarm_triggered = False
    server_started = False
    current_song_index = -1

    while True:
        current_time = datetime.datetime.now()

        # Trigger logic: Either test mode OR time reached
        should_trigger = test_mode or (alarm_time and current_time >= alarm_time)

        if should_trigger:
            if not alarm_triggered:
                logging.info("Alarm triggered!")

                # Wait for enough songs before starting (unless downloading all)
                if music_library.count_songs(playlist_name) >= MIN_SONGS_TO_START:
                    vlc_manager.initialize_vlc_server()
                    while not vlc_manager.is_server_running():
                        logging.info("Waiting for VLC server to start...")
                        await asyncio.sleep(1)

                    # Add initial batch
                    for song in music_library.get_song_paths(playlist_name)[:BUFFER_SIZE]:
                        await vlc_manager.add_to_playlist(song)
                    await vlc_manager.start_playback()

                    server_started = True
                alarm_triggered = True

        if server_started:
            current_song_index = await player_loop(vlc_manager, current_song_index)  # Get the current song index
            await maintain_buffer(videos, playlist_name, music_library, vlc_manager, current_song_index)

        await asyncio.sleep(.25)

async def download_entire_playlist(videos, playlist_name, music_library):
    """Downloads the entire playlist at once."""
    logging.info("Starting download of entire playlist...")
    for video_url in videos:
        await download_audio(video_url, playlist_name, music_library)
    logging.info("Entire playlist download complete.")

def signal_handler(signal, frame):
    logging.info("Ctrl+C detected. Exiting gracefully...")
    for task in asyncio.all_tasks():
        task.cancel()
    asyncio.get_event_loop().stop()

async def main(playlist_url, hour_alarm, minute_alarm, base_dir, test_mode, validate, shuffle, download_all):
    signal.signal(signal.SIGINT, signal_handler)

    start_time = datetime.datetime.now()
    logging.info(f"Program started at {start_time}")

    # Ensure the music directory exists
    if not os.path.exists(base_dir):
        try:
            os.makedirs(base_dir)
            logging.info(f"Created music directory at: {base_dir}")
        except OSError as e:
            logging.error(f"Could not create directory {base_dir}: {e}")
            return

    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True
    }

    logging.info("Fetching playlist info...")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            videos = [entry['url'] for entry in playlist_info['entries']]
            playlist_name = sanitize_name(playlist_info.get('title', 'Unknown Playlist'))
    except Exception as e:
        logging.error(f"Failed to fetch playlist info: {e}")
        return

    if not videos:
        logging.error("No videos found in the playlist.")
        return

    if shuffle:
        random.shuffle(videos)

    # Initialize library with the user-selected (or default) base folder
    music_library = MusicLibrary(base_dir, validate=validate)
    music_library.initialize_playlist(playlist_name)
    music_library.check_metadata(playlist_name)
    music_library.clean_up_non_mp3_files(playlist_name)

    if validate:
        music_library.validate_songs(playlist_name)

    vlc_manager = VLCManager()

    if download_all:
        # Download the entire playlist without buffering
        await download_entire_playlist(videos, playlist_name, music_library)
        # If testing, we might still want to play after downloading all?
        # For now, following logic: download-all just downloads.
        # If you want to play after, user can run without --download-all next time.
        if test_mode:
             # Logic if user wants to play immediately after download-all in test mode
             # Reuse main_loop logic or just exit?
             # Let's assume 'download-all' implies preparation mode, but if 'test' is on, we play.
             logging.info("Download complete. Starting playback due to --test flag.")
             await main_loop(videos, playlist_name, music_library, vlc_manager, None, test_mode)
    else:
        # Calculate Wake Up Time
        wake_up_time = None
        if not test_mode:
            now = datetime.datetime.now()
            wake_up_time = datetime.datetime(now.year, now.month, now.day, hour_alarm, minute_alarm)
            if now > wake_up_time:
                wake_up_time += datetime.timedelta(days=1)
            logging.info(f"Alarm set for {wake_up_time.strftime('%A, %B %d, %Y %I:%M %p')}")

        # Initial buffer fill
        logging.info("Checking initial buffer...")
        # Create a copy of the list for downloading initial buffer so we don't pop from main list yet?
        # Actually, popping is fine as long as we maintain the order.
        # But we need 'videos' list for main_loop.

        # We need to peek at the first few videos without removing them from the main rotation permanently
        # OR just rely on main_loop to fill the rest.
        # Let's just pre-download the first few if missing.
        for i in range(min(MIN_SONGS_TO_START, len(videos))):
             # We reuse the download logic but don't pop yet to keep index sync simple
             await download_audio(videos[i], playlist_name, music_library)

        logging.info(f"Finished checking initial data buffer.")
        await main_loop(videos, playlist_name, music_library, vlc_manager, wake_up_time, test_mode)

def entry_point():
    """
    The main entry point for the 'youtube-alarm' command line script.
    """
    parser = argparse.ArgumentParser(
                    prog='YoutubeAlarm',
                    description='Launches youtube with an alarm.')

    # 1. Hour and Minute are now OPTIONAL in the parser
    parser.add_argument('--hour', type=int, required=False, help='Alarm hour (0-23)')
    parser.add_argument('--minute', type=int, required=False, help='Alarm minute (0-59)')

    parser.add_argument('--playlist', type=str, required=True, help='YouTube playlist URL')

    # 2. New argument for base directory
    # Default is ~/Music/YoutubeAlarm
    default_music_dir = os.path.join(Path.home(), "Music", "YoutubeAlarm")
    parser.add_argument('--base-dir', type=str, default=default_music_dir,
                        help=f'Directory to save music (default: {default_music_dir})')

    parser.add_argument('--test', action='store_true', help='Test mode (starts immediately)')
    parser.add_argument('--validate', action='store_true', help='Validate MP3 files')
    parser.add_argument('--shuffle', action='store_true', help='Shuffle the playlist')
    parser.add_argument('--download-all', action='store_true', help='Download entire playlist immediately')

    args = parser.parse_args()

    # 3. Manual validation logic
    # If we are NOT testing AND NOT downloading all, we MUST have time set.
    if not (args.test or args.download_all):
        if args.hour is None or args.minute is None:
            parser.error("the following arguments are required: --hour, --minute (unless using --test or --download-all)")

    asyncio.run(main(
        playlist_url=args.playlist,
        hour_alarm=args.hour,
        minute_alarm=args.minute,
        base_dir=args.base_dir,
        test_mode=args.test,
        validate=args.validate,
        shuffle=args.shuffle,
        download_all=args.download_all
    ))

if __name__ == "__main__":
    entry_point()
