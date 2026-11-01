import math
import struct
import wave
from urllib.parse import unquote, urlparse

import vlc


def write_alarm_tone(path, sample_rate=22050):
    """Write a short beep-beep-beep WAV to `path` and return the path.

    Generated rather than shipped so the fallback works with no assets.
    """
    frames = bytearray()
    for _ in range(4):
        for i in range(int(sample_rate * 0.15)):  # 150 ms beep
            sample = int(20000 * math.sin(2 * math.pi * 880 * i / sample_rate))
            frames += struct.pack("<h", sample)
        frames += b"\x00\x00" * int(sample_rate * 0.1)  # 100 ms gap
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))
    return path


class Player:
    """In-process audio playlist player backed by libvlc.

    libvlc plays on its own threads, so callers only poll this object.
    """

    def __init__(self, audio_output=None):
        args = ["--no-video", "--quiet"]
        if audio_output:
            args.append(f"--aout={audio_output}")
        self._instance = vlc.Instance(*args)
        self._media_list = self._instance.media_list_new()
        self._list_player = self._instance.media_list_player_new()
        self._list_player.set_media_list(self._media_list)
        self._started = False

    def enqueue(self, path):
        was_finished = self.is_finished()
        self._media_list.add_media(self._instance.media_new_path(path))
        if was_finished:
            # A media list player stops at the end of its list; resume on
            # the new song so a slow download doesn't silence the alarm.
            self._list_player.play_item_at_index(self._media_list.count() - 1)

    def play(self):
        self._started = True
        self._list_player.play()

    def play_on_repeat(self, path):
        """Replace the queue with `path` and loop it until stopped."""
        self._media_list = self._instance.media_list_new()
        self._media_list.add_media(self._instance.media_new_path(path))
        self._list_player.set_media_list(self._media_list)
        self._list_player.set_playback_mode(vlc.PlaybackMode.loop)
        self.play()

    def stop(self):
        self._list_player.stop()

    def now_playing(self):
        """Path of the current song, or None."""
        media = self._list_player.get_media_player().get_media()
        if media is None:
            return None
        return unquote(urlparse(media.get_mrl()).path)

    def songs_ahead(self):
        """Number of queued songs that have not started playing yet."""
        total = self._media_list.count()
        if not self._started:
            return total
        media = self._list_player.get_media_player().get_media()
        current = self._media_list.index_of_item(media) if media else -1
        return total - (current + 1)

    def is_finished(self):
        return self._list_player.get_state() == vlc.State.Ended
