import json
import os
import time
from datetime import datetime
from urllib.parse import urlparse

import dotenv
from bs4 import BeautifulSoup
from platformdirs import user_data_dir
from slugify import slugify

from .log import get_loger
from .utils import Session

dotenv.load_dotenv()
_log = get_loger(__name__)


def _build_canonical_url(band_url, url):
    if band_url in url:
        return url
    return band_url + url


def validate_url(url):
    return url


def load_band(url):
    url_valid = validate_url(url)
    html = _session.get(url_valid).content
    soup = BeautifulSoup(html, "html.parser")
    band_url = soup.find("meta", property="og:url")["content"]
    name = soup.find("meta", property="og:title")["content"]
    for s in soup.find_all("script"):
        if s.get("data-tralbum"):
            url_d = json.loads(s["data-tralbum"])["url"]
            break
    r = {
        "name": name,
        "url": band_url,
        "url_discography": url_d,
    }
    r["albums"] = _get_albums(soup, band_url)
    return r


def _get_albums(soup, band_url):
    ol_tag = soup.find("ol", id="music-grid")
    if ol_tag is None:
        return list()
    _albums = list()
    albums = dict()
    if ol_tag.get("data-client-items"):
        _log("Album URLs obtained from data attribute")
        for i in json.loads(ol_tag["data-client-items"]):
            _albums.append((i["title"], i["page_url"])),
    else:
        _log("Album URLs obtained from li href")
        for li in ol_tag.find_all("li"):
            _albums.append((li.find("p").text.strip(), li.find("a")["href"])),
    for t, u in _albums:
        albums[t] = {"title": t, "url": _build_canonical_url(band_url, u)}

    _log("Lodaded items count:", len(albums))
    return albums


def load_album(url, band_url):
    html = _session.get(url).content
    soup = BeautifulSoup(html, "html.parser")
    for s in soup.find_all("script"):
        if s.get("data-tralbum"):
            d = json.loads(s["data-tralbum"])
            album = {
                "title": d["current"]["title"],
                "url": _build_canonical_url(band_url, d["url"]),
            }
            break
    tracks = dict()
    for t in d["trackinfo"]:
        tracks[t["title"]] = {
            "mp3_url": t["file"]["mp3-128"],
            "title": t["title"],
            "track_num": t["track_num"],
            "duration": t["track_num"],
            "url": _build_canonical_url(band_url, t["title_link"]),
            "artist": d["artist"],
            "album": album["title"],
        }

    album["tracks"] = tracks
    return album


def get_mp3_path(track):
    artist_path, album_path, track_path = _get_track_paths(track)
    if os.path.exists(track_path):
        cached = True
        _log("File exists:", track_path)
    else:
        cached = False
        _log("File doesn't exists:", track_path)
        if not os.path.isdir(album_path):
            os.makedirs(album_path)
        mp3_content = _get_mp3_from_url(track["mp3_url"])
        _write_mp3(mp3_content, track_path)
    return track_path, cached


def _get_track_paths(track):
    artist_path = os.path.join(_tracks_dir, slugify(track["artist"]))
    album_path = os.path.join(artist_path, slugify(track["album"]))
    track_path = os.path.join(album_path, slugify(track["title"]) + ".mp3")
    return artist_path, album_path, track_path


def _write_mp3(mp3_content, mp3_path):
    if not os.path.isfile(mp3_path):
        with open(mp3_path, "bw") as song_file:
            song_file.write(mp3_content)
    return mp3_path


THROTTLE_TIME = 5
ENVIRONMENT = os.environ.get("ENVIRONMENT", "")

# Suppress AlsoFT messages because they bother me
os.environ["ALSOFT_LOGLEVEL"] = "0"

_user_data_dir = user_data_dir("patricie")
_log("User data directory:", _user_data_dir)
_tracks_dir = os.path.join(_user_data_dir, "tracks")
_log("Traks directory:", _tracks_dir)
_environment = f"_{ENVIRONMENT}" if ENVIRONMENT else ""
_cache_name = os.path.join(_user_data_dir, "requests_cache" + _environment + ".sqlite")
_session = Session(_cache_name)
_log("Cache path:", _session.cache.cache_name)
_prev_call_time = datetime(year=2000, month=1, day=1)


def _get_mp3_from_url(url):
    with _session.cache_disabled():
        return _fetch_url_content(url)


def _fetch_url_content(url):
    if not _session.cache.contains(url=url):
        _log("Url not cached", url)
        _throttle()
    else:
        _log("Url cached", url)
    try:
        _log("Request get:", url)
        return _session.get(url).content
    except Exception as e:
        raise StopIteration(f"Error getting url {e}")


def _throttle():
    global _prev_call_time
    _time_diff = (datetime.now() - _prev_call_time).total_seconds()
    if _time_diff < THROTTLE_TIME:
        _throttle_for = THROTTLE_TIME - _time_diff
        _log("Throttle start:", _throttle_for)
        time.sleep(_throttle_for)
    _prev_call_time = datetime.now()


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
