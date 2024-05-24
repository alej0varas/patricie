from bcp.player import main

import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Band, album or track url.")
    parser.add_argument(
        "-s",
        "--skip-downloaded",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip songs that have already been downloaded.",
    )
    parser.add_argument(
        "-f",
        "--fullscreen",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Use fullscreen.",
    )
    args = parser.parse_args()
    main(args.url, fullscreen=args.fullscreen, skip_downloaded=args.skip_downloaded)
