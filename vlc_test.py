# vlc_test.py

import os
import time
import logging
from vlc_manager import VLCManager

DOWNLOAD_FOLDER = "Downloaded_Music_YouTube"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    vlc_manager = VLCManager()
    vlc_manager.initialize_vlc_server()

    mp3_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3")]

    if not mp3_files:
        logging.error("No MP3 files found in the download folder.")
        return

    for mp3_file in mp3_files:
        vlc_manager.add_to_playlist(os.path.join(DOWNLOAD_FOLDER, mp3_file))

    vlc_manager.start_playback()

    logging.info("VLC playlist initialized. Playing songs...")

    try:
        while vlc_manager.vlc_process.poll() is None:
            command = input("Enter 's' to skip the current song or 'q' to quit: ")
            if command.lower() == 's':
                vlc_manager.skip_song()
            elif command.lower() == 'q':
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping VLC server...")
    finally:
        vlc_manager.cleanup()

if __name__ == "__main__":
    main()
