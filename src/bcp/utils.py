from fake_useragent import UserAgent
import tempfile
import os
import random
import ssl
import time
import urllib.request
from datetime import datetime
from tkinter import Tk

from platformdirs import user_data_dir

from .log import get_loger

DEBUG = os.environ.get("DEBUG", False)
_log = get_loger(__name__)

THROTTLE_TIME = (5, 15)
_prev_call_time = datetime(year=2000, month=1, day=1)

NAME = "patricie"
if DEBUG:
    USER_DATA_DIR = os.path.join(tempfile.gettempdir(), NAME)
else:
    USER_DATA_DIR = user_data_dir(NAME)
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)
_log("root directory:", USER_DATA_DIR)
TRACKS_DIR = os.path.join(USER_DATA_DIR, "tracks")
if not os.path.exists(TRACKS_DIR):
    os.makedirs(TRACKS_DIR)


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
    """I'm not using `requests` library because i get 403. i tried
    setting 'User-Agent' and other headers but it doesn't work.

    """

    def get(self, url):
        _log("get url:", url)
        request = urllib.request.Request(url)
        # for some band urls not using a user agent makes bandcamp redirect
        ua = UserAgent(platforms=['desktop'])
        request.add_header("User-Agent", ua.random)
        context = ssl.create_default_context(cafile="certifi/cacert.pem")
        # If a timeout is not set, it waits too long
        return urllib.request.urlopen(request, context=context, timeout=30)
