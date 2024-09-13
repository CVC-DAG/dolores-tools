import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path

CURRENT_PATH = Path(__file__).parent


def main(args: Namespace) -> None:
    with open(args.mxml_path, "r") as f_in:
        mxml_text = f_in.read()

    if args.output != CURRENT_PATH:
        shutil.copy(
            CURRENT_PATH / "mxml_decorator.js", args.output / "mxml_decorator.js"
        )

    output_contents = f"""
    <html>
        <script src="mxml_decorator.js">
        </script> 
        <body class="mxml_text">
            {mxml_text}
        <body>
    </html>
    """

    with open(args.output / "index.html", "w") as f_out:
        f_out.write(output_contents)


def setup() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        "mxml_path",
        type=Path,
        help="Path to a musicxml file",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Folder in which to store the generated html file.",
        default=CURRENT_PATH,
    )

    return parser.parse_args()


if __name__ == "__main__":
    main(setup())
