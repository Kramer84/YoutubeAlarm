import time
import datetime
import argparse
import os
import logging
import random
import asyncio
import yt_dlp
import requests
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TXXX
import re
import subprocess
from vlc_manager import VLCManager
from music_library import MusicLibrary  # Import the updated MusicLibrary class
import signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BUFFER_SIZE = 20
MIN_SONGS_TO_START = 3

def sanitize_title(title):
    return re.sub(r'[\\/*?:"<>|]', "", title).strip()

async def extract_video_info(video_url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            logging.info(f"Extracted info for {video_url}: {info_dict['title']}")
            return info_dict
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error extracting info for {video_url}: {e}")
        return None

async def download_audio(video_url, playlist_name, music_library, vlc_manager):
    playlist_folder = os.path.join(music_library.base_folder, playlist_name)
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(playlist_folder, '%(id)s_%(title)s.%(ext)s'),
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
            video_id = info_dict.get('id', None)
            title = info_dict.get('title', None)
            artist = info_dict.get('uploader', None)
            album = playlist_name  # Use the playlist name as the album
            if video_id and title:
                sanitized_title = sanitize_title(title)
                original_file_path = os.path.join(playlist_folder, f"{video_id}_{title}.mp3")
                sanitized_file_path = os.path.join(playlist_folder, f"{video_id}_{sanitized_title}.mp3")
                if original_file_path != sanitized_file_path:
                    os.rename(original_file_path, sanitized_file_path)
                music_library.add_song(playlist_name, video_id, sanitized_title, sanitized_file_path)
                audio = ID3(sanitized_file_path)
                audio.add(TIT2(encoding=3, text=title))
                if artist:
                    audio.add(TPE1(encoding=3, text=artist))
                audio.add(TALB(encoding=3, text=album))  # Set album as playlist name
                audio.add(TXXX(encoding=3, desc='YouTubeID', text=video_id))
                audio.add(TXXX(encoding=3, desc='PlaylistName', text=playlist_name))  # Save playlist info in metadata
                audio.save()
                logging.info(f"Downloaded {title} (start: {start_time}, end: {end_time})")
                logging.info(f"Saved as: {sanitized_file_path} with metadata - Title: {title}, Artist: {artist}, Album: {album}, YouTubeID: {video_id}")
                if vlc_manager.vlc_process is not None:
                    await vlc_manager.add_to_playlist(sanitized_file_path)
                return title, sanitized_file_path
            else:
                logging.error(f"Failed to extract video info for {video_url}")
                return None
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error downloading {video_url}: {e}")
        return None
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return None

async def maintain_buffer(videos, playlist_name, music_library, vlc_manager):
    while True:
        if vlc_manager.vlc_process is None or vlc_manager.vlc_process.poll() is not None:
            await asyncio.sleep(1)
            continue

        if music_library.count_songs(playlist_name) < BUFFER_SIZE and videos:
            url = videos.pop(0)
            info_dict = await extract_video_info(url)
            video_id = info_dict.get('id', None) if info_dict else None
            title = info_dict.get('title', None) if info_dict else None
            if video_id and title and not music_library.song_exists(playlist_name, video_id):
                await download_audio(url, playlist_name, music_library, vlc_manager)
            else:
                logging.info(f"Song {title} already exists. Skipping download.")
        await asyncio.sleep(1)

async def player_loop(vlc_manager):
    current_song = None
    while vlc_manager.vlc_process and vlc_manager.vlc_process.poll() is not None:
        try:
            new_song = await vlc_manager.get_current_song()
            if new_song != current_song:
                current_song = new_song
                logging.info(f"Currently playing: {current_song}")
            await asyncio.sleep(1)
        except requests.RequestException as e:
            logging.error(f"Error checking VLC status: {e}")
            break

async def main_loop(videos, playlist_name, music_library, vlc_manager, alarm_time, test_mode):
    alarm_triggered = False
    server_started = False

    while True:
        current_time = datetime.datetime.now()

        if test_mode or current_time >= alarm_time:
            if not alarm_triggered:
                logging.info("Alarm triggered!")
                if music_library.count_songs(playlist_name) >= MIN_SONGS_TO_START:
                    vlc_manager.initialize_vlc_server()
                    while not vlc_manager.is_server_running():
                        logging.info("Waiting for VLC server to start...")
                        await asyncio.sleep(1)
                    for song in music_library.get_song_paths(playlist_name)[:BUFFER_SIZE]:
                        await vlc_manager.add_to_playlist(song)
                    await vlc_manager.start_playback()
                    server_started = True
                alarm_triggered = True

        if server_started:
            await player_loop(vlc_manager)
        await maintain_buffer(videos, playlist_name, music_library, vlc_manager)
        await asyncio.sleep(1)

def signal_handler(signal, frame):
    logging.info("Ctrl+C detected. Exiting gracefully...")
    for task in asyncio.all_tasks():
        task.cancel()
    asyncio.get_event_loop().stop()

async def main(playlist_url, hour_alarm, minute_alarm, test_mode, validate, shuffle):
    signal.signal(signal.SIGINT, signal_handler)

    start_time = datetime.datetime.now()
    logging.info(f"Program started at {start_time}")

    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        playlist_info = ydl.extract_info(playlist_url, download=False)
        videos = [entry['url'] for entry in playlist_info['entries']]
        playlist_name = sanitize_title(playlist_info.get('title', 'Unknown Playlist'))

    if not videos:
        logging.error("No videos found in the playlist.")
        return

    if shuffle:
        random.shuffle(videos)

    music_library = MusicLibrary("Downloaded_Music_YouTube", validate=validate)
    music_library.check_metadata(playlist_name)  # Check metadata for existing songs in the playlist
    vlc_manager = VLCManager()

    now = datetime.datetime.now()
    wake_up_time = datetime.datetime(now.year, now.month, now.day, hour_alarm, minute_alarm)
    if now > wake_up_time:
        wake_up_time += datetime.timedelta(days=1)

    logging.info(f"Alarm set for {wake_up_time.strftime('%A, %B %d, %Y %I:%M %p')}")

    # Ensure initial buffer is filled if no songs are available
    while music_library.count_songs(playlist_name) < MIN_SONGS_TO_START and videos:
        await download_audio(videos.pop(0), playlist_name, music_library, vlc_manager)

    await main_loop(videos, playlist_name, music_library, vlc_manager, wake_up_time, test_mode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='YoutubeAlarm',
                    description='Launches youtube with an alarm, pass time as parameter')
    parser.add_argument('--hour', type=int, required=True, help='Alarm hour')
    parser.add_argument('--minute', type=int, required=True, help='Alarm minute')
    parser.add_argument('--playlist', type=str, required=True, help='YouTube playlist URL')
    parser.add_argument('--test', action='store_true', help='Test mode to validate the script without waiting for the alarm')
    parser.add_argument('--validate', action='store_true', help='Validate MP3 files in the music library')
    parser.add_argument('--shuffle', action='store_true', help='Shuffle the playlist')
    args = parser.parse_args()

    hour_alarm = args.hour
    minute_alarm = args.minute
    playlist_url = args.playlist
    test_mode = args.test
    validate = args.validate
    shuffle = args.shuffle

    asyncio.run(main(playlist_url, hour_alarm, minute_alarm, test_mode, validate, shuffle))
