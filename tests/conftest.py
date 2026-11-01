import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yt_dlp
from mutagen.id3 import ID3, TIT2, delete

VIDEO_ID = "dQw4w9WgXcQ"
URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


@pytest.fixture(autouse=True)
def isolated_state_dir(tmp_path, monkeypatch):
    """Keep the app's log file out of the real ~/.local/state."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


@pytest.fixture(scope="session")
def silent_mp3(tmp_path_factory):
    """A real, untagged 1-second MP3, generated once per session."""
    path = tmp_path_factory.mktemp("fixtures") / "silence.mp3"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "anullsrc=r=44100:cl=stereo", "-t", "1", str(path)],
        check=True,
    )
    return path


@pytest.fixture
def make_song(silent_mp3):
    """Copy the silent MP3 to `folder/name`, optionally with an ID3 title."""

    def _make(folder: Path, name: str, title=None) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        shutil.copy(silent_mp3, path)
        delete(path)  # ffmpeg writes its own ID3 header; start truly untagged
        if title:
            tags = ID3()
            tags.add(TIT2(encoding=3, text=title))
            tags.save(path)
        return path

    return _make


class FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL; records downloads, writes real MP3s."""

    downloads = []
    videos = {}  # video_id -> {"title":..., "uploader":...}
    source_mp3 = None

    def __init__(self, opts):
        self.opts = opts
        type(self).last_opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=True):
        if self.opts.get("extract_flat"):
            return {
                "title": "Wake Up: Mix!",
                "entries": [{"url": f"https://www.youtube.com/watch?v={v}"} for v in self.videos],
            }
        video_id = url.rsplit("=", 1)[-1]
        info = {"id": video_id, **self.videos[video_id]}
        if download:
            type(self).downloads.append(url)
            if "logger" in self.opts:  # real yt-dlp routes its warnings here
                self.opts["logger"].warning("WARNING: fake yt-dlp warning")
            # Real yt-dlp replaces characters like | and : in filenames.
            safe_title = info["title"].replace("|", "｜").replace(":", "：")
            template = self.opts["outtmpl"]
            path = template.replace("%(id)s", video_id).replace("%(title)s", safe_title)
            path = path.replace("%(ext)s", "mp3")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            shutil.copy(self.source_mp3, path)
            info["requested_downloads"] = [{"filepath": path}]
        return info


@pytest.fixture
def fake_ydl(monkeypatch, silent_mp3):
    FakeYoutubeDL.downloads = []
    FakeYoutubeDL.videos = {VIDEO_ID: {"title": "Artist | Song: Live", "uploader": "Artist"}}
    FakeYoutubeDL.source_mp3 = silent_mp3
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    return FakeYoutubeDL
