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
    mxml_parser = ParserMXML(args.print_attributes, args.print_notes, args.time_equivalent, args.solve_error_1, args.solve_error_2)
    mxml_parser.return_faulty()


def setup() -> Namespace:
    parser = ArgumentParser()
    
    parser.add_argument('--print_attributes', action='store_true', help='Print all attributes')
    parser.add_argument('--print_notes', action='store_true', help='Print all attributes')
    parser.add_argument('--time_equivalent', action='store_true', help='Do NOT count errors that consist of two equivalent time signatures')
    parser.add_argument('--solve_error_1', action='store_true', help='Sometimes attributes get duplicated, first one with print-object=no and the second one with print-object=yes. This removes the second attribute and changes the first one to print-object=yes')
    parser.add_argument('--solve_error_2', action='store_true', help='Some lines get saved with the wrong clef/key/time and print-object=no while the before and after lines are correct. This changes this middle line to the correct clef/key/time')
    return parser.parse_args()


if __name__ == "__main__":
    main(setup())
