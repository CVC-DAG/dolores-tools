from __future__ import annotations

import json
import logging
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colormaps
from matplotlib.patches import Polygon, Rectangle

# matplotlib.use("tkagg")

_LOGGER = logging.getLogger(__name__)


class Category(Enum):
    ACCENT = "accent"
    ACCIDENTAL = "accidental"
    ARPEGGIATE = "arpeggiate"
    BARLINE_TOK = "barline_tok"
    BEAM = "beam"
    BRACKET = "bracket"
    BREATH_MARK = "breath_mark"
    CAESURA = "caesura"
    CLEF = "clef"
    CODA = "coda"
    DOIT = "doit"
    DOT = "dot"
    DYN = "dyn"
    ENDING = "ending"
    FALLOFF = "falloff"
    FERMATA = "fermata"
    FLAG = "flag"
    GLISSANDO = "glissando"
    HAYDN = "haydn"
    LEGATO = "legato"
    MORDENT = "mordent"
    NOTEHEAD = "notehead"
    NUMBER = "number"
    OCTAVE_SHIFT = "octave_shift"
    PEDAL = "pedal"
    PLOP = "plop"
    REHEARSAL = "rehearsal"
    REPEAT = "repeat"
    REST = "rest"
    SCHLEIFER = "schleifer"
    SCOOP = "scoop"
    SEGNO = "segno"
    SHAKE = "shake"
    SLIDE = "slide"
    SLUR = "slur"
    STACCATO = "staccato"
    STEM = "stem"
    TENUTO = "tenuto"
    TIE = "tie"
    TIMESIG = "timesig"
    TRILL = "trill"
    TUPLET = "tuplet"
    TURN = "turn"
    WAVY_LINE = "wavy_line"
    WEDGE = "wedge"


@dataclass
class Point:
    x: int
    y: int

    def __add__(self, point: Point) -> Point:
        return Point(self.x + point.x, self.y + point.y)

    def __iadd__(self, point: Point) -> Point:
        self.x += point.x
        self.y += point.y

        return self

    def __mul__(self, factor: float) -> Point:
        return Point(int(self.x * factor), int(self.y * factor))

    def __imul__(self, factor: float) -> Point:
        self.x = int(self.x * factor)
        self.y = int(self.y * factor)

        return self

    def as_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)


@dataclass
class BoundingBox:
    tl: Point
    br: Point

    @property
    def width(self) -> int:
        return self.br.x - self.tl.x

    @property
    def height(self) -> int:
        return self.br.y - self.tl.y

    def get_patch(self) -> Rectangle:
        return Rectangle(self.tl.as_tuple(), self.width, self.height)

    def offset(self, point: Point) -> None:
        self.tl += point
        self.br += point

    def scale(self, factor: float) -> None:
        self.tl *= factor
        self.br *= factor


@dataclass
class Annotation:
    bbox: BoundingBox  # Bounding box around the annotation
    poly: List[Point]  # Polygon representing the annotation
    ident: str  # Object identifier from the MusicXML
    category: Category

    def get_poly_patch(self) -> Polygon:
        point_array = np.array(list(map(lambda x: x.as_tuple(), self.poly)))
        return Polygon(point_array, closed=True)

    def offset(self, point: Point) -> None:
        self.bbox.offset(point)
        self.poly = list(map(lambda x: x + point, self.poly))

    def scale(self, factor: float) -> None:
        self.bbox.scale(factor)
        self.poly = list(map(lambda x: x * factor, self.poly))


@dataclass
class ImageSlice:
    bbox: BoundingBox
    anns: List[Annotation]

    def scale(self, factor: float) -> None:
        self.bbox.scale(factor)
        for ann in self.anns:
            ann.scale(factor)


class DoloresProject:
    def __init__(self, path: Path, scale: Optional[float] = None) -> None:
        self.project_name = path.name
        self.scale = scale

        self.image = plt.imread(path / "images" / f"{self.project_name}.jpg")

        self.id2slice, self.id2category = self._load_annotations(
            path / f"{self.project_name}_final.json"
        )
        if self.scale is not None:
            og_height, og_width, _ = self.image.shape
            self.image = cv2.resize(
                self.image,
                dsize=(int(og_width * self.scale), int(og_height * self.scale)),
            )
            for imslice in self.id2slice.values():
                imslice.scale(self.scale)
        self.category2id = {v: k for k, v in self.id2category.items()}
        self.category_cmap = colormaps["gist_rainbow"]

    def get_category_color(self, cat: Category) -> Tuple[float, float, float, float]:
        max_category = max(self.id2category.keys())
        cur_category = self.category2id[cat]

        return self.category_cmap(cur_category * (1 / max_category))

    def get_all_annotations(self) -> List[Annotation]:
        return [y for x in self.id2slice.values() for y in x.anns]

    def _load_annotations(
        self, ann_path: Path
    ) -> Tuple[Dict[int, ImageSlice], Dict[int, Category]]:
        with open(ann_path, "r") as f_in:
            transcript = json.load(f_in)

        id2category = {x["id"]: Category(x["name"]) for x in transcript["categories"]}
        id2slice = {
            x["id"]: ImageSlice(
                BoundingBox(
                    Point(x["originX"], x["originY"]),
                    Point(x["originX"] + x["width"], x["originY"] + x["height"]),
                ),
                [],
            )
            for x in transcript["images"]
        }

        for ann in transcript["annotations"]:
            im_slice = id2slice[ann["imageId"]]
            polygon = [
                Point(x, y)
                for x, y in zip(ann["segmentation"][0::2], ann["segmentation"][1::2])
            ]
            bbox = BoundingBox(Point(*ann["bbox"][:2]), Point(*ann["bbox"][2:]))
            category = id2category[ann["categoryId"]]

            ob_ann = Annotation(bbox, polygon, ann["id"], category)
            ob_ann.offset(im_slice.bbox.tl)
            im_slice.anns.append(ob_ann)

        return id2slice, id2category

    def plot(self) -> None:
        fig, ax = plt.subplots(dpi=80)

        ax.imshow(self.image)
        ax.set_xticks([])
        ax.set_yticks([])

        for ii, (slice_id, slice_ob) in enumerate(self.id2slice.items()):
            slice_bbox = slice_ob.bbox.get_patch()
            slice_bbox.set(
                color="orange" if ii % 2 == 0 else "red",
                alpha=0.15,
                fill=True,
                hatch="//",
            )
            ax.add_patch(slice_bbox)

            for ann in slice_ob.anns:
                ann_polygon = ann.get_poly_patch()
                ann_polygon.set(color=self.get_category_color(ann.category), fill=False)
                ax.add_patch(ann_polygon)
                ax.text(
                    ann.poly[0].x + 10,
                    ann.poly[0].y + 10,
                    f"{ann.ident} ({ann.category.value})",
                )

        plt.show()


def setup() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        "project_path",
        type=Path,
        help="Path to the DoLoReS project",
    )

    return parser.parse_args()


def main(args: Namespace) -> None:
    project = DoloresProject(args.project_path, 0.25)
    project.plot()


if __name__ == "__main__":
    main(setup())
