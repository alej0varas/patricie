import os
from datetime import timedelta

import arcade
import arcade.gui

from . import __VERSION__, textures
from .log import get_loger
from .player import Player
from .utils import get_clipboad_content

_log = get_loger(__name__)

DEFAULT_FONT_SIZE = 20
DEFAULT_LINE_HEIGHT = 45
SCREEN_TITLE = f"Patricie Player {__VERSION__}"


class MyView(arcade.View):
    def __init__(self, screen_width, screen_height, scale, skip_cached=False, url=""):
        super().__init__()
        self.angle = 0

        self.user_is_typing = True

        self.screen_width, self.screen_height = screen_width, screen_height
        # calculate elements' dimentions based on screen size
        width_url_label = screen_width * 0.10
        width_url_input_text = screen_width * 0.6
        height_url_input_text = screen_height * 0.08
        font_size_url_input_text = height_url_input_text * 0.5
        font_size_url_label = font_size_url_input_text * 1
        font_size_track_title = screen_height * 0.05
        font_size_track_album = font_size_track_title * 0.8
        font_size_track_band = font_size_track_title * 0.6
        font_size_time = screen_height * 0.05
        margin_left = screen_width * 0.03
        margin_top = -screen_width * 0.02

        # gui top level elements
        bg_tex = arcade.gui.nine_patch.NinePatchTexture(
            left=5,
            right=5,
            top=5,
            bottom=5,
            texture=arcade.load_texture(
                ":resources:gui_basic_assets/window/grey_panel.png"
            ),
        )

        self.ui = arcade.gui.UIManager()

        # url label, input text , load band button and loading animation
        self.first_grid = arcade.gui.UIGridLayout(
            column_count=4,
            row_count=1,
        )
        self.first_anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        self.first_anchor.add(
            anchor_x="left",
            anchor_y="top",
            align_x=margin_left,
            align_y=margin_top,
            child=self.first_grid,
        )
        self.url_label = arcade.gui.UILabel(
            "Band Link:",
            width=width_url_label,
            text_color=arcade.color.LIGHT_BLUE,
            font_size=font_size_url_label,
        )
        self.url_input_text = arcade.gui.UIInputText(
            width=width_url_input_text,
            height=height_url_input_text,
            texture=bg_tex,
            font_size=font_size_url_input_text,
            text_color=arcade.color.BLACK,
            caret_color=arcade.color.BLACK,
        )
        self.url_input_text.activate()
        self.url_input_text.text = url

        self.load_band_button = arcade.gui.widgets.buttons.UITextureButton(
            scale=scale,
            texture=textures._play_normal_texture,
            texture_hovered=textures._play_hover_texture,
            texture_pressed=textures._play_press_texture,
            texture_disabled=textures._play_disable_texture,
        )
        self.load_band_button.on_click = self.on_click_load_band

        self.loading_animation_image = arcade.load_image("assets/loading_note.png")
        self.loading_animation_texture = arcade.Texture(
            image=self.loading_animation_image
        )
        self.loading_animation = arcade.gui.UIImage(
            texture=self.loading_animation_texture,
            height=height_url_input_text,
            width=height_url_input_text,
        )
        self.first_grid.add(self.url_label, col_num=0, row_num=0)
        self.first_grid.add(
            self.url_input_text.with_padding(all=5).with_background(texture=bg_tex),
            col_num=1,
            row_num=0,
        )
        self.first_grid.add(self.load_band_button, col_num=3, row_num=0)
        self.first_grid.add(self.loading_animation, col_num=2, row_num=0)

        # buttons grid
        self.second_grid = arcade.gui.UIGridLayout(
            column_count=6,
            row_count=1,
            vertical_spacing=20,
        )
        self.second_anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        self.second_anchor.add(
            anchor_x="center",
            anchor_y="bottom",
            align_y=font_size_url_label * 2,
            child=self.second_grid,
        )
        self.play_button = arcade.gui.widgets.buttons.UITextureButton(
            scale=scale,
            texture=textures._play_normal_texture,
            texture_hovered=textures._play_hover_texture,
            texture_pressed=textures._play_press_texture,
            texture_disabled=textures._play_disable_texture,
        )
        self.play_button.on_click = self.on_click_play

        self.pause_button = arcade.gui.widgets.buttons.UITextureButton(
            scale=scale,
            texture=textures._pause_normal_texture,
            texture_hovered=textures._pause_hover_texture,
            texture_pressed=textures._pause_press_texture,
            texture_disabled=textures._pause_disable_texture,
        )
        self.pause_button.on_click = self.on_click_pause

        self.next_button = arcade.gui.widgets.buttons.UITextureButton(
            scale=scale,
            texture=textures._next_normal_texture,
            texture_hovered=textures._next_hover_texture,
            texture_pressed=textures._next_press_texture,
            texture_disabled=textures._next_disable_texture,
        )
        self.next_button.on_click = self.on_click_next
        self.next_button.disabled = True

        self.vol_down_button = arcade.gui.widgets.buttons.UITextureButton(
            scale=scale,
            texture=textures._vol_down_normal_texture,
            texture_hovered=textures._vol_down_hover_texture,
            texture_pressed=textures._vol_down_press_texture,
            texture_disabled=textures._vol_down_disable_texture,
        )
        self.vol_down_button.on_click = self.on_click_vol_down

        self.vol_up_button = arcade.gui.widgets.buttons.UITextureButton(
            scale=scale,
            texture=textures._vol_up_normal_texture,
            texture_hovered=textures._vol_up_hover_texture,
            texture_pressed=textures._vol_up_press_texture,
            texture_disabled=textures._vol_up_disable_texture,
        )
        self.vol_up_button.on_click = self.on_click_vol_up

        self.quit_button = arcade.gui.widgets.buttons.UITextureButton(
            scale=scale,
            texture=textures._quit_normal_texture,
            texture_hovered=textures._quit_hover_texture,
            texture_pressed=textures._quit_press_texture,
            texture_disabled=textures._quit_disable_texture,
        )
        self.quit_button.on_click = self.on_click_quit

        self.second_grid.add(self.play_button, col_num=0, row_num=0)
        self.second_grid.add(self.pause_button, col_num=1, row_num=0)
        self.second_grid.add(self.next_button, col_num=2, row_num=0)
        self.second_grid.add(self.vol_down_button, col_num=3, row_num=0)
        self.second_grid.add(self.vol_up_button, col_num=4, row_num=0)
        self.second_grid.add(self.quit_button, col_num=5, row_num=0)

        # track info grid
        self.third_grid = arcade.gui.UIGridLayout(
            column_count=1,
            row_count=3,
            align_horizontal="left",
            vertical_spacing=20,
        )
        self.third_anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        self.third_anchor.add(
            anchor_x="left",
            anchor_y="top",
            align_x=margin_left,
            align_y=-font_size_url_label * 5,
            child=self.third_grid,
        )
        self.text_track_title = arcade.gui.UILabel(
            " ",
            text_color=arcade.color.BLACK,
            font_size=font_size_track_title,
        )
        self.text_track_album = arcade.gui.UILabel(
            " ",
            text_color=arcade.color.BLACK,
            font_size=font_size_track_album,
        )
        self.text_track_band = arcade.gui.UILabel(
            " ",
            text_color=arcade.color.BLACK,
            font_size=font_size_track_band,
        )
        self.third_grid.add(self.text_track_title, col_num=0, row_num=0)
        self.third_grid.add(
            self.text_track_album,
            col_num=0,
            row_num=1,
        )
        self.third_grid.add(
            self.text_track_band,
            col_num=0,
            row_num=2,
        )

        # track duration
        self.fourth_grid = arcade.gui.UIGridLayout(
            column_count=1,
            row_count=4,
            align_horizontal="left",
            vertical_spacing=20,
        )
        self.fourth_anchor = self.ui.add(arcade.gui.UIAnchorLayout())
        self.fourth_anchor.add(
            anchor_x="center",
            anchor_y="bottom",
            align_y=font_size_url_label * 5.5,
            child=self.fourth_grid,
        )

        self.text_time = arcade.gui.UILabel(
            " ",
            text_color=arcade.color.BLACK,
            font_size=font_size_time,
        )

        self.fourth_grid.add(
            self.text_time,
            col_num=0,
            row_num=1,
        )

        # useless details like albums count, tracks count, ...
        self.useless_details = arcade.gui.UILabel()

        self.ui.add(arcade.gui.UIAnchorLayout()).add(
            anchor_x="right",
            anchor_y="bottom",
            child=self.useless_details,
            align_x=-200,
            align_y=10,
        )

        # version text
        text_version = arcade.gui.UILabel(
            "Version: {} - Build: {}".format(
                __VERSION__, os.environ.get("COMMIT_SHA", "")
            )
        )

        self.ui.add(arcade.gui.UIAnchorLayout()).add(
            anchor_x="left",
            anchor_y="bottom",
            child=text_version,
            align_x=10,
            align_y=10,
        )

        self.player = Player(self.on_click_next, skip_cached)
        self.keys_held = dict()

    def on_click_load_band(self, *_):
        if not self.url_input_text.text:
            return
        self.player.stop()
        self.player.setup(self.url_input_text.text)
        self.user_is_typing = False

    def on_click_play(self, *_):
        if not self.url_input_text.text:
            return
        if self.player.is_setup:
            self.player.play()

    def on_click_next(self, *_):
        self.player.next()

    def on_click_next_album(self, *_):
        self.player.next_album()

    def play_update_gui(self):
        # update buttons `disabled` attribute
        # play
        if self.player.ready_to_play:
            if self.player.playing:
                self.play_button.disabled = True
            else:
                self.play_button.disabled = False
        else:
            self.play_button.disabled = True
        # pause
        if self.player.ready_to_play:
            if self.player.playing:
                self.pause_button.disabled = False
            else:
                self.pause_button.disabled = True
        else:
            self.pause_button.disabled = True
        # next
        if self.player.ready_to_play:
            self.next_button.disabled = False
        else:
            self.next_button.disabled = True

        # volume up
        if self.player.volume_max:
            self.vol_up_button.disabled = True
        else:
            self.vol_up_button.disabled = False

        # volume down
        if self.player.volume_min:
            self.vol_down_button.disabled = True
        else:
            self.vol_down_button.disabled = False

    def on_click_pause(self, *_):
        self.player.pause()

    def on_click_vol_down(self, *_):
        self.player.volume_down()

    def on_click_vol_up(self, *_):
        self.player.volume_up()

    def on_click_quit(self, *_):
        self.player.quit()
        arcade.exit()

    def on_key_press(self, key, modifiers):
        self.keys_held[key] = True

    def on_key_release(self, key, modifiers):
        if self.url_input_text._active:
            self.user_is_typing = True
            new_url = ""
            action = None
            match key:
                case arcade.key.V:
                    if modifiers & arcade.key.MOD_CTRL:
                        new_url = get_clipboad_content()
                        _log("URL from clipboard: ", new_url)
                case arcade.key.ENTER:
                    action = self.load_band_button.on_click
                case arcade.key.TAB:
                    self.url_input_text.deactivate()
                case _:
                    if not modifiers & arcade.key.MOD_CTRL:
                        _log("URL from input: ", self.url_input_text.text)
                        new_url = self.url_input_text.text
            if not new_url:
                new_url = self.url_input_text.text
            self.url_input_text.text = new_url.strip()
            if action:
                action()
            return arcade.pyglet.event.EVENT_HANDLED

        match key:
            case arcade.key.SPACE:
                if self.player.playing:
                    self.pause_button.on_click()
                else:
                    self.play_button.on_click()
            case arcade.key.N:
                self.next_button.on_click()
            case arcade.key.S:
                # TODO: bind to button.on_click
                self.on_click_next_album()
            case arcade.key.DOWN:
                self.vol_down_button.on_click()
                self.keys_held[arcade.key.DOWN] = False
            case arcade.key.UP:
                self.vol_up_button.on_click()
                self.keys_held[arcade.key.UP] = False
            case arcade.key.TAB:
                self.url_input_text.activate()
            case arcade.key.Q:
                self.quit_button.on_click()

        if self.keys_held.get(arcade.key.UP):
            self.player.volume_up(Player.VOLUME_DELTA_SMALL)
        if self.keys_held.get(arcade.key.DOWN):
            self.player.volume_down(Player.VOLUME_DELTA_SMALL)

    def on_show_view(self):
        self.window.background_color = arcade.color.DARK_BLUE_GRAY
        self.ui.enable()

    def on_hide_view(self):
        self.ui.disable()

    def on_update(self, dt):
        self.play_update_gui()

    def on_draw(self):
        self.clear()

        if not self.user_is_typing and self.player.is_setup:
            self.url_input_text.text = self.player.band.url

        self.useless_details.text = " |".join(
            (
                self.player.statistics(),
                self.player.info()["status"],
                self.player.info()["error"],
            )
        )

        if self.player.working:
            self.loading_animation.visible = True
            self.angle -= 1
            self.loading_animation_texture = arcade.Texture(
                image=self.loading_animation_image.rotate(self.angle)
            )
            self.loading_animation.texture = self.loading_animation_texture
            self.loading_animation.trigger_full_render()
        else:
            self.loading_animation.visible = False

        self.text_track_title.text = self.player.info()["title"]
        self.text_track_album.text = self.player.info()["album"]
        self.text_track_band.text = self.player.info()["band"]

        _time = self.player.info()["position"]
        template = "{}"
        pos_string = template.format(str(timedelta(seconds=int(_time)))[2:])
        _time = self.player.info()["duration"]
        dur_string = template.format(str(timedelta(seconds=int(_time)))[2:])
        time_string = pos_string + " / " + dur_string
        self.text_time.text = time_string

        self.ui.draw()


def main(url="", fullscreen=False, skip_cached=False):
    screen_width, screen_height = arcade.get_display_size()
    screen_width = int(screen_width * 0.8)
    screen_height = int(screen_height * 0.8)
    # assets scale is 1 for screen resolution 1920x1080
    scale = 1 / (1080 / screen_width)
    window = arcade.Window(
        screen_width,
        screen_height,
        f"Patricie Player {__VERSION__}",
        fullscreen=fullscreen,
        center_window=True,
    )
    window.show_view(MyView(screen_width, screen_height, scale, skip_cached, url))
    window.run()
