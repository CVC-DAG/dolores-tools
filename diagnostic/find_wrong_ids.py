from argparse import Namespace, ArgumentParser
from pathlib import Path
from typing import Dict, Any, List
from tqdm.auto import tqdm

import json
import re


class AlignmentVerifier:
    REGEXES: Dict[int, re.Pattern] = {
        1: re.compile(
            r"^line\d+:(?:chord\.\w+|\w+)\.articulation\d+\.accent$"
        ),  # accent
        2: re.compile(r"^line\d+:(?:chord\.\w+|\w+)\.accidental\d*$"),  # accidental
        3: re.compile(r"^line\d+:\w+\.(\w+\.)?barline_tok\d+$"),  # barline
        4: re.compile(r"^line\d+:beam\d+$"),  # beam
        5: re.compile(r"^line\d+:(?:chord\.\w+|\w+).bracket$"),  # bracket
        6: re.compile(
            r"^line\d+:(?:chord\.\w+|\w+)\.articulation\d+\.caesura$"
        ),  # caesura
        7: re.compile(r"^line\d+:clef\d+(_\d+)?$"),  # clef
        # 8: re.compile(r"^line\d+:clef\d+_\d+$"),  # coda (not used)
        9: re.compile(r"^line\d+:(?:chord\.\w+|\w+)\.dot\d+$"),  # dots
        # 10: re.compile(r"^line\d+:clef\d+_\d+$"),  # dynamics (not used)
        # 11: re.compile(),  # ending (not used)
        12: re.compile(r"^line\d+:fermata\d+$"),  # fermata
        13: re.compile(r"^line\d+:(?:chord\.\w+|\w+)\.(?:stem\.)?flag$"),  # flag
        # 14: re.compile(),  # glissando
        # 15: re.compile(),  # mordent
        # 16: re.compile(),  # turn
        # 17: re.compile(),  # measure_repeat
        # 18: re.compile(),  # rest (repeated)
        19: re.compile(r"^line\d+:(?:chord\.\w+|\w+)\.notehead(?:\d+)?$"),  # notehead
        # 20: re.compile(),  # number
        # 21: re.compile(),  # octave_shift
        22: re.compile(r"^line\d+:rest\d+$"),  # rest
        # 23: re.compile(),  # schleifer
        # 24: re.compile(),  # segno
        # 25: re.compile(),  # slur
        # 26: re.compile(),  # staccato
        27: re.compile(
            r"^line\d+:(?:chord\.\w+|\w+)\.articulation\d+\.staccato$"
        ),  # staccato
        28: re.compile(r"^line\d+:(?:chord\.\w+|\w+)\.stem$"),  # stem
        # 29: re.compile(),  # accent (repeated)
        # 30: re.compile(),  # tenuto
        # 31: re.compile(),  # tie
        32: re.compile(r"^line\d+:time\d+_\d+(_\d+)?$"),  # timesig
        33: re.compile(
            r"^line\d+:(?:chord\.\w+|\w+)\.tremolo_single\.line\d+$"
        ),  # tremolo line
        34: re.compile(
            r"^line\d+:(?:chord\.\w+|\w+)\.tremolo_beam\.line\d+$"
        ),  # tremolo beam
        # 35: re.compile(),  # trill
        # 36: re.compile(),  # turn (repeated)
        # 37: re.compile(),  # wedge
        # 38: re.compile(),  # repeat
    }

    def __init__(self) -> None:
        self.wrong_files = {}

    def check_file(self, data: Dict[str, Any], fname: str) -> None:
        for ii, ann in enumerate(data["annotations"]):
            if "categoryId" in ann and ann["categoryId"] in self.REGEXES:
                regex = self.REGEXES[ann["categoryId"]]
                if not regex.match(ann["id"]):
                    error = {
                        "annotation": ii,
                        "category": ann["categoryId"],
                        "produced": ann["id"],
                        "should_have": regex.pattern,
                    }
                    if fname not in self.wrong_files:
                        self.wrong_files[fname] = {
                            "fname": fname,
                            "project_date": data["info"]["date_created"],
                            "errors": [error],
                        }
                    else:
                        self.wrong_files[fname]["errors"].append(error)


def main(args: Namespace) -> None:
    verifier = AlignmentVerifier()

    for file in tqdm(args.basepath.glob("*.json")):
        if file.is_file():
            with open(file, "r") as f:
                data = json.load(f)
                verifier.check_file(data, file.name)

    with open(args.output_fname, "w") as f_out:
        json.dump(verifier.wrong_files, f_out, indent=4)


def setup() -> Namespace:
    parser = ArgumentParser(description="Find wrong IDs in DoLoReS files.")
    parser.add_argument(
        "basepath",
        type=Path,
        help="Path to the root directory containing the DoLoReS alignment files.",
    )
    parser.add_argument(
        "--output_fname",
        type=str,
        help="Output file name.",
        default="wrong_ids.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main(setup())
