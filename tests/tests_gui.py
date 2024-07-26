import unittest
from .context import log, gui


log.DEBUG = True


class MainTests(unittest.TestCase):
    def test_main_with_artist(self):
        gui.main(
            skip_downloaded=not True,
            fullscreen=False,
        )
