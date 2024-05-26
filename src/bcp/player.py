import threading
import time

import arcade
import arcade.gui

from . import bandcamplib
from .log import get_loger

_log = get_loger(__name__)


def threaded(func):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()

    return wrapper


class Player:
    VOLUME_DELTA = 0.1
    VOLUME_DELTA_SMALL = 0.01

    def __init__(self, handler_music_over, skip_downloaded=False):
        self._handler_music_over = handler_music_over
        self.skip_downloaded = skip_downloaded
        self.playing = False

    def setup(self, url):
        self.media_player = None
        self.track = None
        self.do_stop = False
        self.user_volume = 100
        self.mp3s_iterator = None
        self.mp3s_iterator = bandcamplib.get_mp3s_from_url(url)

    @threaded
    def play(self):
        if self.do_stop:
            return
        if not self.media_player:
            try:
                self.track, downloaded = self.mp3s_iterator.__next__()
            except StopIteration as e:
                _log("Finished iterating tracks because reason")
                _log(e)
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
        if self.playing:
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
        if self.playing:
            return self.media_player.volume
        return 0.5

    def get_time(self):
        result = 0
        if self.playing:
            result = self.media_player.time
        return result

    def get_duration(self):
        result = 0
        if self.playing:
            result = self.track["duration"]
        return result

    def get_artist(self):
        if self.playing:
            return "{artist}".format(**self.track)
        return ""

    def get_album(self):
        if self.playing:
            return "{album}".format(**self.track)
        return ""

    def get_title(self):
        if self.playing:
            return "{title}".format(**self.track)
        return ""
