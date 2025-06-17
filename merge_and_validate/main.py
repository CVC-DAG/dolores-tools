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
    mxml_parser = ParserMXML(args.print_attributes, args.print_notes)
    mxml_parser.return_faulty()


def setup() -> Namespace:
    parser = ArgumentParser()
    
    parser.add_argument('--print_attributes', action='store_true', help='Print all attributes')
    parser.add_argument('--print_notes', action='store_true', help='Print all attributes')

    return parser.parse_args()


if __name__ == "__main__":
    main(setup())
