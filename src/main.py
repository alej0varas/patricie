# for pyinstall as explained here:
# https://api.arcade.academy/en/development/tutorials/bundling_with_pyinstaller/index.html#handling-data-files
import os
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    os.chdir(sys._MEIPASS)
# end for pyinstall

import argparse

from bcp.gui import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
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
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Use fullscreen. Default is true",
    )
    args = parser.parse_args()
    main(fullscreen=args.fullscreen, skip_downloaded=args.skip_downloaded)
