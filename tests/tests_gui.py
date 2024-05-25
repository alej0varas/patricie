import unittest
from .context import bcp


bcp.log.DEBUG = True


class MainTests(unittest.TestCase):
    def test_main_with_artist(self):
        bcp.gui.main(
            skip_downloaded=not True,
            fullscreen=False,
        )
