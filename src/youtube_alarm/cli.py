import logging
import os
import random
import tempfile
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import typer

from .alarm import AlarmSession, next_alarm_time, run_alarm
from .downloader import fetch_playlist, fetch_song
from .music_library import MusicLibrary

app = typer.Typer(
    name="youtube-alarm",
    help="Alarm clock that plays music from a YouTube playlist.",
    add_completion=False,
    no_args_is_help=True,
)

DEFAULT_BASE_DIR = Path.home() / "Music" / "YoutubeAlarm"
MIN_SONGS_TO_START = 3

PlaylistArg = typer.Argument(..., help="YouTube playlist URL")
BaseDirOpt = typer.Option(DEFAULT_BASE_DIR, "--base-dir", help="Music library folder")
ShuffleOpt = typer.Option(False, "--shuffle", help="Shuffle the playlist")
ValidateOpt = typer.Option(False, "--validate", help="Delete corrupted MP3s (ffmpeg) first")


def log_file_path():
    state_home = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(state_home) / "youtube-alarm" / "youtube-alarm.log"


@app.callback()
def _configure_logging(verbose: bool = typer.Option(False, "--verbose", "-v")):
    log_file = log_file_path()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"),
        ],
        force=True,
    )


def _open_playlist(playlist_url, base_dir, validate):
    """Fetch playlist info and prepare its library folder."""
    name, urls = fetch_playlist(playlist_url)
    library = MusicLibrary(str(base_dir))
    if name:
        library.initialize_playlist(name)
        library.clean_up_non_mp3_files(name)
        if validate:
            library.validate_songs(name)
    else:
        typer.secho("Could not fetch the playlist; only the alarm tone is available.",
                    fg=typer.colors.YELLOW, err=True)
    return name, urls, library


@app.command()
def download(
    playlist_url: str = PlaylistArg,
    base_dir: Path = BaseDirOpt,
    validate: bool = ValidateOpt,
):
    """Download a whole playlist into the library."""
    name, urls, library = _open_playlist(playlist_url, base_dir, validate)
    if not name:
        raise typer.Exit(1)
    failed = [url for url in urls if not fetch_song(url, name, library)]
    typer.secho(f"{len(urls) - len(failed)}/{len(urls)} songs in {base_dir / name}",
                fg=typer.colors.GREEN if not failed else typer.colors.YELLOW)


def _ring(playlist_url, wake_time, base_dir, shuffle, validate):
    from .player import Player, write_alarm_tone  # libvlc loads only when playing

    name, urls, library = _open_playlist(playlist_url, base_dir, validate)
    if name:
        for url in urls[:MIN_SONGS_TO_START]:
            fetch_song(url, name, library)
    songs = library.get_song_paths(name) if name else []
    if shuffle:
        random.shuffle(songs)
        random.shuffle(urls)

    player = Player()
    with tempfile.TemporaryDirectory() as tmp:
        session = AlarmSession(
            player=player,
            library_songs=songs,
            pending_urls=urls if name else [],
            fetch=lambda url: fetch_song(url, name, library),
            alarm_tone=str(write_alarm_tone(Path(tmp) / "alarm.wav")),
        )
        if wake_time > datetime.now():
            logging.info(f"Alarm set for {wake_time:%A %d %B, %H:%M}. Ctrl+C to stop.")
        logging.info(f"Log file: {log_file_path()}")
        try:
            run_alarm(session, wake_time)
            logging.info("Playlist finished.")
        except KeyboardInterrupt:
            logging.info("Alarm stopped by user (Ctrl+C).")
        finally:
            player.stop()


@app.command()
def alarm(
    playlist_url: str = PlaylistArg,
    hour: int = typer.Option(..., min=0, max=23, help="Alarm hour (0-23)"),
    minute: int = typer.Option(..., min=0, max=59, help="Alarm minute (0-59)"),
    base_dir: Path = BaseDirOpt,
    shuffle: bool = ShuffleOpt,
    validate: bool = ValidateOpt,
):
    """Wait until HOUR:MINUTE, then play the playlist."""
    _ring(playlist_url, next_alarm_time(datetime.now(), hour, minute), base_dir, shuffle, validate)


@app.command()
def play(
    playlist_url: str = PlaylistArg,
    base_dir: Path = BaseDirOpt,
    shuffle: bool = ShuffleOpt,
    validate: bool = ValidateOpt,
):
    """Play the playlist right now (useful to test sound and volume)."""
    _ring(playlist_url, datetime.now(), base_dir, shuffle, validate)


if __name__ == "__main__":
    app()
