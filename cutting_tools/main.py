from argparse import ArgumentParser
from pathlib import Path

from cutter import cut_scores

if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "--cut_particcellas", action='store_true', help='Cut particcellas - MusicXMLs and images'
    )
    parser.add_argument(
        "--cut_monophonic", action='store_true', help='Cut monophonic scores - Images'
    )
    args = parser.parse_args()

    if not args.cut_particcellas and not args.cut_monophonic:
        raise ValueError("You must specify at least one of --cut_particcellas or --cut_monophonic")

    cut_scores(cut_particcellas=args.cut_particcellas, cut_monophonic=args.cut_monophonic)