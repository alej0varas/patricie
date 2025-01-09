import time

from arcade import load_sound

from .bandcamp import BandCamp, MP3DownloadError
from .log import get_loger
from .utils import BackgroundTaskRunner, StopCurrentTaskExeption

_log = get_loger(__name__)


class Player:
    VOLUME_DELTA = 0.1
    VOLUME_DELTA_SMALL = 0.01

    task_runner = BackgroundTaskRunner()

    def __init__(self, handler_music_over, skip_cached=False):
        self.url = None
        self.bandcamp = BandCamp()
        self.task_runner.start()
        self.status_text = ""
        self._handler_music_over = handler_music_over
        self.skip_cached = skip_cached
        self.is_setup = None
        self.downloading = None
        self.current_sound = None
        self.media_player = None
        self.band = None
        self.album_index = None
        self.album = None
        self.track_index = None
        self.track = None
        self.user_volume = 100
        self.continue_playing = None

    @task_runner.task
    def setup(self, url):
        self.status_text = "Ready"
        self.is_setup = None
        self.downloading = False
        self.current_sound = None
        self.media_player = None
        self.band = None
        self.album_index = -1
        self.album = None
        self.track_index = -1
        self.track = None
        self.continue_playing = False

        try:
            self.url = self.bandcamp.validate_band_url(url)
        except ValueError as e:
            self.status_text = e
            raise StopCurrentTaskExeption(self.status_text)
        self.status_text = "Loading band"
        self.band = self.bandcamp.get_band(self.url)
        if self.band is None:
            raise StopCurrentTaskExeption("can't load band")
        # *temporary solution* i prefer to call this two methods
        # instead of `play`. the idea is to separate loading a band
        # from starting to play. in the future we'll show band
        # information and albums and let the user choose to play or
        # not.
        self.get_next_album()
        self.get_next_track()

        self.is_setup = True

    @task_runner.task
    def play(self):
        self.continue_playing = True
        self.get_next_album()
        self.get_next_track()
        if not self.media_player:
            if self.skip_cached and self.track.cached:
                _log("Skipping track: ", self.track.name)
                self.status_text = "Skipping track"
                self.track = None
                self.play()
                return
            self.get_media_player(self.track.absolute_path)
        self.media_player.play()
        self.fade_in(0.5)
        self.status_text = "Playing"

    def get_next_track(self):
        if self.track:
            return
        self.status_text = "Loading track"
        track_index = self.track_index + 1
        if track_index >= len(self.album.tracks_urls):
            self.next_album()
            raise StopCurrentTaskExeption("No more tracks in album")
        self.track_index = track_index
        track = self.bandcamp.get_track(
            self.bandcamp.to_full_url(self.band, self.album.get_track_url(track_index))
        )
        if track is None:
            self.next()
            raise StopCurrentTaskExeption("cant load track")
        if track.mp3_url is None:
            self.next()
            raise StopCurrentTaskExeption("track without mp3 url")
        track.album = self.album
        if not track.path_exists:
            try:
                track.path, track.cached = self.bandcamp.download_mp3(track)
            except MP3DownloadError:
                self.status_text = "can't download mp3"
                self.next()
                raise StopCurrentTaskExeption(self.status_text)
        self.track = track
        self.track_index = track_index
        self.status_text = "Ready to play"

    def get_media_player(self, path):
        try:
            self.current_sound = load_sound(path, streaming=True)
        except FileNotFoundError as e:
            _log("Can't get media player: ", e)
            self.status_text = "Can't play this track"
            raise Exception(self.status_text)
        self.media_player = self.current_sound.play(volume=0)
        self.media_player.push_handlers(on_eos=self._handler_music_over)

    @task_runner.task
    def pause(self):
        self.status_text = "Pause"
        if self.media_player:
            self.fade_out(0.25)
            self.media_player.pause()
            self.continue_playing = False
            self.status_text = "Paused"

    @task_runner.task
    def next(self):
        self.status_text = "Next"
        self.track = None
        self.fade_out()
        self.clear_media_player_and_current_sound()
        self.get_next_track()

        if self.continue_playing:
            self.play()

    def get_next_album(self):
        if self.album:
            return
        self.status_text = "Loading album"
        album_index = self.album_index + 1
        if album_index >= len(self.band.albums_urls):
            self.status_text = "End of playlist"
            raise StopCurrentTaskExeption(self.status_text)
        self.album_index = album_index
        album = self.bandcamp.get_album(
            self.bandcamp.to_full_url(self.band, self.band.get_album_url(album_index))
        )
        if album is None:
            raise StopCurrentTaskExeption("get next album: cant get album")
        self.album = album
        self.album.band = self.band
        self.track_index = -1

    @task_runner.task
    def next_album(self):
        self.album = None
        self.get_next_album()
        self.next()

    def stop(self):
        self.fade_out()
        self.clear_media_player_and_current_sound()
        self.continue_playing = False

    def clear_media_player_and_current_sound(self):
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

    @property
    def track_position(self):
        if self.current_sound and self.media_player:
            return self.current_sound.get_stream_position(self.media_player)
        return 0

    @property
    def track_duration(self):
        if self.track:
            return self.track.duration
        return 0

    @property
    def band_name(self):
        if self.track:
            return f"{self.track.album.band.name}"
        return ""

    @property
    def album_name(self):
        if self.track:
            return f"{self.track.album.name}"
        return ""

    @property
    def track_title(self):
        if self.track:
            return f"{self.track.name}"
        return ""

    def quit(self):
        self.stop()

    @property
    def statistics(self):
        r = ""
        if self.band:
            r += f"albums: {len(self.band.albums_urls)}"
            r += f" - current: {self.album_index + 1}"
            if self.album:
                r += f" | tracks: {len(self.album.tracks_urls)}"
            r += f" - current: {self.track_index + 1}"
            if self.album:
                r += f" | album duration {self.album.duration}"
        return r

    @property
    def status(self):
        return str(self.status_text)

    @property
    def playing(self):
        return bool(self.media_player and self.media_player.playing)

    @property
    def ready_to_play(self):
        return bool(self.track)

    @property
    def error(self):
        return ['no', 'yes'][self.task_runner.error]

    @property
    def working(self):
        return self.task_runner.working

    @property
    def volume_min(self):
        return self.get_volume() == 0.0

    @property
    def volume_max(self):
        return self.get_volume() == 1.0

    @property
    def current_url(self):
        return self.url or ""
