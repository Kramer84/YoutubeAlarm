# YouTube Alarm Clock

Wake up to your favorite music! This project is a Python-based alarm clock that plays audio directly from a YouTube playlist.

The script handles the heavy lifting: it downloads audio from the playlist, stores it locally in high-quality MP3 format, and plays it at your specified wake-up time using VLC media player. It acts as both a robust alarm clock and an offline music library manager.

## Features

-   **Alarm Triggered Playback**: Plays music at a specific time, acting as a reliable alarm.
-   **Smart Caching**: Downloads audio once and stores it locally. Subsequent alarms using the same playlist work offline (mostly) and start instantly.
-   **Bulk Downloading**: Can be used to download entire YouTube playlists to your local machine in one go.
-   **Metadata Management**: Automatically tags MP3 files with Title, Artist, Album (Playlist Name), and YouTube ID.
-   **Custom Storage**: You choose where your music is saved (defaults to `~/Music/YoutubeAlarm`).
-   **Robust Playback**: Uses VLC media player for stable, non-blocking audio playback.
-   **Buffer Management**: intelligently buffers upcoming songs to ensure gapless playback during the alarm.

## Requirements

-   **Python 3.10+** (Required for the latest YouTube download protocols)
-   **VLC Media Player** (Must be installed and in your system PATH)
-   **Node.js** (Optional but recommended: helps `yt-dlp` bypass YouTube throttling)
-   **Conda** (Recommended for environment management)

## Installation

### 1. Clone the Repository

```bash
git clone [https://github.com/yourusername/youtube-alarm-clock.git](https://github.com/yourusername/youtube-alarm-clock.git)
cd youtube-alarm-clock
````

### 2\. Set Up the Environment

You can use the provided script to set up a Conda environment with all dependencies:

```bash
# Creates a conda env named 'youtubeAlarm' with Python 3.10
./scripts/create_python_env.sh
```

Alternatively, manually create the environment:

```bash
conda create --name youtubeAlarm python=3.10 -y
conda activate youtubeAlarm
conda install -c conda-forge ffmpeg psutil aioconsole mutagen requests nodejs -y
pip install python-vlc
pip install -U yt-dlp
```

### 3\. Install the Package

To make the `youtube-alarm` command available in your terminal, install the package in editable mode:

```bash
pip install -e .
```

### 4\. VLC Configuration

The script uses VLC's HTTP interface to control playback. You must enable it:

**Linux / macOS:**

```bash
mkdir -p ~/.config/vlc
echo 'http-host=localhost' > ~/.config/vlc/vlcrc
echo 'http-password=vlc' >> ~/.config/vlc/vlcrc
```

**Windows:**

1.  Open VLC Media Player.
2.  Go to **Tools** -\> **Preferences**.
3.  Select **All** under "Show settings" (bottom left).
4.  Navigate to **Interface** -\> **Main interfaces**. Check **Web**.
5.  Navigate to **Interface** -\> **Main interfaces** -\> **Lua**. Set **Lua HTTP Password** to `vlc`.

## Usage

Once installed, you can run the tool using the `youtube-alarm` command.

### 1\. Set an Alarm (Standard Mode)

The standard use case. The script will wait until the specified time, then start playing the playlist. It will download a few songs to buffer before the alarm rings.

```bash
youtube-alarm --hour 07 --minute 30 --playlist "[https://www.youtube.com/playlist?list=](https://www.youtube.com/playlist?list=)..."
```

### 2\. Download a Playlist (Library Mode)

If you just want to download a playlist to your computer without setting an alarm, use the `--download-all` flag. This ignores the time arguments.

```bash
youtube-alarm --playlist "[https://www.youtube.com/playlist?list=](https://www.youtube.com/playlist?list=)..." --download-all
```

### 3\. Play Immediately (Test Mode)

Want to listen right now? The `--test` flag starts playback immediately. This is useful for testing your volume or just listening to music.

```bash
# Play immediately, shuffling the songs
youtube-alarm --playlist "[https://www.youtube.com/playlist?list=](https://www.youtube.com/playlist?list=)..." --test --shuffle
```

### 4\. Custom Music Folder

By default, music is saved to `~/Music/YoutubeAlarm`. You can change this destination using `--base-dir`.

```bash
youtube-alarm --playlist "..." --download-all --base-dir "/home/user/MyServer/Music"
```

## Command Line Arguments

| Argument | Description | Required? |
| :--- | :--- | :--- |
| `--playlist` | URL of the YouTube playlist. | **Yes** |
| `--hour` | Alarm hour (0-23). | Yes (unless testing/downloading) |
| `--minute` | Alarm minute (0-59). | Yes (unless testing/downloading) |
| `--base-dir` | Directory to save MP3s. Defaults to `~/Music/YoutubeAlarm`. | No |
| `--test` | Start playback immediately, ignoring the clock. | No |
| `--download-all` | Download the entire playlist immediately. | No |
| `--shuffle` | Shuffle the playlist order before playing/downloading. | No |
| `--validate` | Check the integrity of existing MP3 files before starting. | No |

## Troubleshooting

  - **HTTP 403 / Download Errors**: YouTube frequently updates their anti-bot protection. If downloads fail, ensure `yt-dlp` is up to date:
    ```bash
    pip install -U yt-dlp
    ```
  - **VLC Not Starting**: Ensure `cvlc` (Linux) or `vlc` (Windows) is in your system PATH.
  - **Command Not Found**: If `youtube-alarm` is not found, ensure you ran `pip install -e .` and that your Conda environment is active.

## License

This project is licensed under the MIT License. See the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your improvements.

## Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube video downloading.
- [ffmpeg](https://ffmpeg.org/) for audio conversion.
- [VLC](https://www.videolan.org/vlc/) for media playback.
- [mutagen](https://mutagen.readthedocs.io/en/latest/) for ID3 tag handling.
- [psutil](https://github.com/giampaolo/psutil) for process management.
