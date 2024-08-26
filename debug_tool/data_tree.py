from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, NamedTuple, Optional

import matplotlib.pyplot as plt
from PIL import Image


class BoundingBox(NamedTuple):
    x: int
    y: int
    w: int
    h: int


class DataTree:
    def __init__(
        self, image: Image, metadata: Dict[str, Any], root: Optional[Node]
    ) -> None:
        self._image = image
        self._metadata = metadata
        self._root = root


class Node(ABC):
    def __init__(
        self,
        parent: Optional[Node],
        children: List[Node],
        bbox: BoundingBox,
    ) -> None:
        self._parent = parent
        self._children = children
        self._bounding_box = BoundingBox

    @abstractmethod
    def plot_self(self, ax: plt.axes) -> None:
        raise NotImplementedError()
