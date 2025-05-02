from pathlib import Path
from argparse import ArgumentParser, Namespace
import shutil

import re

RE_CVC = re.compile(r".+\-cvc205\.(?:mscz|musicxml|svg)$")
RE_OLD = re.compile(r"^OLD_.+\.(?:mscz|musicxml|svg)$")


def setup() -> Namespace:
    parser = ArgumentParser(description="Extract and copy jpeg DoLoReS files.")
    parser.add_argument(
        "basepath",
        type=Path,
        help="Path to the root directory containing the DoLoReS files.",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Directory to save the jpegs.",
    )
    return parser.parse_args()


def main(args: Namespace) -> None:
    """
    Main function to extract data from the DoLoReS files.
    """
    if not (args.output.exists() and args.output.is_dir()):
        raise FileNotFoundError(
            f"Output directory {args.output} does not exist. Please create it first."
        )

    musescore_path = args.output / "MuseScore"
    musicxml_path = args.output / "MusicXML"
    svg_path = args.output / "SVG"

    for file in args.basepath.rglob("*.mscz"):
        if (
            file.is_file()
            and not RE_CVC.match(file.name)
            and not RE_OLD.match(file.name)
        ):
            destination = musescore_path / file.name
            shutil.copy(file, destination)

    for file in args.basepath.rglob("*.musicxml"):
        if (
            file.is_file()
            and not RE_CVC.match(file.name)
            and not RE_OLD.match(file.name)
        ):
            destination = musicxml_path / file.name
            shutil.copy(file, destination)

    for file in args.basepath.rglob("*.svg"):
        if (
            file.is_file()
            and not RE_CVC.match(file.name)
            and not RE_OLD.match(file.name)
        ):
            destination = svg_path / file.name
            shutil.copy(file, destination)


if __name__ == "__main__":
    main(setup())
