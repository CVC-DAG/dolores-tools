from __future__ import annotations

import re
import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List, NamedTuple

CLEAN_FOLDER = re.compile(r".+_CLEAN")


def main(args: Namespace) -> None:
    print(f"Root path: {args.set_path}")
    clean_version = args.set_path.parent / f"{args.set_path.name}_CLEAN"
    if clean_version.exists():
        print(f"\tRemoving:\t{clean_version}")
        shutil.rmtree(clean_version)
    for pack_folder in [x for x in args.set_path.glob("*") if x.is_dir()]:
        print(f"\tProcessing:\t{pack_folder}")
        svg_folder = pack_folder / "SVG"
        mxl_folder = pack_folder / "MUSICXML"

        if svg_folder.exists():
            shutil.rmtree(svg_folder)

        if mxl_folder.exists():
            shutil.rmtree(mxl_folder)


def setup() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        "set_path",
        type=Path,
        help="Root path to a weekly set",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main(setup())
