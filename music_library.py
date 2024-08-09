import os
import logging
import subprocess
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TXXX

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MusicLibrary:
    def __init__(self, base_folder, validate=False):
        self.base_folder = base_folder
        self.validate = validate
        self.songs = {}
        self.initialize_library()

    def initialize_library(self):
        """Initialize the music library by scanning the base folder and loading existing MP3 files organized by playlists."""
        if not os.path.exists(self.base_folder):
            os.makedirs(self.base_folder)
        self.scan_folders()

    def scan_folders(self):
        """Scan all playlist folders and load MP3 files into the library."""
        self.songs.clear()
        for playlist_name in os.listdir(self.base_folder):
            playlist_folder = os.path.join(self.base_folder, playlist_name)
            if os.path.isdir(playlist_folder):
                self.scan_playlist_folder(playlist_name, playlist_folder)

    def scan_playlist_folder(self, playlist_name, playlist_folder):
        """Scan a specific playlist folder and load MP3 files into the library."""
        for f in os.listdir(playlist_folder):
            if f.endswith(".mp3"):
                video_id = f.split("_")[0]
                self.songs[(playlist_name, video_id)] = {
                    "title": f[:-4],
                    "file_path": os.path.join(playlist_folder, f)
                }

    def clean_up_non_mp3_files(self, playlist_name):
        """Remove any non-MP3 files from a specific playlist folder."""
        playlist_folder = os.path.join(self.base_folder, playlist_name)
        for f in os.listdir(playlist_folder):
            if not f.endswith(".mp3"):
                file_path = os.path.join(playlist_folder, f)
                logging.info(f"Removing non-MP3 file: {file_path}")
                os.remove(file_path)

    def add_song(self, playlist_name, video_id, title, file_path):
        """Add a new song to the library within a specific playlist."""
        playlist_folder = os.path.join(self.base_folder, playlist_name)
        if not os.path.exists(playlist_folder):
            os.makedirs(playlist_folder)

        sanitized_title = f"{video_id}_{title}.mp3"
        final_path = os.path.join(playlist_folder, sanitized_title)

        if file_path != final_path:
            os.rename(file_path, final_path)

        self.songs[(playlist_name, video_id)] = {"title": title, "file_path": final_path}

    def remove_song(self, playlist_name, video_id):
        """Remove a song from the library by its playlist and video ID."""
        key = (playlist_name, video_id)
        if key in self.songs:
            os.remove(self.songs[key]['file_path'])
            del self.songs[key]
            logging.info(f"Removed song with ID {video_id} from playlist {playlist_name}.")

    def song_exists(self, playlist_name, video_id):
        """Check if a song exists in the library by its playlist and video ID."""
        return (playlist_name, video_id) in self.songs

    def validate_songs(self, playlist_name=None):
        """Validate all MP3 files in the library and remove corrupted ones."""
        valid_songs = {}
        if playlist_name:
            playlist_folder = os.path.join(self.base_folder, playlist_name)
            for key, song in self.songs.items():
                if key[0] == playlist_name and self.is_valid_mp3(song["file_path"]):
                    valid_songs[key] = song
                else:
                    logging.info(f"Removing corrupted or incomplete file: {song['file_path']}")
                    os.remove(song["file_path"])
        else:
            for key, song in self.songs.items():
                if self.is_valid_mp3(song["file_path"]):
                    valid_songs[key] = song
                else:
                    logging.info(f"Removing corrupted or incomplete file: {song['file_path']}")
                    os.remove(song["file_path"])

        self.songs = valid_songs

    def is_valid_mp3(self, file_path):
        """Check if an MP3 file is valid by running ffmpeg."""
        try:
            subprocess.run(["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def check_metadata(self, playlist_name=None, video_id=None):
        """Check and print the metadata for a specific song or all songs in a playlist or the entire library."""
        if playlist_name and video_id:
            key = (playlist_name, video_id)
            if key in self.songs:
                self._print_metadata(self.songs[key]["file_path"])
            else:
                logging.error(f"Song with ID {video_id} not found in playlist {playlist_name}.")
        elif playlist_name:
            for key, song in self.songs.items():
                if key[0] == playlist_name:
                    self._print_metadata(song["file_path"])
        else:
            for song in self.songs.values():
                self._print_metadata(song["file_path"])

    def _print_metadata(self, file_path):
        """Helper function to print metadata for a given file."""
        audio = ID3(file_path)
        logging.info(f"Metadata for {file_path}:")
        logging.info(f"Title: {audio.get('TIT2')}")
        logging.info(f"Artist: {audio.get('TPE1')}")
        logging.info(f"Album: {audio.get('TALB')}")
        logging.info(f"YouTube ID: {audio.get('TXXX:YouTubeID')}")

    def count_songs(self, playlist_name=None):
        """Return the number of songs in the entire library or within a specific playlist."""
        if playlist_name:
            return sum(1 for key in self.songs if key[0] == playlist_name)
        return len(self.songs)

    def update_library(self):
        """Rescan the folder, clean up non-MP3 files, validate songs, and refresh the library."""
        logging.info("Updating music library...")
        for playlist_name in os.listdir(self.base_folder):
            self.clean_up_non_mp3_files(playlist_name)
        self.scan_folders()
        if self.validate:
            self.validate_songs()

    def get_song_paths(self, playlist_name=None):
        """Return a list of all song file paths in the library or within a specific playlist."""
        if playlist_name:
            return [song["file_path"] for key, song in self.songs.items() if key[0] == playlist_name]
        return [song["file_path"] for song in self.songs.values()]

    def get_song_titles(self, playlist_name=None):
        """Return a list of all song titles in the library or within a specific playlist."""
        if playlist_name:
            return [song["title"] for key, song in self.songs.items() if key[0] == playlist_name]
        return [song["title"] for song in self.songs.values()]
