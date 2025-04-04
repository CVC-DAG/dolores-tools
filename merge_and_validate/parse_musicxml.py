import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union, cast
from xml.etree import ElementTree as ET

from mxml import symbol_table as ST
from mxml import state as MST
from . import mxml as MXML
from mxml.symbols import Clef, Attributes, TimeSig
MeasureID = Tuple[str, str]


class ParserMXML():
    """Navigates a MXML file"""

    def __init__(self) -> None:
        self.state = MST.MeasureState()
        self.symbol_table = ST.SymbolTable()
        self.folder_path = None

        # Super bloated, but necessary since MXML considers each of these kinds of note
        # independent and have to be treated separately.
        # For note groups keep a stack of chords under the same starting level of beams.

        '''self.current_chord: Dict[bool, Optional[MTN.AST.Chord]] = {
            grace: None for grace in [False, True]
        }'''

        #self.group_stack: GroupStack = GroupStack(self.state, self.symbol_table)
        #self.last_measure: Optional[MTN.AST.Measure] = None

    def return_faulty(
        self,
    ) -> None:
        assert self.folder_path is not None, "Please specify which folder to be checked for errors"
        mxml_folder = os.path.join(self.folder_path, "MUSICXML")

        for filename in os.listdir(self.folder_path):
            if filename.lower().endswith('.jpg'):
                for mxml_file in sorted(os.listdir(mxml_folder)):
                    if filename[:-4] + '.01' in mxml_file:
                        
                        full_path = os.path.join(self.folder_path, filename[:-4])


    def get_last_attributes(self, mxml_file: Path) -> Attributes:
        root = ET.parse(mxml_file).getroot()
        for child in root:
            if child.tag == "part":
                part_dict = self._visit_part(child)

                self.symbol_table.reset()


    def _visit_part(
        self,
        part_element: ET.Element,
    ) -> None:
        """Visit a part element and produce a sequence of MTN measures.

        Parameters
        ----------
        part_element : ET.Element
            The part element to visit.
        engr_first_line : Set[MeasureID]
            Set of measure identifiers for those systems that lie at the beginning of a
            line (and thus need a refresh of clef and key elements).

        Returns
        -------
        Dict[MeasureID, MTN.AST.Measure]
            A dictionary with measure identifiers as keys and the measure converted to
            MTN as values.
        """
        for measure in part_element:
            measure_mtn = self._preparse_measure(measure)

    def _preparse_measure(self, measure: ET.Element) -> List[MTN.AST.Attributes]:
        attribute_nodes: List[Attributes] = []
        for child in measure:
            if child.tag == "note":
                self._preparse_note(child)
            elif child.tag == "backup":
                self._backup_or_forward(False, child)
            elif child.tag == "forward":
                self._backup_or_forward(True, child)
            elif child.tag == "attributes":
                attribute_nodes.append(self._visit_attributes(child))
        self.state.change_time(Fraction(0))
        return self.state.attribute_list
        # return attribute_nodes

    def _preparse_note(self, note: ET.Element) -> None:
        print("ENTRA PREPARSE NOTE")
        is_chord = note.find("chord")
        duration_element = note.find("duration")
        if is_chord is not None or duration_element is None:
            return None

        duration = self._visit_duration(duration_element)
        print(self.state)
        self.state.set_buffer(duration)
        print(self.state)
        self.state.move_buffer()
        print(self.state)
        print("SURT PREPARSE_NOTE")

    def _backup_or_forward(
        self,
        forward: bool,
        element: ET.Element,
    ) -> None:
        value_element = element[0]
        assert (
            value_element is not None and value_element.text is not None
        ), "Empty or invalid backup element"

        value = int(value_element.text)
        increment = Fraction(value, self.state.divisions)
        if not forward:
            increment *= -1
        self.state.increment_time(increment)


    def _visit_attributes(
            self,
            attributes: ET.Element,
        ) -> Attributes:
            """Process MXML attributes at a specific point in time.

            Parameters
            ----------
            attributes : ET.Element
                The MXML attribute node.

            Returns
            -------
            MTN.AST.Attributes
                The resulting attributes in MTN format.
            """
            self.state.move_buffer()

            key_elements: List[ET.Element] = []
            timesig_elements: List[ET.Element] = []
            clef_elements: List[ET.Element] = []

            for child in attributes:
                if child.tag == "divisions":
                    if child.text is not None:
                        self.state.divisions = int(child.text)
                elif child.tag == "staves":
                    nstaves = child.text
                    nstaves = cast(str, nstaves)
                    self.state.change_staves(int(nstaves))
                elif child.tag == "key":
                    key_elements.append(child)
                elif child.tag == "time":
                    timesig_elements.append(child)
                elif child.tag == "clef":
                    clef_elements.append(child)

            output_attributes = Attributes(
                self.state._staves,
                self.state.current_time,
            )

            for clef_elm in clef_elements:
                clef = self._visit_clef(clef_elm)
                output_attributes.clef = clef

            for timesig_elm in timesig_elements:
                timesig, staff = self._visit_time(timesig_elm)
                if staff == self._ALL_STAVES:
                    for new_staff in range(1, self.state.nstaves + 1):
                        new_timesig = deepcopy(timesig)
                        token_visitor = VisitorGetTokens()
                        tokens = token_visitor.visit_ast(new_timesig)
                        for tok in tokens:
                            tok.token_id = self.symbol_table.give_identifier()
                            tok.position = MTN.MS.StaffPosition(None, None)
                        output_attributes.set_timesig(new_timesig, new_staff)
                else:
                    output_attributes.timesig[staff] = timesig

            # Merge once to account for the new clef and time, since these are needed for
            # the correct position of key accidentals (could merge a dict and pass it as
            # a parameter to the key processing function but I am lazy).
            self.state.attributes = output_attributes

            for key_elm in key_elements:
                key_processed = self._visit_key(key_elm)
                output_attributes.key |= key_processed

            self.state.attributes = output_attributes

            return output_attributes


    def _visit_clef(
        self,
        clef: ET.Element,
    ) -> Clef:
        
        sign_element = clef.find("sign")
        assert (
            sign_element is not None and sign_element.text is not None
        ), "Invalid clef symbol without a sign"

        clef_type = MXML.TT.ClefSign(sign_element.text)

        if clef_type in {MXML.TT.ClefSign.PERCUSSION, MXML.TT.ClefSign.NONE}:
            clef_type = MXML.TT.ClefSign.G
        elif clef_type in {MXML.TT.ClefSign.TAB, MXML.TT.ClefSign.JIANPU}:
            raise ValueError("Clef type is not supported")

        line_element = clef.find("line")

        '''staff_element = clef.get("number", "1")
        staff = int(staff_element)'''

        print_object_element = clef.get("print-object", "yes")
        print_object = print_object_element == "yes"

        oct_change_element = clef.find("clef-octave-change")
        oct_change = None
        if oct_change_element is not None and oct_change_element.text is not None:
            oct_change = int(oct_change_element.text)

        '''if line_element is not None and line_element.text is not None:
            clef_position = 2 * int(line_element.text)
        else:
            clef_position = MTN.MS.DEFAULT_CLEF_POSITIONS[sign_note]
        '''
        return Clef(
            clef,
            clef_type,
            oct_change,
            line_element,
            print_object
        )
    
    def _visit_time(
        self,
        time: ET.Element,
    ) -> Tuple[MTN.AST.TimeSignature, int]:
        """Generate time signature object from MXML "time" object.

        Parameters
        ----------
        time : ET.Element
            MXML time object.

        Returns
        -------
        MTN.AST.TimeSignature
            The processed MTN time object.
        int
            Staff where this element should be placed. Positive integer for a specific
            placement or self._ALL_STAVES if it applies to all staves.
        """
        time_type = MXML.TT.TimeSymbol(time.get("symbol", "normal"))
        staff_val: Optional[str] = time.get("number", None)
        if staff_val is None:
            staff = self._ALL_STAVES
        else:
            staff = int(staff_val)

        beats, beat_type = self._extract_beats_and_type(time)

        time_value, parse_tree = self.parse_time(beats, beat_type)
        output = MTN.AST.TimeSignature(None, None, time_value)

        if time.get("print-object", "yes") == "no":
            return output, staff

        if time_type == MXML.TT.TimeSymbol.NORMAL:
            output.compound_time_signature = parse_tree

            interchangeable = time.find("interchangeable")
            if interchangeable is not None:
                int_beats, int_beat_type = self._extract_beats_and_type(interchangeable)
                _, interch_parse = self.parse_time(int_beats, int_beat_type)
                interch = [
                    MTN.AST.Token(
                        MTN.TT.TokenType.TIME_RELATION,
                        {"type": MTN.TT.TimeRelation.TR_EQUALS},
                        MTN.MS.StaffPosition(None, None),
                        self.symbol_table.give_identifier(),
                    )
                ] + interch_parse
                output.compound_time_signature += interch
        elif time_type == MXML.TT.TimeSymbol.CUT:
            output.time_symbol = MTN.AST.Token(
                MTN.TT.TokenType.TIMESIG,
                {"type": MTN.TT.TimeSymbol.TS_CUT},
                MTN.MS.StaffPosition(None, None),
                self.symbol_table.give_identifier(),
            )
        elif time_type == MXML.TT.TimeSymbol.COMMON:
            output.time_symbol = MTN.AST.Token(
                MTN.TT.TokenType.TIMESIG,
                {"type": MTN.TT.TimeSymbol.TS_COMMON},
                MTN.MS.StaffPosition(None, None),
                self.symbol_table.give_identifier(),
            )
        elif time_type == MXML.TT.TimeSymbol.NOTE:
            raise UnsupportedElement("Notes as time signatures are not supported")
        elif time_type == MXML.TT.TimeSymbol.DOTTED_NOTE:
            raise UnsupportedElement("Notes as time signatures are not supported")
        elif time_type == MXML.TT.TimeSymbol.SINGLE_NUMBER:
            raise UnsupportedElement("Single nums as time signatures are not supported")

        return output, staff
    
    def _extract_beats_and_type(node: ET.Element) -> Tuple[List[str], List[str]]:
        """Extract the beat and beat_type elements from a time node.

        Compound time signatures are defined in MusicXML by a sequence of "beat" and
        "beat_type" nodes. The point is that complex time signatures can be defined
        adding various smaller ones. This function gathers them and converts them to
        aligned lists of strings with their contents for further processing.

        Parameters
        ----------
        node : ET.Element
            The time element in a MusicXML file.

        Returns
        -------
        Tuple[List[str], List[str]]
            Two lists containing the number of beats and beat type aligned.
        """
        beats = [x.text for x in node.findall("beats") if x.text is not None]
        beat_type = [x.text for x in node.findall("beat-type") if x.text is not None]

        assert len(beats) == len(
            beat_type
        ), "Uneven number of beats and beat types in time signature."

        return beats, beat_type