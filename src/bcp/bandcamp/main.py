import json
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunsplit

from bs4 import BeautifulSoup
from slugify import slugify

from .items import ItemBase, ItemWithChildren, ItemWithParent

from ..log import get_loger
from ..utils import (
    HTTPSession,
    StopCurrentTaskExeption,
    Storage,
    TRACKS_DIR,
    USER_DATA_DIR,
)

_log = get_loger(__name__)

band_type = "band"
album_type = "album"
track_type = "song"

http_session = HTTPSession()


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

    def to_dict(self):
        d = super().to_dict()
        del d["album"]
        return d


class Album(ItemBase, ItemWithChildren, ItemWithParent):
    of_type = album_type
    children_type = track_type
    children_class = Track
    parent_type = band_type

    def __init__(self, url):
        super().__init__(url)
        ItemWithChildren.__init__(self)
        ItemWithParent.__init__(self)

        self.name = ""

        self.band = self.parent

        self.add_track = self.add_children

    @property
    def tracks(self):
        return self.children.values()

    def to_dict(self):
        d = super().to_dict()

        del d["band"]
        if d.get("tracks"):
            del d["tracks"]
        del d["children"]
        del d["add_track"]
        return d


class Band(ItemBase, ItemWithChildren):
    of_type = band_type
    children_type = album_type
    children_class = Album

    def __init__(self, url):
        super().__init__(url)
        ItemWithChildren.__init__(self)

        self.name = ""

        self.add_album = self.add_children

    def to_dict(self):
        d = super().to_dict()
        if d.get("albums"):
            del d["albums"]
        del d["children"]
        del d["add_album"]

        return d


class BandCamp:

    DOMAIN_SITE = "bandcamp.com"
    DOMAIN_CDN = "bcbits.com"

    @classmethod
    def items_serializer(_, obj):
        if isinstance(obj, tuple([i["class"] for i in ITEM_TYPES.values()])):
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
                item = self.create_item(k, v)
            except ValueError as e:
                _log("bandcamp create_item", e)
            else:
                self.items[k] = item
        for band in self.get_bands():
            for a_url in band.albums_urls:
                a = Album(a_url)
                ac = self.storage.as_dict.get(a_url)
                if ac is None:
                    continue
                a.update(ac)
                band.add_album(a)
                a.band = band
        for album in self.get_albums():
            for t_url in album.tracks_urls:
                t = Track(t_url)
                tc = self.storage.as_dict.get(t_url)
                if tc is None:
                    continue
                t.update(tc)
                album.add_track(t)
                t.album = album

    def create_item(self, url, content):
        match content["of_type"]:
            case Band.of_type:
                # validate url, currently is not ../music
                item = Band(url)
                item.add_childrens(content["albums_urls"])
            case Album.of_type:
                item = Album(url)
                item.add_childrens(content["tracks_urls"])
            case Track.of_type:
                item = Track(url)
            case _:
                raise ValueError(f"content type `{content['of_type']}` is not valid")
        item.update(content)
        return item

    def get_bands(self):
        return [i for i in self.items.values() if i.of_type == Band.of_type]

    def get_albums(self):
        return [i for i in self.items.values() if i.of_type == Album.of_type]

    def get_band(self, url):
        url = self.validate_url(url)
        return self.get_item(url, band_type)

    def get_album(self, url):
        return self.get_item(url, album_type)

    def get_track(self, url):
        t = self.get_item(url, track_type)
        return t

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

    def get_item(self, url, of_type):
        item = self.items.get(url)
        if item:
            return item

        content = ITEM_TYPES[of_type]["method"](url)

        item = self.create_item(url, content)
        self.items[item.url] = item
        self.storage.update(self.items)
        return item

    @classmethod
    def _get_albums_urls(cls, html):
        # bandcamp.com now includes tracks in the band page, before it
        # was only albums, so we have to filter them out.
        def is_album(href):
            return href and href.startswith("/album/")

        soup = BeautifulSoup(html, "html.parser")
        r = [i["href"] for i in soup.find_all(href=is_album)]
        return r

    @classmethod
    def _get_tracks_urls(cls, soup):
        tracks = list()
        # some tracks don't have a link to the track page
        for div in soup.find_all("div", "title"):
            a = div.find("a")
            if a:
                tracks.append(a.get("href"))
        return tracks

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
                        raise DownloadNoRetryError(
                            f"The requested url {url} redirected to {new_url}"
                        )
                    content = response.read()
                    break
            except HTTPError as e:
                _log(f"    donwload_content {e}")
                code = e.file.code
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
    def validate_url(cls, url):
        if not url:
            raise ValueError("Invalid url", url)
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if not domain:
            domain = f"{url}.{BandCamp.DOMAIN_SITE}"
        if domain.count(".") != 2:
            raise ValueError("Invalid domain", domain)
        if ".".join(domain.split(".")[-2:]) != BandCamp.DOMAIN_SITE:
            raise ValueError("Not a bandcamp URL", domain)
        scheme = parsed_url.scheme
        if scheme != "https":
            scheme = "https"
        path = parsed_url.path
        if not path or path != "/music":
            path = "music"
        newurl = urlunsplit((scheme, domain, path, "", ""))
        return newurl

    @classmethod
    def download_band(cls, url):
        html = cls.download_content(url)
        soup = BeautifulSoup(html, "html.parser")
        albums_urls = cls._to_full_url(cls._get_albums_urls(html), url)
        name = soup.find("meta", property="og:title").get("content")
        of_type = soup.find("meta", property="og:type").get("content")
        r = {
            "name": name,
            "of_type": of_type,
            "url": soup.find("meta", property="og:url").get("content"),
            "description": soup.find("meta", property="og:description").get("content"),
            "albums_urls": albums_urls,
        }
        return r

    @classmethod
    def download_album(cls, url):
        html = cls.download_content(url)
        soup = BeautifulSoup(html, "html.parser")
        tracks_urls = cls._to_full_url(cls._get_tracks_urls(soup), url)
        name = soup.find(id="name-section").h2.text.strip()
        of_type = soup.find("meta", property="og:type").get("content")
        r = {"name": name, "of_type": of_type, "tracks_urls": tracks_urls}
        return r

    @classmethod
    def download_track(cls, url):
        html = cls.download_content(url)
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", attrs={"data-tralbum": True})
        # happened only once, i wasn't able to reproduce
        if not script:
            return
        data = json.loads(script["data-tralbum"])
        of_type = soup.find("meta", property="og:type").get("content")
        r = {
            "url": data["url"],
            "of_type": of_type,
            "artist": data["artist"],
            "mp3_url": data["trackinfo"][0]["file"]["mp3-128"],
            "title": data["trackinfo"][0]["title"],
            "duration": data["trackinfo"][0]["duration"],
            "lyrics": data["trackinfo"][0]["lyrics"],
        }
        return r

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
    def _to_full_url(cls, paths, base):
        r = list()
        parsed_url = urlparse(base)
        for path in paths:
            r.append(parsed_url._replace(path=path).geturl())
        return r


ITEM_TYPES = {
    band_type: {"class": Band, "method": BandCamp.download_band},
    album_type: {"class": Album, "method": BandCamp.download_album},
    track_type: {"class": Track, "method": BandCamp.download_track},
}


class EndOfPlaylistException(Exception):
    pass


class DownloadRetryError(Exception):
    pass


class DownloadNoRetryError(Exception):
    pass
