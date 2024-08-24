import argparse
import os
import sys

# for pyinstall as explained here:
# https://api.arcade.academy/en/development/tutorials/bundling_with_pyinstaller/index.html#handling-data-files
_sha = ""
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    os.chdir(sys._MEIPASS)
    # load constants created at build time
    import _constants

    _sha = _constants.COMMIT_SHA
os.environ["COMMIT_SHA"] = _sha
# end for pyinstall

# this import must be placed after os.chdir
from bcp.gui import main  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="Optional band url")

    parser.add_argument(
        "-s",
        "--skip-downloaded",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip songs that have already been downloaded. Default is true",
    )
    parser.add_argument(
        "-f",
        "--fullscreen",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Use fullscreen. Default is false",
    )
    args = parser.parse_args()
    main(fullscreen=args.fullscreen, url=args.url, skip_downloaded=args.skip_downloaded)
