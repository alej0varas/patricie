import threading
import time
from datetime import timedelta

from arcade import load_sound

from . import bandcamplib
from .log import get_loger

_log = get_loger(__name__)


class BackgroundTaskRunner(threading.Thread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.working = False
        self.tasks = list()

    def run(self):
        while self.running:
            if not self.working:
                self.do_task()
            time.sleep(1)

    def task(self, name, *args):
        self.tasks.insert(0, (name, args))

    def do_task(self):
        if not self.tasks:
            return
        task_to_run, task_to_run_args = self.tasks.pop()
        self.working = True
        getattr(self, task_to_run)(*task_to_run_args)
        self.working = False


class Player(BackgroundTaskRunner):
    VOLUME_DELTA = 0.1
    VOLUME_DELTA_SMALL = 0.01

    def __init__(self, handler_music_over, skip_cached=False):
        super().__init__()
        self._handler_music_over = handler_music_over
        self.skip_cached = skip_cached
        self.is_setup = False

        self.downloading = None
        self.playing = None
        self.current_sound = None
        self.media_player = None
        self.band = None
        self.album_index = None
        self.album = None
        self.track_index = None
        self.track = None
        self.user_volume = None
        self.status_text = "Ready"

        self.start()

    def setup(self, url):
        self.task("do_setup", url)

    def do_setup(self, url):
        self.is_setup = False
        self.url = url
        self.downloading = False
        self.playing = False
        self.current_sound = None
        self.media_player = None
        self.band = None
        self.album_index = -1
        self.album = None
        self.track_index = -1
        self.track = None
        self.user_volume = self.user_volume or 100
        self.status_text = "Loading band"
        self.band = bandcamplib.get_band(url)
        self.is_setup = True

    def play(self):
        self.task("do_play")

    def do_play(self):
        self.status_text = "Starting to play"
        if not self.album:
            self.get_next_album()
        if not self.track:
            self.get_next_track()
        while not self.media_player:
            if (
                self.skip_cached
                and self.track.get("cached")
                and not self.track.get("preloaded")
            ):
                _log("Skipping track: ", self.track["title"])
                self.status_text = "Skipping track"
                self.get_next_track()
                continue
            self.get_media_player()
        self.status_text = "Playing"
        self.media_player.play()
        self.fade_in(0.5)
        self.playing = True

    def get_next_track(self):
        self.status_text = "Getting next track"
        track_index = self.track_index + 1
        if track_index >= len(self.album["tracks"]):
            self.get_next_album()
            self.get_next_track()
            return

        # update mp3 links if to old, for example when pausing and
        # resuming after x minutes. i don't know how much is x.
        if bandcamplib.request_expired(self.album):
            self.album = bandcamplib.get_album(self.album["url"])

        next_track = self.album["tracks"][track_index]
        if not next_track.get("path"):  # track hasn't been downloaded
            self.status_text = "Downloading track"
            try:
                bandcamplib.get_mp3(next_track)
            except bandcamplib.NoMP3ContentError as e:
                self.status_text = "Unable to download track"
                _log(e)
                return
        self.track = next_track
        self.track_index = track_index

    def get_media_player(self):
        if self.track is None:
            return
        try:
            self.current_sound = load_sound(self.track["path"], streaming=True)
        except FileNotFoundError as e:
            _log("Can't get media player", e)
            return
        self.media_player = self.current_sound.play(volume=0)
        self.media_player.push_handlers(on_eos=self._handler_music_over)

    def pause(self):
        self.task("do_pause")

    def do_pause(self):
        if self.playing:
            self.status_text = "Pausing"
            self.fade_out(0.25)
            self.media_player.pause()
            self.playing = False
            self.status_text = "Paused"

    def next(self):
        self.task("do_next")

    def do_next(self):
        self.status_text = "Getting next track"
        self.get_next_track()
        self.stop()
        self.play()

    def get_next_album(self):
        self.status_text = "Getting next album"
        album_index = self.album_index + 1
        if album_index >= len(self.band["albums_urls"]):
            self.status_text = "End of playlist reached"
            return
        self.album_index = album_index
        album_url = self.band["albums_urls"][self.album_index]
        album = bandcamplib.get_album(album_url)
        if not album["tracks"]:  # three are albums without tracks :/
            self.get_next_album()
            return
        self.album = album
        self.track_index = -1

    def next_album(self):
        self.get_next_album()
        self.next()

    def stop(self):
        if not self.media_player:
            return
        self.status_text = "Stopping"
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
            self.status_text = "Stopped"

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

    def quit(self):
        self.running = False
        self.stop()

    def statistics(self):
        r = ""
        if self.band and self.album:
            d = 0
            for t in self.album["tracks"]:
                d += int(t["duration"])
            r = f"albums {len(self.band['albums'])} - current {self.album_index + 1} | album tracks {len(self.album['tracks'])} - current {self.track_index + 1} | album duration {timedelta(seconds=d)}"
        return r

    def validate_url(self, url):
        try:
            return bandcamplib.validate_url(url)
        except Exception as e:
            self.status_text = "Invalid url"
            _log(e)

