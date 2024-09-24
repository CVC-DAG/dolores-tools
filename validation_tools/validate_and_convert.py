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
from typing import Iterator, List, Optional, Tuple

import numpy as np

# import xml.etree.ElementTree as ET
from lxml import etree
from lxml.etree import _Element as Element


@dataclass
class Point:
    """Represents a point in a bounding box."""

    x: int
    y: int

    def __str__(self) -> str:
        return f"{self.x},{self.y}"

    def as_tuple(self) -> Tuple[int, int]:
        return self.x, self.y

    def dist(self, other: Point) -> float:
        return sqrt((other.x - self.x) ** 2 + (other.y - self.y) ** 2)


@dataclass
class RepeatDot(Point):
    character: str

    def to_svg(self) -> Element:
        return etree.Element(
            "use",
            {
                f"{{{NAMESPACES['xlink']}}}href": str(self.character),
                "x": str(self.x),
                "y": str(self.y),
                "height": "720px",
                "width": "720px",
            },
        )


class RepeatType(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"


class RepeatDots:
    def __init__(
        self,
        point_top: RepeatDot,
        point_bot: RepeatDot,
        direction: RepeatType,
    ) -> None:
        self.point_top = point_top
        self.point_bot = point_bot
        self.direction = direction

    def to_svg(self, ident: str) -> Element:
        output = etree.Element(
            f"{{{NAMESPACES['svg']}}}g",
            {"id": ident, "class": "repeat"},
            nsmap=NAMESPACES,
        )

        output.append(self.point_top.to_svg())
        output.append(self.point_bot.to_svg())

        return output


@dataclass
class Rectangle:
    tl: Point
    tr: Point
    br: Point
    bl: Point

    def __iter__(self) -> Iterator[Point]:
        yield from [self.tl, self.tr, self.br, self.bl]


@dataclass
class SvgLine:
    origin: Point
    dest: Point
    weight: int

    def to_svg(self, ident: str) -> Element:
        output = etree.Element(
            f"{{{NAMESPACES['svg']}}}path",
            {
                "id": ident,
                "d": f"M{self.origin.x} {self.origin.y} L{self.dest.x} {self.dest.y}",
                "stroke": "currentColor",
                "stroke-width": str(self.weight),
                "class": "barline_tok",
            },
            nsmap=NAMESPACES,
        )
        return output


_LOGGER = logging.getLogger(__name__)

MUSESCORE_EXECUTABLE = (
    "/home/ptorras/AppImage/MuseScore-Studio-4.4.1.242490810-x86_64_85baedfc506d4677b0d6b31fcd59c5a3.AppImage"
    # "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
    # "/home/pau/AppImage/MuseScore-Studio-4.3.2.241630832-x86_64.AppImage"
)

VEROVIO_EXECUTABLE = (
    "/home/ptorras/Documents/Repos/verovio/cmake/cmake-build-debug/verovio"
    # "/Users/ptorras/Documents/Repos/verovio/cmake/verovio"
    # "/home/pau/repos/verovio/cmake/cmake-build-debug/verovio"
)

RE_FNAME = re.compile(r"(.+)\.([0-9]{2})\.mscz")
RE_BEAM_ID = re.compile(r"beam(\d+)")
RE_OLD_FILES = re.compile(r"OLD_.*")

RE_MOVETO_COMMAND = re.compile(r"M(\d+)[, ](\d+)")
RE_LINETO_COMMAND = re.compile(r"L(\d+)[, ](\d+)")

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
        # Ensure the file in question does not have an OLD_ prefix
        old_file = RE_OLD_FILES.match(transcript.name)

        if old_file is not None:
            _LOGGER.debug("File has an OLD prefix. Skipping...")
            continue

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
        if pack_path.name[0] == ".":
            _LOGGER.info(f"Skipping hidden folder {pack_path.name}...")
            continue

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
    job_file = []

    for mscz_file in musescore_folder.glob("*.mscz"):
        # Ensure the file in question does not have an OLD_ prefix
        old_file = RE_OLD_FILES.match(mscz_file.name)

        if old_file is not None:
            _LOGGER.debug("File has an OLD prefix. Skipping...")
            continue
        _LOGGER.info(f"Converting {mscz_file} to XML...")

        # Use uncompressed MusicXML to incorporate identifiers afterward
        mxml_file = musicxml_folder / f"{mscz_file.stem}.musicxml"
        svg_file = svg_folder / f"{mscz_file.stem}.svg"

        job_file.append({"in": str(mscz_file), "out": str(mxml_file)})

    with open(pack_path / "job.json", "w") as f_job:
        json.dump(job_file, f_job, indent=4)

    cmd = run(
        args=[
            MUSESCORE_EXECUTABLE,
            "-j",
            str(pack_path / "job.json"),
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

    for converted in job_file:
        mxml_file = Path(converted["out"])
        svg_file = svg_folder / (mxml_file.stem + ".svg")
        add_identifiers(mxml_file)

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


# def _identify_ornaments(root: Element) -> None:
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
    _rebuild_svg_barlines(root)

    # Performed AFTER changing beams - careful!
    _identify_svg_timesigs(root)
    _identify_svg_dots(root)
    _identify_svg_noteheads(root)
    _identify_svg_tremolos(root)
    _identify_svg_flags(root)
    _identify_svg_tuplet_num(root)
    _identify_svg_tuplet_bracket(root)
    _identify_svg_mrep(root)
    _identify_svg_ending(root)

    etree.indent(tree, "    ")
    tree.write(svg_file)


def _remove_unnecessary_svg(root: Element) -> None:
    """Remove header and misc information from the SVG of the score.

    Parameters
    ----------
    root : Element
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
    root : Element
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


def _rebuild_svg_barlines(root: Element) -> None:
    barlines = root.findall(".//svg:g[@class='barLine']", namespaces=NAMESPACES)
    for barline in barlines:
        _edit_barline_elements(barline)


def _edit_barline_elements(barline_node: Element) -> None:
    barline_id = barline_node.get("id")

    # Make sure the barline element is not empty
    if len(barline_node) == 0:
        parent = barline_node.getparent()
        if parent is not None:
            parent.remove(barline_node)
        return None
    segments = barline_node.findall("./svg:path", namespaces=NAMESPACES)
    segments = list(map(_parse_segment, segments))
    segments = _combine_segments(segments)

    dots = barline_node.findall("./svg:use", namespaces=NAMESPACES)
    dots = list(map(_parse_repeat_dot, dots))
    dots = _combine_repeat_dots(dots, segments[0].origin.x)

    for node in barline_node:
        barline_node.remove(node)

    for ii, segment in enumerate(segments, 1):
        barline_node.append(segment.to_svg(f"{barline_id}.barline_tok{ii}"))

    for ii, dot in enumerate([x for x in dots if x.direction == RepeatType.FORWARD], 1):
        barline_node.append(dot.to_svg(f"{barline_id}.repeat_forward{ii}"))

    for ii, dot in enumerate(
        [x for x in dots if x.direction == RepeatType.BACKWARD], 1
    ):
        barline_node.append(dot.to_svg(f"{barline_id}.repeat_backward{ii}"))


def _parse_segment(path_element: Element) -> SvgLine:
    draw_cmd = path_element.get("d")

    if draw_cmd is None:
        raise ValueError("No draw command in Barline segment")

    weight = path_element.get("stroke-width")

    if weight is None:
        raise ValueError("No stroke-width command in Barline segment")

    weight = int(weight)

    move_cmd = RE_MOVETO_COMMAND.search(draw_cmd)
    line_cmd = RE_LINETO_COMMAND.search(draw_cmd)

    if move_cmd is None or line_cmd is None:
        raise ValueError("Malformed draw command in Barline segment")

    origin_x, origin_y = map(int, move_cmd.groups())
    target_x, target_y = map(int, line_cmd.groups())

    return SvgLine(Point(origin_x, origin_y), Point(target_x, target_y), weight)


def _combine_segments(lines: List[SvgLine]) -> List[SvgLine]:
    sorted_lines = list(sorted(lines, key=lambda x: (x.origin.x, x.origin.y)))
    output_lines = []
    base_segment = sorted_lines[0]

    for comp_segment in sorted_lines[1:]:
        if (
            base_segment.dest.y == comp_segment.origin.y
            and base_segment.origin.x == comp_segment.origin.x
            and base_segment.weight == comp_segment.weight
        ):
            base_segment.dest = comp_segment.dest
        else:
            output_lines.append(base_segment)
            base_segment = comp_segment
    output_lines.append(base_segment)
    return output_lines


def _parse_repeat_dot(dot_element: Element) -> RepeatDot:
    character = dot_element.get(f"{{{NAMESPACES['xlink']}}}href")
    xcoord = dot_element.get("x")
    ycoord = dot_element.get("y")

    if character is None:
        raise ValueError("No string value in repeat dot element")

    if xcoord is None or ycoord is None:
        raise ValueError("Missing coordinate in repeat dot element")

    return RepeatDot(int(xcoord), int(ycoord), character)


def _combine_repeat_dots(points: List[RepeatDot], reference_x: int) -> List[RepeatDots]:
    sorted_dots = list(sorted(points, key=lambda x: (x.x, x.y)))
    output_dots = []
    for dot1, dot2 in zip(sorted_dots[::2], sorted_dots[1::2]):
        if dot1.x == dot2.x:
            output_dots.append(
                RepeatDots(
                    dot1,
                    dot2,
                    RepeatType.BACKWARD if dot1.x < reference_x else RepeatType.FORWARD,
                )
            )
    return output_dots


def _identify_svg_timesigs(root: Element) -> None:
    """Give an identifier to time signature elements.

    Parameters
    ----------
    root : Element
        Root SVG score element.
    """
    time_containers = root.findall(".//svg:g[@class='meterSig']", namespaces=NAMESPACES)
    memory = {}
    for container in time_containers:
        container_id = container.get("id")

        if container_id in memory:
            container.set("id", f"{container_id}_{memory[container_id]}")
            memory[container_id] += 1
        else:
            container.set("id", f"{container_id}_1")
            memory[container_id] = 2


def _identify_svg_dots(root: Element) -> None:
    """Give an identifier to dots.

    Parameters
    ----------
    root : Element
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

        notehead_matrix = np.array(list(map(lambda x: x.as_tuple(), notehead_coords)))
        dot_matrix = np.array(list(map(lambda x: x.as_tuple(), dot_coords)))

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
    root : Element
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
    root : Element
        Root SVG score element.
    """
    note_nodes = root.findall(".//svg:g[@class='note']", namespaces=NAMESPACES)
    for note_node in note_nodes:
        notehead_node = note_node.find(
            "./svg:g[@class='notehead']", namespaces=NAMESPACES
        )
        if notehead_node is not None:
            notehead_node.set("id", f"{note_node.get('id')}.notehead")


def _identify_svg_mrep(root: Element) -> None:
    """Provide an identifier to mrep objects in the SVG.

    Parameters
    ----------
    root : Element
        Root SVG score element.
    """
    measure_nodes = root.xpath(".//svg:g[@class='measure']", namespaces=NAMESPACES)
    for measure_node in measure_nodes:
        measure_repeat = measure_node.find(
            ".//svg:g[@class='mRpt']", namespaces=NAMESPACES
        )
        if measure_repeat is not None:
            measure_repeat.set("id", f"{measure_node.get('id')}.measure_repeat")


def _identify_svg_ending(root: Element) -> None:
    """Provide an identifier to ending objects in the SVG.

    Parameters
    ----------
    root : Element
        Root SVG score element.
    """
    ending_nodes = root.xpath(
        ".//svg:g[@class='ending systemMilestone']", namespaces=NAMESPACES
    )
    for ending_node in ending_nodes:
        bracket = ending_node.find(
            "./svg:g[@class='voltaBracket']", namespaces=NAMESPACES
        )
        if bracket is not None:
            bracket.set("id", f"{ending_node.get('id')}.bracket")


def _identify_svg_flags(root: Element) -> None:
    """Provide an identifier to flag objects in the SVG.

    Parameters
    ----------
    root : Element
        Root SVG score element.
    """
    stem_nodes = root.findall(".//svg:g[@class='stem']", namespaces=NAMESPACES)

    for stem_node in stem_nodes:
        flag_node = stem_node.find("./svg:g[@class='flag']", namespaces=NAMESPACES)
        if flag_node is not None:
            flag_node.set("id", f"{stem_node.get('id')}.flag")


def _identify_svg_tuplet_num(root: Element) -> None:
    """Provide an identifier to tuplet number objects in the SVG.

    Parameters
    ----------
    root : Element
        Root SVG score element.

    """
    tuplet_nodes = root.findall(".//svg:g[@class='tuplet']", namespaces=NAMESPACES)
    for tuplet_node in tuplet_nodes:
        number_node = tuplet_node.find(
            "./svg:g[@class='tupletNum']", namespaces=NAMESPACES
        )
        if number_node is not None:
            number_node.set("id", f"{tuplet_node.get('id')}.number")


def _identify_svg_tuplet_bracket(root: Element) -> None:
    """Provide an identifier to tuplet bracket objects in the SVG.

    Parameters
    ----------
    root : Element
        Root SVG score element.

    """
    tuplet_nodes = root.findall(".//svg:g[@class='tuplet']", namespaces=NAMESPACES)
    for tuplet_node in tuplet_nodes:
        number_node = tuplet_node.find(
            "./svg:g[@class='tupletBracket']", namespaces=NAMESPACES
        )
        if number_node is not None:
            number_node.set("id", f"{tuplet_node.get('id')}.bracket")


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
