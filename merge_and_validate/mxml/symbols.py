from . import types as TT
from lxml import etree
from lxml.etree import _Element as Element

class Clef(SyntaxNode):
    def __init__(
        self,
        lxml_object: Element = None,
        sign: TT.ClefSign = None,
        octave: int = None,
        line: int = None,
    ) -> None:
        self.lxml_object = lxml_object
        self.sign = sign
        self.octave = octave
        self.line = line

class TimeSig:
    def __init__(
        self,
        lxml_object: Element = None,
        time_value: tuple[int, int] = None,
    ) -> None:
        self.time_value = time_value
        self.lxml_object = lxml_object

class Attributes:
    def __init__(
        self,
        lxml_object: Element = None,
        clef: Clef = None,
        timesig: TimeSig = None
    ) -> None:
        self.lxml_object = lxml_object
        self.clef = clef
        self.timesig
        self.key



