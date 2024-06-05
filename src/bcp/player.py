import time

import arcade
import arcade.gui

from . import bandcamplib
from .log import get_loger
from .utils import threaded

_log = get_loger(__name__)


class Player:
    VOLUME_DELTA = 0.1
    VOLUME_DELTA_SMALL = 0.01

    def __init__(self, handler_music_over, skip_downloaded=False):
        self._handler_music_over = handler_music_over
        self.skip_downloaded = skip_downloaded
        self.playing = False
        self.user_volume = 100

    # def setup(self):
    #     self.media_player = None
    #     self.do_stop = False

    # @threaded
    def load_band(self, url):
        self.band = bandcamplib.load_band(url)
        return self.band

    # @threaded
    def load_artist(self, url):
        self.artist = bandcamplib.load_url(url)
        return self.artist

    # def play_artist(self):
    #     pass

    # @threaded
    def load_album(self, url):
        full_url = self.band["url"] + url
        self.album = bandcamplib.load_album(full_url)
        return self.album

    # def play_album(self, album):
    #     pass

    # def load_track(self, track):
    #     pass

    @threaded
    def play(self, track):
        self.track = track
        self.my_music = arcade.load_sound(track["path"], streaming=True)
        self.media_player = self.my_music.play()
        self.media_player.volume = 0
        self.fade_in()
        # if self.skip_downloaded and downloaded:
        try:
            self.media_player.pop_handlers()
        except Exception:
            pass
        self.media_player.push_handlers(on_eos=self._handler_music_over)
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
        self.playing = False
        self.fade_out(0.25)
        self.my_music.stop(self.media_player)
        self.media_player = None
        self.play()

    @threaded
    def fade_in(self, duration=1.0):
        if self.media_player:
            new_vol = self.media_player.volume + Player.VOLUME_DELTA_SMALL
            for i in range(100):
                if new_vol > 1:
                    new_vol = 1
                if new_vol > self.user_volume:
                    new_vol = self.user_volume
                self.volume_set(new_vol, set_user_volume=False)
                new_vol += Player.VOLUME_DELTA_SMALL
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
        if self.playing:
            self.fade_out()
            self.my_music.stop(self.media_player)

    def fade_out(self, duration=1.0):
        if self.media_player:
            new_vol = self.media_player.volume - Player.VOLUME_DELTA_SMALL
            for volume in range(100):
                if new_vol < 0.0:
                    new_vol = 0.0
                self.volume_set(new_vol, set_user_volume=False)
                new_vol -= Player.VOLUME_DELTA_SMALL
                time.sleep(duration / 100)

    def get_volume(self):
        if self.playing and self.media_player:
            return self.media_player.volume
        return 0.5

    def get_position(self):
        result = 0
        if self.playing and self.media_player:
            result = self.media_player.time
        return result

    def get_duration(self):
        result = 0
        if self.playing:
            result = self.track["duration"]
        return result

    def get_artist(self):
        if self.playing:
            return "{name}".format(**self.band)
        return ""

    def get_album(self):
        if self.playing:
            return "{name}".format(**self.album)
        return ""

    def get_title(self):
        if self.playing:
            return "{title}".format(**self.track)
        return ""
