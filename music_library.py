import os
import logging
import re
import subprocess
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TXXX

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - line %(lineno)d - %(message)s'
)

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

    def initialize_playlist(self, playlist_name):
        """Initialize the music library by scanning the base folder and loading existing MP3 files organized by playlists."""
        if not os.path.exists(os.path.join(self.base_folder, playlist_name)):
            os.makedirs(os.path.join(self.base_folder, playlist_name))
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
                if self.is_valid_filename_format(f):
                    video_id = self.extract_youtube_id(f)
                    file_path = os.path.join(playlist_folder, f)
                    metadata = self.get_metadata_by_path(file_path)
                    self.songs[(playlist_name, video_id)] = {
                        "title": metadata["title"] if metadata else f[12:-4],  # Title is everything after YouTubeID_ until .mp3
                        "file_path": file_path,
                        "youtube_id": video_id
                    }
                else:
                    logging.warning(f"Invalid filename format: {f}")

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

        self.songs[(playlist_name, video_id)] = {"title": title, "file_path": final_path, "youtube_id": video_id}

    def remove_song(self, playlist_name, video_id):
        """Remove a song from the library by its playlist and video ID."""
        key = (playlist_name, video_id)
        if key in self.songs:
            os.remove(self.songs[key]['file_path'])
            del self.songs[key]
            logging.info(f"Removed song with ID {video_id} from playlist {playlist_name}.")

    def song_exists(self, playlist_name, video_id=None, title=None, file_name=None):
        """Check if a song exists in the library by its playlist and either video ID, title, or file name."""
        if video_id:
            return (playlist_name, video_id) in self.songs
        elif title:
            return any(song["title"] == title for (pl, _), song in self.songs.items() if pl == playlist_name)
        elif file_name:
            return any(os.path.basename(song["file_path"]) == file_name for (pl, _), song in self.songs.items() if pl == playlist_name)
        return False

    def validate_songs(self, playlist_name=None):
        """Validate all MP3 files in the library and remove corrupted ones."""
        valid_songs = {}
        if playlist_name:
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

    def get_metadata_by_path(self, file_path):
        """Retrieve metadata based on the file path."""
        try:
            audio = ID3(file_path)
            return {
                "title": audio.get('TIT2').text[0] if audio.get('TIT2') else None,
                "artist": audio.get('TPE1').text[0] if audio.get('TPE1') else None,
                "album": audio.get('TALB').text[0] if audio.get('TALB') else None,
                "youtube_id": audio.get('TXXX:YouTubeID').text[0] if audio.get('TXXX:YouTubeID') else None,
                "file_path": file_path
            }
        except Exception as e:
            logging.error(f"Error retrieving metadata from {file_path}: {e}")
            return None

    def is_valid_filename_format(self, filename):
        """Check if the filename matches the expected format: 'YouTubeID_Title.mp3'."""
        pattern = r'^[a-zA-Z0-9_-]{11}_.+\.mp3$'
        return bool(re.match(pattern, filename))

    def extract_youtube_id(self, filename):
        """Extract the YouTube ID from the filename (first 11 characters)."""
        return filename[:11]

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

    def check_youtube_ids(self, youtube_ids, playlist_name=None):
        """
        Check if the provided list of YouTube IDs corresponds to songs already in the library.

        Args:
            youtube_ids (list): List of YouTube IDs to check.
            playlist_name (str, optional): If provided, only check within this playlist.

        Returns:
            list: List of boolean values. True if the song is already in the library, False otherwise.
        """
        results = []

        for video_id in youtube_ids:
            if playlist_name:
                exists = (playlist_name, video_id) in self.songs
            else:
                exists = any(pl_id == video_id for pl, pl_id in self.songs.keys())
            results.append(exists)

        return results

    def get_song_paths_by_id(self, video_id, playlist_name=None):
        """
        Get the file path(s) of a song by its YouTube ID.

        Args:
            video_id (str): The YouTube ID of the song.
            playlist_name (str, optional): If provided, search within this playlist. Otherwise, search across all playlists.

        Returns:
            list: A list of file paths for the song(s) matching the YouTube ID.
        """
        paths = []

        if playlist_name:
            # Search within the specified playlist
            key = (playlist_name, video_id)
            if key in self.songs:
                paths.append(self.songs[key]['file_path'])
        else:
            # Search across all playlists
            for (pl_name, pl_id), song in self.songs.items():
                if pl_id == video_id:
                    paths.append(song['file_path'])

        return paths
