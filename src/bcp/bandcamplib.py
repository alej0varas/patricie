import json
import os

from urllib.parse import urlparse

import dotenv
from bs4 import BeautifulSoup
from platformdirs import user_data_dir
from slugify import slugify

from .log import get_loger
from . import utils

dotenv.load_dotenv()
_log = get_loger(__name__)


ENVIRONMENT = os.environ.get("ENVIRONMENT", "")

# Suppress AlsoFT messages because they bother me
os.environ["ALSOFT_LOGLEVEL"] = "0"

USER_DATA_DIR = user_data_dir("patricie")
_log("Root directory:", USER_DATA_DIR)
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)
TRACKS_DIR = os.path.join(USER_DATA_DIR, "tracks")
_log("Traks directory:", TRACKS_DIR)
if not os.path.exists(TRACKS_DIR):
    os.makedirs(TRACKS_DIR)
ENVIRONMENT_STR = f"_{ENVIRONMENT}" if ENVIRONMENT else ""
HTTP_CACHE_PATH = os.path.join(
    USER_DATA_DIR, "requests_cache" + ENVIRONMENT_STR + ".sqlite"
)
_log("Http Cache path:", HTTP_CACHE_PATH)
http_session = utils.Session(HTTP_CACHE_PATH)


def get_band(url):
    # ensure url ends in '/music' some band pages redirect to an album
    # or track when ther's no path.
    url = "/".join(url.split("/")[0:-1]) + "/music"
    r = dict()
    r["albums_urls"] = _get_albums_urls_from_url(url)
    r["albums"] = r["albums_urls"]
    return r


def get_album(url):
    r = dict()
    html = _fetch_url_content(url)
    tracks = _get_tracks_from_html(html)
    t = list()
    for track in tracks:
        parsed_url = urlparse(url)
        # FIX: track's url will have an album with the name of the track
        artist = parsed_url.netloc.split(".")[0]
        album = parsed_url.path.split("/")[2]
        album_path = os.path.join(TRACKS_DIR, artist, album)
        if not os.path.isdir(album_path):
            os.makedirs(album_path)
        track.update(
            {
                "artist": artist,
                "album": album,
                "title": track["title"],
                "album_path": album_path,
            }
        )
        t.append(track)
    r["tracks"] = t
    return r


def get_mp3(track):
    track["path"] = _get_mp3_path(track)
    cached = _get_mp3_file(track)
    track["cached"] = cached
    return track


def _get_albums_urls_from_url(url):
    albums_urls = list()
    music_html = _fetch_url_content(url)
    albums_urls_path = _get_albums_urls_from_html(music_html)

    parsed_url = urlparse(url)
    for album_url_path in albums_urls_path:
        album_url = parsed_url._replace(path=album_url_path).geturl()
        albums_urls.append(album_url)
    return albums_urls


def _get_albums_urls_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    ol_tag = soup.find("ol", id="music-grid")
    if ol_tag is None:
        return list()
    hrefs = list()
    if ol_tag.get("data-client-items"):
        _log("Album URLs obtained from data attribute")
        hrefs = [i["page_url"] for i in json.loads(ol_tag["data-client-items"])]
    else:
        _log("Album URLs obtained from li href")
        hrefs = [li.find("a")["href"] for li in ol_tag.find_all("li")]
    r = list()
    for href in hrefs:
        # bandcamp.com now includes tracks in the band page, before it
        # was only albums, so we have to filter them out.
        if href.startswith("/album/"):
            r.append(href)
    _log("Loaded items count:", len(r))
    return r


def _get_tracks_from_html(html):
    tracks = list()
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        if script.has_attr("data-tralbum"):
            for track in json.loads(script["data-tralbum"])["trackinfo"]:
                if track["id"] and track["file"]:
                    info = {
                        "url": track["file"]["mp3-128"],
                        "title": track["title"],
                        "duration": track["duration"],
                    }
                    tracks.append(info)
    return tracks


def _fetch_url_content(url):
    _log("Fetch url:", url)
    content = http_session.get(url)
    return content


def _get_mp3_path(track):
    title = slugify(track["title"])
    mp3_path = os.path.join(track["album_path"], title + ".mp3")
    return mp3_path


class NoMP3ContentError(Exception):
    pass


def _get_mp3_file(track):
    if os.path.exists(track["path"]):
        cached = True
    else:
        cached = False
        with http_session.cache.cache_disabled():
            mp3_content = _fetch_url_content(track["url"])
            if mp3_content is None:
                raise NoMP3ContentError("Unable to get mp3 file")
        with open(track["path"], "bw") as song_file:
            song_file.write(mp3_content)
    return cached


def _get_url_type(url):
    # return the first part of the url's path
    # https://<bandname>.bandcamp.com/: music
    # https://<bandname>.bandcamp.com/music: music
    # https://<bandname>.bandcamp.com/album/<album-name>
    # https://<bandname>.bandcamp.com/track/<track-name>: track
    # https://.../stream/...: stream
    result = urlparse(url).path.strip("/").split("/")[0]
    return result


def _validate_url(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.split(".")
    if len(domain) < 3:
        raise ValueError("No band subdomain")
    if (domain[1], domain[2]) not in (("bandcamp", "com"), ("bcbits", "com")):
        raise ValueError("Not a bandcamp URL")
    if parsed_url.scheme != "https":
        raise ValueError("No https")
    return url
