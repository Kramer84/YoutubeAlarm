from datetime import datetime, timedelta

from youtube_alarm.alarm import AlarmSession, next_alarm_time, run_alarm


class FakePlayer:
    def __init__(self):
        self.queue = []
        self.position = 0  # songs already started
        self.repeating = None
        self.finished = False

    def enqueue(self, path):
        self.queue.append(path)

    def play(self):
        self.position = 1 if self.queue else 0

    def play_on_repeat(self, path):
        self.repeating = path

    def songs_ahead(self):
        return len(self.queue) - self.position

    def now_playing(self):
        return self.queue[self.position - 1] if self.position else None

    def is_finished(self):
        return self.finished


def make_session(player, library_songs=(), pending=(), fetch=None, **kwargs):
    return AlarmSession(
        player=player,
        library_songs=list(library_songs),
        pending_urls=list(pending),
        fetch=fetch or (lambda url: None),
        alarm_tone="tone.wav",
        **kwargs,
    )


def test_alarm_later_today_rings_today():
    now = datetime(2026, 11, 1, 6, 0)
    assert next_alarm_time(now, 7, 30) == datetime(2026, 11, 1, 7, 30)


def test_alarm_time_already_passed_rings_tomorrow():
    now = datetime(2026, 12, 31, 8, 0)
    assert next_alarm_time(now, 7, 30) == datetime(2027, 1, 1, 7, 30)


def test_alarm_with_no_songs_falls_back_to_alarm_tone():
    player = FakePlayer()

    make_session(player).start()

    assert player.repeating == "tone.wav"


def test_alarm_plays_library_songs_up_to_buffer_size():
    player = FakePlayer()

    make_session(player, library_songs=["a", "b", "c"], buffer_size=2).start()

    assert player.queue == ["a", "b"]
    assert player.position == 1
    assert player.repeating is None


def test_ticks_top_up_queue_one_fetch_at_a_time():
    player = FakePlayer()
    results = {"u1": "p1", "u2": None, "u3": "a", "u4": "p4", "u5": "p5"}
    fetched = []

    def fetch(url):
        fetched.append(url)
        return results[url]

    session = make_session(
        player, library_songs=["a"], pending=list(results), fetch=fetch, buffer_size=2
    )
    session.start()

    session.tick()
    assert fetched == ["u1"]

    for _ in range(5):
        session.tick()

    # u2 failed, u3 is already queued, then the buffer (2 ahead) is full.
    assert player.queue == ["a", "p1", "p4"]
    assert fetched == ["u1", "u2", "u3", "u4"]


def test_library_songs_beyond_buffer_are_queued_before_fetching():
    player = FakePlayer()
    fetched = []
    session = make_session(
        player, library_songs=["a", "b", "c"], pending=["u1"],
        fetch=lambda url: fetched.append(url) or "p1", buffer_size=1,
    )
    session.start()

    session.tick()

    assert player.queue == ["a", "b"]
    assert fetched == []


class FakeClock:
    def __init__(self, start):
        self.time = start
        self.on_sleep = lambda: None

    def now(self):
        return self.time

    def sleep(self, seconds):
        self.time += timedelta(seconds=seconds)
        self.on_sleep()


def test_run_waits_for_wake_time_then_returns_when_everything_played():
    clock = FakeClock(datetime(2026, 11, 1, 7, 0))
    wake = datetime(2026, 11, 1, 7, 30)
    player = FakePlayer()
    started_at = []
    player.play = lambda: started_at.append(clock.now())
    # The player reports the end once the last pending song has been queued.
    clock.on_sleep = lambda: setattr(player, "finished", "p1" in player.queue)
    session = make_session(player, library_songs=["a"], pending=["u1"], fetch=lambda u: "p1")

    run_alarm(session, wake, now=clock.now, sleep=clock.sleep)

    assert started_at == [wake]
    assert player.queue == ["a", "p1"]


def test_session_logs_ringing_and_each_song_change(caplog):
    caplog.set_level("INFO")
    player = FakePlayer()
    session = make_session(player, library_songs=["/m/a.mp3", "/m/b.mp3"])

    session.start()
    session.tick()
    player.position = 2
    session.tick()
    session.tick()

    messages = [r.getMessage() for r in caplog.records]
    assert any("ringing" in m.lower() for m in messages)
    assert [m for m in messages if m.startswith("Now playing")] == [
        "Now playing: /m/a.mp3",
        "Now playing: /m/b.mp3",
    ]


def test_session_logs_fallback_to_alarm_tone(caplog):
    make_session(FakePlayer()).start()

    assert any(r.levelname == "WARNING" and "alarm tone" in r.getMessage() for r in caplog.records)
