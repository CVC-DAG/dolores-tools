import logging
import re
import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path
from subprocess import run
from typing import List

_LOGGER = logging.getLogger(__name__)

MUSESCORE_EXECUTABLE = (
    "/home/ptorras/AppImage/MuseScore-Studio-4.3.1.241490902-x86_64.AppImage"
)

RE_FNAME = re.compile(r"(.+)\.([0-9]{2})\.mscz")


def validate_mscz(images: List[str], mscz_path: Path) -> None:
    found = []
    max_index = {}  # name, max_index
    for transcript in mscz_path.glob("*.mscz"):
        match = RE_FNAME.match(transcript.name)
        if match is None:
            raise ValueError(
                f"Filename does not follow naming convention: {str(mscz_path / transcript)}"
            )
        if match.group(1) not in images:
            raise FileNotFoundError(
                f"Transcription for which there is no image found: {str(mscz_path / match.group(1))}"
            )
        else:
            found.append(match.group(1))
            if not match.group(1) in max_index:
                max_index[match.group(1)] = int(match.group(2))
            else:
                max_index[match.group(1)] = max(
                    max_index[match.group(1)], int(match.group(2))
                )

    # Ensure all lines are present
    for name, max_val in max_index.items():
        for ii in range(1, max_val + 1):
            if not (mscz_path / f"{name}.{ii:02}.mscz").exists():
                raise ValueError(
                    f"Line {ii} transcription is missing for file {name} in file {str(mscz_path)}"
                )

    not_transcribed = set(images) - set(found)
    if len(not_transcribed) > 0:
        raise ValueError(
            f"Some images are not transcribed in {str(mscz_path)}: "
            + ", ".join(not_transcribed)
        )


def process_images(pack_path: Path) -> List[str]:
    images = [im for im in pack_path.glob("*.tif") if im.is_file()]
    images += [im for im in pack_path.glob("*.png") if im.is_file()]
    images += [im for im in pack_path.glob("*.jpg") if im.is_file()]
    images += [im for im in pack_path.glob("*.jpeg") if im.is_file()]

    for img in images:
        if (
            img.suffix in {".tif", ".png", ".jpeg"}
            and not (img.parent / f"{img.stem}.jpg").exists()
        ):
            run(
                ["convert", str(img), str(img.parent / f"{img.stem}.jpg")],
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

    for img in pack_path.glob("*.jpg"):
        if not (out_path / img.name).exists():
            shutil.copy(img, out_path / img.name)


def main(args: Namespace) -> None:
    logging.basicConfig(
        filename="./validate_and_convert.log",
        level=logging.INFO if args.debug is False else logging.DEBUG,
    )
    _LOGGER.info("Setting up...")
    output_path = args.set_path.parent / f"{args.set_path.name}_CLEAN"
    output_path.mkdir(exist_ok=True, parents=False)
    for pack_path in args.set_path.glob("*"):
        _LOGGER.info("Processing {pack_path}...")
        clean_pack_path = output_path / pack_path.name
        clean_pack_path.mkdir(exist_ok=True, parents=False)
        convert_pack(pack_path, args.overwrite)

        _LOGGER.info("Copying output pack...")
        copy_alignment_files(pack_path, clean_pack_path)


def convert_pack(pack_path: Path, overwrite: bool) -> None:
    musescore_folder = pack_path / "MUSESCORE"
    musicxml_folder = pack_path / "MUSICXML"

    _LOGGER.debug(f"Checking {str(musescore_folder)} exists...")
    if not musescore_folder.exists():
        raise FileNotFoundError(
            f"{str(pack_path)} does not contain a MUSESCORE folder!"
        )
    _LOGGER.debug(f"OK!")

    _LOGGER.debug(f"Creating {str(musicxml_folder)}...")
    if not musicxml_folder.exists():
        musicxml_folder.mkdir(exist_ok=False, parents=False)
    _LOGGER.debug(f"OK!")

    images = process_images(pack_path)

    validate_mscz(images, musescore_folder)

    for mscz_file in musescore_folder.glob("*.mscz"):
        _LOGGER.info(f"Converting {mscz_file} to XML...")
        mxml_file = musicxml_folder / f"{mscz_file.name}.mxl"

        if not overwrite and mxml_file.exists():
            _LOGGER.info(f"Skipping {str(mxml_file)} because it already exists")
            continue

        cmd = run(
            [
                MUSESCORE_EXECUTABLE,
                str(mscz_file),
                "-o",
                str(musicxml_folder / f"{mscz_file.stem}.mxl"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _LOGGER.debug("STDERR: " + cmd.stderr)
        _LOGGER.debug("STDOUT: " + cmd.stdout)


def setup() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        "set_path",
        type=Path,
        help="Root path to a weekly set",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Force overwriting of already converted files",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main(setup())
