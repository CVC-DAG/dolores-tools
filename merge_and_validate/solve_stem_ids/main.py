"""Merge and validate works into a single, joint score."""

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List
from id_solver import IdSolver

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
    id_solver = IdSolver(args.categories_to_check, args.list_affected_jsons)

    if args.list_affected_jsons:
        id_solver.identify_affected_jsons()



def setup() -> Namespace:
    parser = ArgumentParser()
    
    parser.add_argument('categories_to_check', nargs='+', type=str, help='A list of strings containing the categories to check (stem, flag, ...)')
    parser.add_argument('--list_affected_jsons', action='store_true', help='Creates a json file with a list of the affected alignment files (jsons)')
    
    return parser.parse_args()




if __name__ == "__main__":
    main(setup())
