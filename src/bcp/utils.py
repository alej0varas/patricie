import json
import os
import random
import ssl
import tempfile
import threading
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from tkinter import Tk

from fake_useragent import UserAgent
from platformdirs import user_data_dir

from .log import get_loger

# Suppress AlsoFT messages because they bother me
os.environ["ALSOFT_LOGLEVEL"] = "0"

DEBUG = os.environ.get("DEBUG", False)
_log = get_loger(__name__)

THROTTLE_TIME = (5, 15)
_prev_call_time = datetime(year=2000, month=1, day=1)

NAME = "patricie"
if DEBUG:
    USER_DATA_DIR = Path(tempfile.gettempdir()) / NAME
else:
    USER_DATA_DIR = Path(user_data_dir()) / NAME
if not USER_DATA_DIR.exists():
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
_log("user data path:", USER_DATA_DIR)

CACHE_PATH = USER_DATA_DIR / "http_cache.json"
_log("cache path:", CACHE_PATH)

STORAGE_PATH = USER_DATA_DIR / "storage.json"
_log("storage path:", STORAGE_PATH)


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


class CacheableResponse:
    """We want to serialize the content of http.client.HTTPResponse
    object but `read` can be called only once, making the content
    unavailable in the response object to be used later. This class
    allows us to cache the request and return a compatible response
    instance

    """

    def __init__(self):
        self._original_url = None
        self._returned_url = None
        self._content = None

    def from_response(self, url, response):
        self._original_url = url
        self._returned_url = response.geturl()
        self._content = response.read().decode("utf-8")
        return self

    def from_cache(self, entry):
        self._original_url = entry["original_url"]
        self._returned_url = entry["returned_url"]
        self._content = entry["content"]
        return self

    def serialize(self):
        return {
            "original_url": self._original_url,
            "returned_url": self._returned_url,
            "content": self._content,
        }

    def geturl(self):
        return self._returned_url

    def read(self):
        return self._content.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class HTTPSession:
    """I'm not using `requests` library because i get 403. i tried
    setting 'User-Agent' and other headers but it doesn't work.

    """

    def __init__(self):
        self.cache = HTTPChache(CACHE_PATH)

    def get(self, url):
        _log(f"http session get: {url}")
        response = self.cache.get(url)
        if not response:
            throttle()
            request = urllib.request.Request(url)
            # for some band urls not using a user agent makes bandcamp redirect
            ua = UserAgent(platforms=["desktop"])
            request.add_header("User-Agent", ua.random)
            context = ssl.create_default_context(cafile="certifi/cacert.pem")
            # If a timeout is not set, it waits too long
            r = urllib.request.urlopen(request, context=context, timeout=30)
            response = self.cache.set(url, r)
        return response


class HTTPChache:
    def __init__(self, path):
        self.path = Path(path)
        self.items = dict()
        self.disabled = False
        if not self.path.exists():
            _log("http cache file created")
            self.path.touch()
            self._write()
        else:
            _log("http cache file exists")
            try:
                self._read()
            except json.decoder.JSONDecodeError as e:
                _log(f"http cache file overwriten {e}")
                self._write()
                self.__init__(path)

    def set(self, key, response):
        _log(f"http cache set {key}")
        if self.disabled:
            _log("    disabled")
            return response
        cacheable = CacheableResponse().from_response(key, response)
        self.items[key] = cacheable.serialize()
        self._write()
        return cacheable

    def get(self, key):
        _log(f"http cache get {key}")
        r = None
        if self.disabled:
            return r
        self._read()
        value = self.items.get(key)
        if value:
            r = CacheableResponse().from_cache(value)
            _log(f"    hit {r.geturl()}")
        return r

    def invalidate(self, url):
        _log(f"http cache invalidate {url}")
        self._read()
        if self.items.get(url):
            del self.items[url]
            self._write()

    def _write(self):
        _log("    write")
        with open(CACHE_PATH, "w") as f:
            f.write(json.dumps(self.items))

    def _read(self):
        with open(CACHE_PATH, "r") as f:
            self.items = json.loads(f.read())
        _log(f"    read {len(self.items)}")

    @contextmanager
    def disable(self):
        try:
            self.disabled = True
            yield
        finally:
            self.disabled = False


class BackgroundTaskRunner(threading.Thread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.working = False
        self.tasks = list()
        self.error = False

    def run(self):
        while self.running:
            if not self.working:
                self.do_task()
            time.sleep(0.01)

    def task(self, func):
        def wrapper(*args, **kwargs):
            self.error = False
            self.tasks.insert(0, (func, args))

        return wrapper

    def do_task(self):
        if not self.tasks:
            return
        task_to_run, task_to_run_args = self.tasks.pop()
        self.working = True
        try:
            task_to_run(*task_to_run_args)
        except StopCurrentTaskExeption as e:
            _log(f"task stopped {e}")
        # except Exception as e:
        #     _log("EXCEPTION CATCHED BY RUNNER", e)
        #     self.error = True
        #     self.tasks.clear()
        self.working = False


class Storage:
    """Does:

    - Read and write player related information to a file. The file
    will contain information about bands, albums and tracks.

    - Serialize to json and deserialize to a dict the information.

    """

    def __init__(self, serializer):
        self.path = STORAGE_PATH
        self.serializer = serializer
        self.content_as_dict = dict()
        if not self.path.exists():
            self.path.touch()
            self.write()
        self.content_as_dict = dict()
        try:
            self.content_as_dict = self.read()
        except json.decoder.JSONDecodeError as e:
            _log(f"storage corrupted {e}")
            self.write()

    def read(self):
        with open(self.path, "r") as f:
            return json.load(f)

    def write(self):
        with open(self.path, "w") as f:
            json.dump(self.content_as_dict, f, default=self.serializer)

    def update(self, items):
        self.content_as_dict = items
        self.write()

    @property
    def as_dict(self):
        self.content_as_dict = self.read()
        return self.content_as_dict


class StopCurrentTaskExeption(Exception):
    pass
