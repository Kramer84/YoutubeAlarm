import os
import shutil
import subprocess
import unittest
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB
from music_library import MusicLibrary

class TestMusicLibrary(unittest.TestCase):

    BASE_TEST_FOLDER = "test_music_library"
    TEST_PLAYLISTS = ["TestPlaylist1", "TestPlaylist2", "TestPlaylist3"]

    def setUp(self):
        # Create test folders for multiple playlists
        for playlist in self.TEST_PLAYLISTS:
            os.makedirs(os.path.join(self.BASE_TEST_FOLDER, playlist), exist_ok=True)
            # Create some dummy MP3 files in each playlist folder
            self.create_dummy_mp3(playlist, "abcdefghijk_1_test_song.mp3", "Test Song 1", "Test Artist", "Test Album")
            self.create_dummy_mp3(playlist, "abcdefghijf_2_another_song.mp3", "Test Song 2", "Test Artist", "Test Album")
            self.create_dummy_mp3(playlist, "abcdefghijg_3_last_song.mp3", "Test Song 3", "Test Artist", "Test Album")
            # Create a non-MP3 file in the playlist folder
            with open(os.path.join(self.BASE_TEST_FOLDER, playlist, "not_a_song.txt"), "w") as f:
                f.write("This is not an MP3 file.")

    def tearDown(self):
        # Clean up the test folder after tests
        shutil.rmtree(self.BASE_TEST_FOLDER)

    def create_dummy_mp3(self, playlist, filename, title, artist, album):
        filepath = os.path.join(self.BASE_TEST_FOLDER, playlist, filename)
        # Generate a 1-second silent MP3 file using ffmpeg
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "1", filepath])

        # Add ID3 tags using mutagen
        audio = MP3(filepath, ID3=ID3)
        audio["TIT2"] = TIT2(encoding=3, text=title)
        audio["TPE1"] = TPE1(encoding=3, text=artist)
        audio["TALB"] = TALB(encoding=3, text=album)
        audio.save()

    def test_initialization(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        for playlist in self.TEST_PLAYLISTS:
            song_count = library.count_songs(playlist)
            print(f"Playlist: {playlist}, Counted Songs: {song_count}, Expected: 3")
            self.assertEqual(song_count, 3)  # Each playlist should have 3 songs
        self.assertTrue(os.path.exists(self.BASE_TEST_FOLDER))

    def test_clean_up_non_mp3_files(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        for playlist in self.TEST_PLAYLISTS:
            library.clean_up_non_mp3_files(playlist)
            self.assertFalse(os.path.exists(os.path.join(self.BASE_TEST_FOLDER, playlist, "not_a_song.txt")))

    def test_add_remove_song(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        playlist = self.TEST_PLAYLISTS[0]
        # Create the song that will be added
        new_song_filename = "abcdefghijk_4_new_song.mp3"
        new_song_path = os.path.join(self.BASE_TEST_FOLDER, playlist, new_song_filename)
        self.create_dummy_mp3(playlist, new_song_filename, "New Song", "New Artist", "New Album")
        # Add the song to the library
        library.add_song(playlist, "abcdefghiji", "New Song", new_song_path)
        # Verify that the song was added
        self.assertEqual(library.count_songs(playlist), 4)
        # Now remove the song using the unique YouTube ID
        library.remove_song(playlist, "abcdefghiji")
        # Verify that the song was removed
        self.assertEqual(library.count_songs(playlist), 3)
        # Check that the file was physically removed
        self.assertFalse(os.path.exists(new_song_path))


    def test_song_exists(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        for playlist in self.TEST_PLAYLISTS:
            self.assertTrue(library.song_exists(playlist, "abcdefghijk"))
            self.assertFalse(library.song_exists(playlist, "xyz12345678"))

    def test_validate_songs(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER, validate=True)
        for playlist in self.TEST_PLAYLISTS:
            self.assertEqual(library.count_songs(playlist), 3)

    def test_update_library(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        playlist = self.TEST_PLAYLISTS[0]
        self.create_dummy_mp3(playlist, "abcdefghiju_4_new_song.mp3", "New Song", "New Artist", "New Album")
        library.update_library()
        self.assertEqual(library.count_songs(playlist), 4)

    def test_get_song_paths(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        for playlist in self.TEST_PLAYLISTS:
            paths = library.get_song_paths(playlist)
            self.assertEqual(len(paths), 3)

    def test_get_song_titles(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        for playlist in self.TEST_PLAYLISTS:
            titles = library.get_song_titles(playlist)
            self.assertEqual(len(titles), 3)

    def test_get_metadata_by_path(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        playlist = self.TEST_PLAYLISTS[0]
        song_path = os.path.join(self.BASE_TEST_FOLDER, playlist, "abcdefghijk_1_test_song.mp3")
        metadata = library.get_metadata_by_path(song_path)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['title'], "Test Song 1")
        self.assertEqual(metadata['file_path'], song_path)

    def test_count_songs_in_all_playlists(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        total_songs = sum(library.count_songs(playlist) for playlist in self.TEST_PLAYLISTS)
        self.assertEqual(total_songs, 9)  # 3 songs in each of the 3 playlists

    def test_filename_validation(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        valid_filename = "abcdefghijk_Valid_Song_Title.mp3"
        invalid_filename = "Invalid_Song_Title.mp3"
        self.assertTrue(library.is_valid_filename_format(valid_filename))
        self.assertFalse(library.is_valid_filename_format(invalid_filename))

    def test_youtube_id_extraction(self):
        library = MusicLibrary(self.BASE_TEST_FOLDER)
        filename = "abcdefghijk_Valid_Song_Title.mp3"
        youtube_id = library.extract_youtube_id(filename)
        self.assertEqual(youtube_id, "abcdefghijk")

if __name__ == "__main__":
    unittest.main()
