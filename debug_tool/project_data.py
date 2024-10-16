from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colormaps
from matplotlib.patches import Polygon, Rectangle

# import matplotlib
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
    MEASURE_REPEAT_OLD = "measure-repeat"  # To keep compatibility with 1.2.1
    MEASURE_REPEAT = "measure_repeat"
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
    TREMOLO_LINE = "tremolo_line"
    TREMOLO_BEAM = "tremolo_beam"
    TRILL = "trill"
    TUPLET = "tuplet"
    TURN = "turn"
    WAVY_LINE = "wavy_line"
    WEDGE = "wedge"

    REPEAT_FORWARD = "repeat_forward1" # Temporal fix
    REPEAT_BACKWARD = "repeat_backward1" # Temporal fix

    def get_category_color(self):
        max_category = len(Category)
        cur_category = list(Category).index(self)

        return colormaps["gist_rainbow"](cur_category * (1 / max_category))


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

    def __str__(self) -> str:
        return f"TL: {self.tl.x}, {self.tl.y} BR: {self.br.x}, {self.br.y}"

    def __repr__(self) -> str:
        return str(self)

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

    def scale(self, factor: float) -> BoundingBox:
        return BoundingBox(self.tl * factor, self.br * factor)


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

    def scale(self, factor: float) -> Annotation:
        return Annotation(
            self.bbox.scale(factor),
            list(map(lambda x: x * factor, self.poly)),
            self.ident,
            self.category,
        )


@dataclass
class ImageSlice:
    slice_idx: int
    bbox: BoundingBox
    anns: List[Annotation]
    gt_file: Optional[Path]

    def scale(self, factor: float) -> ImageSlice:
        return ImageSlice(
            slice_idx=self.slice_idx,
            bbox=self.bbox.scale(factor),
            anns=list(map(lambda x: x.scale(factor), self.anns)),
            gt_file=self.gt_file,
        )


@dataclass
class ProjectMetadata:
    name: str
    date: datetime.datetime
    version: str
    contributor: str


class DoloresProject:
    def __init__(self, path: Path) -> None:
        self.fully_loaded: bool = False

        self.project_path = path
        self.project_name = path.name
        self.project_file = path / f"{self.project_name}_final.json"
        self.image_path = path / "images" / f"{self.project_name}.jpg"

        print(self.project_file)
        
        if not self.project_path.exists():
            raise FileNotFoundError("The path to the project does not exist")

        self.id2slice, self.id2category, self.metadata = self._load_annotations(
            self.project_file
        )

        if not self.image_path.exists():
            _LOGGER.warning("Path to project image not found")
            self.fully_loaded = False

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
    ) -> Tuple[Dict[int, ImageSlice], Dict[int, Category], ProjectMetadata]:

        # Load the data file if possible
        try:
            with open(ann_path, "r") as f_in:
                transcript = json.load(f_in)
        except FileNotFoundError as e:
            _LOGGER.warning(f"There is no final project file for {ann_path}.")
            raise

        # Load the project's metadata
        try:
            metadata = ProjectMetadata(
                self.project_name,
                datetime.datetime.strptime(
                    transcript["info"]["date_created"], "%b %d, %Y %I:%M:%S %p"
                ),
                transcript["info"]["version"],
                transcript["info"]["contributor"],
            )
        except ValueError as e:
            try:
                metadata = ProjectMetadata(
                    self.project_name,
                    datetime.datetime.strptime(
                        transcript["info"]["date_created"], "%b %d, %Y %H:%M:%S"
                    ),
                    transcript["info"]["version"],
                    transcript["info"]["contributor"],
                )
            except ValueError as e:
                _LOGGER.warning(f"Metadata parsing failed for {ann_path}: {e}")
                raise

        # Load the categories within the file
        try:
            id2category = {
                x["id"]: Category(x["name"]) for x in transcript["categories"]
            }
        except ValueError as e:
            _LOGGER.warning(f"Could not load project categories for {ann_path}: {e}")

            return {}, {}, metadata

        # Load image slices
        id2slice = {
            x["id"]: ImageSlice(
                int(x["id"]),
                BoundingBox(
                    Point(x["originX"], x["originY"]),
                    Point(x["originX"] + x["width"], x["originY"] + x["height"]),
                ),
                [],
                self.project_path
                / "files"
                / f"{self.project_name}.{int(x['id']):02}.svg",
            )
            for x in transcript["images"]
        }
        for v in id2slice.values():
            if v.gt_file is not None and not v.gt_file.exists():
                v.gt_file = None
                _LOGGER.warning(
                    f"Ground truth slice {v.slice_idx} for project {self.project_name}"
                )

        # Load annotations
        for ann in transcript["annotations"]:
            im_slice = id2slice[ann["imageId"]]
            polygon = [
                Point(x, y)
                for x, y in zip(ann["segmentation"][0::2], ann["segmentation"][1::2])
            ]
            bbox = BoundingBox(Point(*ann["bbox"][:2]), Point(*ann["bbox"][2:]))
            cat = ann["categoryId"]
            if(cat == 38 and cat not in id2category.keys()):
                id2category[cat] = Category("repeat")
            category = id2category[cat]

            ob_ann = Annotation(bbox, polygon, ann["id"], category)
            ob_ann.offset(im_slice.bbox.tl)
            im_slice.anns.append(ob_ann)

        self.fully_loaded = True
        return id2slice, id2category, metadata

    def plot(
        self,
        annotations: Dict[int, ImageSlice],
        img_path: Path,
        scale: float = 1.0,
    ) -> None:
        fig, ax = plt.subplots(dpi=80)

        # Remove extra space around the plot
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        # Make the figure occupy the entire window
        figManager = plt.get_current_fig_manager()
        figManager.window.state("iconic")

        loaded_image = plt.imread(img_path)

        annotations = {
            ident: imslice.scale(scale) for ident, imslice in annotations.items()
        }
        og_height, og_width, _ = loaded_image.shape
        loaded_image = cv2.resize(
            loaded_image,
            dsize=(int(og_width * scale), int(og_height * scale)),
        )

        ax.imshow(loaded_image)
        ax.set_xticks([])
        ax.set_yticks([])

        for ii, (_, slice_ob) in enumerate(annotations.items()):
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
