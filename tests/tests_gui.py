import unittest

from .context import gui, log

log.DEBUG = True


class MainTests(unittest.TestCase):
    def test_main_with_artist(self):
        gui.main(
            skip_cached=True,
            fullscreen=False,
            url="https://<band>.bandcamp.com/",
        )
