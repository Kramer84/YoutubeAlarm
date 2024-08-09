Here is the updated `README` file:

# YouTube Alarm Clock

This project is a Python-based alarm clock that plays music from a YouTube playlist. The script downloads the audio from the playlist, stores it locally, and plays it at the specified alarm time.

## Features

- Download audio from a YouTube playlist and store it locally in the highest available quality.
- Check if the audio has already been downloaded to avoid redundant downloads.
- Monitor the playlist for changes and download new songs asynchronously.
- Play a randomly selected song from the downloaded collection at the specified alarm time.
- Optionally validate the integrity of MP3 files.
- Use VLC media player for non-blocking audio playback.

## Requirements

- Python 3.x
- Conda
- `yt-dlp`
- `requests`
- `ffmpeg`
- VLC media player

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
    ```

4. Install additional libraries via pip if necessary:

    ```bash
    pip install python-vlc
    ```

5. Deactivate the environment:

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

    - e.g. ```python youtube_alarm.py --hour 10 --minute 00 --playlist https://www.youtube.com/playlist?list=PL8FvEtnALTbRjuG8qcoMqstD5MDwV00f7```

3. Optional flags:

    - `--test`: Start playback immediately for testing purposes.
    - `--validate`: Validate MP3 files in the music library before starting.
    - `--shuffle`: Shuffle the playlist before playing.

Example:

```bash
python youtube_alarm.py --hour 7 --minute 30 --playlist https://www.youtube.com/playlist?list=PL8FvEtnALTbRjuG8qcoMqstD5MDwV00f7 --test --validate --shuffle
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your improvements.

## Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube video downloading.
- [requests](https://github.com/psf/requests) for handling HTTP requests.
- [ffmpeg](https://ffmpeg.org/) for audio conversion.
- [VLC](https://www.videolan.org/vlc/) for media playback.
