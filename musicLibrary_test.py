import unittest
import os
import shutil
from music_library import MusicLibrary

class TestMusicLibrary(unittest.TestCase):

    BASE_TEST_FOLDER = "test_music_library"
    TEST_PLAYLIST = "TestPlaylist"

    def setUp(self):
        # Create test folder
        os.makedirs(os.path.join(self.BASE_TEST_FOLDER, self.TEST_PLAYLIST), exist_ok=True)
        # Create some dummy MP3 files in the playlist folder
        self.create_dummy_mp3("1_test_song.mp3")
        self.create_dummy_mp3("2_another_song.mp3")
        self.create_dummy_mp3("3_last_song.mp3")
        # Create a non-MP3 file in the playlist folder
        with open(os.path.join(self.BASE_TEST_FOLDER, self.TEST_PLAYLIST, "not_a_song.txt"), "w") as f:
            f.write("This is not an MP3 file.")

    def tearDown(self):
        # Clean up the test folder after tests
        shutil.rmtree(self.BASE_TEST_FOLDER)

    def create_dummy_mp3(self, filename):
        filepath = os.path.join(self.BASE_TEST_FOLDER, self.TEST_PLAYLIST, filename)
        with open(filepath, "wb") as f:
            f.write(b"\x00\x00\x00\x00\x00\x00")  # Simple dummy binary data to represent a file

    def test_initialization(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        self.assertEqual(library.count_songs(self.TEST_PLAYLIST), 3)
        self.assertTrue(os.path.exists(self.BASE_TEST_FOLDER))

    def test_clean_up_non_mp3_files(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        library.clean_up_non_mp3_files(self.TEST_PLAYLIST)
        self.assertFalse(os.path.exists(os.path.join(self.BASE_TEST_FOLDER, self.TEST_PLAYLIST, "not_a_song.txt")))

    def test_add_remove_song(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        library.add_song(self.TEST_PLAYLIST, "4", "new_song", os.path.join(self.BASE_TEST_FOLDER, self.TEST_PLAYLIST, "4_new_song.mp3"))
        self.assertEqual(library.count_songs(self.TEST_PLAYLIST), 4)
        library.remove_song(self.TEST_PLAYLIST, "4")
        self.assertEqual(library.count_songs(self.TEST_PLAYLIST), 3)

    def test_song_exists(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        self.assertTrue(library.song_exists(self.TEST_PLAYLIST, "1"))
        self.assertFalse(library.song_exists(self.TEST_PLAYLIST, "4"))

    def test_validate_songs(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER, validate=True)
        # Since we created dummy MP3 files that aren't valid, validation should remove them
        self.assertEqual(library.count_songs(self.TEST_PLAYLIST), 0)

    def test_update_library(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        self.create_dummy_mp3("4_new_song.mp3")
        library.update_library()
        self.assertEqual(library.count_songs(self.TEST_PLAYLIST), 4)

    def test_get_song_paths(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        paths = library.get_song_paths(self.TEST_PLAYLIST)
        self.assertEqual(len(paths), 3)

    def test_get_song_titles(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        titles = library.get_song_titles(self.TEST_PLAYLIST)
        self.assertEqual(len(titles), 3)

if __name__ == "__main__":
    unittest.main()
