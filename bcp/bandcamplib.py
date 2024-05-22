import json
import os
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests
import requests_cache
from bs4 import BeautifulSoup
from slugify import slugify

# suppres message alsoft messages because the bother me
os.environ["ALSOFT_LOGLEVEL"] = "0"

requests_cache.install_cache(".requests_cache")

_prev_call_time = datetime(year=2000, month=1, day=1)


def get_mp3s_from_url(url, track=None):
    """
    url can be:
    https://band.bandcamp.com
    https://band.bandcamp.com/music
    https://band.bandcamp.com/album/album-name
    https://band.bandcamp.com/track/track-name
    """
    url_type = _get_url_type(url)
    if not url_type:
        url_type = "music"
        url += url_type
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
        track["path"] = _get_mp3_path(track)
        yield track


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
    hrefs = [li.find("a")["href"] for li in ol_tag.find_all("li")]
    return hrefs


def _get_tracks_from_html(html):
    tracks = list()
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        if script.has_attr("data-tralbum"):
            for track in json.loads(script["data-tralbum"])["trackinfo"]:
                if track["id"]:
                    info = {
                        "url": track["file"]["mp3-128"],
                        "title": track["title"],
                        "duration": track["duration"],
                    }
                    tracks.append(info)
    return tracks


def _get_mp3_from_url(url):
    with requests_cache.disabled():
        return _fetch_url_content(url)


def _fetch_url_content(url):
    _throttle()
    try:
        return requests.get(url).content
    except Exception:
        raise StopIteration


def _throttle():
    global _prev_call_time
    _throttel_time = 5
    _time_diff = (datetime.now() - _prev_call_time).total_seconds()
    if _time_diff < _throttel_time:
        time.sleep(_throttel_time - _time_diff)
    _prev_call_time = datetime.now()


def _get_mp3_path(info):
    album_path = os.path.join("tracks", info["artist"], info["album"])
    title = slugify(info["title"])
    mp3_path = os.path.join(album_path, title + ".mp3")
    if os.path.exists(os.path.join(album_path, title + ".mp3")):
        return mp3_path
    if not os.path.isdir(album_path):
        os.makedirs(album_path)
    mp3_content = _get_mp3_from_url(info["url"])
    _write_mp3(mp3_content, mp3_path)
    return mp3_path


def _write_mp3(mp3_content, mp3_path):
    if not os.path.isfile(mp3_path):
        with open(mp3_path, "bw") as song_file:
            song_file.write(mp3_content)
    return mp3_path


def _get_url_type(url):
    # return the first part of the url's path
    # https://band.bandcamp.com/: music
    # https://band.bandcamp.com/music: music
    # https://band.bandcamp.com/album/album-name
    # https://band.bandcamp.com/track/track-name: track
    # https://t4.bcbits.../stream/...: stream

    result = urlparse(url).path.strip("/").split("/")[0]
    return result
