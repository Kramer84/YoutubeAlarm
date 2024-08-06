import time
import datetime
import argparse
import os
import logging
import random
import asyncio
import pickle
import aiofiles
from pydub import AudioSegment
from pydub.playback import play
import yt_dlp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD_FOLDER = "Downloaded_Music_YouTube"
METADATA_FILE = "playlist_metadata.pkl"

async def download_audio(video_url, download_folder):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        title = info_dict.get('title', None)
        if title:
            return os.path.join(download_folder, f"{title}.mp3")
        else:
            logging.error(f"Failed to extract video info for {video_url}")
            return None

async def play_audio(file_path):
    audio = AudioSegment.from_file(file_path)
    play(audio)

async def schedule_downloads(videos, download_folder):
    tasks = []
    for url in videos:
        tasks.append(asyncio.create_task(download_audio(url, download_folder)))
    await asyncio.gather(*tasks)

async def load_metadata():
    if os.path.exists(METADATA_FILE):
        async with aiofiles.open(METADATA_FILE, 'rb') as f:
            return pickle.loads(await f.read())
    return {}

async def save_metadata(metadata):
    async with aiofiles.open(METADATA_FILE, 'wb') as f:
        await f.write(pickle.dumps(metadata))

async def main(playlist_url):
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        playlist_info = ydl.extract_info(playlist_url, download=False)
        videos = [entry['url'] for entry in playlist_info['entries']]

    if not videos:
        logging.error("No videos found in the playlist.")
        return

    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    metadata = await load_metadata()
    downloaded_files = [f[:-4] for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3")]
    random.shuffle(videos)

    download_queue = asyncio.Queue()
    play_queue = asyncio.Queue()

    for video_url in videos:
        await download_queue.put(video_url)

    async def downloader():
        while not download_queue.empty():
            video_url = await download_queue.get()
            with yt_dlp.YoutubeDL({'quiet': True, 'forceurl': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
                title = info.get('title', None)
                video_id = info.get('id', None)

            mp3_file = os.path.join(DOWNLOAD_FOLDER, f"{title}.mp3")

            if title not in downloaded_files and video_id not in metadata:
                logging.info(f"Downloading {title}...")
                mp3_file = await download_audio(video_url, DOWNLOAD_FOLDER)
                metadata[video_id] = mp3_file
                await save_metadata(metadata)
                await play_queue.put(mp3_file)

    async def player():
        while True:
            mp3_file = await play_queue.get()
            if os.path.exists(mp3_file):
                logging.info(f"Playing {mp3_file}...")
                await play_audio(mp3_file)

            # Pre-download the next set of songs if any are longer than 10 minutes
            long_videos = []
            while not download_queue.empty():
                next_videos = []
                for _ in range(10):
                    if download_queue.empty():
                        break
                    next_videos.append(await download_queue.get())

                for url in next_videos:
                    with yt_dlp.YoutubeDL({'quiet': True, 'forceurl': True}) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info['duration'] > 600:
                            long_videos.append(url)

                if long_videos:
                    logging.info("Pre-downloading long videos...")
                    await schedule_downloads(long_videos, DOWNLOAD_FOLDER)
                    break

    await asyncio.gather(downloader(), player())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='YoutubeAlarm',
                    description='Launches youtube with an alarm, pass time as parameter')
    parser.add_argument('--hour', type=int, required=True, help='Alarm hour')
    parser.add_argument('--minute', type=int, required=True, help='Alarm minute')
    parser.add_argument('--playlist', type=str, required=True, help='YouTube playlist URL')
    parser.add_argument('--test', action='store_true', help='Test mode to validate the script without waiting for the alarm')
    args = parser.parse_args()

    hour_alarm = args.hour
    minute_alarm = args.minute
    playlist_url = args.playlist

    if args.test:
        logging.info("Test mode activated.")
        asyncio.run(main(playlist_url))
    else:
        now = datetime.datetime.now()
        wake_up_time = datetime.datetime(now.year, now.month, now.day, hour_alarm, minute_alarm)

        if now > wake_up_time:
            wake_up_time += datetime.timedelta(days=1)  # Set for the next day if the time has already passed today

        logging.info(f"Alarm set for {wake_up_time.strftime('%A, %B %d, %Y %I:%M %p')}")

        while datetime.datetime.now() < wake_up_time:
            time.sleep(15)  # Check every 15 seconds

        asyncio.run(main(playlist_url))
        logging.info("Alarm triggered!")
