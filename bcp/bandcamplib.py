import json
import os
from urllib.parse import urlparse

import requests
import requests_cache
from bs4 import BeautifulSoup
from slugify import slugify


requests_cache.install_cache(".requests_cache")


def get_mp3s_from_url(url, info=None):
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
    if url_type == "album":
        album_html = requests.get(url).content
        tracks = _get_tracks_from_html(album_html)
        for track in tracks:
            parsed_url = urlparse(url)
            artist = parsed_url.netloc.split(".")[0]
            album = parsed_url.path.split("/")[2]
            yield from get_mp3s_from_url(
                track["url"],
                {"artist": artist, "album": album, "title": track["title"]},
            )
    if url_type == "track":
        track_html = requests.get(url).content
        tracks = _get_tracks_from_html(track_html)
        for track in tracks_urls:
            yield from get_mp3s_from_url(track["url"], info)
    if url_type == "stream":
        mp3_content = _get_mp3_from_url(url)
        yield _get_mp3_path(mp3_content, info)


def _get_albums_urls_from_url(url):
    albums_urls = list()
    music_html = requests.get(url).content
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
                    tracks.append(
                        {"url": track["file"]["mp3-128"], "title": track["title"]}
                    )
    return tracks


def _get_mp3_from_url(url):
    return requests.get(url).content


def _get_mp3_path(mp3_content, info):
    album_path = os.path.join("tracks", info["artist"], info["album"])
    title = slugify(info["title"])
    if not os.path.isdir(album_path):
        os.makedirs(album_path)
    song_path = os.path.join(album_path, title + ".mp3")
    if not os.path.isfile(song_path):
        with open(song_path, "bw") as song_file:
            song_file.write(mp3_content)
    return song_path


def _get_url_type(url):
    # return the first part of the url's path
    # https://pulverised.bandcamp.com/: music
    # https://pulverised.bandcamp.com/music: music
    # https://pulverised.bandcamp.com/album/eleventh-formulae: album
    # https://pulverised.bandcamp.com/track/mors-gloria-est: track
    # https://t4.bcbits.../stream/...: stream

    result = urlparse(url).path.strip("/").split("/")[0]
    return result
