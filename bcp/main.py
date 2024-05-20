import sys
import time

import arcade
import arcade.gui

from . import bandcamplib


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

        self.media_player = None
        self.mp3s_iterator = bandcamplib.get_mp3s_from_url(url)

    def on_click_play(self, *_):
        if not self.media_player:
            current_song = self.mp3s_iterator.__next__()
            self.my_music = arcade.load_sound(current_song, streaming=True)
            self.media_player = self.my_music.play()
            self.media_player.push_handlers(on_eos=self.handler_music_over)
            self.fade_in()
        else:
            self.media_player.play()

        self.pause_button.disabled = False
        self.play_button.disabled = True
        self.next_button.disabled = False

    def on_click_pause(self, event):
        if self.media_player.playing:
            self.media_player.pause()
            self.play_button.disabled = False
            self.pause_button.disabled = True

    def on_click_next(self, event):
        self.handler_music_over()

    def on_click_quit(self, event):
        arcade.exit()

    def handler_music_over(self):
        self.fade_out()
        self.media_player.pop_handlers()
        self.media_player = None
        self.on_click_play()

    def fade_in(self, duration=1.0):
        for volume in range(100):
            self.media_player.volume = volume / 100
            time.sleep(duration / 100)

    def fade_out(self, duration=1.0):
        for volume in range(100, 0, -1):
            self.media_player.volume = volume / 100
            time.sleep(duration / 100)

    def on_show_view(self):
        self.window.background_color = arcade.color.DARK_BLUE_GRAY
        self.ui.enable()

    def on_hide_view(self):
        self.ui.disable()

    def on_draw(self):
        self.clear()
        self.ui.draw()


def main(url):
    window = arcade.Window(800, 600, "UIExample", resizable=True)
    window.show_view(MyView(url))
    window.run()


if __name__ == "__main__":
    url = sys.argv[1]
    main(url)
