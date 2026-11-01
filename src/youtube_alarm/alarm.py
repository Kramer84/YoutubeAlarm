import logging
import time
from datetime import datetime, timedelta


def next_alarm_time(now: datetime, hour: int, minute: int) -> datetime:
    """The next moment at hour:minute strictly after `now`."""
    alarm = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if alarm <= now:
        alarm += timedelta(days=1)
    return alarm


class AlarmSession:
    """What happens once the alarm fires: play songs, keep the queue topped up.

    `fetch(url)` returns a local song path or None; the player is anything
    with the `Player` interface.
    """

    def __init__(self, player, library_songs, pending_urls, fetch, alarm_tone, buffer_size=20):
        self.player = player
        self.library_songs = list(library_songs)
        self.pending_urls = list(pending_urls)
        self.fetch = fetch
        self.alarm_tone = alarm_tone
        self.buffer_size = buffer_size
        self.queued = set()
        self._last_logged = None

    def start(self):
        if not self.library_songs:
            # Never ring silently: no music means the plain alarm tone.
            logging.warning("Alarm ringing with no songs available: playing the alarm tone")
            self.player.play_on_repeat(self.alarm_tone)
            return
        logging.info(
            f"Alarm ringing: {len(self.library_songs)} songs ready, "
            f"{len(self.pending_urls)} more to fetch"
        )
        for path in self.library_songs[: self.buffer_size]:
            self._enqueue(path)
        self.library_songs = self.library_songs[self.buffer_size :]
        self.player.play()

    def tick(self):
        """Add at most one song if fewer than `buffer_size` are waiting.

        Local songs go first; otherwise one URL is fetched (which blocks
        for the length of one download).
        """
        self._log_song_change()
        if self.player.songs_ahead() >= self.buffer_size:
            return
        if self.library_songs:
            self._enqueue(self.library_songs.pop(0))
        elif self.pending_urls:
            path = self.fetch(self.pending_urls.pop(0))
            if path and path not in self.queued:
                self._enqueue(path)

    def finished(self):
        return (
            self.player.is_finished()
            and not self.library_songs
            and not self.pending_urls
        )

    def _log_song_change(self):
        current = self.player.now_playing()
        if current and current != self._last_logged:
            logging.info(f"Now playing: {current}")
            self._last_logged = current

    def _enqueue(self, path):
        self.queued.add(path)
        self.player.enqueue(path)


def run_alarm(session, wake_time, now=datetime.now, sleep=time.sleep, poll_seconds=0.5):
    """Block until `wake_time`, then play until the session has nothing left."""
    # Short sleeps against the wall clock, so a suspend/resume doesn't make
    # the alarm late by the time the machine was asleep.
    while (remaining := (wake_time - now()).total_seconds()) > 0:
        sleep(min(remaining, 30))
    session.start()
    while not session.finished():
        session.tick()
        sleep(poll_seconds)
