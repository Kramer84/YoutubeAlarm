import time

import pytest

from youtube_alarm.player import Player, write_alarm_tone


def wait_until(condition, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def player():
    p = Player(audio_output="dummy")
    yield p
    p.stop()


def test_plays_queued_songs_in_order_then_finishes(tmp_path, make_song, player):
    songs = [make_song(tmp_path, f"song {i} #&.mp3") for i in range(2)]
    for song in songs:
        player.enqueue(str(song))

    heard = []

    def track():
        now = player.now_playing()
        if now and now not in heard:
            heard.append(now)
        return player.is_finished()

    player.play()

    assert wait_until(track)
    assert heard == [str(s) for s in songs]


def test_counts_songs_not_yet_started(tmp_path, make_song, player):
    for i in range(3):
        player.enqueue(str(make_song(tmp_path, f"s{i}.mp3")))
    assert player.songs_ahead() == 3

    player.play()

    assert wait_until(player.is_finished)
    assert player.songs_ahead() == 0


def test_song_enqueued_after_running_dry_still_plays(tmp_path, make_song, player):
    player.enqueue(str(make_song(tmp_path, "first.mp3")))
    player.play()
    assert wait_until(player.is_finished)

    late = str(make_song(tmp_path, "late.mp3"))
    player.enqueue(late)

    assert wait_until(lambda: player.now_playing() == late)
    assert wait_until(player.is_finished)


def test_alarm_tone_repeats_until_stopped(tmp_path, player):
    tone = str(write_alarm_tone(tmp_path / "tone.wav"))

    player.play_on_repeat(tone)
    time.sleep(1.5)  # longer than the tone itself

    assert player.now_playing() == tone
    assert not player.is_finished()
