from mxml import symbol_table as ST
from mxml import state as MST
from . import mxml as MXML
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union, cast
from xml.etree import ElementTree as ET
MeasureID = Tuple[str, str]


class ParserMXML():
    """Navigates a MXML file"""

    def __init__(self) -> None:
        self.state = MST.ScoreState()
        self.symbol_table = ST.SymbolTable()

        # Super bloated, but necessary since MXML considers each of these kinds of note
        # independent and have to be treated separately.
        # For note groups keep a stack of chords under the same starting level of beams.

        '''self.current_chord: Dict[bool, Optional[MTN.AST.Chord]] = {
            grace: None for grace in [False, True]
        }'''

        #self.group_stack: GroupStack = GroupStack(self.state, self.symbol_table)
        #self.last_measure: Optional[MTN.AST.Measure] = None

    def translate(
        self,
        score_in: ET.Element,
        score_id: str,
    ) -> None:
        """Translate a MusicXML score-partwise root element into MTN.

        Parameters
        ----------
        score_in : ET.Element
            The score-partwise element of a MusicXML document.
        engr_first_line : Set[MeasureID]
            Set of measure identifiers for those systems that lie at the beginning of a
            line (and thus need a refresh of clef and key elements).

        Returns
        -------
        MTN.AST.Score
            Representation of the score in MTN.
        """
        for child in score_in:
            if child.tag == "part":
                part_dict = self._visit_part(child)
                                                  

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
        part_id = part_element.get("id", None)
        for measure in part_element:
            measure_id = measure.get("number", None)
            # print(f"measure id: {measure_id} !!!!!!!!!!!!!!!!!!!!!!!!")

            assert isinstance(part_id, str) and isinstance(
                measure_id, str
            ), "PartID or MeasureID could not be found"
            identifier: MeasureID = (part_id, measure_id)

            measure_mtn = self._visit_measure(measure)


    def _visit_measure(
        self,
        measure: ET.Element,
    ) -> None:
        """Visit a measure element and produce a single Measure MTN object.

        Parameters
        ----------
        measure : ET.Element
            A MXML measure element.

        Returns
        -------
        MTN.AST.Measure
            The translation of the measure into MTN.
        """
        measure_subelements: List[MTN.AST.TopLevel] = []
        left_barline: Optional[MTN.AST.Barline] = None
        right_barline: Optional[MTN.AST.Barline] = None

        # This sets up the state and parses all attribute elements
        measure_subelements.extend(self._preparse_measure(measure))


    def _preparse_measure(self, measure: ET.Element) -> List[MTN.AST.Attributes]:
        attribute_nodes: List[MTN.AST.Attributes] = []
        for child in measure:
            if child.tag == "note":
                self._preparse_note(child)
            elif child.tag == "backup":
                self._backup_or_forward(False, child)
            elif child.tag == "forward":
                self._backup_or_forward(True, child)
            elif child.tag == "attributes":
                attribute_nodes.append(self._visit_attributes(child))
        print(self.state)
        self.state.change_time(Fraction(0))
        print(self.state)
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
    ) -> MTN.AST.Attributes:
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

        output_attributes = MTN.AST.Attributes.make_empty(
            self.state.nstaves,
            self.state.current_time,
        )

        for clef_elm in clef_elements:
            clef = self._visit_clef(clef_elm)
            clef_staff = clef.position[0]
            assert clef_staff is not None, "Invalid staff value for clef"
            output_attributes.set_clef(clef, clef_staff)

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
    