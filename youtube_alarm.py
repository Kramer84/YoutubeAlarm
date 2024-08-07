import time
import datetime
import argparse
import os
import logging
import random
import asyncio
import yt_dlp
import requests

from vlc_manager import VLCManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD_FOLDER = "Downloaded_Music_YouTube"
BUFFER_SIZE = 20

class MusicLibrary:
    def __init__(self, folder, validate=False):
        self.songs = []
        self.folder = folder
        self.validate = validate
        self.initialize_library()

    def initialize_library(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        self.clean_up_non_mp3_files()
        self.songs = [
            {"title": f[:-4], "file_path": os.path.join(self.folder, f)}
            for f in os.listdir(self.folder)
            if f.endswith(".mp3")
        ]
        if self.validate:
            self.validate_songs()

    def clean_up_non_mp3_files(self):
        for f in os.listdir(self.folder):
            if not f.endswith(".mp3"):
                file_path = os.path.join(self.folder, f)
                logging.info(f"Removing non-MP3 file: {file_path}")
                os.remove(file_path)

    def add_song(self, title, file_path):
        self.songs.append({"title": title, "file_path": file_path})

    def song_exists(self, title):
        for song in self.songs:
            if song['title'] == title:
                return True
        return False

    def validate_songs(self):
        valid_songs = []
        for song in self.songs:
            if self.is_valid_mp3(song["file_path"]):
                valid_songs.append(song)
            else:
                logging.info(f"Removing corrupted or incomplete file: {song['file_path']}")
                os.remove(song["file_path"])
        self.songs = valid_songs

    def is_valid_mp3(self, file_path):
        try:
            subprocess.run(["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

async def extract_video_info(video_url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            title = info_dict.get('title', None)
            return title
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error extracting info for {video_url}: {e}")
        return None

async def download_audio(video_url, download_folder, music_library):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
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
            title = info_dict.get('title', None)
            file_path = os.path.join(download_folder, f"{title}.mp3")
            if title:
                music_library.add_song(title, file_path)
                logging.info(f"Downloaded {title} (start: {start_time}, end: {end_time})")
                return title, file_path
            else:
                logging.error(f"Failed to extract video info for {video_url}")
                return None
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error downloading {video_url}: {e}")
        return None

async def schedule_downloads(videos, download_folder, music_library, vlc_manager):
    tasks = []
    for url in videos:
        title = await extract_video_info(url)
        if title and not music_library.song_exists(title):
            tasks.append(asyncio.create_task(download_audio(url, download_folder, music_library)))
        else:
            logging.info(f"Song {title} already exists. Skipping download.")
    downloaded_songs = await asyncio.gather(*tasks)
    for title, file_path in downloaded_songs:
        if file_path:
            vlc_manager.add_to_playlist(file_path)

async def maintain_buffer(videos, download_folder, music_library, vlc_manager):
    while videos:
        while len(music_library.songs) < BUFFER_SIZE:
            if videos:
                url = videos.pop(0)
                title = await extract_video_info(url)
                if title and not music_library.song_exists(title):
                    _, file_path = await download_audio(url, download_folder, music_library)
                    if file_path:
                        vlc_manager.add_to_playlist(file_path)
                else:
                    logging.info(f"Song {title} already exists. Skipping download.")
            else:
                break
        await asyncio.sleep(10)

async def main(playlist_url, hour_alarm, minute_alarm, test_mode, validate, shuffle):
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

    if not videos:
        logging.error("No videos found in the playlist.")
        return

    if shuffle:
        random.shuffle(videos)

    music_library = MusicLibrary(DOWNLOAD_FOLDER, validate=validate)
    vlc_manager = VLCManager()
    vlc_manager.initialize_vlc_server()

    if test_mode:
        logging.info("Test mode activated. Starting playback immediately.")
        wake_up_time = datetime.datetime.now()
    else:
        now = datetime.datetime.now()
        wake_up_time = datetime.datetime(now.year, now.month, now.day, hour_alarm, minute_alarm)
        if now > wake_up_time:
            wake_up_time += datetime.timedelta(days=1)

        time_until_alarm = (wake_up_time - now).total_seconds()
        logging.info(f"Alarm set for {wake_up_time.strftime('%A, %B %d, %Y %I:%M %p')}, which is in {time_until_alarm} seconds.")

        await asyncio.sleep(time_until_alarm)

    logging.info("Alarm triggered!")

    # Add initial songs to VLC playlist
    for song in music_library.songs[:BUFFER_SIZE]:
        vlc_manager.add_to_playlist(song["file_path"])

    vlc_manager.start_playback()

    # Start the player and downloader loops
    await asyncio.gather(
        maintain_buffer(videos, DOWNLOAD_FOLDER, music_library, vlc_manager)
    )

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
