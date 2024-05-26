from datetime import timedelta

import arcade

from . import textures, utils
from .log import get_loger
from .player import Player

_log = get_loger(__name__)

DEFAULT_FONT_SIZE = 20
DEFAULT_LINE_HEIGHT = 45
SCREEN_TITLE = "Bandcamp (url) Player"
VOLUME_DELTA = 0.1
VOLUME_DELTA_SMALL = 0.01


class MyView(arcade.View):
    def __init__(self, screen_width, screen_height, skip_downloaded=False):
        super().__init__()
        self.screen_width, self.screen_height = screen_width, screen_height

        self.box = arcade.gui.widgets.layout.UIBoxLayout(space_between=20)
        bg_tex = arcade.gui.nine_patch.NinePatchTexture(
            left=5,
            right=5,
            top=5,
            bottom=5,
            texture=arcade.load_texture(
                ":resources:gui_basic_assets/window/grey_panel.png"
            ),
        )
        self.url_input_text = arcade.gui.UIInputText(
            width=500, height=50, text="", texture=bg_tex
        )
        self.box.add(
            self.url_input_text.with_padding(all=15).with_background(texture=bg_tex)
        )

        self.v_box = arcade.gui.widgets.layout.UIBoxLayout(
            vertical=False, space_between=20
        )

        self.play_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._play_normal_texture,
            texture_hovered=textures._play_hover_texture,
            texture_pressed=textures._play_press_texture,
            texture_disabled=textures._play_disable_texture,
        )
        self.play_button.on_click = self.on_click_play
        self.v_box.add(self.play_button)

        self.pause_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._pause_normal_texture,
            texture_hovered=textures._pause_hover_texture,
            texture_pressed=textures._pause_press_texture,
            texture_disabled=textures._pause_disable_texture,
        )
        self.pause_button.on_click = self.on_click_pause
        self.v_box.add(self.pause_button)

        self.next_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._next_normal_texture,
            texture_hovered=textures._next_hover_texture,
            texture_pressed=textures._next_press_texture,
            texture_disabled=textures._next_disable_texture,
        )
        self.next_button.on_click = self.on_click_next
        self.next_button.disabled = True
        self.v_box.add(self.next_button)

        self.vol_down_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._vol_down_normal_texture,
            texture_hovered=textures._vol_down_hover_texture,
            texture_pressed=textures._vol_down_press_texture,
            texture_disabled=textures._vol_down_disable_texture,
        )
        self.vol_down_button.on_click = self.on_click_vol_down
        self.v_box.add(self.vol_down_button)

        self.vol_up_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._vol_up_normal_texture,
            texture_hovered=textures._vol_up_hover_texture,
            texture_pressed=textures._vol_up_press_texture,
            texture_disabled=textures._vol_up_disable_texture,
        )
        self.vol_up_button.on_click = self.on_click_vol_up
        self.v_box.add(self.vol_up_button)

        self.quit_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._quit_normal_texture,
            texture_hovered=textures._quit_hover_texture,
            texture_pressed=textures._quit_press_texture,
            texture_disabled=textures._quit_disable_texture,
        )
        self.quit_button.on_click = self.on_click_quit
        self.v_box.add(self.quit_button)

        self.ui = arcade.gui.UIManager()
        self.grid = arcade.gui.UIGridLayout(
            column_count=1, row_count=2, horizontal_spacing=20, vertical_spacing=20
        )

        self.grid.add(self.box, col_num=0, row_num=0)
        self.grid.add(self.v_box, col_num=0, row_num=1)
        self.anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        self.anchor.add(
            anchor_x="center_x",
            anchor_y="center_y",
            child=self.grid,
        )

        self.player = Player(self.handler_music_over, skip_downloaded)
        self.keys_held = dict()
        self._current_url = ""

    def on_click_play(self, *_):
        if self.current_url:
            self.player.setup(self.current_url)
        self.player.play()

    def play_update_gui(self):
        if not self.player:
            return
        if self.player.playing:
            self.play_button.disabled = True
            self.pause_button.disabled = False
        else:
            self.play_button.disabled = False
            self.pause_button.disabled = True
        if self.player.media_player:
            self.next_button.disabled = False
        else:
            self.next_button.disabled = True

        if self.player.get_volume() == 1.0:
            self.vol_up_button.disabled = True
        else:
            self.vol_up_button.disabled = False
        if self.player.get_volume() == 0.0:
            self.vol_down_button.disabled = True
        else:
            self.vol_down_button.disabled = False

    def on_click_pause(self, *_):
        self.player.pause()

    def on_click_next(self, *_):
        self.handler_music_over()

    def on_click_vol_down(self, *_):
        self.player.volume_down()

    def on_click_vol_up(self, *_):
        self.player.volume_up()

    def on_click_quit(self, *_):
        self.player.stop()
        arcade.exit()

    def handler_music_over(self):
        self.player.next()

    def on_key_press(self, key, modifiers):
        self.keys_held[key] = True

    def on_key_release(self, key, modifiers):
        if self.url_input_text._active:
            match key:
                case arcade.key.V:
                    if modifiers & arcade.key.MOD_CTRL:
                        t = utils.get_clipboad_content()
                        _log("From clipboard", t)
                        self.current_url = t
                case _:
                    self.current_url = self.url_input_text.text
            return arcade.pyglet.event.EVENT_HANDLED

        match key:
            case arcade.key.SPACE:
                if self.player.playing:
                    self.pause_button.on_click()
                else:
                    self.play_button.on_click()
            case arcade.key.N:
                self.next_button.on_click()
            case arcade.key.DOWN:
                self.vol_down_button.on_click()
                self.keys_held[arcade.key.DOWN] = False
            case arcade.key.UP:
                self.vol_up_button.on_click()
                self.keys_held[arcade.key.UP] = False
            case arcade.key.Q:
                self.quit_button.on_click()

    def on_show_view(self):
        self.window.background_color = arcade.color.DARK_BLUE_GRAY
        self.ui.enable()

    def on_hide_view(self):
        self.ui.disable()

    def on_update(self, time_delta):
        if self.keys_held.get(arcade.key.UP):
            self.player.volume_up(Player.VOLUME_DELTA_SMALL)
        if self.keys_held.get(arcade.key.DOWN):
            self.player.volume_down(Player.VOLUME_DELTA_SMALL)

    def on_draw(self):
        self.clear()
        self.play_update_gui()

        _string = self.player.get_artist()
        arcade.draw_text(
            _string,
            0,
            100 + DEFAULT_LINE_HEIGHT * 2,
            arcade.color.BLACK,
            DEFAULT_FONT_SIZE * 2,
            width=self.screen_width,
            align="center",
        )
        _string = self.player.get_album()
        arcade.draw_text(
            _string,
            0,
            100 + DEFAULT_LINE_HEIGHT,
            arcade.color.BLACK,
            DEFAULT_FONT_SIZE * 2,
            width=self.screen_width,
            align="center",
        )
        _string = self.player.get_title()
        arcade.draw_text(
            _string,
            0,
            100,
            arcade.color.BLACK,
            DEFAULT_FONT_SIZE * 2,
            width=self.screen_width,
            align="center",
        )

        _time = self.player.get_time()
        milliseconds = int((_time % 1) * 100)
        pos_string = "{}.{:02d}".format(
            str(timedelta(seconds=int(_time)))[2:], milliseconds
        )
        _time = self.player.get_duration()
        milliseconds = int((_time % 1) * 100)
        dur_string = "{}.{:02d}".format(
            str(timedelta(seconds=int(_time)))[2:], milliseconds
        )
        time_string = pos_string + " / " + dur_string
        arcade.draw_text(
            time_string,
            0,
            50,
            arcade.color.BLACK,
            DEFAULT_FONT_SIZE * 2,
            width=self.screen_width,
            align="center",
        )
        self.ui.draw()

    @property
    def current_url(self):
        _log("current_url getter")
        return self._current_url

    @current_url.setter
    def current_url(self, new_value):
        _log("current_url setter", new_value)
        self._current_url = new_value
        self.url_input_text.text = new_value


def main(fullscreen=True, skip_downloaded=False):
    if fullscreen:
        screen_width, screen_height = arcade.get_display_size()
    else:
        screen_width = 640
        screen_height = 480
    window = arcade.Window(
        screen_width, screen_height, SCREEN_TITLE, resizable=True, fullscreen=fullscreen
    )
    window.show_view(MyView(screen_width, screen_height, skip_downloaded))
    window.run()
