import os
import unittest

from . import constants


class MainTests(unittest.TestCase):
    def setUp(self):
        os.environ["DEBUG"] = "True"
        from .context import bandcamplib

        self.module = bandcamplib

    def test_get_band(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/music"
        print(self.module.get_band(url))

    def test_get_album(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/album/{constants.BC_ALBUMNAME}"
        print(self.module.get_album(url))

    def test_get_track(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/track/{constants.BC_TRACKNAME}"
        self.module.get_track(url)

    def test_get_tracks_urls(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/album/{constants.BC_ALBUMNAME}"
        html = self.module._fetch_url(url)
        print(self.module._get_tracks_urls(html))

    def test_get_albums_urls(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/music"
        html = self.module._fetch_url(url)
        print(self.module._get_albums_urls(html))

    def test_get_track_from_artist_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/"
        for mp3_info in self.module.get_mp3s_from_url(url):
            print(mp3_info)
            break

    def test_get_track_from_music_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/music"
        for mp3_info in self.module.get_mp3s_from_url(url):
            pass

    def test_get_mp3s_from_album_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/album/{constants.BC_ALBUMNAME}"
        for mp3_info in self.module.get_mp3s_from_url(url):
            pass

    def test_get_mp3s_from_track_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com/track/{constants.BC_TRACKNAME}"
        for mp3_info in self.module.get_mp3s_from_url(url):
            pass


class ValidateUrlTests(unittest.TestCase):
    def setUp(self):
        os.environ["DEBUG"] = "True"
        from .context import bandcamplib

        self.module = bandcamplib

    def test_empty_str(self):
        url = ""
        with self.assertRaises(ValueError) as cm:
            self.module.validate_url(url)
        self.assertIn("Invalid url", str(cm.exception))

    def test_no_band_subdomain(self):
        url = "https://bandcamp.com"
        with self.assertRaises(ValueError) as cm:
            self.module.validate_url(url)
        self.assertIn("Invalid domain", str(cm.exception))

    def test_not_bandcamp_domain(self):
        url = "https://bandname.someothercamp.com"
        with self.assertRaises(ValueError) as cm:
            self.module.validate_url(url)
        self.assertIn("Not a bandcamp URL", str(cm.exception))

    def test_not_cnd_domain(self):
        url = "https://t4.bc-not-bits.com/stream/"
        with self.assertRaises(ValueError) as cm:
            self.module.validate_url(url)
        self.assertIn("Not a bandcamp URL", str(cm.exception))

    def test_fix_scheme_and_path(self):
        url = "http://bandname.bandcamp.com"
        new_url = self.module.validate_url(url)
        self.assertTrue(new_url.startswith("https"))
        self.assertTrue(new_url.endswith("/music"))

    def test_accept_bandname_only(self):
        url = "justbandname"
        new_url = self.module.validate_url(url)
        self.assertIn(self.module.BANDCAMP_DOMAIN_SITE, new_url)
        self.assertTrue(new_url.startswith("https"))
        self.assertTrue(new_url.endswith("/music"))

    def test_valid(self):
        url = "https://bandname.bandcamp.com/music"
        r = self.module.validate_url(url)
        self.assertEqual(url, r)
