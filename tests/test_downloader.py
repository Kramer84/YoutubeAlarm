import os
import shutil

import yt_dlp
from mutagen.id3 import ID3

from tests.conftest import URL, VIDEO_ID, FakeYoutubeDL
from youtube_alarm.downloader import fetch_playlist, fetch_song
from youtube_alarm.music_library import MusicLibrary


def test_fetched_song_is_stored_in_library_layout_despite_special_characters(tmp_path, fake_ydl):
    library = MusicLibrary(str(tmp_path))

    path = fetch_song(URL, "Morning", library)

    assert os.path.exists(path)
    assert os.path.dirname(path) == str(tmp_path / "Morning")
    assert os.path.basename(path).startswith(f"{VIDEO_ID}_")
    assert library.song_exists("Morning", VIDEO_ID)


def test_song_already_in_library_is_not_downloaded_again(tmp_path, fake_ydl, make_song):
    existing = make_song(tmp_path / "Morning", f"{VIDEO_ID}_Artist_Song_Live.mp3")
    library = MusicLibrary(str(tmp_path))

    path = fetch_song(URL, "Morning", library)

    assert fake_ydl.downloads == []
    assert path == str(existing)
    assert os.listdir(tmp_path / "Morning") == [existing.name]


def test_fetched_song_is_tagged_with_original_title_and_source(tmp_path, fake_ydl):
    path = fetch_song(URL, "Morning", MusicLibrary(str(tmp_path)))

    tags = ID3(path)
    assert str(tags["TIT2"]) == "Artist | Song: Live"
    assert str(tags["TPE1"]) == "Artist"
    assert str(tags["TALB"]) == "Morning"
    assert str(tags["TXXX:YouTubeID"]) == VIDEO_ID
    assert str(tags["TXXX:PlaylistName"]) == "Morning"


def test_failed_download_returns_none(tmp_path, fake_ydl, monkeypatch):
    def unavailable(self, url, download=True):
        raise yt_dlp.utils.DownloadError("Video unavailable")

    monkeypatch.setattr(FakeYoutubeDL, "extract_info", unavailable)

    assert fetch_song(URL, "Morning", MusicLibrary(str(tmp_path))) is None


def test_playlist_gives_sanitized_name_and_video_urls(fake_ydl):
    name, urls = fetch_playlist("https://www.youtube.com/playlist?list=PL123")

    assert name == "Wake_Up_Mix"
    assert urls == [URL]


def test_unreachable_playlist_gives_no_videos(fake_ydl, monkeypatch):
    def offline(self, url, download=True):
        raise yt_dlp.utils.DownloadError("Unable to download webpage")

    monkeypatch.setattr(FakeYoutubeDL, "extract_info", offline)

    assert fetch_playlist("https://www.youtube.com/playlist?list=PL123") == (None, [])


def test_yt_dlp_may_use_every_javascript_runtime_on_path(tmp_path, fake_ydl, monkeypatch):
    on_path = {"node": "/usr/bin/node", "bun": "/opt/bun"}
    monkeypatch.setattr(shutil, "which", on_path.get)

    fetch_song(URL, "Morning", MusicLibrary(str(tmp_path)))

    assert fake_ydl.last_opts["js_runtimes"] == {"node": {}, "bun": {}}
