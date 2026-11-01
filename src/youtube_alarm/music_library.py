import logging
import os
import re
import subprocess

from mutagen import MutagenError
from mutagen.id3 import ID3

from .utils import extract_id_from_filename, sanitize_name

# Intermediate files yt-dlp/ffmpeg leave behind when a download is interrupted.
DOWNLOAD_LEFTOVER_SUFFIXES = (".part", ".ytdl", ".webm", ".m4a", ".opus", ".temp.mp3")


class MusicLibrary:
    def __init__(self, base_folder, validate=False):
        self.base_folder = base_folder
        self.validate = validate
        self.songs = {}
        self.initialize_library()

    def initialize_library(self):

        if not os.path.exists(self.base_folder):
            os.makedirs(self.base_folder)
        self.scan_folders()

    def initialize_playlist(self, playlist_name):

        if not os.path.exists(os.path.join(self.base_folder, playlist_name)):
            os.makedirs(os.path.join(self.base_folder, playlist_name))
        self.scan_folders()

    def scan_folders(self):

        self.songs.clear()
        for playlist_name in os.listdir(self.base_folder):
            playlist_folder = os.path.join(self.base_folder, playlist_name)
            if os.path.isdir(playlist_folder):
                self.scan_playlist_folder(playlist_name, playlist_folder)

    def scan_playlist_folder(self, playlist_name, playlist_folder):

        for f in os.listdir(playlist_folder):
            if f.endswith(".mp3"):
                if self.is_valid_filename_format(f):
                    video_id = extract_id_from_filename(f)
                    file_path = os.path.join(playlist_folder, f)
                    metadata = self.get_metadata_by_path(file_path)
                    self.songs[(playlist_name, video_id)] = {
                        "title": metadata["title"] if metadata else f[12:-4],
                        "file_path": file_path,
                        "youtube_id": video_id,
                    }
                else:
                    logging.warning(f"Invalid filename format: {f}")

    def clean_up_non_mp3_files(self, playlist_name):

        playlist_folder = os.path.join(self.base_folder, playlist_name)
        if not os.path.isdir(playlist_folder):
            return
        for f in os.listdir(playlist_folder):
            if f.endswith(DOWNLOAD_LEFTOVER_SUFFIXES):
                file_path = os.path.join(playlist_folder, f)
                logging.info(f"Removing download leftover: {file_path}")
                os.remove(file_path)

    def add_song(self, playlist_name, video_id, title, file_path):

        playlist_folder = os.path.join(self.base_folder, playlist_name)
        if not os.path.exists(playlist_folder):
            os.makedirs(playlist_folder)

        sanitized_title = f"{video_id}_{title}.mp3"
        final_path = os.path.join(playlist_folder, sanitized_title)

        if file_path != final_path:
            os.rename(file_path, final_path)

        self.songs[(playlist_name, video_id)] = {
            "title": title,
            "file_path": final_path,
            "youtube_id": video_id,
        }

    def remove_song(self, playlist_name, video_id):

        key = (playlist_name, video_id)
        if key in self.songs:
            os.remove(self.songs[key]["file_path"])
            del self.songs[key]
            logging.info(
                f"Removed song with ID {video_id} from playlist {playlist_name}."
            )

    def song_exists(self, playlist_name, video_id=None, title=None, file_name=None):

        if video_id:
            return (playlist_name, video_id) in self.songs
        elif title:
            return any(
                song["title"] == title
                for (pl, _), song in self.songs.items()
                if pl == playlist_name
            )
        elif file_name:
            return any(
                os.path.basename(song["file_path"]) == file_name
                for (pl, _), song in self.songs.items()
                if pl == playlist_name
            )
        return False

    def validate_songs(self, playlist_name=None):

        valid_songs = {}
        for key, song in self.songs.items():
            in_scope = playlist_name is None or key[0] == playlist_name
            if not in_scope or self.is_valid_mp3(song["file_path"]):
                valid_songs[key] = song
            else:
                logging.info(
                    f"Removing corrupted or incomplete file: {song['file_path']}"
                )
                os.remove(song["file_path"])

        self.songs = valid_songs

    def is_valid_mp3(self, file_path):

        try:
            subprocess.run(
                ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"],
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def check_metadata(self, playlist_name=None, video_id=None):

        if playlist_name and video_id:
            key = (playlist_name, video_id)
            if key in self.songs:
                self._print_metadata(self.songs[key]["file_path"])
            else:
                logging.error(
                    f"Song with ID {video_id} not found in playlist {playlist_name}."
                )
        elif playlist_name:
            for key, song in self.songs.items():
                if key[0] == playlist_name:
                    self._print_metadata(song["file_path"])
        else:
            for song in self.songs.values():
                self._print_metadata(song["file_path"])

    def _print_metadata(self, file_path):

        try:
            audio = ID3(file_path)
        except MutagenError as e:
            logging.warning(f"No readable ID3 tags in {file_path}: {e}")
            return
        logging.info(f"Metadata for {file_path}:")
        logging.info(f"Title: {audio.get('TIT2')}")
        logging.info(f"Artist: {audio.get('TPE1')}")
        logging.info(f"Album: {audio.get('TALB')}")
        logging.info(f"YouTube ID: {audio.get('TXXX:YouTubeID')}")

    def get_metadata_by_path(self, file_path):

        try:
            audio = ID3(file_path)
            return {
                "title": audio.get("TIT2").text[0] if audio.get("TIT2") else None,
                "artist": audio.get("TPE1").text[0] if audio.get("TPE1") else None,
                "album": audio.get("TALB").text[0] if audio.get("TALB") else None,
                "youtube_id": audio.get("TXXX:YouTubeID").text[0]
                if audio.get("TXXX:YouTubeID")
                else None,
                "file_path": file_path,
            }
        except Exception as e:
            logging.error(f"Error retrieving metadata from {file_path}: {e}")
            return None

    def is_valid_filename_format(self, filename):

        pattern = r"^[a-zA-Z0-9_-]{11}_.+\.mp3$"
        return bool(re.match(pattern, filename))

    def extract_youtube_id(self, filename):

        return filename[:11]

    def count_songs(self, playlist_name=None):

        if playlist_name:
            return sum(1 for key in self.songs if key[0] == playlist_name)
        return len(self.songs)

    def update_library(self):

        logging.info("Updating music library...")
        for playlist_name in os.listdir(self.base_folder):
            self.clean_up_non_mp3_files(playlist_name)
        self.scan_folders()
        if self.validate:
            self.validate_songs()

    def get_song_paths(self, playlist_name=None):

        if playlist_name:
            return [
                song["file_path"]
                for key, song in self.songs.items()
                if key[0] == playlist_name
            ]
        return [song["file_path"] for song in self.songs.values()]

    def get_song_titles(self, playlist_name=None):

        if playlist_name:
            return [
                song["title"]
                for key, song in self.songs.items()
                if key[0] == playlist_name
            ]
        return [song["title"] for song in self.songs.values()]

    def check_youtube_ids(self, youtube_ids, playlist_name=None):

        results = []

        for video_id in youtube_ids:
            if playlist_name:
                exists = (playlist_name, video_id) in self.songs
            else:
                exists = any(pl_id == video_id for pl, pl_id in self.songs.keys())
            results.append(exists)

        return results

    def get_song_paths_by_id(self, video_id, playlist_name=None):

        paths = []

        if playlist_name:
            key = (playlist_name, video_id)
            if key in self.songs:
                paths.append(self.songs[key]["file_path"])
        else:
            for (pl_name, pl_id), song in self.songs.items():
                if pl_id == video_id:
                    paths.append(song["file_path"])

        return paths
