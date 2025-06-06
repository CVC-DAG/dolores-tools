from argparse import ArgumentParser
from pathlib import Path

from particcellas import cut_particcellas


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "dolores_path",
        help="Path to the folder storing DoLoReS user folders",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--cut_particcellas", action='store_true', help='Cut particcellas - MusicXMLs and images'
    )
    parser.add_argument(
        "--cut_monophonic", action='store_true', help='Cut monophonic scores - Images'
    )
    args = parser.parse_args()

    if args.dolores_path is None:
        args.dolores_path = Path(
            input("Please enter the path to the DoLoReS user folders: ")
        )
    if not args.cut_particcellas and not args.cut_monophonic:
        raise ValueError("You must specify at least one of --cut_particcellas or --cut_monophonic")

    if args.cut_particcellas:
        cut_particcellas()