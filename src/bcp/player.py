from . import bandcamplib

class Player:
    def __init__(self, music_over_handler, skip_downloaded):
        self.playing = False

    def get_volume(self):
        pass

    def load_band(self, url):
        self.band = bandcamplib.load_band(url)
        return self.band

    def load_album(self, url):
        pass
