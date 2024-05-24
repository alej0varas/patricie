from .context import bcp

import unittest

bcp.bandcamplib.DEBUG = True
bcp.bandcamplib.THROTTLE_TIME = 1


class MainTests(unittest.TestCase):
    def test_get_track_from_artist_url(self):
        # using a artist url
        url = "https://<bandname>.bandcamp.com/"
        for mp3_info in bcp.bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_track_from_music_url(self):
        # using a artist url
        url = "https://<bandname>.bandcamp.com/music"
        for mp3_info in bcp.bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_mp3s_from_album_url(self):
        url = "https://<bandname>.bandcamp.com/album/<album_name>"
        for mp3_info in bcp.bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_mp3s_from_track_url(self):
        url = "https://<bandname>.bandcamp.com/track/<track_name>"
        for mp3_info in bcp.bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_albums_urls_from_url(self):
        url = "https://<bandname>.bandcamp.com/music"
        bcp.bandcamplib._get_albums_urls_from_url(url)
