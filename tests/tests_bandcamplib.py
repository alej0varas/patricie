from unittest.mock import patch
import unittest

from . import constants
from .context import bandcamplib

from . import data

bandcamplib.DEBUG = True
bandcamplib.THROTTLE_TIME = 1


class MainTests(unittest.TestCase):
    @patch("bcp.bandcamplib.requests.get")
    def test_load_band_url(self, rg):
        rg.return_value.content = data.band_page_html
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com"
        er = bandcamplib.fetch_band_info(url)
        r = bandcamplib.load_url(url)
        self.assertDictEqual(er, r)

    def test_validate_band_url(self):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com"
        er = url
        r = bandcamplib.validate_url(url)
        self.assertEqual(er, r)

    @patch("bcp.bandcamplib.requests.get")
    def test_fetch_band_info(self, rg):
        url = f"https://{constants.BC_BANDNAME}.bandcamp.com"
        rg.return_value.content = data.band_page_html
        er = bandcamplib.extract_band_info(data.band_page_html)
        r = bandcamplib.fetch_band_info(url)
        self.assertDictEqual(er, r)
        rg.assert_called_once_with(url)

    def test_extract_band_info(self):
        er = {
            "band": {
                "name": "Band Name",
                "url": f"https://{constants.BC_BANDNAME}.bandcamp.com",
                "url_discography": f"https://{constants.BC_BANDNAME}.bandcamp.com/music",
            },
            "albums": bandcamplib.get_albums_info(data.band_page_html),
        }
        r = bandcamplib.extract_band_info(data.band_page_html)
        self.maxDiff=None
        self.assertDictEqual(er, r)

    def test_get_albums_info_using_data(self):
        er = [
            {
                "artist": "Artist One",
                "band_id": 2111,
                "id": 3111,
                "page_url": "/album/album-1",
                "title": "Album Uno",
            },
            {
                "artist": "Artist Dos",
                "band_id": 2222,
                "id": 3222,
                "page_url": "/album/album-2",
                "title": "Album Dos",
            },
        ]
        r = bandcamplib.get_albums_info(data.band_page_html)
        self.assertListEqual(er, r)

    def test_get_albums_info_using_ol(self):
        er = [
            {
                "artist": "Artist Tres",
                "band_id": 4666,
                "id": 6111,
                "page_url": "/album/album-3",
                "title": "Album Tres",
            },
            {
                "artist": "Artist Cuatro",
                "band_id": 5222,
                "id": 6222,
                "page_url": "/album/album-4",
                "title": "Album Cuatro",
            },
        ]
        r = bandcamplib.get_albums_info(data.band_page_ol)
        self.assertListEqual(er, r)
