from __future__ import annotations

import json
import logging
import re
import shutil
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from enum import Enum
from math import inf, sqrt
from pathlib import Path
from subprocess import run
from typing import Callable, Dict, List

import numpy as np

# import xml.etree.ElementTree as ET
from lxml import etree
from lxml.etree import _Element as Element
from mxml_processor import MXMLProcessor
from svg_processor import SVGProcessor
from validate import FileStructureValidator, ValidationOutput

_LOGGER = logging.getLogger(__name__)

MUSESCORE_EXECUTABLE = (
    "/home/ptorras/AppImage/MuseScore-Studio-4.4.2.242570931-x86_64.AppImage"
    # "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
    # "/home/pau/AppImage/MuseScore-Studio-4.3.2.241630832-x86_64.AppImage"
)

VEROVIO_EXECUTABLE = (
    "/home/ptorras/Documents/Repos/verovio/cmake/build-binary-release/verovio"
    # "/Users/ptorras/Documents/Repos/verovio/cmake/verovio"
    # "/home/pau/repos/verovio/cmake/cmake-build-debug/verovio"
)

RE_FNAME = re.compile(r"(.+)\.([0-9]{2})\.mscz")
RE_OLD_FILES = re.compile(r"OLD_.*")


OUTPUT_EXTENSION = "jpg"


# Namespace stuff to parse SVGs adequately

# ET.register_namespace("xmlns", "http://www.w3.org/2000/svg")
# ET.register_namespace("xmlns:xlink", "http://www.w3.org/1999/xlink")
# ET.register_namespace("xmlns:mei", "http://www.music-encoding.org/ns/mei")


def process_images(pack_path: Path) -> List[str]:
    images = FileStructureValidator.find_images(pack_path)

    for img in images:
        if (
            img.suffix
            in set(FileStructureValidator.VALID_EXTENSIONS) - {OUTPUT_EXTENSION}
            and not (img.parent / f"{img.stem}.{OUTPUT_EXTENSION}").exists()
        ):
            run(
                [
                    "convert",
                    str(img),
                    str(img.parent / f"{img.stem}.{OUTPUT_EXTENSION}"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    output = list(set(map(lambda x: x.stem, images)))

    _LOGGER.debug(f"Found {len(output)} images in pack: " + ", ".join(output))
    return output


def copy_alignment_files(pack_path: Path, out_path: Path):
    if not (out_path / "MUSICXML").exists():
        shutil.copytree(pack_path / "MUSICXML", out_path / "MUSICXML")
    if not (out_path / "MUSESCORE").exists():
        shutil.copytree(pack_path / "MUSESCORE", out_path / "MUSESCORE")
    if not (out_path / "SVG").exists():
        shutil.copytree(pack_path / "SVG", out_path / "SVG")

    for img in pack_path.glob("*.jpg"):
        if not (out_path / img.name).exists():
            shutil.copy(img, out_path / img.name)


def main(args: Namespace) -> None:
    print(args)
    pipeline = ConversionPipeline(args.overwrite, args.output_path)

    if args.collection is not None:
        pipeline.convert_from_collection(args.collection)

    elif args.set is not None:
        pipeline.convert_from_set(args.set)

    elif args.pack is not None:
        pipeline.convert_from_pack(args.pack)

    elif args.image is not None:
        pipeline.convert_from_image(args.image)

    elif args.mscz is not None:
        pipeline.convert_from_mscz(args.mscz)


class OutputFilename(Enum):
    MXML = "MUSICXML"
    SVG = "SVG"


class ConversionPipeline:
    def __init__(
        self,
        overwrite: bool,
        output_path: Path | None,
    ) -> None:
        self.mxml_processor = MXMLProcessor()
        self.svg_processor = SVGProcessor()
        self.validator = FileStructureValidator()

        self.overwrite = overwrite
        self.output_path = output_path

        if self.output_path is not None and not self.output_path.exists():
            self.output_path.mkdir(parents=True)

    def get_target_dir(self, pack_folder: Path, which: OutputFilename) -> Path:
        if self.output_path is not None:
            output = self.output_path / which.value
        else:
            output = pack_folder / which.value

        if not output.exists():
            output.mkdir(exist_ok=False, parents=False)
        return output

    def verify_existing(self, file: Path, on_non_existing: None | Callable[[], None]):
        if not file.exists() or self.overwrite:
            if file.exists():
                _LOGGER.info(f"Overwriting: {file}")
            if on_non_existing is not None:
                on_non_existing()
        else:
            _LOGGER.info(f"Skipping file because it already exists: {file}")

    def convert(self, mscz_files: List[Path]) -> None:
        mxml_files = []
        svg_files = []

        job_file: List[Dict[str, str]] = []

        for mscz_file in mscz_files:
            pack_folder = mscz_file.parent.parent

            # Ensure target dirs exist
            mxml_folder = self.get_target_dir(pack_folder, OutputFilename.MXML)
            svg_folder = self.get_target_dir(pack_folder, OutputFilename.SVG)

            # Ensure this is not an old file
            match = RE_OLD_FILES.match(mscz_file.stem)
            if match is not None:
                _LOGGER.info(f"Skipping old file: {mscz_file}")
                continue

            # Files to be created
            mxml_files.append(mxml_folder / f"{mscz_file.stem}.musicxml")
            svg_files.append(svg_folder / f"{mscz_file.stem}.svg")

            # Create MuseScore job
            job_row = {"in": str(mscz_file), "out": str(mxml_files[-1])}
            self.verify_existing(mxml_files[-1], lambda: job_file.append(job_row))

        # Run MuseScore job
        self.run_musescore(job_file)

        # Postprocess files and create SVGs
        for mxml_file, svg_file in zip(mxml_files, svg_files):
            self.mxml_processor.process(mxml_file)
            self.verify_existing(
                svg_file, lambda: self.run_verovio(mxml_file, svg_file)
            )
            self.svg_processor.process(svg_file)

    def run_verovio(self, mxml_file: Path, svg_file: Path) -> None:
        # Run Verovio to generate the SVGs accordingly
        cmd = run(
            args=[
                VEROVIO_EXECUTABLE,
                # "-a",
                "--adjust-page-height",
                "--adjust-page-width",
                "--breaks",
                "none",
                "--page-margin-bottom",
                "50",
                "--page-margin-left",
                "50",
                "--page-margin-right",
                "50",
                "--page-margin-top",
                "50",
                "--condense-first-page",
                "--header",
                "none",
                str(mxml_file),
                "-o",
                str(svg_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if cmd.returncode != 0:
            _LOGGER.info("Output for Verovio: " + cmd.stderr)
            raise ValueError("Return code for Verovio was not zero!")

    def run_musescore(self, job: List[Dict[str, str]]) -> None:
        job_path = Path("job.json")
        with open(job_path, "w") as f_job:
            json.dump(job, f_job, indent=4)

        cmd = run(
            args=[
                MUSESCORE_EXECUTABLE,
                "-j",
                job_path,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        job_path.unlink()

        if cmd.returncode != 0:
            _LOGGER.info("Output for MuseScore: " + cmd.stderr)
            raise ValueError("Return code for MuseScore was not zero!")

    def convert_from_collection(self, collection_path: Path) -> None:
        raise NotImplementedError()

    def convert_from_set(self, set_path: Path) -> None:
        validation = self.validator.validate_set(set_path)
        mscz_files = []

        if not validation.valid():
            _LOGGER.info("File structure is not valid. Aborting...")
            _LOGGER.info(str(validation))
            raise FileNotFoundError("Invalid File Structure")

        for pack in set_path.glob("*"):
            if not pack.is_dir():
                continue

            if pack.name[0] == ".":
                _LOGGER.info(f"Skipping hidden folder {pack.name}...")
                continue

            musescore_folder = pack / "MUSESCORE"
            if not musescore_folder.exists():
                raise FileNotFoundError(f"No MuseScore folder in {pack}")
            mscz_files += list(musescore_folder.glob("*.mscz"))

        self.convert(mscz_files)
        self.validator.reset()

    def convert_from_pack(self, pack_path: Path) -> None:
        validation = self.validator.validate_pack(pack_path)
        mscz_files = []

        if not validation.valid():
            _LOGGER.info("File structure is not valid. Aborting...")
            _LOGGER.info(str(validation))
            raise FileNotFoundError("Invalid File Structure")

        musescore_folder = pack_path / "MUSESCORE"
        if not musescore_folder.exists():
            raise FileNotFoundError(f"No MuseScore folder in {pack_path}")
        mscz_files += list(musescore_folder.glob("*.mscz"))

        self.convert(mscz_files)
        self.validator.reset()

    def convert_from_image(self, img_path: Path) -> None:
        validation = self.validator.validate_image(img_path)

        if not validation.valid():
            _LOGGER.info("File structure is not valid. Aborting...")
            _LOGGER.info(str(validation))
            raise FileNotFoundError("Invalid File Structure")

        pack_path = img_path.parent
        mscz_path = pack_path / "MUSESCORE"
        mscz_files = list(sorted(mscz_path.glob(f"{img_path.stem}.??.mscz")))

        self.convert(mscz_files)
        self.validator.reset()

    def convert_from_mscz(self, mscz_path: Path) -> None:
        match = self.validator.validate_mscz_filename(mscz_path)

        if match is None:
            _LOGGER.info("Invalid mscz filename. Not converting.")
            raise FileNotFoundError("Invalid File Structure")

        self.convert([mscz_path])
        self.validator.reset()


def setup() -> Namespace:
    parser = ArgumentParser()

    target = parser.add_mutually_exclusive_group(required=True)

    target.add_argument(
        "--collection",
        type=Path,
        help="Path to the full collection of sets to convert all at once.",
    )
    target.add_argument(
        "--set",
        type=Path,
        help="Root path to a weekly set.",
    )
    target.add_argument(
        "--pack",
        type=Path,
        help="Root path to a pack within a weekly set.",
    )
    target.add_argument(
        "--image",
        type=Path,
        help="Path to an image within a weekly set.",
    )
    target.add_argument(
        "--mscz",
        type=Path,
        help="Path to a MuseScore file within a weekly set.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Force overwriting of already converted files.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Force overwriting of already converted files.",
    )
    parser.add_argument(
        "--output_path",
        type=Path,
        help="Force overwriting of already converted files.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        filename="./validate_and_convert.log",
        level=logging.INFO if args.debug is False else logging.DEBUG,
    )
    return args


if __name__ == "__main__":
    main(setup())
