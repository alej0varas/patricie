import json
import os
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunsplit

import dotenv
from bs4 import BeautifulSoup
from slugify import slugify

from . import utils
from .log import get_loger

dotenv.load_dotenv()
_log = get_loger(__name__)


ENVIRONMENT = os.environ.get("ENVIRONMENT", "")

# Suppress AlsoFT messages because they bother me
os.environ["ALSOFT_LOGLEVEL"] = "0"

TRACKS_DIR = os.path.join(utils.USER_DATA_DIR, "tracks")
_log("Traks directory:", TRACKS_DIR)
if not os.path.exists(TRACKS_DIR):
    os.makedirs(TRACKS_DIR)
ENVIRONMENT_STR = f"_{ENVIRONMENT}" if ENVIRONMENT else ""

BANDCAMP_DOMAIN_SITE = "bandcamp.com"
BANDCAMP_DOMAIN_CDN = "bcbits.com"

http_session = utils.Session()


def get_band(url):
    r = dict()
    r["albums_urls"] = _get_albums_urls_from_url(url)
    r["albums"] = r["albums_urls"]
    return r


def get_album(url):
    r = dict()
    html = _fetch_url_content(url)
    tracks = _get_tracks_from_html(html)
    t = list()
    _log("Loaded tracks:", len(tracks))
    for track in tracks:
        parsed_url = urlparse(url)
        artist = parsed_url.netloc.split(".")[0]
        album = parsed_url.path.split("/")[2]
        album_path = os.path.join(TRACKS_DIR, artist, album)
        if not os.path.isdir(album_path):
            os.makedirs(album_path)
        _log("    ", track["title"])
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
    r["request_datetime"] = datetime.now()
    return r


def get_mp3(track):
    path = _get_mp3_path(track)
    mp3_content = None
    if not os.path.exists(path):
        mp3_content = _fetch_url_content(track["url"])
        with open(path, "bw") as song_file:
            song_file.write(mp3_content)
        track["cached"] = False
    else:
        track["cached"] = True
    track["path"] = path


def _get_albums_urls_from_url(url):
    albums_urls = list()
    music_html = _fetch_url_content(url)
    albums_urls_path = _get_albums_urls_from_html(music_html)

    parsed_url = urlparse(url)
    _log("Loaded albums", len(albums_urls_path))
    for album_url_path in albums_urls_path:
        album_url = parsed_url._replace(path=album_url_path).geturl()
        albums_urls.append(album_url)
        _log("    ", album_url)
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
    attempt, retries = (1, 3)
    while attempt <= retries:
        _log(f"Fetch url: {url} attempt: {attempt}")
        content = http_session.get(url)
        if content:
            break
        time.sleep(3 * attempt)
        attempt += 1
    else:
        raise NoMP3ContentError("Unable to download mp3")
    return content


def _get_mp3_path(track):
    title = slugify(track["title"])
    mp3_path = os.path.join(track["album_path"], title + ".mp3")
    return mp3_path


class NoMP3ContentError(Exception):
    pass


def validate_url(url):
    if not url:
        raise ValueError("Invalid url", url)
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if not domain:
        domain = f"{url}.{BANDCAMP_DOMAIN_SITE}"
    if domain.count(".") != 2:
        raise ValueError("Invalid domain", domain)
    if ".".join(domain.split(".")[-2:]) not in (
        BANDCAMP_DOMAIN_SITE,
        BANDCAMP_DOMAIN_CDN,
    ):
        raise ValueError("Not a bandcamp URL", domain)
    scheme = parsed_url.scheme
    if scheme != "https":
        scheme = "https"
    path = parsed_url.path
    if not path or path != "/music":
        path = "music"
    newurl = urlunsplit((scheme, domain, path, "", ""))
    return newurl


def request_expired(obj):
    if datetime.now() - obj["request_datetime"] > timedelta(minutes=10):
        return True
    return False
