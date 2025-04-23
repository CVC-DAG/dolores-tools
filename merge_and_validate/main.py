"""Merge and validate works into a single, joint score."""

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List
from parse_musicxml import ParserMXML

class Work:
    def __init__(
        self,
        work_name: str,
        musicxml_list: List[Path],
    ) -> None:
        self._musicxml_list = musicxml_list
        self._work_name = work_name


class WorkCatalogue:
    def __init__(self) -> None:
        ...


def main(args: Namespace) -> None:
    mxml_parser = ParserMXML(args.dolores_path, args.debug_prints)
    mxml_parser.return_faulty()


def setup() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        "--dolores_path",
        type=Path,
        help="For now it will be a CVC.S01.P01 type folder, in the future it will be the " \
        "general Dolores folder",
    )

    parser.add_argument('--debug_prints', action='store_true', help='Print all attributes')

    return parser.parse_args()


if __name__ == "__main__":
    main(setup())
