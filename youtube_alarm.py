import time
import datetime
import argparse
import os
import logging
import random
from pytube import Playlist, YouTube
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment
from pydub.playback import play

logging.basicConfig(level=logging.INFO)

DOWNLOAD_FOLDER = "Downloaded_Music_YouTube"

def download_audio(video_url, download_folder):
    yt = YouTube(video_url)
    title = yt.title
    audio_stream = yt.streams.filter(only_audio=True).first()
    if audio_stream:
        audio_file = audio_stream.download(output_path=download_folder, filename=f"{title}.mp4")
        mp3_file = os.path.join(download_folder, f"{title}.mp3")
        AudioSegment.from_file(audio_file).export(mp3_file, format="mp3")
        os.remove(audio_file)
        logging.info(f"Downloaded and converted: {title}")
    else:
        logging.error(f"No audio stream found for: {title}")

def play_audio_from_folder(folder_path):
    files = [f for f in os.listdir(folder_path) if f.endswith(".mp3")]
    if not files:
        logging.error("No audio files found in the folder.")
        return

    file_to_play = random.choice(files)
    audio_path = os.path.join(folder_path, file_to_play)
    audio = AudioSegment.from_mp3(audio_path)
    play(audio)

def main(playlist_url):
    playlist = Playlist(playlist_url)
    videos = list(playlist.video_urls)

    if not videos:
        logging.error("No videos found in the playlist.")
        return

    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    downloaded_files = [f[:-4] for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3")]
    videos_to_download = [url for url in videos if YouTube(url).title not in downloaded_files]

    with ThreadPoolExecutor(max_workers=2) as executor:
        for url in videos_to_download:
            executor.submit(download_audio, url, DOWNLOAD_FOLDER)

    play_audio_from_folder(DOWNLOAD_FOLDER)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='YoutubeAlarm',
                    description='Launches youtube with an alarm, pass time as parameter')
    parser.add_argument('--hour', type=int, required=True, help='Alarm hour')
    parser.add_argument('--minute', type=int, required=True, help='Alarm minute')
    parser.add_argument('--playlist', type=str, required=True, help='YouTube playlist URL')
    args = parser.parse_args()

    hour_alarm = args.hour
    minute_alarm = args.minute
    playlist_url = args.playlist

    now = datetime.datetime.now()
    wake_up_time = datetime.datetime(now.year, now.month, now.day, hour_alarm, minute_alarm)

    if now > wake_up_time:
        wake_up_time += datetime.timedelta(days=1)  # Set for the next day if the time has already passed today

    logging.info(f"Alarm set for {wake_up_time.strftime('%A, %B %d, %Y %I:%M %p')}")

    while datetime.datetime.now() < wake_up_time:
        time.sleep(15)  # Check every 15 seconds

    main(playlist_url)
    logging.info("Alarm triggered!")
