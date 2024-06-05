import requests
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


def load_band(url):
    url_valid = validate_url(url)
    r = fetch_band_info(url_valid)
    return r


def validate_url(url):
    return url


def fetch_band_info(url):
    html = requests.get(url).content
    r = extract_band_info(html)
    return r


def extract_band_info(html):
    soup = BeautifulSoup(html, "html.parser")
    url = soup.find("meta", property="og:url")["content"]
    name = soup.find("meta", property="og:title")["content"]
    for s in soup.find_all("script"):
        if s.get("data-tralbum"):
            url_d = json.loads(s["data-tralbum"])["url"]
            break
    r = {
        "name": name,
        "url": url,
        "url_discography": url_d,
        "albums": get_albums_info(html, name),
    }
    return r


def get_albums_info(html, artist):
    soup = BeautifulSoup(html, "html.parser")
    ol_tag = soup.find("ol", id="music-grid")
    r = list()
    # if ol_tag is None:
    #    return list()
    data_items = ol_tag.get("data-client-items")
    if data_items:
        for item in json.loads(ol_tag["data-client-items"]):
            item.pop("art_id")
            item.pop("type")
            r.append(item)
    else:
        for li in ol_tag.find_all("li"):
            if li.find("span"):
                _artist = li.find("span").text.strip()
            else:
                _artist = artist
            r.append(
                {
                    "artist": _artist,
                    "band_id": int(li["data-band-id"]),
                    "id": int(li["data-item-id"].split("-")[1]),
                    "page_url": li.find("a")["href"],
                    "title": li.find("p").contents[0].strip(),
                }
            )
    return r


def load_album(url):
    r = fetch_album_info(url)
    return r


def fetch_album_info(url):
    html = requests.get(url).content
    album = extract_album_info(html)
    print(album)
    tracks = _get_tracks_from_html(html)
    # mp3_path, cached = _get_mp3_path(track)
    parsed_url = urlparse(url)
    artist_slug = parsed_url.netloc.split(".")[0]
    album_slug = parsed_url.path.split("/")[2]
    for track in tracks:
        track["path"], cached = _get_mp3_path(
            track["title"], artist_slug, album_slug, track["mp3_url"]
        )
    r = {
        "name": album["title"],
        "tracks": tracks,
    }
    return r


def extract_album_info(html):
    soup = BeautifulSoup(html, "html.parser")
    for s in soup.find_all("script"):
        if s.get("data-tralbum"):
            return json.loads(s["data-tralbum"])["current"]


def _get_tracks_from_html(html):
    tracks = list()
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        if script.has_attr("data-tralbum"):
            for track in json.loads(script["data-tralbum"])["trackinfo"]:
                if track["id"] and track["file"]:
                    info = {
                        "mp3_url": track["file"]["mp3-128"],
                        "title": track["title"],
                        "duration": track["duration"],
                    }
                    tracks.append(info)
    return tracks


def _get_mp3_path(title, artist_slug, album_slug, url):
    album_path = os.path.join(_tracks_dir, artist_slug, album_slug)
    title = slugify(title)
    mp3_path = os.path.join(album_path, title + ".mp3")
    if os.path.exists(os.path.join(album_path, title + ".mp3")):
        cached = True
        _log("File exists:", mp3_path)
    else:
        cached = False
        if not os.path.isdir(album_path):
            os.makedirs(album_path)
        mp3_content = _get_mp3_from_url(url)
        _write_mp3(mp3_content, mp3_path)
    return mp3_path, cached


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


def _get_albums_urls_from_url(url):
    albums_urls = list()
    music_html = _fetch_url_content(url)
    albums_urls_path = _get_albums_urls_from_html(music_html)

    parsed_url = urlparse(url)
    for album_url_path in albums_urls_path:
        album_url = parsed_url._replace(path=album_url_path).geturl()
        albums_urls.append(album_url)
    return albums_urls


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
