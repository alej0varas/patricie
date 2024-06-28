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
    # fmt: off
    def __init__(self, screen_width, screen_height, scale, skip_downloaded=False, url=None):
        super().__init__()
        # Calculate elements' dimentions based on screen size.
        font_size_url_label = screen_height // 55
        font_size_url_input_text = screen_height // 55
        font_size_track_title = screen_height // 20
        font_size_track_album = screen_height // 25
        font_size_track_artist = screen_height // 23
        font_size_time = font_size_track_title

        self.ui = arcade.gui.UIManager()

        # GUI layout
        #
        # | band link and load button                  |
        # |--------------------------------------------|
        # | band info                                  |
        # |-------------+------------------------------|
        # | albuml list | tracks list                  |
        # |---------------------------+----------------|
        # | album cover / track info  | player buttons |
        #
        # Each row uses one anchor. Those that contains more than one
        # element will use a grid with x columns and 1 row. Why? It's
        # easier for me to align and set sizes. All elements have
        # fixed dimensions and use placeholders when empty. Track and
        # album lists have a fixed number of elements that will be
        # populated on load and scroll.

        #
        # First anchor
        #
        # | label | text field | button |
        #
        url_label = arcade.gui.UILabel("Band Link:", text_color=arcade.color.LIGHT_BLUE, font_size=font_size_url_label)
        bg_tex = arcade.gui.nine_patch.NinePatchTexture(left=5, right=5, top=5, bottom=5, texture=arcade.load_texture(":resources:gui_basic_assets/window/grey_panel.png"))
        self.url_input_text = arcade.gui.UIInputText(texture=bg_tex, font_size=font_size_url_input_text)
        # May be not the same issue but cursor doesn't blink if text is not set. Adding text and then removing text from input makes cursor blink. https://github.com/pythonarcade/arcade/issues/1059
        self.url_input_text.text = " "
        self.url_input_text.text = ""
        self.load_band_button = arcade.gui.widgets.buttons.UITextureButton(scale=scale, texture=textures._play_normal_texture, texture_hovered=textures._play_hover_texture, texture_pressed=textures._play_press_texture, texture_disabled=textures._play_disable_texture)
        self.load_band_button.on_click = self.on_click_load_band

        self.first_grid = arcade.gui.UIGridLayout(column_count=3, row_count=1, horizontal_spacing=20, vertical_spacing=20)
        self.first_grid.add(col_num=0, row_num=0, child=url_label)
        self.first_grid.add(col_num=1, row_num=0, child=self.url_input_text.with_background(texture=bg_tex))
        self.first_grid.add(col_num=2, row_num=0, child=self.load_band_button)
        first_anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        first_anchor.add(anchor_x="center", anchor_y="top", child=self.first_grid)

        #
        # Second anchor. Band info.
        #
        # | image | label |
        self.band_image_texture = arcade.texture.load_texture('/home/alej0/tmp/patricie/band_image_1234.jpg')
        self.band_image = arcade.gui.UIImage(texture=self.band_image_texture)
        self.band_name = arcade.gui.UILabel("<band name>", text_color=arcade.color.BLACK, font_size=20)

        self.second_grid = arcade.gui.UIGridLayout(column_count=3, row_count=1, horizontal_spacing=20, vertical_spacing=20)
        self.second_grid.add(col_num=0, row_num=0, child=self.band_image)
        self.second_grid.add(col_num=1, row_num=0, child=self.band_name)
        second_anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        second_anchor.add(anchor_x="center", anchor_y="top", align_y=-100, child=self.second_grid)

        #
        # Third anchor. Album list and track list.
        #
        # | album 1 | track 1 |
        # | ...     | ...     |
        _button_height = 30
        self.third_grid = arcade.gui.UIGridLayout(column_count=2, row_count=1, horizontal_spacing=1, vertical_spacing=1)

        def _callback_album(event):
            print(self.albums.get(event.action))
        self.albums_row = arcade.gui.constructs.UIButtonRow(vertical=True, callback=_callback_album, space_between=1)
        self.albums = dict([(f"album {i}", i) for i in range(10)])
        for k, v in self.albums.items():
            self.albums_row.add_button(k, height=_button_height)
        self.third_grid.add(col_num=0, row_num=0, child=self.albums_row)

        def _callback_track(event):
            print(self.tracks.get(event.action))
        self.tracks_row = arcade.gui.constructs.UIButtonRow(vertical=True, callback=_callback_track, space_between=1)
        self.tracks = dict([(f"track {i}", i) for i in range(10)])
        for k, v in self.tracks.items():
            self.tracks_row.add_button(k, height=_button_height)
        self.third_grid.add(col_num=1, row_num=0, child=self.tracks_row)

        third_anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        third_anchor.add(anchor_x="center", anchor_y="top", align_y=-250, child=self.third_grid)

        # Fourth anchor. Album info. Track info.
        #
        self.text_track_title = arcade.gui.UILabel(" ", text_color=arcade.color.BLACK, font_size=font_size_track_title, align="center")
        self.text_track_album = arcade.gui.UILabel(" ", text_color=arcade.color.BLACK, font_size=font_size_track_album, align="center")
        self.text_track_artist = arcade.gui.UILabel(" ", text_color=arcade.color.BLACK, font_size=font_size_track_artist, align="center")
        self.text_time = arcade.gui.UILabel(" ",text_color=arcade.color.BLACK,font_size=font_size_time,align="center")

        self.track_info_grid = arcade.gui.UIGridLayout(column_count=1,row_count=4,horizontal_spacing=20,vertical_spacing=20)
        self.track_info_grid.add(col_num=0, row_num=0, child=self.text_track_title)
        self.track_info_grid.add(col_num=0, row_num=1, child=self.text_track_album)
        self.track_info_grid.add(col_num=0, row_num=2, child=self.text_track_artist)
        self.track_info_grid.add(col_num=0, row_num=3, child=self.text_time)

        track_info_anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        track_info_anchor.add(anchor_x="center", anchor_y="center", child=self.track_info_grid)

        #
        # GUI player buttons at the bottom
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

        self.player_grid = arcade.gui.UIGridLayout(column_count=6, row_count=1, horizontal_spacing=20, vertical_spacing=20)
        self.player_grid.add(col_num=0, row_num=0, child=self.play_button)
        self.player_grid.add(col_num=1, row_num=0, child=self.pause_button)
        self.player_grid.add(col_num=2, row_num=0, child=self.next_button)
        self.player_grid.add(col_num=3, row_num=0, child=self.vol_down_button)
        self.player_grid.add(col_num=4, row_num=0, child=self.vol_up_button)
        self.player_grid.add(col_num=5, row_num=0, child=self.quit_button)

        player_anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        player_anchor.add(anchor_x="center", anchor_y="bottom", child=self.player_grid)

        #
        # Version/build text
        #
        text_version = arcade.gui.UILabel("Version: {} - Build: {}".format(__VERSION__, os.environ.get("COMMIT_SHA", "")))

        self.ui.add(arcade.gui.UIAnchorLayout()).add(anchor_x="left", anchor_y="bottom", child=text_version, align_x=10, align_y=10)

        #
        # Setup
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
        # fmt: on

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
            self.focus_set.pop(self.url_grid, None)
            match key:
                case arcade.key.V:
                    if modifiers & arcade.key.MOD_CTRL:
                        t = get_clipboad_content()
                        _log("From clipboard", t)
                        self.current_url = t
                case arcade.key.TAB:
                    self._set_focus_on_widget(self.url_grid)
                case arcade.key.ENTER:
                    self.play_button.on_click()
                    # I don't know how to avoid "\n" to be added to
                    # the input text so it's removed.
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
        # This method exist because I haven't found another way to set
        # focus on a widget. It's used to set focus on
        # `url_input_text` when app starts. Setting focus on other
        # widget allows to "leave" the field when pressing
        # TAB. Setting the focus on self.grid works. When the user
        # clicks on `url_input_text` again self.grid is removed to
        # allow TAB to work again.
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
