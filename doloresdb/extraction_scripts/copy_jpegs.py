from pathlib import Path
from argparse import ArgumentParser, Namespace
import shutil


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

    for file in args.basepath.rglob("*.jpg"):
        if file.is_file():
            destination = args.output / file.name
            shutil.copy(file, destination)


if __name__ == "__main__":
    main(setup())
