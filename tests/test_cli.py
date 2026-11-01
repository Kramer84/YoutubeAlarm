import os

from typer.testing import CliRunner

from youtube_alarm.cli import app

runner = CliRunner()


def test_each_command_exists():
    for command in ("download", "alarm", "play"):
        assert runner.invoke(app, [command, "--help"]).exit_code == 0


def test_alarm_rejects_out_of_range_time(fake_ydl):
    result = runner.invoke(app, ["alarm", "https://x/playlist", "--hour", "25", "--minute", "0"])

    assert result.exit_code == 2
    assert "--hour" in result.output
    assert "25" in result.output
    assert fake_ydl.downloads == []


def test_download_puts_whole_playlist_in_library(tmp_path, fake_ydl):
    fake_ydl.videos["abcdefghijk"] = {"title": "Second", "uploader": "B"}

    result = runner.invoke(app, ["download", "https://x/playlist", "--base-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    files = sorted(os.listdir(tmp_path / "Wake_Up_Mix"))
    assert files == ["abcdefghijk_Second.mp3", "dQw4w9WgXcQ_Artist_Song_Live.mp3"]


def test_download_fails_when_playlist_unreachable(tmp_path, fake_ydl, monkeypatch):
    import yt_dlp

    def offline(self, url, download=True):
        raise yt_dlp.utils.DownloadError("Unable to download webpage")

    monkeypatch.setattr(fake_ydl, "extract_info", offline)

    result = runner.invoke(app, ["download", "https://x/playlist", "--base-dir", str(tmp_path)])

    assert result.exit_code == 1


def test_download_is_logged_to_state_folder(tmp_path, fake_ydl, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    result = runner.invoke(app, ["download", "https://x/playlist", "--base-dir", str(tmp_path / "music")])

    assert result.exit_code == 0, result.output
    log = (tmp_path / "state" / "youtube-alarm" / "youtube-alarm.log").read_text()
    assert "Downloaded" in log
    assert "fake yt-dlp warning" in log
