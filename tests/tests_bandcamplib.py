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

    def test_validate_url(self):
        url = "https://bandcamp.com"
        with self.assertRaises(ValueError) as cm:
            bcp.bandcamplib._validate_url(url)
        self.assertEqual("No band subdomain", str(cm.exception))

        url = "https://bandname.someothercamp.com"
        with self.assertRaises(ValueError) as cm:
            bcp.bandcamplib._validate_url(url)
        self.assertEqual("Not a bandcamp URL", str(cm.exception))
        url = "http://bandname.bandcamp.com"
        with self.assertRaises(ValueError) as cm:
            bcp.bandcamplib._validate_url(url)
        self.assertEqual("No https", str(cm.exception))

        url = "https://t4.bc-not-bits.com/stream/"
        with self.assertRaises(ValueError) as cm:
            bcp.bandcamplib._validate_url(url)
        self.assertEqual("Not a bandcamp URL", str(cm.exception))
