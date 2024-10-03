from __future__ import annotations

import logging
import re
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


@dataclass
class ValidationOutput:
    valid_files: List[Path]
    transcripts_without_image: List[Path]
    transcripts_badly_named: List[Path]
    missing_line_transcripts: List[Path]
    packs_without_musescore_folder: List[Path]
    untranscribed_images: List[Path]

    def __str__(self) -> str:
        output = ""

        # output = "=" * 20 + "\n"
        # output += "Valid Filenames\n"
        # output += "=" * 20 + "\n"
        # output += "\n".join(map(str, self.valid_files)) + "\n"

        output += "=" * 20 + "\n"
        output += "Invalid Filenames\n"
        output += "=" * 20 + "\n"

        if len(self.transcripts_without_image):
            output += "\nTranscripts without image:\n\n"
            output += (
                "\t" + "\n\t".join(map(str, self.transcripts_without_image)) + "\n"
            )

        if len(self.transcripts_badly_named):
            output += "\nMalformed transcript name:\n\n"
            output += "\t" + "\n\t".join(map(str, self.transcripts_badly_named)) + "\n"

        if len(self.missing_line_transcripts):
            output += "\nMissing lines:\n\n"
            output += "\t" + "\n\t".join(map(str, self.missing_line_transcripts)) + "\n"

        if len(self.packs_without_musescore_folder):
            output += "\nNo Musescore Folder:\n\n"
            output += (
                "\t" + "\n\t".join(map(str, self.packs_without_musescore_folder)) + "\n"
            )

        if len(self.untranscribed_images):
            output += "=" * 20 + "\n"
            output += "Untranscribed images\n"
            output += "=" * 20 + "\n"
            output += "\t" + "\n\t".join(map(str, self.untranscribed_images)) + "\n"
        output += "\n"
        return output

    @classmethod
    def make_empty(cls) -> ValidationOutput:
        return ValidationOutput([], [], [], [], [], [])

    def valid(self) -> bool:
        if (
            len(self.transcripts_without_image) == 0
            and len(self.packs_without_musescore_folder) == 0
        ):
            return True
        else:
            return False


class FileStructureValidator:
    RE_FNAME = re.compile(r"(.+)\.([0-9]{2})\.mscz")
    RE_OLD_FILES = re.compile(r"OLD_.*")

    VALID_EXTENSIONS = ["tif", "jpg", "jpeg", "png"]
    VALID_EXTENSIONS += [x.upper() for x in VALID_EXTENSIONS]

    def __init__(self) -> None:
        self.validation_output: ValidationOutput = ValidationOutput.make_empty()

    def reset(self) -> None:
        self.validation_output: ValidationOutput = ValidationOutput.make_empty()

    def get_output(self) -> ValidationOutput:
        return self.validation_output

    def validate_set(self, set_path: Path) -> ValidationOutput:
        for pack_path in set_path.glob("*"):
            if pack_path.is_dir():
                self.validate_pack(pack_path)

        return self.validation_output

    def validate_pack(self, pack_path: Path) -> ValidationOutput:
        images = self.find_images(pack_path)
        mscz_path = pack_path / "MUSESCORE"

        if mscz_path.exists():
            self.validate_mscz_folder(mscz_path, set(map(lambda x: x.stem, images)))
        else:
            _LOGGER.warning(f"Pack without MuseScore folder: {str(pack_path)}")
            self.validation_output.packs_without_musescore_folder.append(pack_path)

        return self.validation_output

    @classmethod
    def find_images(cls, pack_path: Path) -> List[Path]:
        images = []
        for extension in cls.VALID_EXTENSIONS:
            images += [im for im in pack_path.glob(f"*.{extension}") if im.is_file()]

        return images

    def validate_mscz_folder(
        self, mscz_path: Path, images: Set[str]
    ) -> ValidationOutput:
        """Validate the contents of a MUSESCORE folder within a pack.

        Checks whether the contents of the MSCZ folder conform to standard. Changes the
        state of the class.

        Parameters
        ----------
        mscz_path : Path
            Full path to the MUSESCORE folder.
        images : Set[str]
            List of image file names within the parent pack to ensure that they have
            their corresponding transcriptions.

        Returns
        -------
        ValidationOutput
            Pointer to the validation result object contained within the validation
            class, updated with the newly analised files.
        """
        max_index = {}  # name, max_index
        found = set()

        for transcript in mscz_path.glob("*.mscz"):
            old_file = self.RE_OLD_FILES.match(transcript.name)

            # Ensure it is not an old file
            if old_file is not None:
                _LOGGER.debug(f"Skipping 'OLD_' file: {transcript}")
                continue

            # Check file naming convention
            match = self.validate_mscz_filename(transcript)
            if match is None:
                continue

            filename = match.group(1)
            index = int(match.group(2))

            found.add(filename)

            # Check there is an associated image to this transcript
            if filename not in images:
                _LOGGER.info(
                    f"Transcription for which there is no image found: {transcript}"
                )
                self.validation_output.transcripts_without_image.append(transcript)
                continue

            if filename not in max_index:
                max_index[filename] = index
            else:
                max_index[filename] = max(index, max_index[filename])
            self.validation_output.valid_files.append(transcript)

        # Ensure all lines are present
        for name, max_val in max_index.items():
            for ii in range(1, max_val + 1):
                line_transcript = mscz_path / f"{name}.{ii:02}.mscz"
                if not line_transcript.exists():
                    _LOGGER.info(
                        f"Line {ii} transcription is missing for file {name} in file {str(mscz_path)}"
                    )
                    self.validation_output.missing_line_transcripts.append(
                        line_transcript
                    )

        # Ensure all images are transcribed
        not_transcribed = [mscz_path.parent / x for x in images - found]
        if len(not_transcribed) > 0:
            _LOGGER.info(
                f"Some images are not transcribed in {str(mscz_path)}: "
                + ", ".join(map(str, not_transcribed))
            )
        self.validation_output.untranscribed_images += not_transcribed

        return self.validation_output

    def validate_mscz_filename(self, transcript: Path) -> re.Match | None:
        match = self.RE_FNAME.match(transcript.name)
        if match is None:
            _LOGGER.info(f"Filename does not follow naming convention: {transcript}")
            self.validation_output.transcripts_badly_named.append(transcript)
        return match

    def validate_image(self, img_path: Path) -> ValidationOutput:
        """Validate the files required to align a single image file within a pack.

        Checks whether the contents of the MSCZ folder related to an individual image
        conform to standard. Changes the state of the class.

        Parameters
        ----------
        img_path : Path
            Full path to the image within a pack.

        Returns
        -------
        ValidationOutput
            Pointer to the validation result object contained within the validation
            class, updated with the newly analised files.
        """
        pack_path = img_path.parent
        mscz_path = pack_path / "MUSESCORE"

        # Ensure MuseScore folder exists
        if not mscz_path.exists():
            _LOGGER.info(f"Pack without MuseScore folder: {str(img_path.parent)}")
            self.validation_output.packs_without_musescore_folder.append(
                img_path.parent
            )
            return self.validation_output

        mscz_files = list(sorted(mscz_path.glob(f"{img_path.stem}.??.mscz")))

        # Transcriptions?
        if len(mscz_files) == 0:
            _LOGGER.info(f"Image without transcription: {img_path}")
            self.validation_output.untranscribed_images.append(img_path)
            return self.validation_output

        # Missing Lines
        present_indices = set(map(lambda x: int(x.stem.split(".")[-1]), mscz_files))
        missing_indices = {x for x in range(1, max(present_indices))} - present_indices
        self.validation_output.missing_line_transcripts.extend(
            [mscz_path / f"{img_path.stem}.{ii:02}.mscz" for ii in missing_indices]
        )

        # Format
        map(self.validate_mscz_filename, mscz_files)

        return self.validation_output


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "set_path",
        type=Path,
        help="Path pointing to a specific DOLORES score set",
    )

    args = parser.parse_args()

    validator = FileStructureValidator()
    output = validator.validate_set(args.set_path)
    print(str(output))
    exit(0 if output.valid() else 1)
