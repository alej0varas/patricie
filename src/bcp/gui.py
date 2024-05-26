import time
from datetime import timedelta

import arcade

from . import textures
from .log import get_loger
from .player import Player
from .utils import get_clipboad_content, threaded

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

        # gui top level elements
        self.ui = arcade.gui.UIManager()
        self.grid = arcade.gui.UIGridLayout(
            column_count=1, row_count=2, horizontal_spacing=20, vertical_spacing=20
        )
        self.anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        self.anchor.add(
            anchor_x="center_x",
            anchor_y="center_y",
            child=self.grid,
        )

        # URL input field
        self.box_url = arcade.gui.widgets.layout.UIBoxLayout(space_between=20)
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
            width=500, height=50, texture=bg_tex
        )
        # may be not the same issue but cursor doesn't blink if text
        # is not set. So we set something and then remove to make it
        # empty again see. seting focus at start don't make cursor
        # blink anyway :(
        # https://github.com/pythonarcade/arcade/issues/1059
        self.url_input_text.text = " "
        self.url_input_text.text = ""
        self.box_url.add(
            self.url_input_text.with_padding(all=15).with_background(texture=bg_tex)
        )
        self.grid.add(self.box_url, col_num=0, row_num=0)

        # Buttons
        self.box_buttons = arcade.gui.widgets.layout.UIBoxLayout(
            vertical=False, space_between=20
        )

        self.play_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._play_normal_texture,
            texture_hovered=textures._play_hover_texture,
            texture_pressed=textures._play_press_texture,
            texture_disabled=textures._play_disable_texture,
        )
        self.play_button.on_click = self.on_click_play
        self.box_buttons.add(self.play_button)

        self.pause_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._pause_normal_texture,
            texture_hovered=textures._pause_hover_texture,
            texture_pressed=textures._pause_press_texture,
            texture_disabled=textures._pause_disable_texture,
        )
        self.pause_button.on_click = self.on_click_pause
        self.box_buttons.add(self.pause_button)

        self.next_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._next_normal_texture,
            texture_hovered=textures._next_hover_texture,
            texture_pressed=textures._next_press_texture,
            texture_disabled=textures._next_disable_texture,
        )
        self.next_button.on_click = self.on_click_next
        self.next_button.disabled = True
        self.box_buttons.add(self.next_button)

        self.vol_down_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._vol_down_normal_texture,
            texture_hovered=textures._vol_down_hover_texture,
            texture_pressed=textures._vol_down_press_texture,
            texture_disabled=textures._vol_down_disable_texture,
        )
        self.vol_down_button.on_click = self.on_click_vol_down
        self.box_buttons.add(self.vol_down_button)

        self.vol_up_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._vol_up_normal_texture,
            texture_hovered=textures._vol_up_hover_texture,
            texture_pressed=textures._vol_up_press_texture,
            texture_disabled=textures._vol_up_disable_texture,
        )
        self.vol_up_button.on_click = self.on_click_vol_up
        self.box_buttons.add(self.vol_up_button)

        self.quit_button = arcade.gui.widgets.buttons.UITextureButton(
            texture=textures._quit_normal_texture,
            texture_hovered=textures._quit_hover_texture,
            texture_pressed=textures._quit_press_texture,
            texture_disabled=textures._quit_disable_texture,
        )
        self.quit_button.on_click = self.on_click_quit
        self.box_buttons.add(self.quit_button)

        self.grid.add(self.box_buttons, col_num=0, row_num=1)

        # track info
        self.text_track_title = arcade.gui.UILabel(
            " ", width=500, text_color=arcade.color.BLACK, font_size=50, align="center"
        )
        self.text_track_album = arcade.gui.UILabel(
            " ", width=500, text_color=arcade.color.BLACK, font_size=30, align="center"
        )
        self.text_track_artist = arcade.gui.UILabel(
            " ", width=500, text_color=arcade.color.BLACK, font_size=20, align="center"
        )
        self.anchor_track_info = self.ui.add(arcade.gui.UIAnchorLayout())
        self.anchor_track_info.add(
            anchor_x="center",
            anchor_y="bottom",
            child=self.text_track_title,
            align_y=240,
        )
        self.anchor_track_info.add(
            anchor_x="center",
            anchor_y="bottom",
            child=self.text_track_album,
            align_y=200,
        )
        self.anchor_track_info.add(
            anchor_x="center",
            anchor_y="bottom",
            child=self.text_track_artist,
            align_y=180,
        )
        self.text_time = arcade.gui.UILabel(
            " ", width=500, text_color=arcade.color.BLACK, font_size=40, align="center"
        )
        self.anchor_track_info.add(
            anchor_x="center",
            anchor_y="bottom",
            child=self.text_time,
            align_y=50,
        )

        # version text
        self.anchor_version = self.ui.add(arcade.gui.UIAnchorLayout())
        self.text_version = arcade.gui.UILabel("Version: 0.1")
        self.anchor_version.add(
            anchor_x="left",
            anchor_y="bottom",
            child=self.text_version,
            align_x=10,
            align_y=10,
        )

        self.player = Player(self.handler_music_over, skip_downloaded)
        self.keys_held = dict()
        self._current_url = ""
        self.url_has_changed = False
        self.focus_set = dict()
        self.current_track_info = None

    def on_click_play(self, *_):
        if self.url_has_changed:
            self.current_url = self.url_input_text.text
            self.url_has_changed = False
            self.player.setup(self.current_url)
        if self.current_url:
            self.player.play()
            self.update_track_info()

    @threaded
    def update_track_info(self):
        while not self.player.playing:
            time.sleep(0.1)
        self.current_track_info = {
            "title": self.player.get_title(),
            "album": self.player.get_album(),
            "artist": self.player.get_artist(),
            "duration": self.player.get_duration(),
        }

    def play_update_gui(self):
        if not self.player:
            return
        if self.player.playing:
            self.play_button.disabled = True
            self.pause_button.disabled = False
        else:
            self.play_button.disabled = False
            self.pause_button.disabled = True
        if hasattr(self.player, "media_player"):
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
        self.update_track_info()

    def on_key_press(self, key, modifiers):
        self.keys_held[key] = True

    def on_key_release(self, key, modifiers):
        if self.url_input_text._active:
            # WHY[0]: remove self.box_buttons so focus can be set again on it
            self.focus_set.pop(self.box_buttons, None)
            match key:
                case arcade.key.V:
                    if modifiers & arcade.key.MOD_CTRL:
                        t = get_clipboad_content()
                        _log("From clipboard", t)
                        self.current_url = t
                case arcade.key.TAB:
                    # WHY[0]: just another widget not the text field
                    self._set_focus_on_widget(self.box_buttons)
                case arcade.key.ENTER:
                    self.play_button.on_click()
                    # don't know how to avoid \n to be added so we remove them
                    self.url_input_text.text = self.url_input_text.text.replace(
                        "\n", ""
                    )
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
        self._set_focus_on_widget(self.url_input_text)
        if self.keys_held.get(arcade.key.UP):
            self.player.volume_up(Player.VOLUME_DELTA_SMALL)
        if self.keys_held.get(arcade.key.DOWN):
            self.player.volume_down(Player.VOLUME_DELTA_SMALL)

    def on_draw(self):
        self.clear()
        self.play_update_gui()

        if self.current_track_info:
            self.text_track_title.text = self.current_track_info["title"]
            self.text_track_album.text = self.current_track_info["album"]
            self.text_track_artist.text = self.current_track_info["artist"]

            if self.player.playing:
                _time = self.player.get_position()
                milliseconds = int((_time % 1) * 100)
                pos_string = "{}.{:02d}".format(
                    str(timedelta(seconds=int(_time)))[2:], milliseconds
                )
                _time = self.current_track_info["duration"]
                milliseconds = int((_time % 1) * 100)
                dur_string = "{}.{:02d}".format(
                    str(timedelta(seconds=int(_time)))[2:], milliseconds
                )
                time_string = pos_string + " / " + dur_string
                self.text_time.text = time_string

        self.ui.draw()

    def _set_focus_on_widget(self, widget):
        # WHY[0]: this method exist because we haven't found another
        # way to set focus on a widget. we use it to set focus on
        # url_input_text when app start. to leave field when pressing
        # TAB we want to set focus on other widget, setting it to
        # self.box works. when user click on url_input_text again we
        # remove self.box so using tab will work again. it's necessary
        # because this function is called all the time by on_update.
        if not self.focus_set.get(widget):
            self.focus_set[widget] = True
            x, y = widget.rect.center
            self.ui.dispatch_event(
                "on_event", arcade.gui.UIMousePressEvent("", x, y, 0, 0)
            )

    @property
    def current_url(self):
        return self._current_url

    @current_url.setter
    def current_url(self, new_value):
        self._current_url = new_value
        self.url_input_text.text = new_value
        self.url_has_changed = True


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
