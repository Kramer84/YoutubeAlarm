from importlib.metadata import PackageNotFoundError, version

from .music_library import MusicLibrary

__all__ = ["MusicLibrary"]

try:
    __version__ = version("youtube-alarm")
except PackageNotFoundError:
    __version__ = "unknown"
