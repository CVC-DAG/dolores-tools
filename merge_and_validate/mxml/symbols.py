from typing import Optional, List
from lxml.etree import _Element as Element
from copy import deepcopy

from . import types as TT
from . import musicxml as MXML


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
    
    def __str__(self) -> str:
        """Get simple representation for debugging purposes."""
        return (
            f"========= CLEF =========\nsign: {self.sign}\nOctave_Change:"
            f" {self.octave_change}\nLine: {self.line}\nPrint_Object:"
            f" {self.print_object}"
        ) + "\n - - -\n"
    
    def copy(self) -> "Clef":
        return Clef(
            deepcopy(self.lxml_object),
            self.clef.copy(),
            self.timesig.copy(),
            self.key.copy(),
        )

class TimeSig:
    def __init__(
        self,
        lxml_object: Element = None,
        time_value: tuple[int, int] = None,
        staff: int = None,
        time_type: TT.TimeSymbol = None,
        print_object: bool = None
    ) -> None:
        self.lxml_object = lxml_object
        self.time_value = time_value
        self.staff = staff
        self.time_type = time_type
        self.print_object = print_object

    def __str__(self) -> str:
        """Get simple representation for debugging purposes."""
        return (
            f"========= TIME_SIG =========\nTime_Value: {self.time_value}\nStaff:"
            f" {self.staff}\nTime_Type: {self.time_type}\nPrint_Object:"
            f" {self.print_object}"
        ) + "\n - - -\n"
    

class Key:
    def __init__(
        self,
        lxml_object: Element = None,
        is_fifths: bool = None,
        print_object: bool = None,
        fifths: Optional[int] = None,
        cancel: Optional[int] = None,
        alter_steps: Optional[List[MXML.Step]] = None,
        alter_value: Optional[List[int]] = None,
        alter_accidentals: Optional[List[TT.AccidentalValue]] = None
    ) -> None:
        self.lxml_object = lxml_object
        self.is_fifths = is_fifths
        self.print_object = print_object
        self.fifths = fifths
        self.cancel = cancel
        self.alter_steps = alter_steps
        self.alter_value = alter_value
        self.alter_accidentals = alter_accidentals
    
    def __str__(self) -> str:
        """Get simple representation for debugging purposes."""
        assert (
            self.is_fifths is not None
        ), "Key not initialised"
        if self.is_fifths:
            return (
            f"========= KEY =========\nFifths: {self.fifths}\nCancel:"
            f" {self.cancel}\nPrint_Object: {self.print_object}"
            ) + "\n - - -\n"
        else:
            return (
            f"========= KEY =========\nAlter Steps: {self.alter_steps}\nAlter Value:"
            f" {self.alter_value}\nAlter Accidentals: {self.alter_accidentals}\nPrint_Object:"
            f" {self.print_object}"
            ) + "\n - - -\n"

        
        


    
    



