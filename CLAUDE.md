# CLAUDE.md

YouTube Alarm: a Python CLI alarm clock. It downloads a YouTube playlist to local MP3s (yt-dlp + ffmpeg) and plays them in-process through libvlc (python-vlc) at the wake-up time.

Read `CODEBASE.md` before exploring: it maps every module and the on-disk library format. Read `ROADMAP.md` at the start of a session. Its top section holds the current state, the decisions already made (don't reopen them) and the open questions. Issues are numbered there: reference them by ID (e.g. `N1`) in commits, add any new one you find, and move finished items to its done log.

## Environment

- System binaries required at runtime: `ffmpeg` and VLC/libvlc. yt-dlp also needs a JS runtime for YouTube (`node` is installed).
- The venv is uv-managed: `uv venv --python 3.11 && uv pip install -e '.[dev]'`. The user runs an editable `uv tool install -e .` build of the same checkout.
- yt-dlp enables only `deno` by default. `downloader/songs.py:_base_opts` passes every JS runtime found on the PATH; without one, YouTube returns 403s or drops formats.

## Running

- Run the app as `.venv/bin/youtube-alarm {download,alarm,play} PLAYLIST_URL`. `play` rings right away, so use it to try a change without waiting for an alarm time.
- A real run reaches YouTube and plays sound out loud. For a quiet check, construct `Player(audio_output="dummy")`. The smoke-test pattern is to patch `Player.__init__` with `functools.partialmethod(..., audio_output="dummy")` and call `cli.app`.

## Tests

- Run `.venv/bin/python -m pytest`. The tests need ffmpeg and libvlc, and never reach the network. An autouse fixture points `XDG_STATE_HOME` at `tmp_path`, so they never write the real log.
- Test only at the agreed seams: the Typer CLI (`CliRunner`), `MusicLibrary` on `tmp_path`, `fetch_song`/`fetch_playlist` with `FakeYoutubeDL` patched over `yt_dlp.YoutubeDL`, `Player` on real libvlc with the `dummy` output, and `AlarmSession`/`run_alarm` with `FakePlayer`/`FakeClock`.
- ffmpeg-generated MP3s carry an ID3 header. The `make_song` fixture strips it, so "untagged" really means untagged.

## Workflow

- Work test-first with the `tdd` skill: one failing test, then the code to pass it, at the seams listed under Tests. Agree on a new seam with the user before testing at it.
- The user commits directly to `main`. Commit when asked, with a descriptive message that names roadmap IDs.
- At the end of a session, update `ROADMAP.md` (state, decisions, next steps) and `CODEBASE.md` (module map), so the next session can start from them.

## Conventions

- Code is formatted with black and isort. Match that style.
- On-disk contract: `<base_dir>/<sanitized playlist title>/<11-char video id>_<sanitized title>.mp3`, plus ID3 tags (`TIT2`, `TPE1`, `TALB`, `TXXX:YouTubeID`, `TXXX:PlaylistName`). `MusicLibrary` parses IDs from the first 11 characters of the filename. Any download path must produce exactly this layout.
- The default library location is `~/Music/YoutubeAlarm`. Do not point a test run at it: `MusicLibrary` deletes files in there (download leftovers, and corrupted MP3s with `--validate`).
- An alarm that stays silent is the worst failure this program can have. Any change to the trigger and playback path must still make sound when the network, YouTube or VLC fails.
