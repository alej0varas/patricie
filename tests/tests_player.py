import unittest
from . import constants
from .context import player, log

log.DEBUG = True


class PlayerTests(unittest.TestCase):
    def test_load_artist(self):
        r = player.Player(lambda x: x).load_band(
            f"https://{constants.BC_BANDNAME}.bandcamp.com/"
        )
        print(r)
