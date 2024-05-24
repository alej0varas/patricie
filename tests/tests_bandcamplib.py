import unittest

from . import constants
from .context import bcp

bcp.bandcamplib.DEBUG = True
bcp.bandcamplib.THROTTLE_TIME = 1


class MainTests(unittest.TestCase):
    def test_get_track_from_artist_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/"
        for mp3_info in bcp.bandcamplib.get_mp3s_from_url(url):
            print(mp3_info)
            break

    def test_get_track_from_music_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/music"
        for mp3_info in bcp.bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_mp3s_from_album_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/album/{constants.BC_ALBUMNAME}"
        for mp3_info in bcp.bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_mp3s_from_track_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/track/{constants.BC_TRACKNAME}>"
        for mp3_info in bcp.bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_albums_urls_from_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/music"
        bcp.bandcamplib._get_albums_urls_from_url(url)
