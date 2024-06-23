import arcade.gui

from . import __VERSION__
from .log import get_loger
from .views import MainView

_log = get_loger(__name__)

DEFAULT_FONT_SIZE = 20
DEFAULT_LINE_HEIGHT = 45
SCREEN_TITLE = f"Patricie Player {__VERSION__}"


def main(url=None, fullscreen=False, skip_downloaded=False):
    # assets scale is 1 for screen resolution 1920x1080 from wich we
    # take the smaller value.
    screen_width, screen_height = arcade.get_display_size()
    # reduce screen dimentions to 80% an then make the screen
    # dimensions a square the size of the smaller side
    screen_width = int(screen_width * 0.8)
    screen_height = int(screen_height * 0.8)
    if screen_height > screen_width:
        screen_height = screen_width
    else:
        screen_width = screen_height
    # calculate scale using user screen size
    scale = 1 / (1080 / screen_width)
    window = arcade.Window(
        screen_width,
        screen_height,
        f"Patricie Player {__VERSION__}",
        fullscreen=fullscreen,
        center_window=True,
    )
    window.show_view(
        MainView(screen_width, screen_height, scale, skip_downloaded, url=url)
    )
    window.run()
