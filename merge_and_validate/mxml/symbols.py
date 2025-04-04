from . import types as TT
from lxml import etree
from lxml.etree import _Element as Element

class Clef:
    def __init__(
        self,
        lxml_object: Element = None,
        sign: TT.ClefSign = None,
        octave_change: int = None,
        line: int = None,
        print_object: bool = None
    ) -> None:
        self.lxml_object = lxml_object
        self.sign = sign
        self.octave_change = octave_change
        self.line = line
        self.print_object = print_object

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
    
    



