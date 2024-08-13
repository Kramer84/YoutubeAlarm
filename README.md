# YouTube Alarm Clock

This project is a Python-based alarm clock that plays music from a YouTube playlist. The script downloads the audio from the playlist, stores it locally, and plays it at the specified alarm time using VLC media player. It also includes robust handling for metadata management, asynchronous downloading, and validation of downloaded files.

## Features

- **Download and Store Audio**: Downloads audio from a YouTube playlist and stores it locally in high-quality MP3 format.
- **Metadata Management**: Automatically adds ID3 tags (title, artist, album) to downloaded MP3 files.
- **Redundant Download Avoidance**: Checks if audio has already been downloaded to avoid redundant downloads.
- **Asynchronous Operations**: Monitors the playlist and downloads new songs asynchronously.
- **Playlist Management**: Maintains a buffer of songs to ensure continuous playback without interruptions.
- **Alarm Triggered Playback**: Plays music at a specified alarm time, optionally starting with a set number of pre-downloaded songs.
- **File Validation**: Optionally validate the integrity of MP3 files in the music library.
- **VLC Integration**: Uses VLC media player for non-blocking audio playback with the ability to manage and monitor the playlist.

## Requirements

- Python 3.x
- Conda
- `yt-dlp`
- `requests`
- `ffmpeg`
- VLC media player
- `mutagen` (for metadata handling)
- `psutil` (for process management)

## Installation

### Clone the Repository

```bash
git clone https://github.com/yourusername/youtube-alarm-clock.git
cd youtube-alarm-clock
```

### Create the Conda Environment

Run the provided bash script to create the Conda environment and install the necessary libraries:

```bash
./create_youtube_alarm_env.sh
```

### Manual Installation

If you prefer to install the dependencies manually, follow these steps:

1. Create a new Conda environment and install Python:

    ```bash
    conda create --name youtubeAlarm python -y
    ```

2. Activate the environment:

    ```bash
    conda activate youtubeAlarm
    ```

3. Install the required libraries:

    ```bash
    conda install -c conda-forge yt-dlp requests ffmpeg psutil -y
    conda install -c anaconda logging argparse
    pip install mutagen python-vlc
    ```

4. Deactivate the environment:

    ```bash
    conda deactivate
    ```

## VLC Configuration

Enable VLC's HTTP interface by creating a VLC configuration file `vlcrc` if it doesn't already exist:

```sh
mkdir -p ~/.config/vlc
echo 'http-host=localhost' > ~/.config/vlc/vlcrc
echo 'http-password=vlc' >> ~/.config/vlc/vlcrc
```

## Usage

1. Activate the Conda environment:

    ```bash
    conda activate youtubeAlarm
    ```

2. Run the script with the required arguments:

    ```bash
    python youtube_alarm.py --hour <hour> --minute <minute> --playlist <playlist_url>
    ```

    - Replace `<hour>` with the hour you want the alarm to trigger (0-23).
    - Replace `<minute>` with the minute you want the alarm to trigger (0-59).
    - Replace `<playlist_url>` with the URL of the YouTube playlist.

    Example:

    ```bash
    python youtube_alarm.py --hour 10 --minute 00 --playlist https://www.youtube.com/playlist?list=PL8FvEtnALTbRjuG8qcoMqstD5MDwV00f7
    ```

3. Optional flags:

    - `--test`: Start playback immediately for testing purposes.
    - `--validate`: Validate MP3 files in the music library before starting.
    - `--shuffle`: Shuffle the playlist before playing.

    Example with optional flags:

    ```bash
    python youtube_alarm.py --hour 7 --minute 30 --playlist https://www.youtube.com/playlist?list=PL8FvEtnALTbRjuG8qcoMqstD5MDwV00f7 --test --validate --shuffle
    ```

## Testing

### Unit Tests

Unit tests are available to validate the functionality of both the `MusicLibrary` and `VLCManager` classes.

1. **Run Music Library Tests**:

    ```bash
    python -m unittest discover -s tests -p "music_library_test.py"
    ```

2. **Run VLC Manager Tests**:

    ```bash
    python -m unittest discover -s tests -p "vlc_test.py"
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
