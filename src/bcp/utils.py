import http.client
import os
import random
import ssl
import time
import urllib.request
from datetime import datetime
from tkinter import Tk
from urllib.error import HTTPError

from platformdirs import user_data_dir

from .log import get_loger

DEBUG = os.environ.get("DEBUG", False)
_log = get_loger(__name__)

THROTTLE_TIME = (5, 15)
_prev_call_time = datetime(year=2000, month=1, day=1)

USER_DATA_DIR = user_data_dir("patricie")
_log("Root directory:", USER_DATA_DIR)
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)


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

    def get(self, url):
        throttle()
        content = self._fetch(url)
        return content

    def _fetch(self, url):
        _log("Fetch url:", url)
        context = ssl.create_default_context(cafile="certifi/cacert.pem")
        content = None
        try:
            # If a timeout is not set, it waits too long
            with urllib.request.urlopen(url, context=context, timeout=30) as f:
                content = f.read()
        except (HTTPError, http.client.IncompleteRead, urllib.error.URLError, TimeoutError) as e:
            _log(f"failed to get url: {url}")
            _log(f"error: {e}")
        return content
