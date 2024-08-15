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

_user_data_dir = user_data_dir("patricie")
_log("User data directory:", _user_data_dir)
_tracks_dir = os.path.join(_user_data_dir, "tracks")
_log("Traks directory:", _tracks_dir)
_environment = f"_{ENVIRONMENT}" if ENVIRONMENT else ""
_cache_name = os.path.join(_user_data_dir, "requests_cache" + _environment + ".sqlite")
_session = utils.Session(_cache_name)
_log("Cache path:", _session.cache.cache_name)


def get_mp3s_from_url(url, track=None):
    # For supported urls see readme.
    assert _validate_url(url)
    url_type = _get_url_type(url)
    if not url_type:
        url_type = "music"
        url += "/" + url_type
    if url_type == "music":
        albums_urls = _get_albums_urls_from_url(url)
        for album_url in albums_urls:
            yield from get_mp3s_from_url(album_url)
    if url_type in ["album", "track"]:
        html = _fetch_url_content(url)
        tracks = _get_tracks_from_html(html)
        for track in tracks:
            parsed_url = urlparse(url)
            # FIX: track's url will have an album with the name of the track
            artist = parsed_url.netloc.split(".")[0]
            album = parsed_url.path.split("/")[2]
            track.update({"artist": artist, "album": album, "title": track["title"]})
            yield from get_mp3s_from_url(
                track["url"],
                track,
            )
    if url_type == "stream":
        track["path"], cached = _get_mp3_path(track)
        yield track, cached


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
        for i in json.loads(ol_tag["data-client-items"]):
            hrefs.append(i["page_url"])
    else:
        _log("Album URLs obtained from li href")
        hrefs = [li.find("a")["href"] for li in ol_tag.find_all("li")]
    _log("Lodaded items count:", len(hrefs))
    return hrefs


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


def _get_mp3_from_url(url):
    with _session.cache_disabled():
        return _fetch_url_content(url)


def _fetch_url_content(url):
    if not _session.cache.contains(url=url):
        _log("Url not cached", url)
        utils.throttle()
    else:
        _log("Url cached", url)
    try:
        _log("Request get:", url)
        content = _session.get(url).content
    except Exception as e:
        raise StopIteration(f"Error getting url {e}")
    else:
        if not content:
            raise ValueError("The url can't be fetched or the response is invalid")
    return content


def _get_mp3_path(info):
    album_path = os.path.join(_tracks_dir, info["artist"], info["album"])
    title = slugify(info["title"])
    mp3_path = os.path.join(album_path, title + ".mp3")
    if os.path.exists(os.path.join(album_path, title + ".mp3")):
        cached = True
        _log("File exists:", mp3_path)
    else:
        cached = False
        if not os.path.isdir(album_path):
            os.makedirs(album_path)
        mp3_content = _get_mp3_from_url(info["url"])
        _write_mp3(mp3_content, mp3_path)
    return mp3_path, cached


def _write_mp3(mp3_content, mp3_path):
    if not os.path.isfile(mp3_path):
        with open(mp3_path, "bw") as song_file:
            song_file.write(mp3_content)
    return mp3_path


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
