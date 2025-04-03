"""Classes for operating on MusicXML."""

from typing import List, Tuple

MAX_DIVISIONS = 16383


class MusicalState:
    def __init__(self, clef: Clef, timesig: TimeSig) -> None:
        self.clef = clef


class MeasureState:
    def __init__(self, staves: int, divisions: int) -> None:
        self._staves = staves
        self._divisions = divisions

        self._substates: List[Tuple[int, MusicalState]] = []

    @classmethod
    def from_previous_measure(cls, measure: "MeasureState") -> "MeasureState":
        ...
