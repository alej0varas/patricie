import threading
import sys
import time
from datetime import timedelta

import arcade
import arcade.gui

from . import bandcamplib

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Bandcamp(url) Player"
DEFAULT_LINE_HEIGHT = 45
DEFAULT_FONT_SIZE = 20


def threaded(func):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()

    return wrapper


class Player:
    def __init__(self, handler_music_over):
        self.media_player = None
        self._handler_music_over = handler_music_over

    def setup(self, url):
        self.mp3s_iterator = bandcamplib.get_mp3s_from_url(url)

    @threaded  # or not
    def play(self):
        if not self.media_player:
            song_info = self.mp3s_iterator.__next__()
            self.my_music = arcade.load_sound(song_info["path"], streaming=True)
            self.media_player = self.my_music.play()
            self.fade_in()
            try:
                self.media_player.pop_handlers()
            except Exception:
                pass
            self.media_player.push_handlers(on_eos=self._handler_music_over)
            to_fade_out = song_info["duration"] - self.media_player.time - 1
            arcade.unschedule(self.fade_out)
            arcade.schedule_once(self.fade_out, to_fade_out)
        else:
            self.media_player.play()
            self.fade_in(0.5)

    @threaded
    def pause(self):
        if self.media_player.playing:
            self.fade_out(0.25)
            self.media_player.pause()

    @threaded
    def next(self):
        self.pause()
        while self.media_player.playing:
            time.sleep(0.1)
        self.media_player = None
        self.play()

    @threaded
    def fade_in(self, duration=1.0):
        for volume in range(100):
            self.media_player.volume = volume / 100
            time.sleep(duration / 100)

    def fade_out(self, duration=1.0):
        for volume in range(100, 0, -1):
            self.media_player.volume = volume / 100
            time.sleep(duration / 100)

    def get_time(self):
        time = 0
        if self.media_player:
            time = self.media_player.time
        return time


class MyView(arcade.View):
    def __init__(self, url):
        super().__init__()

        self.ui = arcade.gui.UIManager()
        self.v_box = arcade.gui.widgets.layout.UIBoxLayout(space_between=20)

        self.play_button = arcade.gui.widgets.buttons.UIFlatButton(
            text="Play", width=200
        )
        self.play_button.on_click = self.on_click_play
        self.v_box.add(self.play_button)
        self.pause_button = arcade.gui.widgets.buttons.UIFlatButton(
            text="Pause", width=200
        )
        self.pause_button.on_click = self.on_click_pause
        self.pause_button.disabled = True
        self.v_box.add(self.pause_button)
        self.next_button = arcade.gui.widgets.buttons.UIFlatButton(
            text="Next", width=200
        )
        self.next_button.on_click = self.on_click_next
        self.next_button.disabled = True
        self.v_box.add(self.next_button)
        quit_button = arcade.gui.widgets.buttons.UIFlatButton(text="Quit", width=200)
        quit_button.on_click = self.on_click_quit
        self.v_box.add(quit_button)

        ui_anchor_layout = arcade.gui.widgets.layout.UIAnchorLayout()
        ui_anchor_layout.add(child=self.v_box, anchor_x="center_x", anchor_y="center_y")
        self.ui.add(ui_anchor_layout)

        self.player = Player(self.handler_music_over)
        self.player.setup(url)

    def on_click_play(self, *_):
        self.player.play()
        self.play_update_gui()

    def play_update_gui(self):
        self.pause_button.disabled = False
        self.play_button.disabled = True
        self.next_button.disabled = False

    def on_click_pause(self, *_):
        self.player.pause()
        self.pause_update_gui()

    def pause_update_gui(self):
        self.play_button.disabled = False
        self.pause_button.disabled = True

    def on_click_next(self, event):
        self.handler_music_over()

    def on_click_quit(self, event):
        arcade.exit()

    def handler_music_over(self):
        self.player.next()
        self.play_update_gui()
        self.pause_update_gui()

    def on_show_view(self):
        self.window.background_color = arcade.color.DARK_BLUE_GRAY
        self.ui.enable()

    def on_hide_view(self):
        self.ui.disable()

    def on_draw(self):
        self.clear()
        _time = self.player.get_time()
        milliseconds = int((_time % 1) * 100)
        time_string = "{}.{:02d}".format(
            str(timedelta(seconds=int(_time)))[2:], milliseconds
        )
        arcade.draw_text(
            time_string,
            0,
            50,
            arcade.color.BLACK,
            DEFAULT_FONT_SIZE * 2,
            width=SCREEN_WIDTH,
            align="center",
        )
        self.ui.draw()


def main(url):
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
    window.show_view(MyView(url))
    window.run()


if __name__ == "__main__":
    url = sys.argv[1]
    main(url)
