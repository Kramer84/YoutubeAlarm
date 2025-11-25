# YouTube Alarm Clock

This project is a Python-based alarm clock that plays music from a YouTube playlist. The script downloads the audio from the playlist, stores it locally, and plays it at the specified alarm time using VLC media player.

## Features

- **Download and Store Audio**: Downloads audio from a YouTube playlist and stores it locally in high-quality MP3 format.
- **Metadata Management**: Automatically adds ID3 tags (title, artist, album) to downloaded MP3 files.
- **Redundant Download Avoidance**: Checks if audio has already been downloaded to avoid redundant downloads.
- **Asynchronous Operations**: Monitors the playlist and downloads new songs asynchronously.
- **Playlist Management**: Maintains a buffer of songs to ensure continuous playback without interruptions.
- **Alarm Triggered Playback**: Plays music at a specified alarm time.
- **File Validation**: Optionally validate the integrity of MP3 files in the music library.
- **VLC Integration**: Uses VLC media player for non-blocking audio playback.

## Requirements

- Python 3.8+
- Conda (recommended)
- VLC media player (must be installed and in your system PATH)
- **Python Packages**:
  - `yt-dlp`
  - `requests`
  - `ffmpeg-python` (or `ffmpeg` installed on system)
  - `mutagen`
  - `psutil`
  - `aioconsole`
  - `python-vlc`

## Installation

### 1. Clone the Repository

```bash
git clone [https://github.com/yourusername/youtube-alarm-clock.git](https://github.com/yourusername/youtube-alarm-clock.git)
cd youtube-alarm-clock
```

### Create the Conda Environment

Run the provided bash script to create the Conda environment and install the necessary libraries:

```bash
./create_youtube_alarm_env.sh
```

### 2\. Create the Environment

**Linux / macOS:**
Run the provided bash script to create the Conda environment:

```bash
./create_youtube_alarm_env.sh
```

**Windows:**
Windows users cannot run the `.sh` script directly. Please run these commands in your Anaconda Prompt:

```bash
conda create --name youtubeAlarm python=3.8 -y
conda activate youtubeAlarm
conda install -c conda-forge yt-dlp requests ffmpeg psutil aioconsole mutagen -y
pip install python-vlc
```

### 3\. VLC Configuration

Enable VLC's HTTP interface by creating a VLC configuration file `vlcrc` if it doesn't already exist:

**Linux / macOS:**

```sh
mkdir -p ~/.config/vlc
echo 'http-host=localhost' > ~/.config/vlc/vlcrc
echo 'http-password=vlc' >> ~/.config/vlc/vlcrc
```

**Windows:** (NOT YET TESTED)

1.  Open VLC Media Player.
2.  Go to **Tools** -\> **Preferences**.
3.  At the bottom left, under "Show settings", select **All**.
4.  Navigate to **Interface** -\> **Main interfaces**.
5.  Check the box for **Web**.
6.  Navigate to **Interface** -\> **Main interfaces** -\> **Lua**.
7.  Under **Lua HTTP**, set **Password** to `vlc`.
8.  *Note: Ensure `vlc.exe` is added to your System PATH so the script can launch it.*


## Usage

1.  Activate the environment:

    ```bash
    conda activate youtubeAlarm
    ```

2.  Run the script:

    ```bash
    python src/main.py --hour <hour> --minute <minute> --playlist <playlist_url>
    ```

    **Example:**

    ```bash
    python src/main.py --hour 07 --minute 30 --playlist [https://www.youtube.com/playlist?list=PL8FvEtnALTbRjuG8qcoMqstD5MDwV00f7](https://www.youtube.com/playlist?list=PL8FvEtnALTbRjuG8qcoMqstD5MDwV00f7)
    ```

3.  **Arguments & Flags:**

    | Argument | Description |
    | :--- | :--- |
    | `--hour` | Alarm hour (0-23). |
    | `--minute` | Alarm minute (0-59). |
    | `--playlist` | URL of the YouTube playlist. |
    | `--test` | Start playback immediately (ignores time). |
    | `--validate` | Check integrity of MP3 files before starting. |
    | `--shuffle` | Shuffle the playlist order. |
    | `--download-all` | Download the entire playlist immediately without waiting/buffering. |

## Testing

**Run Unit Tests:**

```bash
python -m unittest discover -s tests
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your improvements.

## Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube video downloading.
- [ffmpeg](https://ffmpeg.org/) for audio conversion.
- [VLC](https://www.videolan.org/vlc/) for media playback.
- [mutagen](https://mutagen.readthedocs.io/en/latest/) for ID3 tag handling.
- [psutil](https://github.com/giampaolo/psutil) for process management.
