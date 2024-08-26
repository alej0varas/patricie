import arcade

from . import bandcamplib


class Player:
    def __init__(self, music_over_handler, skip_downloaded):
        self.playing = False
        self.band = dict()
        self.album = dict()
        self.track = dict()
        self.sound = None
        self.media_player = None

    def get_track_position(self):
        if self.sound:
            return self.sound.get_stream_position(self.media_player)
        else:
            return 0

    def get_volume(self):
        pass

    def load_band(self, url):
        self.band = bandcamplib.load_band(url)
        return self.band

    def load_album(self, title):
        album = bandcamplib.load_album(
            self.band["url"] + self.band["albums"][title]["url"]
        )
        self.band["albums"][title] = album
        self.album = self.band["albums"][title]
        self.tracks = self.band["albums"][title]["tracks"]

    def track_info(self):
        return {
            "title": self.track["title"],
            "album": self.album["title"],
            "artist": self.artist,
            "duration": self.track["duration"],
        }

    def play(self, track):
        if self.sound and self.media_player:
            self.sound.stop(self.media_player)
        mp3_path, cached = bandcamplib.get_mp3_path(self.tracks[track])
        self.sound = arcade.load_sound(mp3_path)
        self.media_player = self.sound.play(volume=1)
