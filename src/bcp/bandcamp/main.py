from datetime import timedelta
import json
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from slugify import slugify

from .items import ItemBase, ItemWithChildren, ItemWithParent

from ..log import get_loger
from ..utils import (
    HTTPSession,
    StopCurrentTaskExeption,
    Storage,
    USER_DATA_DIR,
)

_log = get_loger(__name__)

TRACKS_DIR = USER_DATA_DIR / "tracks"
if not TRACKS_DIR.exists():
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
_log("tracks path:", TRACKS_DIR)

band_type = "band"
album_type = "album"
track_type = "song"

http_session = HTTPSession()


class Track(ItemBase, ItemWithParent):
    of_type = "song"

    def __init__(self, url):
        super().__init__()
        ItemWithParent.__init__(self)

        self.url = url
        self.album = self.parent

    def update_from_soup(self, soup):
        super().update_from_soup(soup)
        script = soup.find("script", attrs={"data-tralbum": True})
        # happened only once, i wasn't able to reproduce
        if not script:
            return

        data = json.loads(script["data-tralbum"])
        self.url = data["url"]
        self.of_type = soup.find("meta", property="og:type").get("content")
        self.artist = data["artist"]
        # The album has a link to the track, but there's no MP3
        # available.  In this case, we skip the track. I haven't found
        # a way to skip listing this track when loading the album.
        if data["trackinfo"][0]["file"] is None:
            return
        self.mp3_url = data["trackinfo"][0]["file"]["mp3-128"]
        self.title = data["trackinfo"][0]["title"]
        self.duration = data["trackinfo"][0]["duration"]
        self.lyrics = data["trackinfo"][0]["lyrics"]
        return True

    def update_from_dict(self, content):
        super().update(content)

    def to_dict(self):
        d = super().to_dict()
        del d["album"]
        return d


class Album(ItemBase, ItemWithChildren, ItemWithParent):
    of_type = "album"
    children_class = Track

    def __init__(self, url):
        super().__init__()
        ItemWithChildren.__init__(self)
        ItemWithParent.__init__(self)

        self.url = url
        self.band = self.parent
        self.add_track = self.add_children
        self.add_tracks = self.add_childrens

    def update_from_soup(self, soup):
        super().update_from_soup(soup)
        self.name = soup.find(id="name-section").h2.text.strip()
        self.of_type = soup.find("meta", property="og:type").get("content")
        self.duration = self.get_album_duration(soup)
        self.tracks_urls = self.get_tracks_urls(soup)
        for t_url in self.tracks_urls:
            self.add_track(self.children_class(t_url))
        return True

    def update_from_dict(self, content):
        super().update(content)
        self.add_tracks(content["tracks_urls"])

    def get_track_url(self, index):
        return self.tracks_urls[index]

    @classmethod
    def get_tracks_urls(cls, soup):
        """there's no way to know if the track can be played from the
        album page's html so we return track urls that lead to a track
        page that has no mp3 file. if the track can be played will be
        validated when loading the track.

        """

        def is_track(tag):
            if tag.name == "a" and tag.find("span", attrs={"class": "track-title"}):
                return tag

        return [i["href"] for i in soup.find_all(is_track)]

    @classmethod
    def get_album_duration(cls, soup):
        def in_seconds(time_string):
            m, s = time_string.split(":")
            return int(m) * 60 + int(s)

        d = 0
        for div in soup.find_all("div", "title"):
            t = div.find("span", "time")
            if t:
                d += in_seconds(t.text.strip())
        return str(timedelta(seconds=d))

    @property
    def tracks(self):
        return self.children.values()

    def to_dict(self):
        d = super().to_dict()

        del d["band"]
        if d.get("tracks"):
            del d["tracks"]
        del d["children"]
        return d


class Band(ItemBase, ItemWithChildren):
    of_type = "band"
    children_class = Album

    def __init__(self, url):
        super().__init__()
        ItemWithChildren.__init__(self)

        self.url = self.validate_url(url)
        self.add_album = self.add_children
        self.add_albums = self.add_childrens

    def update_from_soup(self, soup):
        super().update_from_soup(soup)
        self.name = soup.find("meta", property="og:title").get("content")
        self.of_type = soup.find("meta", property="og:type").get("content")
        self.url = soup.find("meta", property="og:url").get("content")
        self.description = soup.find("meta", property="og:description").get("content")
        # already set if loaded form storage
        self.albums_urls = self.get_albums_urls(soup)
        for a_url in self.albums_urls:
            self.add_album(Album(a_url))
        return True

    def update_from_dict(self, content):
        super().update(content)
        self.albums_urls = content["albums_urls"]
        self.add_albums(self.albums_urls)

    def get_album_url(self, index):
        return self.albums_urls[index]

    @classmethod
    def get_albums_urls(cls, soup):
        """extract from html and returns relative albums urls"""

        # bandcamp.com now includes tracks in the band page, before it
        # was only albums, so we have to filter them out.
        def is_album(href):
            return href and href.startswith("/album/")

        r = [i["href"] for i in soup.find_all(href=is_album)]
        return r

    def to_dict(self):
        d = super().to_dict()
        if d.get("albums"):
            del d["albums"]
        del d["children"]
        return d

    @property
    def download_url(self):
        return urlparse(super().download_url)._replace(path="music").geturl()

    @classmethod
    def validate_url(cls, url):
        if url.isalpha():
            url = f"https://{url}.{BandCamp.BASE_URL}"
            return url

        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if domain.count(".") != 2:
            raise ValueError(f"Invalid site {domain}")
        sub_domain, bandcamp, dot_com = domain.split(".")
        if (not sub_domain) or f"{bandcamp}.{dot_com}" != BandCamp.DOMAIN_NAME:
            raise ValueError(f"Invalid site {domain}")
        newurl = parsed_url._replace(scheme="https", path="")

        return newurl.geturl()


class BandCamp:
    DOMAIN_NAME = "bandcamp.com"
    BASE_URL = f"https://{DOMAIN_NAME}"
    DOMAIN_CDN = "bcbits.com"

    @classmethod
    def items_serializer(_, obj):
        if isinstance(obj, (Band, Album, Track)):
            return obj.to_dict()
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )

    def __init__(self):
        super().__init__()
        self.storage = Storage(self.items_serializer)
        self.items = dict()
        for k, v in self.storage.as_dict.items():
            try:
                item = self.load_item(k, v)
            except ValueError as e:
                _log("bandcamp __init__", e)
            else:
                self.items[k] = item
        for band in self.get_bands():
            for a_url in band.albums_urls:
                a = Album(self.to_full_url(band, a_url))
                ac = self.storage.as_dict.get(a_url)
                if ac is None:
                    continue
                a.update(ac)
                band.add_album(a)
                a.band = band
        for album in self.get_albums():
            for t_url in album.tracks_urls:
                t = Track(self.to_full_url(band, t_url))
                tc = self.storage.as_dict.get(t_url)
                if tc is None:
                    continue
                t.update(tc)
                album.add_track(t)
                t.album = album

    def load_item(self, url, content):
        """called when loading items from storage. returns an instance
        of the item obtained with using url and attributes set using
        the stored content.

        """
        match content["of_type"]:
            case Band.of_type:
                # validate url, currently is not ../music
                item = Band(url)
            case Album.of_type:
                item = Album(url)
            case Track.of_type:
                item = Track(url)
            case _:
                raise ValueError(f"content type `{content['of_type']}` is not valid")
        item.update_from_dict(content)
        return item

    def get_bands(self):
        return [i for i in self.items.values() if i.of_type == Band.of_type]

    def get_albums(self):
        return [i for i in self.items.values() if i.of_type == Album.of_type]

    def get_band(self, url):
        return self.get_item(url, Band)

    def get_album(self, url):
        return self.get_item(url, Album)

    def get_track(self, url):
        return self.get_item(url, Track)

    def get_mp3_path(self, track):
        path = self.build_track_path_name(track)
        return path

    def build_track_path_name(self, track):
        band = slugify(track.album.band.name)
        album = slugify(track.album.name)
        absolute_path = TRACKS_DIR / band / album
        if not absolute_path.exists():
            absolute_path.mkdir(parents=True, exist_ok=True)
        from pathlib import Path

        path = Path(TRACKS_DIR.name) / band / album / f"{slugify(track.title)}.mp3"
        return path

    def get_item(self, url, item_class):
        item = self.items.get(url)
        if item is not None and not item.expired:
            return item
        http_session.cache.invalidate(url)
        item = item_class(url)
        success = item.update_from_soup(self.get_soup(item.download_url))
        if not success:
            raise LoadItemException(f"Cant load item {item_class.__name__} {url}")
        self.items[item.url] = item
        self.storage.update(self.items)
        return item

    @classmethod
    def get_soup(cls, url):
        html = cls.download_content(url)
        return BeautifulSoup(html, "html.parser")

    @classmethod
    def download_content(cls, url):
        content = None
        attempt, retries = (1, 3)
        while attempt <= retries:
            _log(f"download_content attempt: {attempt}")
            try:
                with http_session.get(url) as response:
                    new_url = response.geturl()
                    if url != new_url:
                        # we don't know in which cases bandcamp redirecs so we
                        # don't know what to do in case it happens
                        _log(f"The requested url {url} redirected to {new_url}")
                        break
                    content = response.read()
                    break
            except HTTPError as e:
                _log(f"    download_content {e}")
                code = e.file.code
                if code == 410:
                    _log("    link expired")
                    raise LinkExpiredException
                if 400 <= code < 500:
                    break
                _log("        retrying")
            except (IncompleteRead, URLError, TimeoutError) as e:
                _log(f"    retrying for: {e}")
                attempt += 1
        else:
            _log("    Problem reaching server")
        return content

    @classmethod
    def download_mp3(cls, track):
        cached = True
        path = cls.get_absolute_path(track.path)
        if not path.exists():
            cached = False
            with http_session.cache.disable():
                content = cls.download_content(track.mp3_url)
            if content is None:
                raise StopCurrentTaskExeption("download_mp3: cant get mp3")
            with open(path, "bw") as song_file:
                song_file.write(content)
        return cached

    @classmethod
    def get_absolute_path(self, part):
        return USER_DATA_DIR / part

    @classmethod
    def to_full_url(cls, band, path):
        parsed_url = urlparse(band.url)
        newurl = parsed_url._replace(path=path)
        return newurl.geturl()


class EndOfPlaylistException(Exception):
    pass


class DownloadRetryError(Exception):
    pass


class DownloadNoRetryError(Exception):
    pass


class LoadItemException(Exception):
    pass


class LinkExpiredException(Exception):
    pass
