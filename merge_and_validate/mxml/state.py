"""Classes for operating on MusicXML."""

from typing import List, Tuple
from lxml.etree import _Element as Element
from fractions import Fraction
from sortedcontainers import SortedDict
from copy import deepcopy

from .symbols import Clef, TimeSig, Key


MAX_DIVISIONS = 16383


class Attributes:
    def __init__(
        self,
        lxml_object: Element = None,
        clef: Clef = None,
        timesig: TimeSig = None,
        key: Key = None
    ) -> None:
        self.lxml_object = lxml_object
        self.clef = clef
        self.timesig = timesig
        self.key = key

    def merge(self, other: "Attributes") -> None:
        """Combine the contents of two attribute objects into the current one.

        It prioritises the defaults from the caller but overrides anything that is not
        None in the other object.

        Parameters
        ----------
        other : Attributes
            An attributes object to merge with the current one.
        """

        self.lxml_object = other.lxml_object

        if other.key is not None:
            self.key = other.key
        if other.clef is not None:
            self.clef = other.clef
        if other.timesig is not None:
            self.timesig = other.timesig

    def __str__(self) -> str:
        return (
            "===== ATTRIBUTES =====\n"
            f"{self.clef}\n"
            f"{self.key}\n"
            f"{self.timesig}\n"
            "=======================\n"
        )
    
    def copy(self) -> "Attributes":
        
        return Attributes(
            deepcopy(self.lxml_object),
            deepcopy(self.clef),
            deepcopy(self.timesig),
            deepcopy(self.key),
        )


class ScoreState:
    def __init__(self) -> None:
        self.nstaves = 1
        self.divisions = 1
        self.current_time = 0
        self.time_buffer = 0

        # The initial state for a measure. Posterior attributes are computed by
        # composing these initial attributes with a stack of saved attribute elements.
        self.initial_attributes: Attributes = Attributes()

        # The attributes at the current time step (composing the initial state with
        # the stack of states).
        self.current_attributes: Attributes = self.initial_attributes.copy()

        self.stack: SortedDict[int, Attributes] = SortedDict()


    @classmethod
    def from_previous_measure(cls, measure: "ScoreState") -> "ScoreState":
        ...

    def change_staves(self, nstaves: int) -> None:
        """Change the current number of staves within the score.

        Parameters
        ----------
        nstaves : int
            The number of staves to change the part to.
        """
        assert self.current_time == 0, "Changing number of staves mid-measure"
        assert len(self.stack) == 0, "Changing number of staves mid-measure"

        #self.current_attributes = self.initial_attributes.copy()
        self.nstaves = nstaves

    def set_buffer(self, buffer: int) -> None:
        """Set a value for the time buffer.

        The time buffer is the amount of time that will pass on the next call to
        move_buffer. This is used to account for chords when parsing nodes in succession
        from a MXML file.

        Parameters
        ----------
        buffer : int
            Number of fractions of a beat to move the time by.
        """
        self.move_buffer()
        self.time_buffer = buffer

    def move_buffer(self) -> None:
        """Update the current time with the buffer and reset the latter."""
        if self.time_buffer != 0:
            new_time = self.current_time + self.time_buffer
            self.change_time(new_time)

    def increment_time(self, increment: int) -> None:
        """Move the internal time by a set increment (positive or negative).

        Parameters
        ----------
        increment : int
            Amount of fractions of a step to change timer by.
        """
        self.move_buffer()
        target_time = self.current_time + increment
        self.change_time(target_time)

    
    def change_time(self, time: int) -> None:
        """Move the internal timer and update the state accordingly.

        It goes through every state change within the measure, but given that attribute
        nodes should be a rather rare occurrence anyway for the time being this naive
        approach should be enough.

        Parameters
        ----------
        time : Fraction
            What time to move the state to.
        """
        if time < self.current_time:
            if len(self.stack) > 0:
                index = self.stack.bisect_left(time + 0.5)
                self.current_attributes = self.initial_attributes.copy()

                for intermediate in self.stack.keys()[:index]:
                    self.current_attributes.merge(self.stack[intermediate])
        else:
            if len(self.stack) > 0:
                right_index = self.stack.bisect_left(time + 0.5)
                left_index = self.stack.bisect_right(time - 0.5)

                for intermediate in self.stack.keys()[left_index:right_index]:
                    self.current_attributes.merge(self.stack[intermediate])

        self.current_time = time
        self.time_buffer = 0


    @property
    def attributes(self) -> Attributes:
        """Get the current attributes of the score."""
        return self.current_attributes


    @attributes.setter
    def attributes(
        self,
        attributes: Attributes,
    ) -> None:
        """Update the attributes of the score.

        Parameters
        ----------
        attributes : AST.Attributes
            Attributes object currently in use.
        """
        if self.current_time in self.stack:
            self.stack[self.current_time].merge(attributes)
        else:
            self.stack[self.current_time] = attributes

        self.current_attributes.merge(attributes)
