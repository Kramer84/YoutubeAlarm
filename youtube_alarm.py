import time
import datetime
import argparse
import os
import logging
import random
import asyncio
import subprocess
import yt_dlp
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD_FOLDER = "Downloaded_Music_YouTube"
VLC_HTTP_URL = "http://localhost:8080/requests/status.json"
VLC_PASSWORD = "vlc"

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
                await add_to_vlc_playlist(file_path)
                return title, file_path
            else:
                logging.error(f"Failed to extract video info for {video_url}")
                return None
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error downloading {video_url}: {e}")
        return None

async def add_to_vlc_playlist(file_path):
    try:
        requests.get(f"http://localhost:8080/requests/status.json?command=in_enqueue&input=file://{os.path.abspath(file_path)}", auth=("", VLC_PASSWORD))
        logging.info(f"Added to VLC playlist: {file_path}")
    except requests.RequestException as e:
        logging.error(f"Error adding to VLC playlist: {e}")

async def play_audio_vlc():
    play_command = ["cvlc", "--extraintf=http", "--http-password", VLC_PASSWORD]
    process = subprocess.Popen(play_command)
    await asyncio.sleep(5)  # Give VLC a moment to start
    return process

async def schedule_downloads(videos, download_folder, music_library):
    tasks = []
    for url in videos:
        title = await extract_video_info(url)
        if title and not music_library.song_exists(title):
            tasks.append(asyncio.create_task(download_audio(url, download_folder, music_library)))
        else:
            logging.info(f"Song {title} already exists. Skipping download.")
    await asyncio.gather(*tasks)

async def pre_download(videos, download_folder, music_library):
    await schedule_downloads(videos[:20], download_folder, music_library)

async def player_loop(vlc_process):
    while vlc_process.poll() is None:
        try:
            response = requests.get(VLC_HTTP_URL, auth=("", VLC_PASSWORD))
            if response.status_code == 200 and "state" in response.json() and response.json()["state"] == "stopped":
                break
            await asyncio.sleep(1)
        except requests.RequestException as e:
            logging.error(f"Error checking VLC status: {e}")
            break

async def downloader_loop(videos, download_folder, music_library):
    await schedule_downloads(videos, download_folder, music_library)

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

    # Start pre-downloading songs
    await pre_download(videos, DOWNLOAD_FOLDER, music_library)

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

    vlc_process = await play_audio_vlc()

    # Start the player and downloader loops
    await asyncio.gather(
        player_loop(vlc_process),
        downloader_loop(videos, DOWNLOAD_FOLDER, music_library)
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
