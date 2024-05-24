import unittest

from . import constants
from .context import bcp

bcp.log.DEBUG = True


class MainTests(unittest.TestCase):
    def test_main_with_artist(self):
        bcp.player.main(
            f"https://{constants.BC_BANDNAME}.bandcamp.com/",
            skip_downloaded=not True,
            fullscreen=False,
        )

    def test_main_with_album(self):
        bcp.player.main(
            f"https://{constants.BC_BANDNAME}.bandcamp.com/album/{constants.BC_ALBUMNAME}/"
        )
