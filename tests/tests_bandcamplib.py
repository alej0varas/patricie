import unittest

from . import constants
from .context import bandcamplib

bandcamplib.DEBUG = True
bandcamplib.THROTTLE_TIME = 1


class MainTests(unittest.TestCase):
    def test_get_track_from_artist_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/"
        for mp3_info in bandcamplib.get_mp3s_from_url(url):
            print(mp3_info)
            break

    def test_get_track_from_music_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/music"
        for mp3_info in bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_mp3s_from_album_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/album/{constants.BC_ALBUMNAME}"
        for mp3_info in bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_mp3s_from_track_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/track/{constants.BC_TRACKNAME}"
        for mp3_info in bandcamplib.get_mp3s_from_url(url):
            pass

    def test_get_albums_urls_from_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/music"
        bandcamplib._get_albums_urls_from_url(url)


class ValidateUrlTests(unittest.TestCase):
    def test_no_band_subdomain(self):
        url = "https://bandcamp.com"
        with self.assertRaises(ValueError) as cm:
            bandcamplib.validate_url(url)
        self.assertIn("Invalid domain", str(cm.exception))

    def test_not_bandcamp_domain(self):
        url = "https://bandname.someothercamp.com"
        with self.assertRaises(ValueError) as cm:
            bandcamplib.validate_url(url)
        self.assertIn("Not a bandcamp URL", str(cm.exception))

    def test_not_cnd_domain(self):
        url = "https://t4.bc-not-bits.com/stream/"
        with self.assertRaises(ValueError) as cm:
            bandcamplib.validate_url(url)
        self.assertIn("Not a bandcamp URL", str(cm.exception))

    def test_fix_scheme_and_path(self):
        url = "http://bandname.bandcamp.com"
        new_url = bandcamplib.validate_url(url)
        self.assertTrue(new_url.startswith("https"))
        self.assertTrue(new_url.endswith("/music"))

    def test_accept_bandname_only(self):
        url = "justbandname"
        new_url = bandcamplib.validate_url(url)
        self.assertIn(bandcamplib.BANDCAMP_DOMAIN_SITE, new_url)
        self.assertTrue(new_url.startswith("https"))
        self.assertTrue(new_url.endswith("/music"))

    def test_valid(self):
        url = "https://bandname.bandcamp.com/music"
        r = bandcamplib.validate_url(url)
        self.assertEqual(url, r)
