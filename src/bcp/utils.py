import sqlite3
import ssl
import threading
import urllib.request
from contextlib import contextmanager
from tkinter import Tk


def get_clipboad_content():
    a = Tk()
    a.withdraw()
    t = a.clipboard_get()
    a.quit()
    return t


def threaded(func):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()

    return wrapper


class Session:
    """HTTP session like object created because using `requests` fails. I was not able to find the reason."""

    def __init__(self, cache_name):
        self.cache = HTTPCache(cache_name)

    def get(self, url):
        if self.cache.enabled:
            content = self.cache.get(url)
            if not content:
                content = self._fetch(url)
                self.cache.set(url, content)
        else:
            content = self._fetch(url)
        self.content = content
        return self

    def _fetch(self, url):
        context = ssl.create_default_context(cafile="certifi/cacert.pem")
        with urllib.request.urlopen(url, context=context) as f:
            content = f.read()
        return content

    @contextmanager
    def cache_disabled(self, *args, **kwds):
        try:
            self.cache.disable()
            yield self
        finally:
            self.cache.enable()


class HTTPCache:
    def __init__(self, cache_name):
        self.enabled = True
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

    def contains(self, url):
        self.conn = sqlite3.connect(self.cache_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT content FROM cache WHERE url=?", (url,))
        result = self.cursor.fetchone()
        self.conn.close()
        return result

    def get(self, url):
        result = self.contains(url)
        if result:
            return result[0]

    def set(self, url, content):
        self.conn = sqlite3.connect(self.cache_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            "INSERT INTO cache (url, content) VALUES (?, ?)", (url, content)
        )
        self.conn.commit()
        self.conn.close()
