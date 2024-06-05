import unittest
from .context import gui, log


log.DEBUG = True


class MainTests(unittest.TestCase):
    def test_main_with_artist(self):
        gui.main(
            url="https://queenofsaba.bandcamp.com/music",
            skip_downloaded=not True,
            fullscreen=False,
        )
