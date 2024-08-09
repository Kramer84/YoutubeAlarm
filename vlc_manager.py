import os
import logging
import requests
import subprocess
import time
import signal
import psutil
import asyncio

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
                proc.terminate()
                logging.info(f"Killed existing VLC process with PID {proc.info['pid']}")

    def initialize_vlc_server(self):
        self.kill_existing_vlc()
        play_command = ["cvlc", "--extraintf=http", "--http-password", VLC_PASSWORD, "--play-and-exit"]
        self.vlc_process = subprocess.Popen(play_command)
        time.sleep(5)  # Give VLC a moment to start
        logging.info("VLC server initialized.")

    async def send_vlc_command(self, command, params=None):
        try:
            url = f"{VLC_HTTP_URL}?command={command}"
            if params:
                url += f"&{params}"
            response = requests.get(url, auth=("", VLC_PASSWORD))
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.error(f"Error sending command to VLC: {e}")
            return None

    async def add_to_playlist(self, file_path):
        response = await self.send_vlc_command('in_enqueue', f"input=file://{os.path.abspath(file_path)}")
        if response and response.status_code == 200:
            logging.info(f"Added to VLC playlist: {file_path}")
        else:
            logging.error(f"Failed to add to VLC playlist: {file_path}")

    async def start_playback(self):
        response = await self.send_vlc_command('pl_play')
        if response and response.status_code == 200:
            logging.info("Started VLC playback.")
        else:
            logging.error("Failed to start VLC playback.")

    async def skip_song(self):
        response = await self.send_vlc_command('pl_next')
        if response and response.status_code == 200:
            logging.info("Skipped to next song.")
        else:
            logging.error("Failed to skip song.")

    async def previous_song(self):
        response = await self.send_vlc_command('pl_previous')
        if response and response.status_code == 200:
            logging.info("Went back to previous song.")
        else:
            logging.error("Failed to go back to previous song.")

    async def get_current_song(self):
        response = await self.send_vlc_command('')
        if response and response.status_code == 200:
            status = response.json()
            if 'information' in status:
                meta = status['information'].get('category', {}).get('meta', {})
                return meta.get('title', 'Unknown')
            elif 'state' in status and status['state'] == 'playing':
                for category in status['information']['category'].values():
                    if 'meta' in category:
                        return category['meta'].get('title', 'Unknown')
        logging.error("Failed to get current song.")
        return None

    async def get_playlist(self):
        response = await self.send_vlc_command('pl_info')
        if response and response.status_code == 200:
            return response.json()
        logging.error("Failed to get VLC playlist.")
        return None

    def is_server_running(self):
        try:
            response = requests.get(VLC_HTTP_URL, auth=("", VLC_PASSWORD))
            return response.status_code == 200
        except requests.RequestException:
            return False

    def cleanup(self, signum=None, frame=None):
        if self.vlc_process:
            self.vlc_process.terminate()
            self.vlc_process.wait()
            logging.info("VLC server terminated.")
