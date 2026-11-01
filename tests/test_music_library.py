from youtube_alarm.music_library import MusicLibrary


def test_validating_one_playlist_keeps_songs_of_other_playlists(tmp_path, make_song):
    kept = make_song(tmp_path / "Other", "aaaaaaaaaaa_kept.mp3")
    make_song(tmp_path / "Morning", "bbbbbbbbbbb_good.mp3")

    library = MusicLibrary(str(tmp_path))
    library.validate_songs("Morning")

    assert kept.exists()
    assert library.count_songs("Other") == 1
    assert library.count_songs("Morning") == 1


def test_validating_removes_corrupted_files(tmp_path, make_song):
    folder = tmp_path / "Morning"
    make_song(folder, "bbbbbbbbbbb_good.mp3")
    broken = folder / "ccccccccccc_broken.mp3"
    broken.write_bytes(b"not audio")

    library = MusicLibrary(str(tmp_path))
    library.validate_songs("Morning")

    assert not broken.exists()
    assert library.count_songs("Morning") == 1


def test_checking_metadata_tolerates_untagged_songs(tmp_path, make_song):
    make_song(tmp_path / "Morning", "bbbbbbbbbbb_untagged.mp3")

    library = MusicLibrary(str(tmp_path))
    library.check_metadata("Morning")


def test_updating_library_ignores_plain_files_in_base_folder(tmp_path, make_song):
    make_song(tmp_path / "Morning", "bbbbbbbbbbb_good.mp3")
    (tmp_path / "notes.txt").write_text("mine")

    library = MusicLibrary(str(tmp_path))
    library.update_library()

    assert (tmp_path / "notes.txt").exists()
    assert library.count_songs("Morning") == 1


def test_cleanup_removes_download_leftovers_but_keeps_user_files(tmp_path, make_song):
    folder = tmp_path / "Morning"
    make_song(folder, "bbbbbbbbbbb_good.mp3")
    leftovers = [folder / n for n in ("x.webm", "x.m4a", "x.mp3.part", "x.ytdl", "x.temp.mp3")]
    for f in leftovers:
        f.write_bytes(b"")
    cover = folder / "cover.jpg"
    cover.write_bytes(b"")

    MusicLibrary(str(tmp_path)).clean_up_non_mp3_files("Morning")

    assert cover.exists()
    assert not any(f.exists() for f in leftovers)
