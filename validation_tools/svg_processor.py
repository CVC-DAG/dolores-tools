from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from math import sqrt
from pathlib import Path
from typing import Iterator, List, Tuple

import numpy as np
from lxml import etree
from lxml.etree import _Element as Element

_LOGGER = logging.getLogger(__name__)

NAMESPACES = {
    "svg": "http://www.w3.org/2000/svg",
    "xlink": "http://www.w3.org/1999/xlink",
    "mei": "http://www.music-encoding.org/ns/mei",
}


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


class SVGProcessor:
    """Processes an SVG file to incorporate our needed identifiers."""

    RE_MOVETO_COMMAND = re.compile(r"M(\d+)[, ](\d+)")
    RE_LINETO_COMMAND = re.compile(r"L(\d+)[, ](\d+)")
    RE_BEAM_ID = re.compile(r"beam(\d+)")

    def process(self, svg_file: Path) -> None:
        tree = etree.parse(svg_file)
        root = tree.getroot()

        self._remove_unnecessary_svg(root)
        self._rebuild_svg_beams(root)
        self._rebuild_svg_barlines(root)

        # Performed AFTER changing beams - careful!
        self._identify_svg_timesigs(root)
        self._identify_svg_dots(root)
        self._identify_svg_noteheads(root)
        self._identify_svg_tremolos(root)
        self._identify_svg_flags(root)
        self._identify_svg_tuplet_num(root)
        self._identify_svg_tuplet_bracket(root)
        self._identify_svg_mrep(root)
        self._identify_svg_ending(root)

        etree.indent(tree, "    ")
        tree.write(svg_file)

    def _remove_unnecessary_svg(self, root: Element) -> None:
        """Remove empty SVG group elements and other minor annoyances.

        Parameters
        ----------
        root : Element
            Root element of the score in SVG format.
        """
        group_elements = root.findall(".//svg:g", namespaces=NAMESPACES)
        for child in group_elements:
            if len(child) == 0:
                child.getparent().remove(child)
                _LOGGER.debug(f"Removing subtree: {etree.tostring(child)}")

    def _rebuild_svg_beams(self, root: Element) -> None:
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
            beam_id_match = self.RE_BEAM_ID.match(beam_id)

            if beam_id_match is None:
                raise ValueError("Invalid beam id formatting")
            id_index = int(beam_id_match.group(1))

            new_beams = []

            beam_fragments = beam_node.findall("./svg:polygon", namespaces=NAMESPACES)
            if len(beam_fragments) == 0:
                raise ValueError("Beam without drawn polygons")

            prev_frag = self._get_beam_rectangle(beam_fragments[0])

            for curr_frag in beam_fragments[1:]:
                curr_frag = self._get_beam_rectangle(curr_frag)

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

    def _get_beam_rectangle(self, et_poly: Element) -> Rectangle:
        points = et_poly.get("points")

        if points is None:
            raise ValueError("Beam polygon element has no points attribute")

        points = points.split(" ")

        if len(points) != 4:
            raise ValueError("More than 4 points present in rectangle polygon")

        tl, tr, br, bl = map(lambda x: Point(*map(int, x.split(","))), points)

        return Rectangle(tl, tr, br, bl)

    def _rebuild_svg_barlines(self, root: Element) -> None:
        barlines = root.findall(".//svg:g[@class='barLine']", namespaces=NAMESPACES)
        for barline in barlines:
            self._edit_barline_elements(barline)

    def _edit_barline_elements(self, barline_node: Element) -> None:
        barline_id = barline_node.get("id")

        # Make sure the barline element is not empty
        if len(barline_node) == 0:
            parent = barline_node.getparent()
            if parent is not None:
                parent.remove(barline_node)
            return None
        segments = barline_node.findall("./svg:path", namespaces=NAMESPACES)
        segments = list(map(self._parse_segment, segments))
        segments = self._combine_segments(segments)

        dots = barline_node.findall("./svg:use", namespaces=NAMESPACES)
        dots = list(map(self._parse_repeat_dot, dots))
        dots = self._combine_repeat_dots(dots, segments[0].origin.x)

        for node in barline_node:
            barline_node.remove(node)

        for ii, segment in enumerate(segments, 1):
            barline_node.append(segment.to_svg(f"{barline_id}.barline_tok{ii}"))

        for ii, dot in enumerate(
            [x for x in dots if x.direction == RepeatType.FORWARD], 1
        ):
            barline_node.append(dot.to_svg(f"{barline_id}.repeat_forward{ii}"))

        for ii, dot in enumerate(
            [x for x in dots if x.direction == RepeatType.BACKWARD], 1
        ):
            barline_node.append(dot.to_svg(f"{barline_id}.repeat_backward{ii}"))

    def _parse_segment(self, path_element: Element) -> SvgLine:
        draw_cmd = path_element.get("d")

        if draw_cmd is None:
            raise ValueError("No draw command in Barline segment")

        weight = path_element.get("stroke-width")

        if weight is None:
            raise ValueError("No stroke-width command in Barline segment")

        weight = int(weight)

        move_cmd = self.RE_MOVETO_COMMAND.search(draw_cmd)
        line_cmd = self.RE_LINETO_COMMAND.search(draw_cmd)

        if move_cmd is None or line_cmd is None:
            raise ValueError("Malformed draw command in Barline segment")

        origin_x, origin_y = map(int, move_cmd.groups())
        target_x, target_y = map(int, line_cmd.groups())

        return SvgLine(Point(origin_x, origin_y), Point(target_x, target_y), weight)

    def _combine_segments(self, lines: List[SvgLine]) -> List[SvgLine]:
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

    def _parse_repeat_dot(self, dot_element: Element) -> RepeatDot:
        character = dot_element.get(f"{{{NAMESPACES['xlink']}}}href")
        xcoord = dot_element.get("x")
        ycoord = dot_element.get("y")

        if character is None:
            raise ValueError("No string value in repeat dot element")

        if xcoord is None or ycoord is None:
            raise ValueError("Missing coordinate in repeat dot element")

        return RepeatDot(int(xcoord), int(ycoord), character)

    def _combine_repeat_dots(
        self, points: List[RepeatDot], reference_x: int
    ) -> List[RepeatDots]:
        sorted_dots = list(sorted(points, key=lambda x: (x.x, x.y)))
        output_dots = []
        for dot1, dot2 in zip(sorted_dots[::2], sorted_dots[1::2]):
            if dot1.x == dot2.x:
                output_dots.append(
                    RepeatDots(
                        dot1,
                        dot2,
                        RepeatType.BACKWARD
                        if dot1.x < reference_x
                        else RepeatType.FORWARD,
                    )
                )
        return output_dots

    def _identify_svg_timesigs(self, root: Element) -> None:
        """Give an identifier to time signature elements.

        Parameters
        ----------
        root : Element
            Root SVG score element.
        """
        time_containers = root.findall(
            ".//svg:g[@class='meterSig']", namespaces=NAMESPACES
        )
        memory = {}
        for container in time_containers:
            container_id = container.get("id")

            if container_id in memory:
                container.set("id", f"{container_id}_{memory[container_id]}")
                memory[container_id] += 1
            else:
                container.set("id", f"{container_id}_1")
                memory[container_id] = 2

    def _identify_svg_dots(self, root: Element) -> None:
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

            dots_element = container.find(
                "./svg:g[@class='dots']", namespaces=NAMESPACES
            )
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
                    raise ValueError(
                        "Dot ellipse has no center. Can't identify SVG dots."
                    )

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

            notehead_matrix = np.array(
                list(map(lambda x: x.as_tuple(), notehead_coords))
            )
            dot_matrix = np.array(list(map(lambda x: x.as_tuple(), dot_coords)))

            # Use only y coordinates
            dist_matrix = (
                dot_matrix[:, np.newaxis, 1] - notehead_matrix[np.newaxis, :, 1]
            )
            dist_matrix = np.abs(dist_matrix)

            dot_indices = dist_matrix.argmin(1)

            repeat_dots = {ii: 1 for ii in range(len(notehead_matrix))}

            for dot_ind, note_ind in enumerate(dot_indices):
                note_ob = noteheads[note_ind].getparent().getparent()
                note_id = note_ob.get("id", None)

                dots_element[dot_ind].set("id", f"{note_id}.dot{repeat_dots[note_ind]}")
                repeat_dots[note_ind] += 1

    def _identify_svg_tremolos(self, root: Element) -> None:
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
            for ii, line in enumerate(
                btrem.findall("./svg:use", namespaces=NAMESPACES), 1
            ):
                line.set("id", f"{ident}.line{ii}")
                line.set("class", f"bTrem_line")

    def _identify_svg_noteheads(self, root: Element) -> None:
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

    def _identify_svg_mrep(self, root: Element) -> None:
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

    def _identify_svg_ending(self, root: Element) -> None:
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

    def _identify_svg_flags(self, root: Element) -> None:
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

    def _identify_svg_tuplet_num(self, root: Element) -> None:
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

    def _identify_svg_tuplet_bracket(self, root: Element) -> None:
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
