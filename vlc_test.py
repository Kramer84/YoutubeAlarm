import os
import asyncio
import logging
import aioconsole
from vlc_manager import VLCManager

DOWNLOAD_FOLDER = "Downloaded_Music_YouTube"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main_loop(vlc_manager):
    while vlc_manager.vlc_process.poll() is None:
        current_song = await vlc_manager.get_current_song()
        logging.info(f"Currently playing: {current_song}")

        try:
            command = await asyncio.wait_for(aioconsole.ainput("Enter 's' to skip the current song, 'p' to get the playlist, 'r' to play previous song, 'c' to check if server is running, or 'q' to quit: "), timeout=1)
            if command.lower() == 's':
                await vlc_manager.skip_song()
            elif command.lower() == 'p':
                playlist = await vlc_manager.get_playlist()
                logging.info(f"Current playlist: {playlist}")
            elif command.lower() == 'r':
                await vlc_manager.previous_song()
            elif command.lower() == 'c':
                if vlc_manager.is_server_running():
                    logging.info("VLC server is running.")
                else:
                    logging.error("VLC server is not running.")
            elif command.lower() == 'q':
                break
        except asyncio.TimeoutError:
            pass
        await asyncio.sleep(1)

async def main():
    vlc_manager = VLCManager()
    vlc_manager.initialize_vlc_server()

    mp3_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3")]

    if not mp3_files:
        logging.error("No MP3 files found in the download folder.")
        return

    for mp3_file in mp3_files:
        await vlc_manager.add_to_playlist(os.path.join(DOWNLOAD_FOLDER, mp3_file))

    await vlc_manager.start_playback()

    logging.info("VLC playlist initialized. Playing songs...")

    try:
        await main_loop(vlc_manager)
    except KeyboardInterrupt:
        logging.info("Stopping VLC server...")
    finally:
        vlc_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
