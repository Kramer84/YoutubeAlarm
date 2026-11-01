import logging
import os
import shutil

import yt_dlp
from mutagen import MutagenError
from mutagen.id3 import ID3, TALB, TIT2, TPE1, TXXX

from ..utils import extract_id_from_url, sanitize_name


# yt-dlp needs a JS runtime for YouTube but only enables deno by default.
JS_RUNTIMES = ("deno", "node", "bun", "quickjs")


def _base_opts():
    # Route yt-dlp's own warnings and errors into our log instead of stderr.
    opts = {"quiet": True, "logger": logging.getLogger("yt_dlp")}
    runtimes = {name: {} for name in JS_RUNTIMES if shutil.which(name)}
    if runtimes:
        opts["js_runtimes"] = runtimes
    return opts


def _audio_opts(playlist_folder):
    return {
        **_base_opts(),
        "format": "bestaudio/best",
        "outtmpl": os.path.join(playlist_folder, "%(id)s_%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "noplaylist": True,
    }


def fetch_song(video_url, playlist_name, music_library):
    """Download one video as MP3 into the library layout and return its path.

    Returns None if the download fails.
    """
    known_id = extract_id_from_url(video_url)
    if known_id and music_library.song_exists(playlist_name, known_id):
        return music_library.songs[(playlist_name, known_id)]["file_path"]

    playlist_folder = os.path.join(music_library.base_folder, playlist_name)

    try:
        with yt_dlp.YoutubeDL(_audio_opts(playlist_folder)) as ydl:
            info = ydl.extract_info(video_url, download=True)
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Download failed for {video_url}: {e}")
        return None

    video_id = info["id"]
    # yt-dlp rewrites characters it can't put in filenames, so ask it where
    # the file landed instead of rebuilding the path from the title.
    downloaded_path = info["requested_downloads"][0]["filepath"]
    music_library.add_song(
        playlist_name=playlist_name,
        video_id=video_id,
        title=sanitize_name(info["title"]),
        file_path=downloaded_path,
    )
    path = music_library.songs[(playlist_name, video_id)]["file_path"]
    _write_tags(path, info, playlist_name)
    logging.info(f"Downloaded: {path}")
    return path


def _write_tags(path, info, playlist_name):
    try:
        tags = ID3(path)
    except MutagenError:
        tags = ID3()
    tags.add(TIT2(encoding=3, text=info["title"]))
    if info.get("uploader"):
        tags.add(TPE1(encoding=3, text=info["uploader"]))
    tags.add(TALB(encoding=3, text=playlist_name))
    tags.add(TXXX(encoding=3, desc="YouTubeID", text=info["id"]))
    tags.add(TXXX(encoding=3, desc="PlaylistName", text=playlist_name))
    tags.save(path)


def fetch_playlist(playlist_url):
    """Return (sanitized playlist name, video URLs), or (None, []) on failure."""
    opts = {**_base_opts(), "extract_flat": "in_playlist", "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Failed to fetch playlist {playlist_url}: {e}")
        return None, []
    name = sanitize_name(info.get("title") or "Unknown Playlist")
    urls = [entry["url"] for entry in info.get("entries") or [] if entry.get("url")]
    return name, urls
