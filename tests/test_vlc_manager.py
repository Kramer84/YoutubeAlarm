import os
import asyncio
import logging
import aioconsole
from vlc_manager import VLCManager
from music_library import MusicLibrary  # Assuming the updated MusicLibrary is available

BASE_FOLDER = "Downloaded_Music_YouTube"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def select_playlist(music_library):
    playlists = [d for d in os.listdir(BASE_FOLDER) if os.path.isdir(os.path.join(BASE_FOLDER, d))]
    if not playlists:
        logging.error("No playlists found.")
        return None

    print("Available playlists:")
    for i, playlist in enumerate(playlists):
        print(f"{i + 1}. {playlist}")

    while True:
        try:
            choice = await aioconsole.ainput("Select a playlist by number: ")
            index = int(choice) - 1
            if 0 <= index < len(playlists):
                return playlists[index]
            else:
                print(f"Invalid selection. Please choose a number between 1 and {len(playlists)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

async def main_loop(vlc_manager):
    while vlc_manager.vlc_process and vlc_manager.vlc_process.poll() is None:
        current_song, current_index = await vlc_manager.get_current_song()
        logging.info(f"Currently playing: {current_song} (Index: {current_index})")

        try:
            command = await asyncio.wait_for(aioconsole.ainput(
                "Enter 's' to skip the current song, 'p' to get the playlist, 'r' to play previous song, 'c' to check if server is running, or 'q' to quit: "), timeout=1)
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
        await vlc_manager.update_current_song_index()

async def main():
    vlc_manager = VLCManager()
    vlc_manager.initialize_vlc_server()

    music_library = MusicLibrary(BASE_FOLDER)
    playlist_name = await select_playlist(music_library)

    if not playlist_name:
        logging.error("No playlist selected. Exiting...")
        return

    mp3_files = music_library.get_song_paths(playlist_name)

    if not mp3_files:
        logging.error(f"No MP3 files found in the playlist '{playlist_name}'.")
        return

    for mp3_file in mp3_files:
        await vlc_manager.add_to_playlist(mp3_file)

    await vlc_manager.start_playback()

    logging.info(f"VLC playlist '{playlist_name}' initialized. Playing songs...")

    try:
        await main_loop(vlc_manager)
    except KeyboardInterrupt:
        logging.info("Stopping VLC server...")
    finally:
        vlc_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
