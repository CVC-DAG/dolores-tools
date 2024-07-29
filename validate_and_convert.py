from __future__ import annotations

import logging
import re
import shutil
from argparse import ArgumentParser, Namespace
from math import inf, sqrt
from pathlib import Path
from subprocess import run
from typing import List, NamedTuple

import numpy as np
# import xml.etree.ElementTree as ET
from lxml import etree
from lxml.etree import _Element as Element


class Point(NamedTuple):
    x: int
    y: int

    def __str__(self) -> str:
        return f"{self.x},{self.y}"

    def dist(self, other: Point) -> float:
        return sqrt((other.x - self.x) ** 2 + (other.y - self.y) ** 2)


class Rectangle(NamedTuple):
    tl: Point
    tr: Point
    br: Point
    bl: Point


_LOGGER = logging.getLogger(__name__)

MUSESCORE_EXECUTABLE = (
    "/home/ptorras/AppImage/MuseScore-Studio-4.3.2.241630832-x86_64.AppImage"
    # "/home/pau/AppImage/MuseScore-Studio-4.3.2.241630832-x86_64.AppImage"
)

VEROVIO_EXECUTABLE = (
    "/home/ptorras/Documents/Repos/verovio/cmake/cmake-build-debug/verovio"
    # "/home/pau/repos/verovio/cmake/cmake-build-debug/verovio"
)

RE_FNAME = re.compile(r"(.+)\.([0-9]{2})\.mscz")
RE_BEAM_ID = re.compile(r"beam(\d+)")
OUTPUT_EXTENSION = "jpg"


# Namespace stuff to parse SVGs adequately

# ET.register_namespace("xmlns", "http://www.w3.org/2000/svg")
# ET.register_namespace("xmlns:xlink", "http://www.w3.org/1999/xlink")
# ET.register_namespace("xmlns:mei", "http://www.music-encoding.org/ns/mei")

NAMESPACES = {
    "svg": "http://www.w3.org/2000/svg",
    "xlink": "http://www.w3.org/1999/xlink",
    "mei": "http://www.music-encoding.org/ns/mei",
}


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
            img.suffix in {".tif", ".png", ".jpeg", "jpg"} - {OUTPUT_EXTENSION}
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
    logging.basicConfig(
        filename="./validate_and_convert.log",
        level=logging.INFO if args.debug is False else logging.DEBUG,
    )
    _LOGGER.info("Setting up...")
    output_path = args.set_path.parent / f"{args.set_path.name}_CLEAN"
    output_path.mkdir(exist_ok=True, parents=False)
    for pack_path in args.set_path.glob("*"):
        _LOGGER.info(f"Processing {pack_path}...")
        clean_pack_path = output_path / pack_path.name
        clean_pack_path.mkdir(exist_ok=True, parents=False)
        convert_pack(pack_path, args.overwrite)

        _LOGGER.info("Copying output pack...")
        copy_alignment_files(pack_path, clean_pack_path)


def convert_pack(pack_path: Path, overwrite: bool) -> None:
    musescore_folder = pack_path / "MUSESCORE"
    musicxml_folder = pack_path / "MUSICXML"
    svg_folder = pack_path / "SVG"

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

    _LOGGER.debug(f"Creating {str(svg_folder)}...")
    if not svg_folder.exists():
        svg_folder.mkdir(exist_ok=False, parents=False)
    _LOGGER.debug(f"OK!")

    images = process_images(pack_path)

    validate_mscz(images, musescore_folder)

    for mscz_file in musescore_folder.glob("*.mscz"):
        _LOGGER.info(f"Converting {mscz_file} to XML...")

        # Use uncompressed MusicXML to incorporate identifiers afterward
        mxml_file = musicxml_folder / f"{mscz_file.stem}.musicxml"
        svg_file = svg_folder / f"{mscz_file.stem}.svg"

        if not overwrite and mxml_file.exists():
            _LOGGER.info(f"Skipping {str(mxml_file)} because it already exists")
            continue

        cmd = run(
            [
                MUSESCORE_EXECUTABLE,
                str(mscz_file),
                "-o",
                str(mxml_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if cmd.returncode != 0:
            _LOGGER.info("Output for Musescore: " + cmd.stderr)
            raise ValueError("Return code for Musescore was not zero!")

        _LOGGER.debug("STDERR: " + cmd.stderr)
        _LOGGER.debug("STDOUT: " + cmd.stdout)

        add_identifiers(mxml_file)

        # Run Verovio to generate the SVGs accordingly
        cmd = run(
            [
                VEROVIO_EXECUTABLE,
                # "-a",
                "--adjust-page-height",
                "--adjust-page-width",
                "--page-margin-bottom",
                "0",
                "--page-margin-left",
                "0",
                "--page-margin-right",
                "0",
                "--page-margin-top",
                "0",
                "--condense-first-page",
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

        _LOGGER.debug("STDERR: " + cmd.stderr)
        _LOGGER.debug("STDOUT: " + cmd.stdout)

        postprocess_svg(svg_file)


def add_identifiers(mxml_file: Path) -> None:
    tree = etree.parse(mxml_file)
    root = tree.getroot()

    # fmt: off

    # Objects that are present in only one place
    _identify_notes(root)

    _find_and_ident(root, "attributes/clef")
    _find_and_ident(root, "attributes/key")
    _find_and_ident(root, "attributes/time")
    _find_and_ident(root, "barline")
    _find_and_ident(root, "direction/direction-type/rehearsal")
    _find_and_ident(root, "direction/direction-type/pedal")
    # _find_and_ident(root, "note/notations/tuplet")

    # Objects found in various places
    _find_and_ident(root, "barline/coda", "direction/direction-type/coda")
    _find_and_ident(root, "barline/fermata", "note/notations/fermata")
    _find_and_ident(root, "barline/segno", "direction/direction-type/segno")
    _find_and_ident(root, "note/notations/dynamics", "direction/direction-type/dynamics")

    # Objects defined in parts
    _identify_beams(root)
    _identify_end_to_end(root, "note/notations/glissando")
    _identify_end_to_end(root, "note/notations/slide")
    _identify_end_to_end(root, "note/notations/slur")
    _identify_end_to_end(root, "note/notations/tied")
    _identify_end_to_end(root, "note/notations/tuplet")
    _identify_end_to_end(root, "direction/direction-type/wedge")
    _identify_end_to_end(root, "direction/direction-type/octave-shift")
    _identify_end_to_end(root, "direction/direction-type/bracket")
    _identify_end_to_end(root, "direction/direction-type/dashes")

    # Other objects
    # _identify_articulations(root)
    # _identify_ornaments(root)
    # _identify_arpeggiate(root)

    # fmt: on

    # Set measure identifiers from the measure numbers
    _identify_measures(root)

    tree.write(mxml_file)


def _identify_list(elm_list: List[Element], name: str) -> None:
    for ii, node in enumerate(elm_list, 1):
        node.attrib["id"] = f"{name}{ii}"


def _identify_notes(root: Element) -> None:
    nodes = _find(root, "./part/measure", "note")

    rest_nodes = [x for x in nodes if x.find("rest") is not None]
    note_nodes = [x for x in nodes if x.find("rest") is None]

    _identify_list(rest_nodes, "rest")
    _identify_list(note_nodes, "note")


def _identify_beams(root: Element) -> None:
    beams = root.findall("./part/measure/note/beam")
    # beam_stack = {}

    ident = 1

    for beam in beams:
        # We assume all beam elements have numbers, as generated by MuseScore 4
        number = beam.get("number")
        assert number is not None, "NUMBER WITH NONE FOR BEAMS!"

        number = int(number)

        if beam.text == "begin":
            # beam_stack[number] = ident
            beam.set("id", f"beam{ident}")
            ident += 1
        elif beam.text == "backward hook":
            beam.set("id", f"beam{ident}")
            ident += 1
        elif beam.text == "forward hook":
            beam.set("id", f"beam{ident}")
            ident += 1
        # Continuations do not need the same identifier

        # elif beam.text == "continue":
        #     beam.set("id", f"beam{beam_stack[number]}")
        # elif beam.text == "end":
        #     beam.set("id", f"beam{beam_stack.pop(number)}")


# def _identify_articulations(root: Element) -> None:
#     arts = _find(root, "./part/measure", "note/notations/articulations")

#     for ii, art in enumerate(arts, 1):
#         art.set("id", f"artic{ii}")


# def _identify_ornaments(root: ET.Element) -> None:
#     orns = _find(root, "./part/measure", "note/notations/ornaments")

#     for ii, art in enumerate(orns, 1):
#         art.set("id", f"ornam{ii}")


def _identify_end_to_end(root: Element, *paths: str) -> None:
    elements = _find(root, "./part/measure", *paths)
    # print(elements)
    idents = {x.split("/")[-1]: 1 for x in paths}

    for element in elements:
        style = element.get("type")
        tag = element.tag

        assert style is not None, "end to end object without style property"

        if style in {
            "start",
            "crescendo",
            "diminuendo",
            "let-ring",
            "up",
            "down",
            "sostenuto",
        }:
            element.set("id", f"{tag}{idents[tag]}")
            idents[tag] += 1


def _identify_measures(root: Element) -> None:
    for part in root.findall("part"):
        part_id = part.get("id")
        for measure in part:
            measure_id = measure.get("number")
            measure.set("id", f"p{part_id}_m{measure_id}")


def _find(root: Element, path_prefix: str, *paths: str) -> List[Element]:
    output = []

    for path in paths:
        output += root.findall(path_prefix + "/" + path)

    return output


def _find_and_ident(root: Element, *paths: str) -> None:
    _identify_list(
        _find(root, "./part/measure", *paths),
        paths[0].split("/")[-1],
    )


def postprocess_svg(svg_file: Path) -> None:
    tree = etree.parse(svg_file)
    root = tree.getroot()

    _remove_unnecessary_svg(root)
    _rebuild_svg_beams(root)

    # Performed AFTER changing beams - careful!
    _identify_svg_dots(root)
    _identify_svg_noteheads(root)
    _identify_svg_tremolos(root)
    _identify_svg_flags(root)
    _identify_svg_tuplet_num(root)

    etree.indent(tree, "    ")
    tree.write(svg_file)


def _remove_unnecessary_svg(root: Element) -> None:
    """Remove header and misc information from the SVG of the score.

    Parameters
    ----------
    root : ET.Element
        Root element of the score in SVG format.
    """


def _rebuild_svg_beams(root: Element) -> None:
    """Change Verovio beam fragments into continuous beams that can be identified well.

    Verovio segments beams into segments. If the initial geometry of the beam is
    something like:

    +--+--+--+
    +--+--|  |
    |  |  |  |
    O  O  O  O

    This will be converted into 3 different segments. The top beam will always be
    one singular object, whereas beams below will be segmented into fragments spanning
    the full width of the space between stems. Thus:

    +11+11+11+
    +22+33|  |
    |  |  |  |
    O  O  O  O

    Parameters
    ----------
    root : ET.Element
        Root SVG score element.
    """
    beam_nodes = root.findall(".//svg:g[@class='beam']", namespaces=NAMESPACES)

    for beam_node in beam_nodes:
        beam_id = beam_node.get("id", "")
        beam_id_match = RE_BEAM_ID.match(beam_id)

        if beam_id_match is None:
            raise ValueError("Invalid beam id formatting")
        id_index = int(beam_id_match.group(1))

        new_beams = []

        beam_fragments = beam_node.findall("./svg:polygon", namespaces=NAMESPACES)
        if len(beam_fragments) == 0:
            raise ValueError("Beam without drawn polygons")

        prev_frag = _get_beam_rectangle(beam_fragments[0])

        for curr_frag in beam_fragments[1:]:
            curr_frag = _get_beam_rectangle(curr_frag)

            if prev_frag.tr == curr_frag.tl and prev_frag.br == curr_frag.bl:
                prev_frag = Rectangle(
                    prev_frag.tl, curr_frag.tr, curr_frag.br, prev_frag.bl
                )
            else:
                new_beams.append(prev_frag)
                prev_frag = curr_frag

        new_beams.append(prev_frag)

        for frag in beam_fragments:
            beam_node.remove(frag)

        for ii, new_beam in enumerate(reversed(new_beams), 1):
            beam_node.insert(
                0,
                etree.Element(
                    "polygon",
                    attrib={
                        "points": " ".join(map(str, new_beam)),
                        "id": f"beam{len(new_beams) + id_index - ii}",
                        "class": "beam",
                    },
                    nsmap=NAMESPACES,
                ),
            )
        beam_node.set("id", beam_node.get("id", "") + "_parent")
        beam_node.set("class", beam_node.get("class", "") + "_parent")


def _get_beam_rectangle(et_poly: Element) -> Rectangle:
    points = et_poly.get("points")

    if points is None:
        raise ValueError("Beam polygon element has no points attribute")

    points = points.split(" ")

    if len(points) != 4:
        raise ValueError("More than 4 points present in rectangle polygon")

    tl, tr, br, bl = map(lambda x: Point(*map(int, x.split(","))), points)

    return Rectangle(tl, tr, br, bl)


def _identify_svg_dots(root: Element) -> None:
    """Give an identifier to dots.

    Parameters
    ----------
    root : ET.Element
        Root SVG score element.

    """
    # Find dots elements within other elements
    dot_containers = root.xpath(".//*[svg:g[@class='dots']]", namespaces=NAMESPACES)
    for container in dot_containers:
        container_id = container.get("id", None)

        if container_id is None:
            raise ValueError("Container has null id")

        container_class = container.get("class", None)

        if container_class is None:
            raise ValueError("Container has no known class")

        dots_element = container.find("./svg:g[@class='dots']", namespaces=NAMESPACES)
        if dots_element is None:
            raise ValueError("For some reason there are no dots on a dot query")
        dots_element.set("id", f"{container_id}.dots_parent")

        # If the object is under a note, it is easy to process because we only need to
        # set the id of the parent object
        if container_class in {"note", "rest"}:
            for ii, ellipse in enumerate(dots_element, 1):
                ellipse.set("id", container_id + f".dot{ii}")
                ellipse.set("class", "single_dot")
            continue

        # Otherwise, we have to find all noteheads within the container and assign each
        # dot to the closest note.
        dot_coords = []
        for dot in dots_element:
            # Should be an ellipse
            dot.set("class", "single_dot")

            x_dot = dot.get("cx")
            y_dot = dot.get("cy")

            if x_dot is None or y_dot is None:
                raise ValueError("Dot ellipse has no center. Can't identify SVG dots.")

            x_dot = int(x_dot)
            y_dot = int(y_dot)

            dot_coords.append(Point(x_dot, y_dot))

        noteheads = container.xpath(
            ".//svg:g[@class='note']/svg:g[@class='notehead']/svg:use",
            namespaces=NAMESPACES,
        )
        notehead_coords = []

        for notehead in noteheads:
            # Should be an ellipse

            x_notehead = notehead.get("x")
            y_notehead = notehead.get("y")

            assert (
                x_notehead is not None and y_notehead is not None
            ), "Notehead has no center"

            x_notehead = int(x_notehead)
            y_notehead = int(y_notehead)

            notehead_coords.append(Point(x_notehead, y_notehead))

        notehead_matrix = np.array(notehead_coords)
        dot_matrix = np.array(dot_coords)

        # Use only y coordinates
        dist_matrix = dot_matrix[:, np.newaxis, 1] - notehead_matrix[np.newaxis, :, 1]
        dist_matrix = np.abs(dist_matrix)

        dot_indices = dist_matrix.argmin(1)

        repeat_dots = {ii: 1 for ii in range(len(notehead_matrix))}

        for dot_ind, note_ind in enumerate(dot_indices):
            note_ob = noteheads[note_ind].getparent().getparent()
            note_id = note_ob.get("id", None)

            dots_element[dot_ind].set("id", f"{note_id}.dot{repeat_dots[note_ind]}")
            repeat_dots[note_ind] += 1


def _identify_svg_tremolos(root: Element) -> None:
    """Give an identifier to tremolos.

    Verovio will provide the identifier of the first note of the tremolo group or
    tremolo stem. This function propagates the id alongside an index to the various
    line elements that form the tremolo, as well as giving them a "tremolo_line" class.

    Parameters
    ----------
    root : ET.Element
        Root SVG score element.

    """
    ftrem_objects = root.findall(".//svg:g[@class='fTrem']", namespaces=NAMESPACES)
    for ftrem in ftrem_objects:
        ident = ftrem.get("id")
        for ii, line in enumerate(
            ftrem.findall("./svg:polygon", namespaces=NAMESPACES), 1
        ):
            line.set("id", f"{ident}.line{ii}")
            line.set("class", f"fTrem_line")

    btrem_objects = root.findall(".//svg:g[@class='bTrem']", namespaces=NAMESPACES)
    for btrem in btrem_objects:
        ident = btrem.get("id")
        for ii, line in enumerate(btrem.findall("./svg:use", namespaces=NAMESPACES), 1):
            line.set("id", f"{ident}.line{ii}")
            line.set("class", f"bTrem_line")


def _identify_svg_noteheads(root: Element) -> None:
    """Provide an identifier to notehead objects in the SVG.

    Parameters
    ----------
    root : ET.Element
        Root SVG score element.
    """
    note_nodes = root.findall(".//svg:g[@class='note']", namespaces=NAMESPACES)
    for note_node in note_nodes:
        notehead_node = note_node.find(
            "./svg:g[@class='notehead']", namespaces=NAMESPACES
        )
        if notehead_node is not None:
            notehead_node.set("id", f"{note_node.get('id')}.notehead")


def _identify_svg_flags(root: Element) -> None:
    """Provide an identifier to flag objects in the SVG.

    Parameters
    ----------
    root : ET.Element
        Root SVG score element.
    """
    stem_nodes = root.findall(".//svg:g[@class='stem']", namespaces=NAMESPACES)

    for stem_node in stem_nodes:
        flag_node = stem_node.find("./g[@class='flag']", namespaces=NAMESPACES)
        if flag_node is not None:
            flag_node.set("id", f"{stem_node.get('id')}.flag")


def _identify_svg_tuplet_num(root: Element) -> None:
    """Provide an identifier to tuplet number objects in the SVG.

    Parameters
    ----------
    root : ET.Element
        Root SVG score element.

    """
    tuplet_nodes = root.findall(".//svg:g[@class='tuplet']", namespaces=NAMESPACES)
    for tuplet_node in tuplet_nodes:
        number_node = tuplet_node.find(
            "./svg:g[@class='tupletNum']", namespaces=NAMESPACES
        )
        if number_node is not None:
            number_node.set("id", f"{tuplet_node.get('id')}.number")


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
