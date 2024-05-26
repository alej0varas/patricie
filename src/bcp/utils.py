import threading
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
