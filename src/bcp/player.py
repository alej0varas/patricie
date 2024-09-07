import time

import arcade
import arcade.gui

from . import bandcamplib
from .log import get_loger

_log = get_loger(__name__)


class Player:
    VOLUME_DELTA = 0.1
    VOLUME_DELTA_SMALL = 0.01

    def __init__(self, handler_music_over, skip_cached=False):
        self._handler_music_over = handler_music_over
        self.skip_cached = skip_cached
        self.playing = False
        self.is_setup = False
        self.current_sound = None
        self.media_player = None
        self.band = None
        self.album_index = -1
        self.album = None
        self.track_index = -1
        self.track = None
        self.user_volume = 100

    def setup(self, url):
        self.band = bandcamplib.get_band(url)
        self.is_setup = True

    def play(self, url=None):
        if not self.is_setup and url is not None:
            self.setup(url)
        while not self.media_player:
            self.get_next_track()
            if self.track and self.skip_cached and self.track["cached"]:
                _log("Skipping track", self.track["title"])
                continue
            self.get_media_player()
        self.media_player.play()
        self.fade_in(0.5)
        self.playing = True

    def get_next_track(self):
        new_album = False
        self.track_index += 1
        if not self.album:
            self.album = bandcamplib.get_album(
                self.band["albums_urls"][self.album_index]
            )
        try:
            self.album["tracks"][self.track_index]
        except IndexError:
            self.album_index += 1
            self.track_index = 0
            new_album = True
        if new_album:
            try:
                self.band["albums_urls"][self.album_index]
            except IndexError:
                raise Exception("EOD: End Of Discography :L")
            else:
                _log("Next album:", self.band["albums_urls"][self.album_index])
                self.album = bandcamplib.get_album(
                    self.band["albums_urls"][self.album_index]
                )
        # there are albums without tracks :/
        if self.album["tracks"]:
            _log("Next track:", self.album["tracks"][self.track_index]["title"])
            try:
                self.track = bandcamplib.get_mp3(self.album["tracks"][self.track_index])
            except bandcamplib.NoMP3ContentError:
                self.track = None

    def get_media_player(self):
        if self.track is None:
            return
        try:
            self.current_sound = arcade.load_sound(self.track["path"], streaming=True)
        except FileNotFoundError as e:
            _log("Can't get media player", e)
            return
        self.media_player = self.current_sound.play(volume=0)
        self.media_player.push_handlers(on_eos=self._handler_music_over)

    def pause(self):
        if self.playing:
            self.fade_out(0.25)
            self.media_player.pause()
            self.playing = False

    def next(self):
        self.stop()
        self.get_next_track()

    def stop(self):
        if self.playing:
            self.fade_out()
        self.playing = False
        if self.current_sound and self.media_player:
            self.current_sound.stop(self.media_player)
            try:
                self.media_player.pop_handlers()
            except Exception as e:
                _log("Unable to pop handler", e)
            del self.current_sound
            del self.media_player
            self.current_sound = None
            self.media_player = None

    def fade_in(self, duration=1.0):
        if self.media_player:
            new_vol = (
                self.current_sound.get_volume(self.media_player)
                + Player.VOLUME_DELTA_SMALL
            )
            for i in range(100):
                if new_vol > 1:
                    new_vol = 1
                if new_vol > self.user_volume:
                    new_vol = self.user_volume
                self.volume_set(new_vol, set_user_volume=False)
                new_vol += Player.VOLUME_DELTA_SMALL
                time.sleep(duration / 100)

    def volume_up(self, value=VOLUME_DELTA):
        if self.media_player:
            new_vol = self.current_sound.get_volume(self.media_player) + value
            if new_vol > 1.0:
                new_vol = 1
            self.volume_set(new_vol)

    def volume_down(self, value=VOLUME_DELTA):
        if self.media_player:
            new_vol = self.current_sound.get_volume(self.media_player) - value
            if new_vol < 0.0:
                new_vol = 0.0
            self.volume_set(new_vol)

    def volume_set(self, value, set_user_volume=True):
        if self.media_player:
            try:
                self.current_sound.set_volume(value, self.media_player)
            except AttributeError:
                pass
            if set_user_volume:
                self.user_volume = value

    def fade_out(self, duration=1.0):
        if self.media_player:
            new_vol = (
                self.current_sound.get_volume(self.media_player)
                - Player.VOLUME_DELTA_SMALL
            )
            for volume in range(100):
                if new_vol < 0.0:
                    new_vol = 0.0
                self.volume_set(new_vol, set_user_volume=False)
                new_vol -= Player.VOLUME_DELTA_SMALL
                time.sleep(duration / 100)

    def get_volume(self):
        if self.playing and self.media_player:
            return self.current_sound.get_volume(self.media_player)
        return 0.5

    def get_position(self):
        result = 0
        if self.playing and self.media_player:
            result = self.current_sound.get_stream_position(self.media_player)
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

    def statistics(self):
        if self.band and self.album:
            return f"albums {len(self.band['albums'])} | current album tracks {len(self.album['tracks'])}"
