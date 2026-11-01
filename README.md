# YouTube Alarm Clock

Wake up to your favorite music! This project is a Python-based alarm clock that plays audio directly from a YouTube playlist.

The script handles the heavy lifting: it downloads audio from the playlist, stores it locally in high-quality MP3 format, and plays it at your specified wake-up time using VLC media player. It acts as both a robust alarm clock and an offline music library manager.

## Features

-   **Alarm Triggered Playback**: Plays music at a specific time, acting as a reliable alarm.
-   **Smart Caching**: Downloads audio once and stores it locally. Subsequent alarms using the same playlist work offline (mostly) and start instantly.
-   **Bulk Downloading**: Can be used to download entire YouTube playlists to your local machine in one go.
-   **Metadata Management**: Automatically tags MP3 files with Title, Artist, Album (Playlist Name), and YouTube ID.
-   **Custom Storage**: You choose where your music is saved (defaults to `~/Music/YoutubeAlarm`).
-   **Robust Playback**: Plays through libvlc, in-process.
-   **Never silent**: Falls back to an alarm tone when no music is available.

## Requirements

-   **Python 3.11+**
-   **VLC** installed (the app uses libvlc through `python-vlc`; no VLC configuration needed)
-   **ffmpeg** (audio extraction and `--validate`)
-   **A JavaScript runtime**: Deno, Node.js, Bun or QuickJS on your PATH. yt-dlp needs one for YouTube, and the app enables whichever it finds.

## Installation

```bash
git clone https://github.com/Kramer84/YoutubeAlarm.git
cd YoutubeAlarm
uv tool install -e .                     # puts `youtube-alarm` on your PATH
# for development: uv venv --python 3.11 && uv pip install -e '.[dev]'
```

## Usage

```bash
# Ring at 07:30 (today, or tomorrow if 07:30 has passed)
youtube-alarm alarm "https://www.youtube.com/playlist?list=..." --hour 7 --minute 30 --shuffle

# Play right now (check sound and volume)
youtube-alarm play "https://www.youtube.com/playlist?list=..."

# Download the whole playlist ahead of time, so the alarm doesn't depend on the network
youtube-alarm download "https://www.youtube.com/playlist?list=..."
```

`youtube-alarm COMMAND --help` lists all options. Common ones:

| Option | Commands | Description |
| :--- | :--- | :--- |
| `--hour`, `--minute` | `alarm` | Alarm time (0-23, 0-59). |
| `--base-dir` | all | Music library folder. Defaults to `~/Music/YoutubeAlarm`. |
| `--shuffle` | `alarm`, `play` | Shuffle the playing order. |
| `--validate` | all | Check the playlist's MP3s with ffmpeg and delete corrupted ones first. |
| `-v` / `--verbose` | (before the command) | Debug logging. |

How it works: at start the playlist is fetched and the first few songs are downloaded. At the alarm time, songs already in the library play first, while the rest download in the background of the queue. If no songs are available (offline, YouTube blocked), a generated **alarm tone** plays on repeat instead, so the alarm never stays silent. Ctrl+C stops it.

Everything is logged to the terminal and to `~/.local/state/youtube-alarm/youtube-alarm.log` (rotated at 1 MB, 3 old files kept). That includes downloads, yt-dlp warnings, when the alarm rang, each song played, and how it stopped. Use `youtube-alarm -v ...` for debug detail.

Songs are stored as `<base-dir>/<playlist title>/<video id>_<title>.mp3`, tagged with title, artist, album (the playlist) and the YouTube ID.

## Development

```bash
.venv/bin/python -m pytest
```

The tests need `ffmpeg` and libvlc, but never reach the network or play sound.

## Troubleshooting

  - **HTTP 403 / download errors**: check that a JS runtime is installed (see Requirements). YouTube also changes its anti-bot protection often, so update yt-dlp: `uv tool upgrade youtube-alarm`.
  - **What happened this morning?** Read `~/.local/state/youtube-alarm/youtube-alarm.log`.
  - **Only the alarm tone plays**: the playlist couldn't be fetched at start and no songs were in the library. Run `download` the evening before.
  - **Command not found**: make sure the virtualenv is active or call `.venv/bin/youtube-alarm`.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your improvements.

## Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube video downloading.
- [ffmpeg](https://ffmpeg.org/) for audio conversion.
- [VLC](https://www.videolan.org/vlc/) for media playback.
- [mutagen](https://mutagen.readthedocs.io/en/latest/) for ID3 tag handling.
- [Typer](https://typer.tiangolo.com/) for the command line.
