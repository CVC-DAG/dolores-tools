"""Merge and validate works into a single, joint score."""

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List

from lxml import etree
from lxml.etree import _Element as Element


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
    ...


def setup() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        "--dolores_path",
        type=Path,
        help="Root dolores path",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main(setup())


class Attributes:
    def __init__(self) -> None:
        self.lxml_object
        self.clef
        self.timesig
        self.key
