import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast
from xml.etree import ElementTree as ET
import json

#from mxml import symbol_table as ST
from mxml import state as MST
from mxml import musicxml as MXML
from mxml.symbols import Clef, TimeSig, Key, Errors
from mxml import types as TT
MeasureID = Tuple[str, str]


class UnsupportedElement(ValueError):
    """Exception to throw with (currently) unsupported elements."""


class ParserMXML():
    """Navigates a MXML file"""

    _ALL_STAVES = -1

    def __init__(self, folder_path, debug_prints) -> None:

        self.states: List[MST.ScoreState] = []
        #self.symbol_table = ST.SymbolTable()
        self.folder_path = folder_path
        self.debug_prints = debug_prints
        self.error_dict = {}

        #self.actual_line: int = None

        # Super bloated, but necessary since MXML considers each of these kinds of note
        # independent and have to be treated separately.
        # For note groups keep a stack of chords under the same starting level of beams.

        '''self.current_chord: Dict[bool, Optional[MTN.AST.Chord]] = {
            grace: None for grace in [False, True]
        }'''

        #self.group_stack: GroupStack = GroupStack(self.states, self.symbol_table)
        #self.last_measure: Optional[MTN.AST.Measure] = None

    def return_faulty(
        self,
    ) -> None:
        """
        Primera passada que comprovi quins scores son erronis comparant els clefs a diferents linies
        """
        assert self.folder_path is not None, "Please specify which folder to be checked for errors"
        last_mxml = None

        for folder in os.listdir(self.folder_path):
            folder_path = os.path.join(self.folder_path, folder)
            if os.path.isdir(folder_path):
                print("Processing folder: " + folder)
                mxml_folder = os.path.join(folder_path, "MUSICXML")
                # Iterem segons cada carpeta (Ex: CVC.S01.P01) i comparem cada linia amb la seguent
                for score in os.listdir(folder_path):
                    if score.lower().endswith('.jpg'):
                        for mxml_file in sorted(os.listdir(mxml_folder)):
                            if score[:-4] in mxml_file and 'cvc205' not in mxml_file:
                                # Agafar score state per tenir initial_attributes i last_attributes
                                print("Processing line: " + mxml_file)
                                self.states.append(MST.ScoreState())
                                mxml_path = os.path.join(mxml_folder, mxml_file)
                                self.parse_for_attributes(mxml_path)

                                if(self.debug_prints):
                                    print("INITIAL!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                                    print(self.states[-1].initial_attributes)
                                    print("CURRENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                                    print(self.states[-1].current_attributes)
                                
                                if last_mxml is not None:
                                    self.check_attributes(folder, score[:-4], mxml_file)

                                last_mxml = mxml_file
                        last_mxml = None

        with open("faulty_files.json", "w") as json_file:
            json.dump(self.error_dict, json_file, indent=4)


    def check_attributes(self, folder: str, score: str, mxml_file: str) -> None:
        # Comprovar diferencies entre clef, key i time de self.states[-2].current_attributes i self.states[-1].initial_attributes

        # CLEF
        error = self.states[-2].current_attributes.clef.compare(self.states[-1].initial_attributes.clef) 
        if error is not None and not self.states[-1].initial_attributes.clef.print_object:
            if folder not in self.error_dict:
                self.error_dict[folder] = {}
            if score not in self.error_dict[folder]:
                self.error_dict[folder][score] = {}
            self.error_dict[folder][score][mxml_file] = error.value
        
        # KEY
        error = self.states[-2].current_attributes.key.compare(self.states[-1].initial_attributes.key)
        if error is not None and not self.states[-1].initial_attributes.key.print_object:
            if folder not in self.error_dict:
                self.error_dict[folder] = {}
            if score not in self.error_dict[folder]:
                self.error_dict[folder][score] = {}
            self.error_dict[folder][score][mxml_file] = error.value

        # TIMESIG
        error =  self.states[-2].current_attributes.timesig.compare(self.states[-1].initial_attributes.timesig)
        if error is not None and not self.states[-1].initial_attributes.timesig.print_object:
            if folder not in self.error_dict:
                self.error_dict[folder] = {}
            if score not in self.error_dict[folder]:
                self.error_dict[folder][score] = {}
            self.error_dict[folder][score][mxml_file] = error.value


    def parse_for_attributes(self, mxml_file: Path) -> None:
        '''
        Funció que actualitzi el score states de la linea amb els atributs inicials i els finals, perque es puguin comparar i veure
          si es canvia de clef amb print_object = Fals (Cas erroni) a la seguent linia
        '''
        root = ET.parse(mxml_file).getroot()
        for child in root:
            if child.tag == "part":
                self._visit_part(child)

                # Haig de mirar-me més a fons la utilitat de la symbol_table
                #self.symbol_table.reset()


    def _visit_part(
        self,
        part_element: ET.Element,
    ) -> None:
        for measure in part_element:
            self._visit_measure(measure)


    def _visit_measure(self, measure: ET.Element) -> None:
        for child in measure:
            if child.tag == "note":
                self._preparse_note(child)
            elif child.tag == "backup":
                self._backup_or_forward(False, child)
            elif child.tag == "forward":
                self._backup_or_forward(True, child)
            elif child.tag == "attributes":
                self._visit_attributes(child)
        self._new_measure()
        #self.states.change_time(Fraction(0))

    def _new_measure(self) -> None:
        # print("NEW MEASURE", end="\n\n")
        self.states[-1].new_measure()

        # Soooo... apparently musicXML allows beams going from measure to measure...
        # self.group_stack.reset()
        #self.current_chord = {grace: None for grace in [False, True]}
    

    def _preparse_note(self, note: ET.Element) -> None:
        
        is_chord = note.find("chord")
        duration_element = note.find("duration")
        if is_chord is not None or duration_element is None:
            return None

        duration = int(duration_element.text)
        #print(self.states[-1])
        self.states[-1].set_buffer(duration)
        #print(self.states[-1])
        self.states[-1].move_buffer()
        #print(self.states[-1])

    def _backup_or_forward(
        self,
        forward: bool,
        element: ET.Element,
    ) -> None:
        value_element = element[0]
        assert (
            value_element is not None and value_element.text is not None
        ), "Empty or invalid backup element"

        increment = int(value_element.text)
        if not forward:
            increment *= -1
        self.states[-1].increment_time(increment)


    def _visit_attributes(
            self,
            attributes: ET.Element,
        ) -> None:
            """Process MXML attributes at a specific point in time and updates them in the score states

            Parameters
            ----------
            attributes : ET.Element
                The MXML attribute node.

            Returns
            -------
            MTN.AST.MST.Attributes
                The resulting attributes in MTN format.
            """
            self.states[-1].move_buffer()

            key_elements: List[ET.Element] = []
            timesig_elements: List[ET.Element] = []
            clef_elements: List[ET.Element] = []

            for child in attributes:
                if child.tag == "divisions":
                    if child.text is not None:
                        self.states[-1]._divisions = int(child.text)
                elif child.tag == "staves":
                    nstaves = child.text
                    nstaves = cast(str, nstaves)
                    self.states[-1].change_staves(int(nstaves))
                elif child.tag == "key":
                    key_elements.append(child)
                elif child.tag == "time":
                    timesig_elements.append(child)
                elif child.tag == "clef":
                    clef_elements.append(child)

            output_attributes = MST.Attributes(attributes)

            # Revisar que sha de fer en el cas de tenir mes d'una clef en un attributes
            for clef_elm in clef_elements:
                clef = self._visit_clef(clef_elm)
                #print(clef)
                output_attributes.clef = clef

            for timesig_elm in timesig_elements:
                timesig = self._visit_time(timesig_elm)
                output_attributes.timesig = timesig
                
            # Merge once to account for the new clef and time, since these are needed for
            # the correct position of key accidentals (could merge a dict and pass it as
            # a parameter to the key processing function but I am lazy).

            self.states[-1].attributes = output_attributes

            for key_elm in key_elements:
                key_processed = self._visit_key(key_elm)
                output_attributes.key = key_processed

            self.states[-1].attributes = output_attributes
            
            if self.states[-1].initial_attributes.xml_object == None:
                self.states[-1].initial_attributes = output_attributes





    def _visit_clef(
        self,
        clef: ET.Element,
    ) -> Clef:
        
        sign_element = clef.find("sign")
        assert (
            sign_element is not None and sign_element.text is not None
        ), "Invalid clef symbol without a sign"

        clef_type = TT.ClefSign(sign_element.text)

        if clef_type in {TT.ClefSign.PERCUSSION, TT.ClefSign.NONE}:
            clef_type = TT.ClefSign.G
        elif clef_type in {TT.ClefSign.TAB, TT.ClefSign.JIANPU}:
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
    ) -> TimeSig:
        
        time_type = TT.TimeSymbol(time.get("symbol", "normal"))
        staff_val: Optional[str] = time.get("number", None)
        if staff_val is None:
            staff = self._ALL_STAVES
        else:
            staff = int(staff_val)

        beats, beat_type = self._extract_beats_and_type(time)

        print_object = time.get("print-object", "yes") == "yes"

        if time_type == TT.TimeSymbol.NOTE:
            raise UnsupportedElement("Notes as time signatures are not supported")
        elif time_type == TT.TimeSymbol.DOTTED_NOTE:
            raise UnsupportedElement("Notes as time signatures are not supported")
        elif time_type == TT.TimeSymbol.SINGLE_NUMBER:
            raise UnsupportedElement("Single nums as time signatures are not supported")

        return TimeSig(
            time,
            (beats, beat_type),
            staff,
            time_type,
            print_object
        )
    
    def _extract_beats_and_type(self, node: ET.Element) -> Tuple[List[str], List[str]]:
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
    
    def _visit_key(
        self,
        key: ET.Element,
    ) -> Dict[int, Key]:
        """Visit a key element in MXML and get its information.

        Parameters
        ----------
        key : ET.Element
            The MXML key node.

        Returns
        -------
        Dict[int, MTN.AST.Key]
            A dictionary mapping each staff with the corresponding key.
        """
        
        if key[0].tag in {"cancel", "fifths"}:
            return self._key_fifths(key)
        return self._key_alters(key)
    

    def _key_fifths(
        self,
        key: ET.Element
    ) -> Key:
        """Generate the key element denoted by a number of fifths upward or downward.

        Parameters
        ----------
        key : ET.Element
            Element in the MXML tree for a key.
        staff: int
            What staff this key applies to.

        Returns
        -------
        MTN.AST.Key
            Same key in MTN format.
        """
        cancel = None

        for child in key:
            if child.tag == "cancel":
                if child.text is None:
                    continue
                cancel = int(child.text)

            elif child.tag == "fifths":
                if child.text is None:
                    continue
                fifths = int(child.text)

        print_object_element = key.get("print-object", "yes")
        print_object = print_object_element == "yes"

        return Key(key, is_fifths=True, print_object=print_object, fifths=fifths, cancel=cancel)
    

    def _key_alters(
        self,
        key: ET.Element
    ) -> Key:
        """Process a key using a list of arbitrary alterations.

        Parameters
        ----------
        key : ET.Element
            MXML element with the key information.

        Returns
        -------
        MTN.AST.Key
            Same key in MTN format.
        """
        alter_steps = []
        alter_values = []
        alter_symbols = []

        for child in key:
            if child.tag == "key-step":
                if child.text is None:
                    raise ValueError("Invalid empty key-step element.")
                alter_steps.append(MXML.Step[child.text])

            elif child.tag == "key-alter":
                if child.text is None:
                    raise ValueError("Invalid empty key-step element.")
                value = int(child.text)
                alter_values.append(value)

                alter_symbols.append(
                    TT.AccidentalValue.SHARP
                    if value > 0
                    else TT.AccidentalValue.FLAT
                )

            elif child.tag == "key-accidental":
                if child.text is not None:
                    alter_symbols[-1] = TT.AccidentalValue(child.text)

        print_object_element = key.get("print-object", "yes")
        print_object = print_object_element == "yes"

        return Key(key, is_fifths=False, print_object=print_object, alter_steps=alter_steps, 
                   alter_value=alter_values, alter_accidentals=alter_symbols)
