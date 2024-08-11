import re
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
from mutagen import MutagenError
import re
import subprocess
from vlc_manager import VLCManager
from music_library import MusicLibrary  # Import the updated MusicLibrary class
import signal
from slugify import slugify as sanitize_title  # Or define your own sanitize function

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
    playlist_folder = os.path.join(music_library.base_folder, playlist_name)
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
            album = playlist_name  # Use the playlist name as the album

            # Use the original title as it is without sanitizing it
            file_path = os.path.join(playlist_folder, f"{video_id}_{title}.mp3")

            # Verify if the file was actually created
            if os.path.exists(file_path):
                logging.info(f"File {file_path} exists after download.")

                music_library.add_song(playlist_name, video_id, title, file_path)

                try:
                    # Add ID3 metadata
                    audio = ID3(file_path)
                    audio.add(TIT2(encoding=3, text=title))
                    if artist:
                        audio.add(TPE1(encoding=3, text=artist))
                    audio.add(TALB(encoding=3, text=album))  # Set album as playlist name
                    audio.add(TXXX(encoding=3, desc='YouTubeID', text=video_id))
                    audio.add(TXXX(encoding=3, desc='PlaylistName', text=playlist_name))  # Save playlist info in metadata
                    audio.save()
                except MutagenError as e:
                    logging.error(f"Mutagen error while processing {file_path}: {e}")
                    return None

                logging.info(f"Downloaded {title} (start: {start_time}, end: {end_time})")
                logging.info(f"Saved as: {file_path} with metadata - Title: {title}, Artist: {artist}, Album: {album}, YouTubeID: {video_id}")

                return file_path  # Return the file path instead of adding directly to VLC playlist
            else:
                logging.error(f"File not found after download: {file_path}")
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
        title = info_dict.get('title', None) if info_dict else None

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

        if test_mode or current_time >= alarm_time:
            if not alarm_triggered:
                logging.info("Alarm triggered!")
                if music_library.count_songs(playlist_name) >= MIN_SONGS_TO_START:
                    vlc_manager.initialize_vlc_server()
                    while not vlc_manager.is_server_running():
                        logging.info("Waiting for VLC server to start...")
                        await asyncio.sleep(1)

                    # Start playback after songs are added to the playlist
                    for song in music_library.get_song_paths(playlist_name)[:BUFFER_SIZE]:
                        await vlc_manager.add_to_playlist(song)
                    await vlc_manager.start_playback()

                    server_started = True
                alarm_triggered = True

        if server_started:
            current_song_index = await player_loop(vlc_manager, current_song_index)  # Get the current song index
            await maintain_buffer(videos, playlist_name, music_library, vlc_manager, current_song_index)
        await asyncio.sleep(.25)

def signal_handler(signal, frame):
    logging.info("Ctrl+C detected. Exiting gracefully...")
    for task in asyncio.all_tasks():
        task.cancel()
    asyncio.get_event_loop().stop()

def extract_youtube_id(url):
    """Extract the YouTube ID from a YouTube URL."""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

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
        playlist_name = playlist_info.get('title', 'Unknown Playlist')

    if not videos:
        logging.error("No videos found in the playlist.")
        return

    if shuffle:
        random.shuffle(videos)

    music_library = MusicLibrary("Downloaded_Music_YouTube", validate=validate)
    music_library.initialize_playlist(playlist_name)
    music_library.check_metadata(playlist_name)  # Check metadata for existing songs in the playlist
    music_library.clean_up_non_mp3_files(playlist_name)
    if validate :
        music_library.validate_songs(playlist_name)
    vlc_manager = VLCManager()

    # Extract YouTube IDs from URLs
    youtube_ids = [extract_youtube_id(video) for video in videos]

    # Check which songs are already downloaded
    songs_in_library = music_library.check_youtube_ids(youtube_ids, playlist_name)

    # Only keep the URLs for songs that are not yet downloaded
    videos_to_download = [video for video, exists in zip(videos, songs_in_library) if not exists]

    now = datetime.datetime.now()
    wake_up_time = datetime.datetime(now.year, now.month, now.day, hour_alarm, minute_alarm)
    if now > wake_up_time:
        wake_up_time += datetime.timedelta(days=1)

    logging.info(f"Alarm set for {wake_up_time.strftime('%A, %B %d, %Y %I:%M %p')}")

    # Ensure initial buffer is filled with the first MIN_SONGS_TO_START songs
    for i in range(min(MIN_SONGS_TO_START, len(videos))):
        youtube_id = extract_youtube_id(videos[i])
        if not music_library.song_exists(playlist_name, video_id=youtube_id):
            await download_audio(videos_to_download.pop(0), playlist_name, music_library)

    logging.info(f"Finished checking initial data buffer.")

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
