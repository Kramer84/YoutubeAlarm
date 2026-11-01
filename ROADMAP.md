# ROADMAP

Issues and improvements found while reviewing the code on 2026-10-30, sorted by priority. IDs are stable, so reference them in commits (e.g. `fix(B3): ...`). Line numbers are for the working tree at that date.

**Status 2026-11-01:** the first TDD pass is done (26 tests). The app now runs on Typer, python-vlc and a synchronous loop. **Fixed:** B1-B16, R1-R3, R5, R8, A1, A2, A7, T1, T2, T5, D1-D3, F1. Struck-through rows below are done. **Still to do:** delete the obsolete `main.py`, `vlc_manager.py`, `downloader/youtube.py` and `scripts/manual_vlc_player.py` (A3/A4), then decide A8. The obsolete files were deleted by the user on 2026-11-01. New: N1-N3 at the bottom.

Legend: **B** = bug, **R** = reliability/robustness, **A** = architecture/cleanup, **T** = tests/tooling, **D** = docs, **F** = feature.

---

## P0: broken or destructive

| ID | Issue | Where |
|---|---|---|
| ~~B1~~ | ~~**Installed CLI is broken.** `pyproject.toml` points at `youtube_alarm.main:app`, but `main.py` has no `app`. The Typer app lives in `cli.py`, and its `alarm` command is a stub. Running `youtube-alarm` raises ImportError. | `pyproject.toml:36`, `cli.py:60`~~ |
| ~~B2~~ | ~~**Missing dependency.** `requests` is imported by `main.py` and `vlc_manager.py`, but the working tree replaced it with `httpx` (unused) in `pyproject.toml`. A clean install fails on import. | `pyproject.toml:22`~~ |
| ~~B3~~ | ~~**`--validate` deletes other playlists.** In `validate_songs(playlist_name)`, the `else` branch also catches every song from *other* playlists and calls `os.remove` on them. | `music_library.py:118-125`~~ |
| ~~B4~~ | ~~**Ctrl+C is swallowed.** `main()` installs a SIGINT handler, then `VLCManager.__init__` replaces it with `cleanup`. That kills VLC and returns, so `main_loop` spins forever. The original handler also calls `loop.stop()` inside `asyncio.run`, which is invalid. | `main.py:257`, `vlc_manager.py:25-26`~~ |
| ~~B5~~ | ~~**Silent alarm.** If the playlist folder has fewer than 3 songs when the alarm fires (offline, YouTube blocked, first run failed), `alarm_triggered` is set and VLC is never started. Nothing plays and there is no retry. | `main.py:208-221`~~ |
| ~~B6~~ | ~~**Kills every VLC process.** `kill_existing_vlc` terminates any process whose name contains "vlc", including the user's own player. It also raises TypeError when `proc.info["name"]` is None. | `vlc_manager.py:28-43`~~ |

## P1: wrong behaviour in common cases

| ID | Issue | Where |
|---|---|---|
| ~~B7~~ | ~~**Downloaded file not found when a title has special characters.** yt-dlp sanitizes filenames (`\|`, `:`, `/`, `?`, `"` become fullwidth look-alikes), but `download_audio` rebuilds the path from the raw title. "Expected file not found" follows, and the song is neither renamed, tagged nor enqueued during that session. Fix: use `info_dict["requested_downloads"][0]["filepath"]`. | `main.py:72`~~ |
| ~~B8~~ | ~~**Redundant re-downloads and duplicate files.** The initial buffer and `--download-all` call `download_audio` even for songs already in the library. Because the stored file was renamed, yt-dlp downloads it again, and the `song_exists` branch then returns None and leaves a duplicate `<id>_<raw>.mp3`. Check `song_exists` before downloading. | `main.py:71,235,324`~~ |
| ~~B9~~ | ~~**Program never exits.** `--play-and-exit` stops VLC at the end of the playlist, but `main_loop` keeps polling forever. | `main.py:199`~~ |
| ~~B10~~ | ~~**Paths with spaces or `#`/`&` fail to enqueue.** `in_enqueue` builds `input=file://...` without URL encoding. Use `Path.as_uri()` and pass `params=` to the HTTP client. | `vlc_manager.py:71-73,91`~~ |
| ~~B11~~ | ~~**`--shuffle` only partly applies.** It shuffles the *download* order, but the first 20 enqueued songs come from `get_song_paths()` in scan order. | `main.py:214`~~ |
| ~~B12~~ | ~~**Startup crash on untagged MP3s.** `check_metadata` → `_print_metadata` calls `ID3(path)` without a try block, so one file without an ID3 header aborts the run. It also logs four lines for every song on every start. | `music_library.py:149-174`, `main.py:293`~~ |
| ~~B13~~ | ~~**NameError in the error path.** `except MutagenError` logs `file_path`, which is undefined there. | `main.py:120`~~ |
| ~~B14~~ | ~~**`update_library` crashes when the base folder holds a plain file.** It calls `clean_up_non_mp3_files` on every entry. | `music_library.py:211`~~ |
| ~~B15~~ | ~~**Hour and minute are not validated.** `--hour 25` produces a raw `ValueError` traceback. | `main.py:313`~~ |
| ~~B16~~ | ~~**`cli.py download` output does not match the library layout.** There is no playlist subfolder, no sanitization and no ID3 tags. `MusicLibrary` would then flag or ignore the files. | `cli.py:27`~~ |

## P2: reliability and robustness

| ID | Issue |
|---|---|
| ~~R1~~ | ~~Everything marked `async` blocks the event loop (yt-dlp, `requests.get`, `time.sleep` in `initialize_vlc_server`). While `maintain_buffer` downloads up to 20 songs back to back, nothing else runs (no index updates, no Ctrl+C). Move blocking work to `asyncio.to_thread`, or drop async altogether (see A1).~~ |
| ~~R2~~ | ~~HTTP calls to VLC have no timeout, so a stuck VLC hangs the app.~~ |
| ~~R3~~ | ~~The VLC HTTP interface uses the hardcoded password `vlc` on a fixed port 8080, and `--http-host` is not set. Bind it to `127.0.0.1`, use a random password and a free port, or remove HTTP entirely (A1).~~ |
| R4 | The alarm time is computed once at start. If the machine suspends overnight, the wall-clock check still works, but nothing stops suspend. Consider `systemd-inhibit`, or document the systemd timer / `rtcwake` route. |
| ~~R5~~ | ~~`clean_up_non_mp3_files` deletes any non-MP3 file in a playlist folder (cover art, user notes, `.part` files from a download in progress). Restrict it to known temp extensions.~~ |
| R6 | There is no volume control. The alarm plays at whatever the system volume is, which may be muted. |
| R7 | yt-dlp is unpinned and YouTube breaks it often. Add a startup check or a `--update` hint, and document the JS runtime requirement (deno/node). |
| ~~R8~~ | ~~`logging.basicConfig` is called at import time in three modules, so library users cannot configure logging.~~ |

## P3: architecture and cleanup

| ID | Item |
|---|---|
| ~~A1~~ | ~~**Replace cvlc+HTTP with `python-vlc`, which is already a dependency.** It runs in-process `MediaListPlayer` with no subprocess, port, password, retries, process killing or index guessing. This removes most of `vlc_manager.py` and fixes B6, B10, R2 and R3.~~ |
| ~~A2~~ | ~~**Pick one CLI.** Finish the Typer migration (`download`, `alarm`, `play`, `library validate`), delete the argparse path, and fix the entry point (B1).~~ |
| A3 | **One download path.** `main.download_audio` and `downloader/youtube.py` duplicate the yt-dlp configuration. Build a single `fetch_song(url, playlist) -> Song` that owns the layout contract (naming, ID3 tags). It could use yt-dlp's own `FFmpegMetadata`/`--parse-metadata` instead of separate mutagen calls. |
| A4 | `downloader/youtube.py` defines `YouTubeInteractionClient` twice and imports `json` without using it. Most builders (subtitles, comments, remux, sponsorblock) are unused for an audio alarm (YAGNI). Shrink it to what the app uses. |
| A5 | Separate `Scheduler` (when) from `Player` (what plays) and `Library` (what is on disk). `main_loop` currently mixes all three. |
| A6 | `MusicLibrary` duplicates `extract_youtube_id` (also in `utils`), `song_exists` carries three modes, and some methods are unused (`check_youtube_ids`, `get_song_titles`, `song_exists(title=)`). Use a `Song` dataclass instead of raw dicts. |
| ~~A7~~ | ~~`__version__ = "0.1.0"` disagrees with pyproject `0.2.0`. Read it from `importlib.metadata`.~~ |
| A8 | The uncommitted reformat also **removed all docstrings and explanatory comments** (e.g. the "CRITICAL FIX" note on sanitized renames). Decide whether to restore them before committing. |
| A9 | Add type hints throughout, which helps a refactor this size. |

## Tests and tooling

| ID | Item |
|---|---|
| ~~T1~~ | ~~`test_music_library.py` imports `music_library` instead of `youtube_alarm.music_library`, writes into the CWD, and needs ffmpeg. Port it to pytest with `tmp_path`, and generate fixtures once per session.~~ |
| ~~T2~~ | ~~`test_vlc_manager.py` is an interactive script. Move it to `scripts/` or make it a `play` CLI command, and write real tests against a mocked player.~~ |
| T3 | Nothing tests the scheduling logic (`wake_up_time` rollover to the next day, trigger, buffer refill). Inject a clock and a fake downloader/player. |
| T4 | Add `[project.optional-dependencies] dev = [pytest, ruff]`, ruff config, and (optionally) a GitHub Actions workflow. |
| ~~T5~~ | ~~`.venv` is broken (its base interpreter is gone). Recreate it with uv, and consider committing `uv.lock`.~~ |
| T6 | Commits are auto-generated "chore: sync" messages. Write descriptive messages from now on, referencing roadmap IDs. |

## Docs

| ID | Item |
|---|---|
| ~~D1~~ | ~~The README references the deleted `scripts/create_python_env.sh` and a conda setup. Replace them with uv/pip instructions.~~ |
| ~~D2~~ | ~~The README's "VLC Configuration" step (`vlcrc`) is unnecessary because the app passes the HTTP flags itself. Remove it, or drop VLC HTTP entirely after A1.~~ |
| ~~D3~~ | ~~The README has broken links: the clone URL `yourusername/youtube-alarm-clock` wrapped in a markdown link, playlist URLs inside `[...]()`, and LICENSE linked to a Google search. Its usage section also documents the argparse flags, not the Typer commands.~~ |
| D4 | Document how to run it as an actual alarm: a systemd user timer or service, wake from suspend, and keeping the machine awake. |

## Features (after the P0/P1 fixes)

| ID | Feature |
|---|---|
| ~~F1~~ | ~~**Offline fallback sound.** Ship a bundled alarm tone and play it if no songs are available (completes the B5 fix).~~ |
| F2 | Volume fade-in, plus setting volume and unmuting at alarm start. |
| F3 | Snooze and stop controls (keyboard, or a tiny local web page or tray icon). |
| F4 | Recurring alarms (weekdays, specific days) and several saved alarms in a config file (`~/.config/youtube-alarm/config.toml`). |
| F5 | `library sync` to download new playlist entries ahead of time (e.g. a nightly timer), so the alarm itself never depends on the network. |
| F6 | Auto-stop after N minutes so the alarm doesn't play all day when nobody is home. |
| F7 | Playlist management commands: `list`, `prune` (songs removed from the YouTube playlist), `stats`. |
| F8 | SponsorBlock "music_offtopic" trimming, so wake-up songs start on the music and not on a video intro. |

---

## Found during the first pass

| ID | Item |
|---|---|
| N1 | **Offline at start means beep only.** The playlist name comes from YouTube, so if the network is down when `alarm` starts, the songs already in the library can't be found either. Cache `playlist URL → name` (e.g. `<base>/.playlists.json`) or accept `--name`. |
| ~~N2~~ | ~~yt-dlp has deprecated Python 3.10. Move to `requires-python >= 3.11`.~~ Done 2026-11-01. |
| ~~N4~~ | ~~yt-dlp only enabled `deno`, so `node` was ignored, which caused 403s and missing formats; `yt-dlp-ejs` was also missing. Now uses `yt-dlp[default]` plus auto-detected runtimes.~~ Done 2026-11-01. |
| ~~N5~~ | ~~No log file.~~ Now `~/.local/state/youtube-alarm/youtube-alarm.log`, with yt-dlp output routed in, plus ring/now-playing/stop events. Done 2026-11-01. |
| N6 | Log lines use the `root` logger name; switch modules to `logging.getLogger(__name__)`. Song paths in the log are long, so log titles instead. |
| N3 | Rename `MusicLibrary.clean_up_non_mp3_files` to `remove_download_leftovers`, and lower the per-song "Error retrieving metadata" log on untagged files from ERROR to DEBUG. |

## Suggested order

1. **Make it run:** B1, B2, T5, and A8 (decide before the reformat gets committed).
2. **Stop destroying or hanging:** B3, B4, B6, B9, B13.
3. **Make the alarm reliable:** B5 + F1, B7, B8, R2.
4. **Refactor:** A1 (python-vlc), then A2/A3 (one CLI, one downloader), with tests T1–T3 alongside.
5. Then features, starting with F2, F5 and F4.
