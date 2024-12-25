import os

import dotenv

dotenv.load_dotenv()

DEBUG = os.environ.get("DEBUG", False)


class Log:
    def __call__(self, *args):
        from . import utils

        path = os.path.join(utils.USER_DATA_DIR, ".log.txt")
        with open(path, "a") as f:
            match args:
                case int():
                    a = str(args)
                case list() | tuple():
                    a = "".join(map(str, args))
                case _:
                    a = args
            f.write(f"{self.caller} {a}\n")

    def __init__(self, caller):
        self.caller = caller


def get_loger(caller):
    return Log(caller)
