from datetime import timedelta
import threading
import time

from arcade import load_sound
from slugify import slugify

from . import bandcamplib, utils
from .log import get_loger

_log = get_loger(__name__)


class BackgroundTaskRunner(threading.Thread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.working = False
        self.tasks = list()
        self.error = False

    def run(self):
        while self.running:
            if not self.working:
                self.do_task()
            time.sleep(1)

    def task(self, name, *args):
        self.error = False
        self.tasks.insert(0, (name, args))

    def do_task(self):
        if not self.tasks:
            return
        task_to_run, task_to_run_args = self.tasks.pop()
        self.working = True
        try:
            getattr(self, task_to_run)(*task_to_run_args)
        except StopCurrentTaskExeption as e:
            _log(f"task stopped {e}")
        except Exception as e:
            _log('EXCEPTION CATCHED BY RUNNER', e)
            self.error = True
            self.tasks.clear()
        self.working = False


class Player(BackgroundTaskRunner):
    VOLUME_DELTA = 0.1
    VOLUME_DELTA_SMALL = 0.01

    def __init__(self, handler_music_over, skip_cached=False):
        super().__init__()
        self.status_text = "Ready"
        self._handler_music_over = handler_music_over
        self.skip_cached = skip_cached
        self.is_setup = False
        self.downloading = None
        self.current_sound = None
        self.media_player = None
        self.band = None
        self.album_index = None
        self.album = None
        self.track_index = None
        self.track = None
        self.user_volume = None

        self.start()

    def setup(self, url):
        self.task("do_setup", url)

    def do_setup(self, url):
        self.status_text = "Loading band"
        self.is_setup = False
        self.url = url
        self.downloading = False
        self.current_sound = None
        self.media_player = None
        self.band = None
        self.album_index = -1
        self.album = None
        self.track_index = -1
        self.track = None
        self.user_volume = self.user_volume or 100
        self.band = self.handle_call_to_bcl(bandcamplib.get_band, url)
        self.is_setup = True

    def play(self):
        self.task("do_play")

    def do_play(self):
        if not self.album:
            try:
                self.get_next_album()
            except EndOfPlaylistException as e:
                _log(e)
                return
        if not self.track:
            self.get_next_track()
        if not self.media_player:
            if self.skip_cached and self.track.get("cached"):
                _log("Skipping track: ", self.track["title"])
                self.status_text = "Skipping track"
                self.track = None
                self.play()
                return
            self.get_media_player()
        self.media_player.play()
        self.fade_in(0.5)
        self.status_text = "Playing"

    def get_next_track(self):
        self.status_text = "Loading track"
        track_index = self.track_index + 1
        if track_index >= len(self.album["tracks_urls"]):
            self.album = None
            self.track = None
            self.play()
            raise StopCurrentTaskExeption('No more tracks in album')
        track = self.handle_call_to_bcl(
            bandcamplib.get_track, self.album["tracks_urls"][track_index]
        )
        track["album"] = self.album
        path = self._get_mp3_path(track)
        if not path.exists():
            self.status_text = "Downloading mp3"
            content = self.handle_call_to_bcl(bandcamplib.get_mp3, track["file"])
            with open(path, "bw") as song_file:
                song_file.write(content)
                cached = False
        else:
            cached = True
        track["path"] = path
        track["cached"] = cached
        self.track = track
        self.track_index = track_index

    def _get_mp3_path(self, track):
        band = slugify(track["album"]["band"]["name"])
        album = slugify(track["album"]["name"])
        album_path = utils.TRACKS_DIR / band / album
        if not album_path.exists():
            album_path.mkdir(parents=True, exist_ok=True)
        title = slugify(track["title"])
        path = album_path / f"{title}.mp3"
        return path

    def get_media_player(self):
        try:
            self.current_sound = load_sound(self.track["path"], streaming=True)
        except FileNotFoundError as e:
            _log("Can't get media player: ", e)
            self.status_text = "Can't play this track"
            raise Exception(self.status_text)
        self.media_player = self.current_sound.play(volume=0)
        self.media_player.push_handlers(on_eos=self._handler_music_over)

    def pause(self):
        self.task("do_pause")

    def do_pause(self):
        self.status_text = "Pause"
        if self.media_player:
            self.fade_out(0.25)
            self.media_player.pause()
            self.status_text = "Paused"

    def next(self):
        self.task("do_next")

    def do_next(self):
        self.status_text = "Next"
        self.track = None
        self.stop()
        self.play()

    def get_next_album(self):
        self.status_text = "Loading album"
        album_index = self.album_index + 1
        if album_index >= len(self.band["albums_urls"]):
            self.status_text = "End of playlist"
            raise EndOfPlaylistException(self.status_text)
        self.album_index = album_index
        album_url = self.band["albums_urls"][self.album_index]
        album = self.handle_call_to_bcl(bandcamplib.get_album, album_url)
        album["band"] = self.band
        self.album = album
        self.track_index = -1

    def next_album(self):
        self.album = None
        self.next()

    def stop(self):
        if not self.media_player:
            return
        if self.playing:
            self.fade_out()
        if self.current_sound and self.media_player:
            self.current_sound.stop(self.media_player)
            try:
                self.media_player.pop_handlers()
            except Exception as e:
                _log("Unable to pop handler", e)
            # in some cases, the GUI called `get_volume` and the
            # `current_sound` attribute did not exist. that's why we
            # set to None before we delete the object.
            _ = self.current_sound
            self.current_sound = None
            del _
            _ = self.media_player
            self.media_player = None
            del _
            self.status_text = "Stopped"

    def fade_in(self, duration=1.0):
        if self.media_player and self.current_sound:
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
        if self.current_sound and self.media_player and self.media_player.playing:
            return self.current_sound.get_volume(self.media_player)
        return 0.5

    def get_position(self):
        result = 0
        if self.current_sound and self.media_player:
            result = self.current_sound.get_stream_position(self.media_player)
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

    def quit(self):
        self.running = False
        self.stop()

    def handle_call_to_bcl(self, call, arg):
        """i don't agree with this method but i can't figure out a
        better way. the idea is to be able to:

          - retry only when it's necesary . responsability of the player.
            - yes for connection issues
            - not for 40X or 30X
          - have a informational message for te gui. responsability of the player.
          - return the content directly to the player. responsability of bandcamplib.
          - don't repeat this validation code on the player for every call to bandcamplib.
          - don't crash the player thread

        maybe it's ok and i'm just confused :/

        """
        attempt, retries = (1, 3)
        while attempt <= retries:
            _log(f"handle bcl call {attempt}")
            try:
                return call(arg)
            except bandcamplib.DownloadNoRetryError as e:
                _log(e)
                self.status_text = "Invalid url"
                raise Exception(self.status_text)
            except bandcamplib.DownloadRetryError as e:
                _log(e)
                self.status_text = "Trying to download again"
                attempt += 1
        else:
            self.status_text = "Problem reaching server"
            raise Exception(self.status_text)

    def validate_url(self, url):
        try:
            return bandcamplib.validate_url(url)
        except Exception as e:
            self.status_text = "Invalid url"
            _log(e)

    def info(self):
        d = {
            "title": self.track and self.track["title"] or "",
            "album": self.album and self.album["name"] or "",
            "band": self.band and self.band["name"] or "",
            "position": self.get_position(),
            "duration": self.get_duration(),
            "error": str(self.error),
            "status": str(self.status_text),
        }
        return d

    def statistics(self):
        r = ""
        if self.band:
            r += f"albums: {len(self.band['albums_urls'])}"
            r += f" - current: {self.album_index + 1}"
            if self.album:
                r += f" | tracks: {len(self.album['tracks_urls'])}"
            r += f" - current: {self.track_index + 1}"
            if self.album:
                tracks = self.album.get("tracks")
                if tracks:
                    d = 0
                    for t in self.album.get("tracks"):
                        d += int(t["duration"])
                    r += f" | album duration {timedelta(seconds=d)}"
        return r

    @property
    def playing(self):
        return bool(self.media_player and self.media_player.playing)

    @property
    def ready_to_play(self):
        return bool(self.track)
    @property
    def volume_min(self):
        return self.get_volume() == 0.0

    @property
    def volume_max(self):
        return self.get_volume() == 1.0


class EndOfPlaylistException(Exception):
    pass


class StopCurrentTaskExeption(Exception):
    pass
