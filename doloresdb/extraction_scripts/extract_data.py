from pathlib import Path
from argparse import ArgumentParser, Namespace


def setup() -> Namespace:
    parser = ArgumentParser(description="Extract data from the DoLoReS files.")
    parser.add_argument(
        "basepath",
        type=Path,
        help="Path to the root directory containing the DoLoReS files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("extracted"),
        help="Directory to save the extracted files.",
    )
    return parser.parse_args()


def main(args: Namespace) -> None:
    """
    Main function to extract data from the DoLoReS files.
    """
    args.output.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main(setup())
