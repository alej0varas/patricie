import json
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
            time.sleep(0.01)

    def task(self, func):
        def wrapper(*args, **kwargs):
            self.error = False
            self.tasks.insert(0, (func, args))

        return wrapper

    def do_task(self):
        if not self.tasks:
            return
        task_to_run, task_to_run_args = self.tasks.pop()
        self.working = True
        try:
            task_to_run(*task_to_run_args)
        except StopCurrentTaskExeption as e:
            _log(f"task stopped {e}")
        except Exception as e:
            _log("EXCEPTION CATCHED BY RUNNER", e)
            self.error = True
            self.tasks.clear()
        self.working = False


class Storage:
    """Does:

    - Read and write player related information to a file. The file
    will contain information about bands, albums and tracks.

    - Serialize to json and deserialize to a dict the information.

    """

    def __init__(self, path, serializer):
        self.path = path
        self.serializer = serializer
        self.content_as_dict = dict()
        if not path.exists():
            path.touch()
            self.write()
        self.content_as_dict = dict()
        try:
            self.content_as_dict = self.read()
        except json.decoder.JSONDecodeError as e:
            _log(f"storage corrupted {e}")
            self.write()

    def read(self):
        with open(self.path, "r") as f:
            return json.load(f)

    def write(self):
        with open(self.path, "w") as f:
            json.dump(self.content_as_dict, f, default=self.serializer)

    def update(self, items):
        self.content_as_dict = items
        self.write()

    @property
    def as_dict(self):
        self.content_as_dict = self.read()
        return self.content_as_dict


class ItemBase:
    def __init__(self, url):
        self.url = url

    def update(self, content):
        for k, v in content.items():
            setattr(self, k, v)

    def to_dict(self):
        d = dict()
        for k, v in self.__dict__.items():
            if k.startswith('_'):
                continue
            d[k] = v
        return d


class ItemWithChildren:
    def __init__(self):
        self.children = dict()

    def add_childrens(self, children_urls):
        for c_url in children_urls:
            cc = BandCamp.children_class(self)
            self.add_children(cc(c_url))

    def add_children(self, children):
        self.children[children.url] = children

    def get_children(self, children_url):
        return self.children.get(children_url)


class ItemWithParent:
    def __init__(self):
        self._parent_obj = None

    @property
    def parent(self):
        return self._parent_obj

    @parent.setter
    def parent(self, item):
        if item.of_type != self.parent_type:
            raise ValueError(f"parent type {item.of_type} is not {self.parent_type}")
        self._parent_obj = item


band_type = "band"
album_type = "album"
track_type = "song"


class Band(ItemBase, ItemWithChildren):
    of_type = band_type
    children_type = album_type

    def __init__(self, url):
        super().__init__(url)
        ItemWithChildren.__init__(self)

        self.name = ''

    def to_dict(self):
        d = super().to_dict()
        del d['children']

        return d


class Album(ItemBase, ItemWithChildren, ItemWithParent):
    of_type = album_type
    children_type = track_type
    parent_type = band_type

    def __init__(self, url):
        super().__init__(url)
        ItemWithChildren.__init__(self)
        ItemWithParent.__init__(self)

        self.name = ''

        self.band = self.parent

    @property
    def tracks(self):
        return self.children.values()


    def to_dict(self):
        d = super().to_dict()
        del d['children']

        return d


class Track(ItemBase, ItemWithParent):
    of_type = track_type
    parent_type = album_type

    def __init__(self, url):
        super().__init__(url)
        ItemWithParent.__init__(self)
        self.duration = 0
        self.title = ""
        self.mp3_url = None
        self.album = self.parent


class BandCamp:
    item_types = {
        band_type: {"class": Band, "method": bandcamplib.get_band},
        album_type: {"class": Album, "method": bandcamplib.get_album},
        track_type: {"class": Track, "method": bandcamplib.get_track},
    }

    @classmethod
    def items_serializer(_, obj):
        if isinstance(obj, tuple([i["class"] for i in BandCamp.item_types.values()])):
            return obj.to_dict()
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )

    def __init__(self):
        super().__init__()
        self.storage = Storage(utils.STORAGE_PATH, self.items_serializer)
        self.items = dict()
        for k, v in self.storage.as_dict.items():
            try:
                item = self.create_item(k, v)
            except ValueError as e:
                _log("bandcamp create_item", e)
            else:
                self.items[k] = item
        # add parents to childrens?
        # add childrens to parents?

    def create_item(self, url, content):
        match content["of_type"]:
            case Band.of_type:
                item = Band(url)
                item.add_childrens(content['albums_urls'])
            case Album.of_type:
                item = Album(url)
                item.add_childrens(content['tracks_urls'])
            case Track.of_type:
                item = Track(url)
            case _:
                raise ValueError(f"content type `{content['of_type']}` is not valid")
        item.update(content)
        return item

    def get_band(self, url):
        return self.get_item(url, band_type)

    def get_album(self, url):
        return self.get_item(url, album_type)

    def get_track(self, url, album):
        t = self.get_item(url, track_type)
        t.album = album
        path, cached = self.get_mp3_path(t)
        t.path = str(path)
        t.cached = cached
        return t

    def get_mp3_path(self, track):
        path = self.build_track_path_name(track)
        cached = True
        if not path.exists():
            content = self.get_content(
                bandcamplib.get_mp3, track.mp3_url
            )
            if content is None:
                raise StopCurrentTaskExeption('bandcamp get_mp3_path: cant get mp3')
            with open(path, "bw") as song_file:
                song_file.write(content)
                cached = False
        return path, cached

    def build_track_path_name(self, track):
        band = slugify(track.album.band.name)
        album = slugify(track.album.name)
        album_path = utils.TRACKS_DIR / band / album
        if not album_path.exists():
            album_path.mkdir(parents=True, exist_ok=True)
        title = slugify(track.title)
        path = album_path / f"{title}.mp3"
        return path

    def get_item(self, url, of_type):
        item = self.items.get(url)
        if item:
            return item

        content = self.get_content(
            self.item_types[of_type]["method"], url
        )

        item = self.create_item(url, content)
        self.items[item.url] = item
        self.storage.update(self.items)
        return item

    def get_content(self, method, url):
        """i don't agree with this method but i can't figure out a
        better way. the idea is to be able to:

          - retry only when it's necesary . responsability of ?.
            - yes for connection issues
            - not for 40X or 30X
          - have a informational message for te gui. responsability of
            the player.
          - return the content directly to the player. player don't
            need to know about the response object. responsability of
            BandCamp.
          - don't repeat this validation code BandCamp for every call
            to bandcamplib.

        maybe it's ok and i'm just confused :/

        """
        content = None
        attempt, retries = (1, 3)
        while attempt <= retries:
            _log(f"handle bcl call {attempt}")
            try:
                content = method(url)
                break
            except bandcamplib.DownloadNoRetryError as e:
                _log(e)
                break
            except bandcamplib.DownloadRetryError as e:
                _log(e)
                attempt += 1
        else:
            pass
            # message = "Problem reaching server"
        return content

    @classmethod
    def children_class(cls, obj):
        return cls.item_types[obj.children_type]["class"]


class Player:
    VOLUME_DELTA = 0.1
    VOLUME_DELTA_SMALL = 0.01

    task_runner = BackgroundTaskRunner()

    def __init__(self, handler_music_over, skip_cached=False):
        self.bandcamp = BandCamp()
        self.task_runner.start()
        self.status_text = "Ready"
        self._handler_music_over = handler_music_over
        self.skip_cached = skip_cached
        self.is_setup = None
        self.downloading = False
        self.current_sound = None
        self.media_player = None
        self.band = None
        self.album_index = -1
        self.album = None
        self.track_index = -1
        self.track = None
        self.user_volume = 100
        self.continue_playing = False

    @task_runner.task
    def setup(self, url):
        self.status_text = "Loading band"
        self.url = url
        self.band = self.bandcamp.get_band(url)
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
        if not self.album:
            try:
                self.get_next_album()
            except EndOfPlaylistException as e:
                _log(e)
                return
        if not self.track:
            self.get_next_track()
        if not self.media_player:
            if self.skip_cached and self.track.cached:
                _log("Skipping track: ", self.track.title)
                self.status_text = "Skipping track"
                self.track = None
                self.play()
                return
            self.get_media_player()
        self.media_player.play()
        self.fade_in(0.5)
        self.continue_playing = True
        self.status_text = "Playing"

    def get_next_track(self):
        self.status_text = "Loading track"
        track_index = self.track_index + 1
        if track_index >= len(self.album.tracks_urls):
            self.album = None
            self.track = None
            self.play()
            raise StopCurrentTaskExeption("No more tracks in album")
        track = self.bandcamp.get_track(
            self.album.tracks_urls[track_index], self.album
        )
        if track is None:
            raise StopCurrentTaskExeption('cant load track')
        track.album = self.album
        self.track = track
        self.track_index = track_index
        self.status_text = "Ready to play"

    def get_media_player(self):
        try:
            self.current_sound = load_sound(self.track.path, streaming=True)
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
        self.status_text = "Loading album"
        album_index = self.album_index + 1
        if album_index >= len(self.band.albums_urls):
            self.status_text = "End of playlist"
            raise EndOfPlaylistException(self.status_text)
        self.album_index = album_index
        album_url = self.band.albums_urls[self.album_index]
        album = self.bandcamp.get_album(album_url)
        if album is None:
            raise StopCurrentTaskExeption('bandcamp get_mp3_path: cant get mp3')
        self.album = album
        self.album.band = self.band
        self.track_index = -1

    def next_album(self):
        self.album = None
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

    def get_position(self):
        result = 0
        if self.current_sound and self.media_player:
            result = self.current_sound.get_stream_position(self.media_player)
        return result

    def get_duration(self):
        result = 0
        if self.track:
            result = self.track.duration
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
        self.task_runner.running = False
        self.stop()

    def validate_url(self, url):
        try:
            return bandcamplib.validate_url(url)
        except Exception as e:
            self.status_text = "Invalid url"
            _log(e)

    def info(self):
        d = {
            "title": self.track and self.track.title or "",
            "album": self.album and self.album.name or "",
            "band": self.band and self.band.name or "",
            "position": self.get_position(),
            "duration": self.get_duration(),
            "error": self.error,
            "status": str(self.status_text),
        }
        return d

    def statistics(self):
        r = ""
        if self.band:
            r += f"albums: {len(self.band.albums_urls)}"
            r += f" - current: {self.album_index + 1}"
            if self.album:
                r += f" | tracks: {len(self.album.tracks_urls)}"
            r += f" - current: {self.track_index + 1}"
            if self.album:
                tracks = self.album.tracks
                if tracks:
                    d = 0
                    for t in tracks:
                        d += t.duration
                    r += f" | album duration {timedelta(seconds=d)}"
        return r

    @property
    def playing(self):
        return bool(self.media_player and self.media_player.playing)

    @property
    def ready_to_play(self):
        return bool(self.track)

    @property
    def error(self):
        return str(self.task_runner.error)

    @property
    def working(self):
        return self.task_runner.working

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
