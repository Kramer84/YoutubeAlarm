# vlc_manager.py

import os
import logging
import requests
import subprocess
import time
import signal
import psutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VLC_HTTP_URL = "http://localhost:8080/requests/status.json"
VLC_PASSWORD = "vlc"

class VLCManager:
    def __init__(self):
        self.vlc_process = None
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)

    def kill_existing_vlc(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if 'vlc' in proc.info['name']:
                os.kill(proc.info['pid'], signal.SIGTERM)
                logging.info(f"Killed existing VLC process with PID {proc.info['pid']}")

    def initialize_vlc_server(self):
        self.kill_existing_vlc()
        play_command = ["cvlc", "--extraintf=http", "--http-password", VLC_PASSWORD, "--play-and-exit"]
        self.vlc_process = subprocess.Popen(play_command)
        time.sleep(5)  # Give VLC a moment to start
        logging.info("VLC server initialized.")

    def add_to_playlist(self, file_path):
        try:
            response = requests.get(
                f"{VLC_HTTP_URL}?command=in_enqueue&input=file://{os.path.abspath(file_path)}",
                auth=("", VLC_PASSWORD)
            )
            if response.status_code == 200:
                logging.info(f"Added to VLC playlist: {file_path}")
            else:
                logging.error(f"Failed to add to VLC playlist: {file_path} - {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Error adding to VLC playlist: {e}")

    def start_playback(self):
        try:
            response = requests.get(
                f"{VLC_HTTP_URL}?command=pl_play",
                auth=("", VLC_PASSWORD)
            )
            if response.status_code == 200:
                logging.info("Started VLC playback.")
            else:
                logging.error(f"Failed to start VLC playback: {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Error starting VLC playback: {e}")

    def skip_song(self):
        try:
            response = requests.get(
                f"{VLC_HTTP_URL}?command=pl_next",
                auth=("", VLC_PASSWORD)
            )
            if response.status_code == 200:
                logging.info("Skipped to next song.")
            else:
                logging.error(f"Failed to skip song: {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Error skipping song: {e}")

    def get_playlist(self):
        try:
            response = requests.get(
                f"{VLC_HTTP_URL}?command=pl_info",
                auth=("", VLC_PASSWORD)
            )
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Failed to get VLC playlist: {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Error getting VLC playlist: {e}")
        return None

    def cleanup(self, signum=None, frame=None):
        if self.vlc_process:
            self.vlc_process.terminate()
            self.vlc_process.wait()
            logging.info("VLC server terminated.")

# Ensure proper cleanup on script termination
vlc_manager = VLCManager()
signal.signal(signal.SIGINT, vlc_manager.cleanup)
signal.signal(signal.SIGTERM, vlc_manager.cleanup)
