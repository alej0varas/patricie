import os


DEBUG = os.environ.get("DEBUG", False)


class Log:
    def __call__(self, *args):
        if DEBUG:
            print(self.caller, *args)

    def __init__(self, caller):
        self.caller = caller


def get_loger(caller):
    return Log(caller)
