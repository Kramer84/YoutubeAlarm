# ROADMAP

Living plan for YouTube Alarm. IDs are stable: reference them in commits (e.g. `fix(N1): ...`). When an item is done, move it to the done log at the bottom.

Legend: **B** = bug, **R** = reliability, **A** = architecture, **T** = tests/tooling, **D** = docs, **F** = feature, **N** = found later.

---

## Where we are (2026-11-01)

- The app was rewritten and pushed to `main` (commit `3ff8adf`). It is a Typer CLI (`download` / `alarm` / `play`) with in-process python-vlc playback, a synchronous alarm loop (no asyncio), and one yt-dlp download path. It falls back to a generated alarm tone when no songs are available, and logs to `~/.local/state/youtube-alarm/youtube-alarm.log`.
- **Tests:** 30 pytest tests at the agreed seams (see CLAUDE.md). They pass on Python 3.11 and need no network or sound.
- **Verified by hand:** a real playlist downloaded and played, with the JS runtime picked up and no 403s. The offline run falls back to the tone. Ctrl+C stops cleanly.
- **Installed:** the user runs `uv tool install -e . --python 3.11 --force` from this checkout, so `youtube-alarm` is on their PATH.
- **For now** the alarm is run by hand in a terminal (`youtube-alarm alarm URL --hour 7 --minute 30`). Scheduling comes later.

## Decisions made

| Decision | Why |
|---|---|
| Typer, not argparse | User preference. The argparse `main.py` is deleted. |
| python-vlc in-process, not cvlc + HTTP | Tested: it plays a queue in order, handles odd filenames and reports song changes. It removes the subprocess, port, password and the killing of VLC processes. |
| No asyncio | libvlc plays on its own threads. A plain loop that fetches one song per tick keeps Ctrl+C working and the code simple. |
| Never ring silently | With no songs (offline, blocked), loop a generated beep (`write_alarm_tone`). This rule applies to every future change on the trigger and playback path. |
| Python ≥ 3.11 | yt-dlp deprecated 3.10. |
| `yt-dlp[default]` + auto-detected JS runtimes | yt-dlp only enables deno by default, so the user's node was ignored, which caused 403s. `[default]` brings in `yt-dlp-ejs`. |
| TDD at agreed seams | The user asked for TDD. The seams are listed in CLAUDE.md. |
| Commit directly to `main` | The user's choice for this repo. Write descriptive messages with roadmap IDs. |

## Open questions (for the next grilling session)

1. **How should the alarm run in practice?** (D4, R4) The user wasn't sure what the options imply. Options to walk through:
   - **Terminal, by hand** (current): simplest. The machine must stay on and awake, it's lost on reboot or logout, and it's stopped with Ctrl+C.
   - **systemd user service** started every evening, or launched with the alarm time: survives a closed terminal, journald keeps logs, and it's stopped with `systemctl --user stop`. The machine must still stay awake unless combined with the next option.
   - **systemd timer (`OnCalendar=`) that runs `play` at the wake time**: recurring alarms for free. `WakeSystem=true` can resume from suspend on most hardware. The downside is that songs must already be downloaded (see F5), because the network may be slow right after resume.
   - **`rtcwake`**: suspend now, wake at time X, then ring. Needs root or a polkit rule, and depends on the hardware.
   - Cross-cutting questions: how to snooze or stop when not in a terminal (F3), whether to unmute and set the volume (R6/F2), and whether the laptop lid or suspend inhibitors matter.
2. **Recurring alarms and config file** (F4): CLI flags only, or `~/.config/youtube-alarm/config.toml`? This depends on question 1.
3. **Offline at start** (N1): cache the playlist URL → folder name, or add a `--name` flag?

## Next steps (suggested order)

1. N1: offline start should still find the songs on disk (small, and it's a reliability gap).
2. N3, N6: log and naming cleanups (quick wins).
3. Grilling session on question 1, then D4 plus the chosen scheduling approach.
4. F5 (`sync` ahead of time) and F2 (volume and fade-in), which most scheduling options need.
5. F3, F4, F6, and the rest.

---

## Open items

### Reliability

| ID | Item |
|---|---|
| N1 | **Offline at start means beep only.** The playlist folder name comes from the YouTube title, so with no network at start the songs already downloaded can't be found. Cache `playlist URL → name` (e.g. `<base>/.playlists.json`) or accept `--name`. |
| R4 | Nothing keeps the machine awake until the alarm. The wall-clock wait copes with suspend/resume (30 s sleeps), but a suspended machine won't ring. This is resolved by the scheduling decision (question 1). |
| R6 | There is no volume control. The alarm plays at the current system volume, which may be muted. |
| R7 | yt-dlp is unpinned and YouTube breaks it often. Consider a startup check, or a hint to run `uv tool upgrade youtube-alarm` when downloads fail. |
| N7 | `cli._ring` downloads the first 3 songs *before* waiting for the alarm. If those songs were downloaded much earlier, that's fine. But nothing refreshes the queue during the night, so new playlist entries are only fetched once it rings. F5 fixes this. |

### Architecture and cleanup

| ID | Item |
|---|---|
| N3 | Rename `MusicLibrary.clean_up_non_mp3_files` to `remove_download_leftovers`. Lower the per-file "Error retrieving metadata" message on untagged files from ERROR to DEBUG. |
| N6 | Log lines say `root:`. Use `logging.getLogger(__name__)` per module, and log song titles instead of full paths. |
| A6 | `MusicLibrary`: `extract_youtube_id` duplicates `utils.extract_id_from_filename`, `song_exists` has three modes, and several methods are unused (`check_youtube_ids`, `get_song_titles`, `check_metadata`, `update_library`). Return a `Song` dataclass instead of raw dicts. |
| A9 | Add type hints throughout. |
| N8 | `fetch_song` could write tags with yt-dlp's `FFmpegMetadata` postprocessor instead of mutagen (optional). |

### Tests and tooling

| ID | Item |
|---|---|
| T4 | Add ruff (lint + format) to `[dev]`, plus an optional GitHub Actions workflow. Note that CI needs ffmpeg and libvlc installed. |
| T7 | The `play` and `alarm` commands have no CLI-level test, only their parts are tested. A test needs a way to pass `audio_output="dummy"` (e.g. a hidden `--audio-output` option, which is also useful for picking a device). |
| T8 | Consider committing `uv.lock` for reproducible installs. |

### Docs

| ID | Item |
|---|---|
| D4 | Document how to run it as a real alarm, once question 1 is decided. |

### Features

| ID | Feature |
|---|---|
| F2 | Volume fade-in, plus setting volume and unmuting at alarm start. |
| F3 | Snooze and stop controls without a terminal (keyboard, tiny local web page, tray icon, or `youtube-alarm stop`). |
| F4 | Recurring alarms and several saved alarms in a config file. |
| F5 | `sync` command: download new playlist entries ahead of time (e.g. a nightly timer), so the alarm never depends on the network. |
| F6 | Auto-stop after N minutes. |
| F7 | Library commands: `list`, `prune` (songs removed from the YouTube playlist), `stats`. |
| F8 | SponsorBlock `music_offtopic` trimming, so songs start on the music. |

---

## Done log

Original review (2026-10-30), all fixed on 2026-11-01 in `3ff8adf`:

- **Broken or destructive:**
  - B1: the entry point pointed at a missing `main:app`.
  - B2: `requests` was used but not declared.
  - B3: `--validate` deleted other playlists' songs.
  - B4: Ctrl+C was swallowed by VLCManager's signal handler.
  - B5: the alarm stayed silent with fewer than 3 songs; it now falls back to a tone (F1).
  - B6: every process with "vlc" in its name was killed.
- **Wrong behaviour:**
  - B7: titles with `|` or `:` weren't found after download.
  - B8: songs were re-downloaded and duplicated.
  - B9: the program never exited.
  - B10: paths weren't URL-encoded for VLC.
  - B11: shuffle didn't apply to library songs.
  - B12: an untagged MP3 crashed `check_metadata`.
  - B13: NameError in an error path.
  - B14: a plain file in the base folder crashed `update_library`.
  - B15: hour and minute weren't validated.
  - B16: the Typer `download` command didn't produce the library layout.
- **Reliability:**
  - R1: blocking calls inside async code.
  - R2: no timeouts on VLC HTTP calls.
  - R3: VLC HTTP used a hardcoded password.
  - R5: cleanup deleted user files; now only download leftovers.
  - R8: `logging.basicConfig` ran at import time.
- **Architecture:**
  - A1: python-vlc replaced cvlc + HTTP.
  - A2: one CLI (Typer).
  - A3: one download path.
  - A4: the `downloader/youtube.py` builders were deleted.
  - A5: scheduling, playing and the library are separated (`alarm.py`, `player.py`, `music_library.py`).
  - A7: the version comes from package metadata.
  - A8: the reformat that stripped docstrings was committed as is; the new modules have their own docstrings.
- **Tests:**
  - T1: pytest suite with `tmp_path`.
  - T2: the interactive VLC script was removed.
  - T3: alarm logic tested with a fake clock and player.
  - T5: venv rebuilt with uv.
  - T6: descriptive commit messages.
- **Docs:** D1 to D3, the README rewrite.

Found during the work, fixed on 2026-11-01:

- N2: Python ≥ 3.11.
- N4: JS runtime detection and `yt-dlp[default]`, which fixed the 403s.
- N5: log file, with yt-dlp output plus ring, now-playing and stop events.
