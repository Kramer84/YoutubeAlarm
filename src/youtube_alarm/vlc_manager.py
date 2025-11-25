import os
import time
import logging
import requests
import subprocess
import asyncio
import signal
import psutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - line %(lineno)d - %(message)s'
)

VLC_PASSWORD = "vlc"

class VLCManager:
    def __init__(self, port=8080):
        self.vlc_process = None
        self.playlist = []  # To track the playlist order
        self.current_index = -1  # To track the current song index
        self.port = port  # Store the port as an attribute
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)

    def kill_existing_vlc(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if 'vlc' in proc.info['name']:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    logging.info(f"Killed existing VLC process with PID {proc.info['pid']}")
                except psutil.NoSuchProcess:
                    logging.info(f"VLC process {proc.info['pid']} already terminated.")
                except psutil.TimeoutExpired:
                    logging.warning(f"VLC process {proc.info['pid']} did not terminate in time. Forcing kill.")
                    proc.kill()

    def initialize_vlc_server(self):
        self.kill_existing_vlc()
        play_command = [
            "cvlc",
            "--extraintf=http",
            f"--http-port={self.port}",  # Set the custom HTTP port from the attribute
            "--http-password", VLC_PASSWORD,
            "--play-and-exit",
            "--no-video",  # Disable video output
            "--no-metadata-network-access",  # Prevent fetching metadata online
        ]
        self.vlc_process = subprocess.Popen(play_command)

        # Wait until VLC is ready by checking the HTTP server
        for _ in range(10):
            if self.is_server_running():
                logging.info(f"VLC server initialized on port {self.port}.")
                return
            time.sleep(1)

        logging.error(f"VLC server failed to start on port {self.port}.")

    async def send_vlc_command(self, command, params=None):
        max_retries = 5
        retry_delay = 2  # seconds

        url = f"http://localhost:{self.port}/requests/status.json?command={command}"
        if params:
            url += f"&{params}"

        for attempt in range(max_retries):
            try:
                response = requests.get(url, auth=("", VLC_PASSWORD))
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logging.error(f"Error sending command to VLC: {e}. Attempt {attempt + 1}/{max_retries}")
                await asyncio.sleep(retry_delay)

        logging.error("Failed to send command to VLC after multiple attempts.")
        return None

    async def add_to_playlist(self, file_path):
        response = await self.send_vlc_command('in_enqueue', f"input=file://{os.path.abspath(file_path)}")
        if response and response.status_code == 200:
            self.playlist.append(file_path)
            logging.info(f"Added to VLC playlist: {file_path}")
        else:
            logging.error(f"Failed to add to VLC playlist: {file_path}")

    async def start_playback(self):
        if not self.playlist:
            logging.warning("No songs in the playlist. Cannot start playback.")
            return

        response = await self.send_vlc_command('pl_play')
        if response and response.status_code == 200:
            logging.info("Started VLC playback.")
            await self.update_current_song_index()
        else:
            logging.error("Failed to start VLC playback.")

    async def skip_song(self):
        response = await self.send_vlc_command('pl_next')
        if response and response.status_code == 200:
            await self.update_current_song_index()
        else:
            logging.error("Failed to skip song.")

    async def previous_song(self):
        response = await self.send_vlc_command('pl_previous')
        if response and response.status_code == 200:
            await self.update_current_song_index()
        else:
            logging.error("Failed to go back to previous song.")

    async def get_current_song(self):
        try:
            response = await self.send_vlc_command('')
            if response and response.status_code == 200:
                status = response.json()
                if 'information' in status:
                    meta = status['information'].get('category', {}).get('meta', {})
                    current_file_path = meta.get('filename', None)
                    #logging.info(f"VLC current song info: {meta}")
                    return current_file_path, self.current_index
                else:
                    logging.error(f"No 'information' field in VLC status response: {status}")
            else:
                logging.error(f"Unexpected HTTP response from VLC: {response.status_code} - {response.text}")
            logging.error("Failed to get current song from VLC.")
        except requests.RequestException as e:
            logging.error(f"Error sending command to VLC: {e}")
        return None, self.current_index

    async def update_current_song_index(self):
        current_file_path, _ = await self.get_current_song()
        if current_file_path:
            # Extract the YouTube ID from the current filename (first 11 characters)
            current_filename = os.path.basename(current_file_path)
            current_youtube_id = current_filename[:11]  # Assume the YouTube ID is always 11 characters long

            try:
                for i, file_path in enumerate(self.playlist):
                    # Extract the YouTube ID from the playlist file path
                    playlist_youtube_id = os.path.basename(file_path)[:11]

                    if playlist_youtube_id == current_youtube_id:
                        if self.current_index == i:
                            return
                        self.current_index = i
                        logging.info(f"Updated current index to: {self.current_index} for YouTube ID: {current_youtube_id}")
                        return

                logging.error(f"Current song with YouTube ID {current_youtube_id} not found in playlist.")
                self.current_index = -1  # Reset the index to indicate an issue
            except ValueError:
                logging.error(f"Error in finding current song {current_filename} in playlist.")
                self.current_index = -1
        else:
            logging.error("Could not retrieve current song from VLC.")
            self.current_index = -1

    async def get_playlist(self):
        response = await self.send_vlc_command('pl_info')
        if response and response.status_code == 200:
            return response.json()
        logging.error("Failed to get VLC playlist.")
        return None

    def is_server_running(self):
        try:
            response = requests.get(f"http://localhost:{self.port}/requests/status.json", auth=("", VLC_PASSWORD))
            return response.status_code == 200
        except requests.RequestException:
            return False

    def cleanup(self, signum=None, frame=None):
        if self.vlc_process:
            if self.vlc_process.poll() is None:  # Check if process is still running
                self.vlc_process.terminate()
                try:
                    self.vlc_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.vlc_process.kill()
                    logging.warning("VLC server forcefully terminated.")
            logging.info("VLC server terminated.")

    def get_playlist_length(self):
        return len(self.playlist)
