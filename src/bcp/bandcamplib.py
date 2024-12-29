import json
import os
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunsplit

from bs4 import BeautifulSoup

from . import utils
from .log import get_loger

_log = get_loger(__name__)

# Suppress AlsoFT messages because they bother me
os.environ["ALSOFT_LOGLEVEL"] = "0"

BANDCAMP_DOMAIN_SITE = "bandcamp.com"
BANDCAMP_DOMAIN_CDN = "bcbits.com"

http_session = utils.Session()


def get_band(url):
    html = _fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")
    albums_urls = _to_full_url(_get_albums_urls(html), url)
    name = soup.find("meta", property="og:title").get("content")
    r = {
        "name": name,
        "url": soup.find("meta", property="og:url").get("content"),
        "description": soup.find("meta", property="og:description").get("content"),
        "albums_urls": albums_urls,
    }
    return r


def get_album(url):
    html = _fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")
    tracks_urls = _to_full_url(_get_tracks_urls(soup), url)
    name = soup.find(id="name-section").h2.text.strip()
    r = {"name": name, "tracks_urls": tracks_urls}
    return r


def _to_full_url(paths, base):
    r = list()
    parsed_url = urlparse(base)
    for path in paths:
        r.append(parsed_url._replace(path=path).geturl())
    return r


def get_track(url):
    html = _fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")
    data = json.loads(soup.find("script", attrs={"data-tralbum": True})["data-tralbum"])
    r = {
        "url": data["url"],
        "artist": data["artist"],
        "file": data["trackinfo"][0]["file"]["mp3-128"],
        "title": data["trackinfo"][0]["title"],
        "duration": data["trackinfo"][0]["duration"],
        "lyrics": data["trackinfo"][0]["lyrics"],
    }
    return r


def get_mp3(url):
    # TODO: this could be done on the client now?
    with http_session.cache.disable():
        content = _fetch_url(url)
    return content


def _get_albums_urls(html):
    # bandcamp.com now includes tracks in the band page, before it
    # was only albums, so we have to filter them out.
    def is_album(href):
        return href and href.startswith("/album/")

    soup = BeautifulSoup(html, "html.parser")
    r = [i["href"] for i in soup.find_all(href=is_album)]
    return r


def _get_tracks_urls(soup):
    tracks = list()
    for div in soup.find_all("div", "title"):
        tracks.append(div.find("a")["href"])
    return tracks


def _fetch_url(url):
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
    except HTTPError as e:
        code = e.file.code
        if 400 <= code < 500:
            raise DownloadNoRetryError("Unavailable url ({code})")
        raise DownloadRetryError(f"Internet connection or server issue ({code})")
    except (IncompleteRead, URLError, TimeoutError) as e:
        raise DownloadRetryError(f"Internet connection or server issue ({e})")
    return content


def validate_url(url):
    if not url:
        raise ValueError("Invalid url", url)
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if not domain:
        domain = f"{url}.{BANDCAMP_DOMAIN_SITE}"
    if domain.count(".") != 2:
        raise ValueError("Invalid domain", domain)
    if ".".join(domain.split(".")[-2:]) != BANDCAMP_DOMAIN_SITE:
        raise ValueError("Not a bandcamp URL", domain)
    scheme = parsed_url.scheme
    if scheme != "https":
        scheme = "https"
    path = parsed_url.path
    if not path or path != "/music":
        path = "music"
    newurl = urlunsplit((scheme, domain, path, "", ""))
    return newurl


class DownloadRetryError(Exception):
    pass


class DownloadNoRetryError(Exception):
    pass
