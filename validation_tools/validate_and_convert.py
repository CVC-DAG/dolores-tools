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
from typing import Dict, List

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
    _LOGGER.info("Validating pack file structure")
    validator = FileStructureValidator()
    validation = validator.validate_set(args.set_path)

    if not validation.valid():
        _LOGGER.info("File structure is not valid. Aborting...")
        _LOGGER.info(str(validation))
        raise FileNotFoundError("Invalid File Structure")

    _LOGGER.info("Data structure for pack is valid!")

    output_path = args.set_path.parent / f"{args.set_path.name}_CLEAN"
    output_path.mkdir(exist_ok=True, parents=False)

    for pack_path in args.set_path.glob("*"):
        if pack_path.name[0] == ".":
            _LOGGER.info(f"Skipping hidden folder {pack_path.name}...")
            continue

        _LOGGER.info(f"Processing {pack_path}")
        clean_pack_path = output_path / pack_path.name
        clean_pack_path.mkdir(exist_ok=True, parents=False)

        _LOGGER.info("Copying output pack")
        copy_alignment_files(pack_path, clean_pack_path)


class ConversionPipeline:
    def __init__(
        self,
        overwrite: bool,
    ) -> None:
        self.mxml_processor = MXMLProcessor()
        self.svg_processor = SVGProcessor()
        self.validator = FileStructureValidator()

        self.overwrite = overwrite

    def convert(self, mscz_files: List[Path]) -> None:
        mxml_files = []
        svg_files = []

        job_file: List[Dict[str, str]] = []

        for mscz_file in mscz_files:
            pack_folder = mscz_file.parent.parent

            # Ensure target dirs exist
            mxml_folder = pack_folder / "MUSICXML"
            if not mxml_folder.exists():
                mxml_folder.mkdir(exist_ok=False, parents=False)

            svg_folder = pack_folder / "SVG"
            if not svg_folder.exists():
                svg_folder.mkdir(exist_ok=False, parents=False)

            # Files to be created
            mxml_files.append(mxml_folder / f"{mscz_file.stem}.musicxml")
            svg_files.append(svg_folder / f"{mscz_file.stem}.svg")

            # Create MuseScore job
            if not mxml_files[-1].exists() or self.overwrite:
                job_file.append({"in": str(mscz_file), "out": str(mxml_files[-1])})
            else:
                _LOGGER.debug(
                    f"Skipping MXML file because it already exists: {mxml_files[-1]}"
                )
        # Run MuseScore job
        self.run_musescore(job_file)

        # Postprocess files and create SVGs
        for mxml_file, svg_file in zip(mxml_files, svg_files):
            self.mxml_processor.process(mxml_file)

            if not svg_file.exists() or self.overwrite:
                self.run_verovio(mxml_file, svg_file)
            else:
                _LOGGER.debug(
                    f"Skipping conversion to SVG file because it already exists: {svg_file}"
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
        with open("job.json", "w") as f_job:
            json.dump(job, f_job, indent=4)

        cmd = run(
            args=[
                MUSESCORE_EXECUTABLE,
                "-j",
                "job.json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if cmd.returncode != 0:
            _LOGGER.info("Output for MuseScore: " + cmd.stderr)
            raise ValueError("Return code for MuseScore was not zero!")

    def convert_from_collection(self, set_path: Path) -> None:
        raise NotImplementedError()

    def convert_from_set(self, set_path: Path) -> None:
        validation = self.validator.validate_set(set_path)
        mscz_files = []

        if not validation.valid():
            _LOGGER.info("File structure is not valid. Aborting...")
            _LOGGER.info(str(validation))
            raise FileNotFoundError("Invalid File Structure")

        for pack in set_path.glob("*"):
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

    def convert_from_image(self, set_path: Path) -> None:
        ...


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

    parser.add_argument(
        "--overwrite",
        action="store_true",
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
