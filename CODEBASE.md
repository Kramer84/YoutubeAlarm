# CODEBASE.md

Index of modules and responsibilities. Update it in the same commit as any change that adds, moves or re-scopes a module.

## Layout

```
src/youtube_alarm/
  cli.py               Typer app (entry point `youtube-alarm`): download / alarm / play; logging setup
  alarm.py             next_alarm_time, AlarmSession (queue + refill + fallback), run_alarm loop
  player.py            Player (libvlc via python-vlc, in-process) + write_alarm_tone
  downloader/songs.py  fetch_playlist, fetch_song: yt-dlp → library layout + ID3 tags
  music_library.py     MusicLibrary: in-memory index of the MP3 folder tree
  utils.py             sanitize_name, extract_id_from_url, extract_id_from_filename
  __main__.py          `python -m youtube_alarm`

tests/                 pytest; conftest.py holds the MP3 fixtures and FakeYoutubeDL
```

## Runtime flow

1. `cli._ring()` (shared by `alarm` and `play`) calls `fetch_playlist(url)`, which returns `(sanitized name, video URLs)` or `(None, [])` when offline.
2. It prepares `MusicLibrary`: creates the playlist folder, removes download leftovers, and validates if `--validate` is set. It then downloads the first `MIN_SONGS_TO_START` (3) songs.
3. It builds an `AlarmSession(player, library_songs, pending_urls, fetch, alarm_tone)` and calls `run_alarm(session, wake_time)`:
   - It sleeps in chunks of at most 30 s against the wall clock until the wake time, so a suspend doesn't make the alarm late.
   - `session.start()` either loops the alarm tone (no songs at all) or enqueues up to `buffer_size` (20) library songs and plays.
   - `session.tick()` runs every 0.5 s. When fewer than 20 songs are waiting, it adds one: the next library song first, otherwise one fetched URL. A fetch blocks the loop for one download, which is fine because libvlc plays on its own threads.
   - The loop ends when the player has finished and nothing is left to queue. Ctrl+C raises KeyboardInterrupt, which the CLI catches before stopping the player.

There is no asyncio and no subprocess: playback runs in-process in libvlc.

## Logging

- The `cli._configure_logging` callback sends output to stderr and to a `RotatingFileHandler` at `$XDG_STATE_HOME/youtube-alarm/youtube-alarm.log` (default `~/.local/state/...`).
- yt-dlp's messages are routed through `logging.getLogger("yt_dlp")` via its `logger` option.
- `AlarmSession` logs when it rings (or falls back to the alarm tone) and each song change, detected on `tick()`.

## Player (`player.py`)

- It wraps a `vlc.MediaListPlayer`. `songs_ahead()` uses `media_list.index_of_item(current media)`.
- `enqueue()` on a finished player resumes on the new song, so a slow download doesn't leave the alarm silent.
- `play_on_repeat(path)` replaces the queue and loops it. `write_alarm_tone()` generates a beep WAV with `wave`.
- Tests use `Player(audio_output="dummy")`. The dummy output plays faster than real time, which keeps the tests fast and silent.

## Downloader (`downloader/songs.py`)

- `_base_opts()` sets `quiet`, the yt-dlp logger, and `js_runtimes` for every runtime found on the PATH.
- `fetch_song` skips the download when the URL's video ID is already in the library. It takes the real file path from `info["requested_downloads"][0]["filepath"]`, because yt-dlp rewrites characters like `|` and `:`. It renames the file to `<id>_<sanitize_name(title)>.mp3` through `MusicLibrary.add_song`, writes the ID3 tags, and returns None on `DownloadError`.

## MusicLibrary (`music_library.py`)

- `songs: dict[(playlist_name, video_id)] -> {title, file_path, youtube_id}`. It is rebuilt from disk by `scan_folders()`.
- Each subfolder of `base_folder` is a playlist. Filenames must match `^[A-Za-z0-9_-]{11}_.+\.mp3$`.
- `clean_up_non_mp3_files` (misnamed) deletes only download leftovers (`DOWNLOAD_LEFTOVER_SUFFIXES`).
- `validate_songs(playlist)` deletes corrupted MP3s of that playlist only, checked with `ffmpeg -v error -f null`.

## External dependencies

- yt-dlp: extraction and download. Update it often.
- python-vlc + system libvlc: playback.
- ffmpeg: MP3 extraction and validation.
- mutagen: ID3 tags.
- typer: the CLI.
