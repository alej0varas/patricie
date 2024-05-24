import threading
import time
from datetime import timedelta

import arcade
import arcade.gui

from . import bandcamplib, textures
from .log import get_loger

_log = get_loger(__name__)

DEFAULT_FONT_SIZE = 20
DEFAULT_LINE_HEIGHT = 45
SCREEN_TITLE = "Bandcamp (url) Player"
VOLUME_DELTA = 0.1
VOLUME_DELTA_SMALL = 0.01


def threaded(func):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()

    return wrapper


class Player:
    def __init__(self, handler_music_over, skip_downloaded=False):
        self._handler_music_over = handler_music_over
        self.skip_downloaded = skip_downloaded

    def setup(self, url):
        self.track = None
        self.playing = False
        self.mp3s_iterator = bandcamplib.get_mp3s_from_url(url)
        self.media_player = None
        self.do_stop = False
        self.user_volume = 100

    @threaded
    def play(self):
        if self.do_stop:
            return
        if not self.media_player:
            try:
                self.track, downloaded = self.mp3s_iterator.__next__()
            except Exception:
                return
            if self.skip_downloaded and downloaded:
                _log("Skip song:", self.track["title"])
                self.play()
                return
            self.my_music = arcade.load_sound(self.track["path"], streaming=True)
            self.media_player = self.my_music.play()
            self.media_player.volume = 0
            self.fade_in()
            try:
                self.media_player.pop_handlers()
            except Exception:
                pass
            self.media_player.push_handlers(on_eos=self._handler_music_over)
            self.playing = True
        else:
            self.media_player.play()
            self.fade_in(0.5)
            self.playing = True

    @threaded
    def pause(self):
        if self.playing:
            self.fade_out(0.25)
            self.media_player.pause()
            self.playing = False

    @threaded
    def next(self):
        if not self.media_player:
            return
        self.fade_out(0.25)
        self.my_music.stop(self.media_player)
        self.media_player = None
        self.play()

    @threaded
    def fade_in(self, duration=1.0):
        volume_delta = 0.01
        if self.media_player:
            new_vol = self.media_player.volume + volume_delta
            for i in range(100):
                if new_vol > 1:
                    new_vol = 1
                if new_vol > self.user_volume:
                    new_vol = self.user_volume
                self.volume_set(new_vol, set_user_volume=False)
                new_vol += volume_delta
                time.sleep(duration / 100)

    @threaded
    def volume_up(self, value=VOLUME_DELTA):
        if self.media_player:
            new_vol = self.media_player.volume + value
            if new_vol > 1.0:
                new_vol = 1
            self.volume_set(new_vol)

    @threaded
    def volume_down(self, value=VOLUME_DELTA):
        if self.media_player:
            new_vol = self.media_player.volume - value
            if new_vol < 0.0:
                new_vol = 0.0
            self.volume_set(new_vol)

    def volume_set(self, value, set_user_volume=True):
        if self.media_player:
            self.media_player.volume = value
            if set_user_volume:
                self.user_volume = value

    def stop(self):
        self.do_stop = True
        if self.media_player:
            self.fade_out()
            self.my_music.stop(self.media_player)

    def fade_out(self, duration=1.0):
        volume_delta = 0.01
        if self.media_player:
            new_vol = self.media_player.volume - volume_delta
            for volume in range(100):
                if new_vol < 0.0:
                    new_vol = 0.0
                self.volume_set(new_vol, set_user_volume=False)
                new_vol -= volume_delta
                time.sleep(duration / 100)

    def get_volume(self):
        if self.media_player:
            return self.media_player.volume
        return 0.5

    def get_time(self):
        result = 0
        if self.media_player:
            result = self.media_player.time
        return result

    def get_duration(self):
        result = 0
        if self.track:
            result = self.track["duration"]
        return result

    def get_artist(self):
        if self.track:
            return "{artist}".format(**self.track)
        return ""

    def get_album(self):
        if self.track:
            return "{album}".format(**self.track)
        return ""

    def get_title(self):
        if self.track:
            return "{title}".format(**self.track)
        return ""


class MyView(arcade.View):
    def __init__(self, screen_width, screen_height, url, skip_downloaded=False):
        super().__init__()
        self.screen_width, self.screen_height = screen_width, screen_height
        self.ui = arcade.gui.UIManager()
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

        ui_anchor_layout = arcade.gui.widgets.layout.UIAnchorLayout()
        ui_anchor_layout.add(child=self.v_box, anchor_x="center_x", anchor_y="center_y")
        self.ui.add(ui_anchor_layout)

        self.player = Player(self.handler_music_over, skip_downloaded)
        self.player.setup(url)
        self.keys_held = dict()

    def on_click_play(self, *_):
        self.player.play()

    def play_update_gui(self):
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
            self.player.volume_up(VOLUME_DELTA_SMALL)
        if self.keys_held.get(arcade.key.DOWN):
            self.player.volume_down(VOLUME_DELTA_SMALL)

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


def main(url, fullscreen=True, skip_downloaded=False):
    if fullscreen:
        screen_width, screen_height = arcade.get_display_size()
    else:
        screen_width = 640
        screen_height = 480
    window = arcade.Window(
        screen_width, screen_height, SCREEN_TITLE, resizable=True, fullscreen=fullscreen
    )
    window.show_view(MyView(screen_width, screen_height, url, skip_downloaded))
    window.run()
