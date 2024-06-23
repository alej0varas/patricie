# fmt: off
import os
import time
from datetime import timedelta

import arcade

from . import __VERSION__, textures
from .log import get_loger
from .player import Player
from .utils import get_clipboad_content, threaded

_log = get_loger(__name__)


class MainView(arcade.View):
    def __init__(self, screen_width, screen_height, scale, skip_downloaded=False, url=None):
        super().__init__()
        # calculate elements' dimentions based on screen size
        width_url_label = screen_width // 20
        font_size_url_label = screen_height // 55
        width_url_input_text = screen_width // 1.75
        height_url_input_text = screen_height // 25
        font_size_url_input_text = screen_height // 55
        font_size_track_title = screen_height // 20
        font_size_track_album = screen_height // 25
        font_size_track_artist = screen_height // 23
        font_size_time = font_size_track_title

        #
        # GUI top level elements
        #
        self.ui = arcade.gui.UIManager()
        self.grid = arcade.gui.UIGridLayout(column_count=1, row_count=6, vertical_spacing=20)
        anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        anchor.add(anchor_x="center", anchor_y="top", child=self.grid)

        # TODO: another anchor for player anchored to bottom

        #
        # first row: ..., url input, ...
        #
        url_label = arcade.gui.UILabel("Band Link:", text_color=arcade.color.LIGHT_BLUE, font_size=font_size_url_label)
        bg_tex = arcade.gui.nine_patch.NinePatchTexture(left=5, right=5, top=5, bottom=5, texture=arcade.load_texture(":resources:gui_basic_assets/window/grey_panel.png"))
        self.url_input_text = arcade.gui.UIInputText(texture=bg_tex, font_size=font_size_url_input_text)
        # may be not the same issue but cursor doesn't blink if text
        # is not set. So we set something and then remove to make it
        # empty again see. seting focus at start don't make cursor
        # blink anyway :(
        # https://github.com/pythonarcade/arcade/issues/1059
        self.url_input_text.text = " "
        self.url_input_text.text = ""

        self.load_band_button = arcade.gui.widgets.buttons.UITextureButton(scale=scale, texture=textures._play_normal_texture, texture_hovered=textures._play_hover_texture, texture_pressed=textures._play_press_texture, texture_disabled=textures._play_disable_texture)
        self.load_band_button.on_click = self.on_click_load_band

        _grid = arcade.gui.UIGridLayout(column_count=3, row_count=1, horizontal_spacing=20)
        _grid.add(url_label, col_num=0, row_num=0)
        _grid.add(self.url_input_text.with_background(texture=bg_tex), col_num=1, row_num=0)
        _grid.add(self.load_band_button, col_num=2, row_num=0)

        self.grid.add(_grid, col_num=0, row_num=0)
        # self.grid.add(url_label, col_num=0, row_num=0, col_span=2)
        # self.grid.add(self.url_input_text.with_padding(all=5).with_background(texture=bg_tex), col_num=3, row_num=0, col_span=2)
        # self.grid.add(self.load_band_button, col_num=5, row_num=0)

        #
        # player buttons at the bottom
        #
        self.play_button = arcade.gui.widgets.buttons.UITextureButton(scale=scale, texture=textures._play_normal_texture, texture_hovered=textures._play_hover_texture, texture_pressed=textures._play_press_texture, texture_disabled=textures._play_disable_texture)
        self.play_button.on_click = self.on_click_play

        self.pause_button = arcade.gui.widgets.buttons.UITextureButton(scale=scale, texture=textures._pause_normal_texture, texture_hovered=textures._pause_hover_texture, texture_pressed=textures._pause_press_texture, texture_disabled=textures._pause_disable_texture)
        self.pause_button.on_click = self.on_click_pause

        self.next_button = arcade.gui.widgets.buttons.UITextureButton(scale=scale, texture=textures._next_normal_texture, texture_hovered=textures._next_hover_texture, texture_pressed=textures._next_press_texture, texture_disabled=textures._next_disable_texture)
        self.next_button.on_click = self.on_click_next
        self.next_button.disabled = True

        self.vol_down_button = arcade.gui.widgets.buttons.UITextureButton(scale=scale, texture=textures._vol_down_normal_texture, texture_hovered=textures._vol_down_hover_texture, texture_pressed=textures._vol_down_press_texture, texture_disabled=textures._vol_down_disable_texture)
        self.vol_down_button.on_click = self.on_click_vol_down

        self.vol_up_button = arcade.gui.widgets.buttons.UITextureButton(scale=scale, texture=textures._vol_up_normal_texture, texture_hovered=textures._vol_up_hover_texture, texture_pressed=textures._vol_up_press_texture, texture_disabled=textures._vol_up_disable_texture)
        self.vol_up_button.on_click = self.on_click_vol_up

        self.quit_button = arcade.gui.widgets.buttons.UITextureButton(scale=scale, texture=textures._quit_normal_texture, texture_hovered=textures._quit_hover_texture, texture_pressed=textures._quit_press_texture, texture_disabled=textures._quit_disable_texture)
        self.quit_button.on_click = self.on_click_quit

        _grid = arcade.gui.UIGridLayout(column_count=6, row_count=1, horizontal_spacing=20)

        _grid.add(self.play_button, col_num=0)
        _grid.add(self.pause_button, col_num=1)
        _grid.add(self.next_button, col_num=2)
        _grid.add(self.vol_down_button, col_num=3)
        _grid.add(self.vol_up_button, col_num=4)
        _grid.add(self.quit_button, col_num=5)
        self.grid.add(_grid, col_num=0, row_num=1)

        #
        # track info
        #
        self.text_track_title = arcade.gui.UILabel(" ", text_color=arcade.color.BLACK, font_size=font_size_track_title, align="center")
        self.text_track_album = arcade.gui.UILabel(" ", text_color=arcade.color.BLACK, font_size=font_size_track_album, align="center")
        self.text_track_artist = arcade.gui.UILabel(" ", text_color=arcade.color.BLACK, font_size=font_size_track_artist, align="center")
        self.text_time = arcade.gui.UILabel(" ", text_color=arcade.color.BLACK, font_size=font_size_time, align="center")

        _grid = arcade.gui.UIGridLayout(column_count=1, row_count=4, vertical_spacing=20)
        _grid.add(self.text_track_title, col_num=0, row_num=0)
        _grid.add(self.text_track_album, col_num=0, row_num=1)
        _grid.add(self.text_track_artist, col_num=0, row_num=2)
        _grid.add(self.text_time, col_num=0, row_num=3)
        self.grid.add(_grid, col_num=0, row_num=2)

        #
        # version/build text
        #
        text_version = arcade.gui.UILabel("Version: {} - Build: {}".format(__VERSION__, os.environ.get("COMMIT_SHA", "")))

        self.ui.add(arcade.gui.UIAnchorLayout()).add(anchor_x="left", anchor_y="bottom", child=text_version, align_x=10, align_y=10)

        #
        # setup
        #

        self.url_has_changed = False
        self._current_url = url
        self.url_input_text.text = url
        if self._current_url:
            self.url_has_changed = True

        self.player = Player(self.handler_music_over, skip_downloaded)
        self.keys_held = dict()
        self.focus_set = dict()
        self.current_track_info = None

    def on_click_load_band(self, *_):
        if self.url_has_changed:
            self.current_url = self.url_input_text.text
            self.url_has_changed = False
            self.band = self.player.load_band(self.current_url)
            for a in self.band["albums"]:
                print(a["title"])
            # self.albums = self.player.load_album(self.band["albums"][0]["page_url"])
            # self.tracks = self.album["tracks"]
            # self.player.play(self.tracks[0])

    def on_click_play(self, *_):
        if self.url_has_changed:
            self.current_url = self.url_input_text.text
            self.url_has_changed = False
            self.band = self.player.load_band(self.current_url)
            self.album = self.player.load_album(self.band["albums"][0]["page_url"])
            self.tracks = self.album["tracks"]
            self.player.play(self.tracks[0])

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
            # WHY[0]: remove self.grid so focus can be set again on it
            self.focus_set.pop(self.grid, None)
            match key:
                case arcade.key.V:
                    if modifiers & arcade.key.MOD_CTRL:
                        t = get_clipboad_content()
                        _log("From clipboard", t)
                        self.current_url = t
                case arcade.key.TAB:
                    # WHY[0]: just another widget not the text field
                    self._set_focus_on_widget(self.grid)
                case arcade.key.ENTER:
                    self.play_button.on_click()
                    # don't know how to avoid \n to be added so we remove them
                    self.url_input_text.text = self.url_input_text.text.replace("\n", "")
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
                pos_string = "{}.{:02d}".format(str(timedelta(seconds=int(_time)))[2:], milliseconds)
                _time = self.current_track_info["duration"]
                milliseconds = int((_time % 1) * 100)
                dur_string = "{}.{:02d}".format(str(timedelta(seconds=int(_time)))[2:], milliseconds)
                time_string = pos_string + " / " + dur_string
                self.text_time.text = time_string

        self.ui.draw()

    def _set_focus_on_widget(self, widget):
        # WHY[0]: this method exist because we haven't found another
        # way to set focus on a widget. we use it to set focus on
        # url_input_text when app start. to leave field when pressing
        # TAB we want to set focus on other widget, setting it to
        # self.grid works. when user click on url_input_text again we
        # remove self.grid so using tab will work again. it's
        # necessary because this function is called all the time by
        # on_update.
        if not self.focus_set.get(widget):
            self.focus_set[widget] = True
            x, y = widget.rect.center
            self.ui.dispatch_event("on_event", arcade.gui.UIMousePressEvent("", x, y, 0, 0))

    @property
    def current_url(self):
        return self._current_url

    @current_url.setter
    def current_url(self, new_value):
        self._current_url = new_value
        self.url_input_text.text = new_value
        self.url_has_changed = True
