import http.client
import os
import random
import sqlite3
import ssl
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from tkinter import Tk
from urllib.error import HTTPError

from .log import get_loger

DEBUG = os.environ.get("DEBUG", False)

_log = get_loger(__name__)
THROTTLE_TIME = (5, 15)
_prev_call_time = datetime(year=2000, month=1, day=1)


def get_clipboad_content():
    a = Tk()
    a.withdraw()
    t = a.clipboard_get()
    a.quit()
    return t


def throttle():
    if DEBUG:
        return
    global _prev_call_time
    _time_diff = (datetime.now() - _prev_call_time).total_seconds()
    _throttle_for = random.randint(*THROTTLE_TIME) - _time_diff
    if _throttle_for >= 0:
        _log("Throttle start: {:.2f}".format(_throttle_for))
        time.sleep(_throttle_for)
    _prev_call_time = datetime.now()


class Session:
    """HTTP session like object created because using `requests` fails. I was not able to find the reason."""

    def __init__(self, cache_name):
        self.cache = HTTPCache(cache_name)

    def get(self, url):
        content = self.cache.get(url)
        if not content:
            throttle()
            content = self._fetch(url)
            self.cache.set(url, content)
        return content

    def _fetch(self, url):
        _log("Fetch url:", url)
        context = ssl.create_default_context(cafile="certifi/cacert.pem")
        content = None
        try:
            with urllib.request.urlopen(url, context=context) as f:
                content = f.read()
        except HTTPError as e:
            _log(f"failed to get url: {url}")
            _log(f"error: {e.status}")
        except http.client.IncompleteRead as e:
            _log(f"failed to get url: {url}")
            _log(f"error: {e}")
        return content


class HTTPCache:
    def __init__(self, cache_name, enabled=False):
        self.enabled = DEBUG
        self.cache_name = cache_name
        self.conn = sqlite3.connect(self.cache_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS cache (url TEXT PRIMARY KEY, content TEXT)"""
        )
        self.conn.commit()
        self.conn.close()

    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True

    def get(self, url):
        if not self.enabled:
            return None
        self.conn = sqlite3.connect(self.cache_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT content FROM cache WHERE url=?", (url,))
        result = self.cursor.fetchone()
        self.conn.close()
        if result:
            _log("url cached:", url)
            return result[0]

    def set(self, url, content):
        if not self.enabled:
            return
        self.conn = sqlite3.connect(self.cache_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            "INSERT INTO cache (url, content) VALUES (?, ?)", (url, content)
        )
        self.conn.commit()
        self.conn.close()

    @contextmanager
    def cache_disabled(self, *args, **kwds):
        try:
            self.disable()
            yield self
        finally:
            self.enable()
