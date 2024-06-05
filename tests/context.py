import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from bcp import bandcamplib, gui, player, log  # noqa: F401, E402
