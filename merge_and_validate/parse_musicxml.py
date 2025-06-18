import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast
from xml.etree import ElementTree as ET
import json
import requests

#from mxml import symbol_table as ST
from mxml import state as MST
from mxml import musicxml as MXML
from mxml.symbols import Clef, TimeSig, Key, Errors
from mxml import types as TT
MeasureID = Tuple[str, str]

from config import username, password, backend_url


class UnsupportedElement(ValueError):
    """Exception to throw with (currently) unsupported elements."""


class ParserMXML():
    """Navigates a MXML file"""

    _ALL_STAVES = -1

    def __init__(self, print_attributes, print_notes) -> None:
        
        # Backend info
        self.backend_base_url = backend_url
        self.username = username
        self.password = password

        #Backend pre-ops
        self._authenticate()
        self.projects_dict = self._fetch_projects()

        self.states: Dict[List[MST.ScoreState]] = {}
        #self.symbol_table = ST.SymbolTable()
        self.print_attributes = print_attributes
        self.print_notes = print_notes
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

    def _authenticate(self):

        global GLOBAL_ACCESS_TOKEN
        url = f"{self.backend_base_url}/token"
        data = {
            'grant_type': 'password',
            'username': self.username,
            'password': self.password,
            'scope': '',
            'client_id': '',
            'client_secret': '',
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        try:
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            GLOBAL_ACCESS_TOKEN = token_data.get('access_token')
            if not GLOBAL_ACCESS_TOKEN:
                raise Exception("No access_token in response")
        except Exception as e:
            print(f"Error authenticating with backend: {e}")
            GLOBAL_ACCESS_TOKEN = None

    def _fetch_projects(self):
        global GLOBAL_ACCESS_TOKEN
        url = f"{self.backend_base_url}/projects"
        headers = {}
        if GLOBAL_ACCESS_TOKEN:
            headers['Authorization'] = f"Bearer {GLOBAL_ACCESS_TOKEN}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            projects = response.json()
            return {proj["project_id"]: proj["project_name"] for proj in projects}
        except Exception as e:
            print(f"Error fetching projects from backend: {e}")
            return {}


    def _fetch_lines(self, project_id):
        global GLOBAL_ACCESS_TOKEN
        url = f"{self.backend_base_url}/lines/{project_id}"
        headers = {}
        if GLOBAL_ACCESS_TOKEN:
            headers['Authorization'] = f"Bearer {GLOBAL_ACCESS_TOKEN}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching lines for project {project_id}: {e}")
            return None


    def _fetch_musicxml(self, project_id, line_id):
        global GLOBAL_ACCESS_TOKEN
        url = f"{self.backend_base_url}/transcription/musicxml/{project_id}/{line_id}"
        headers = {}
        if GLOBAL_ACCESS_TOKEN:
            headers['Authorization'] = f"Bearer {GLOBAL_ACCESS_TOKEN}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"Error fetching musicxml for project {project_id}, line {line_id}: {e}")
            return None

    def return_faulty(
        self,
    ) -> None:
        """
        Primera passada que comprovi quins scores son erronis comparant els clefs a diferents linies
        """
        for project_id, project_name in self.projects_dict.items():
            #if project_id < 22:
            #    continue
            if "CEDOC_CMM_1.5.1_0082.008" not in project_name:
                continue
            lines_info = self._fetch_lines(project_id)
            if not lines_info or "line_ids" not in lines_info:
                continue
            for line_id in lines_info["line_ids"]:
                print(f"Processing: {project_name} (ID: {project_id}) line {line_id}")
                musicxml_bytes = self._fetch_musicxml(project_id, line_id)
                if not musicxml_bytes:
                    continue
                try:
                    tree = ET.ElementTree(ET.fromstring(musicxml_bytes))
                except Exception as e:
                    print(f"Error parsing MusicXML for project {project_id}, line {line_id}: {e}")
                    continue

                self.parse_for_attributes(tree)
                if(self.print_attributes):
                    print("INITIAL!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    for part in self.states.keys():
                        print("PART ", part+1)
                        print(self.states[part][-1].initial_attributes)
                    print("CURRENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    for part in self.states.keys():
                        print("PART ", part+1)
                        print(self.states[part][-1].current_attributes)

                if line_id != 1:
                    self.check_attributes(project_name, line_id)

            self.states = {}

        with open("faulty_files.json", "w") as json_file:
            json.dump(self.error_dict, json_file, indent=4)
        print("Operació completada! S'han guardat els errors a faulty_files.json")


    def check_attributes(self, score: str, line_id: int) -> None:
        
        # Comprovar diferencies entre clef, key i time de self.states[-2].current_attributes i self.states[-1].initial_attributes
        for part in self.states.keys():

            # CLEF
            if self.states[part][-1].initial_attributes.clef == []:
                self.save_error_to_dict(score, line_id, part+1, Errors.NoClef)
            else:
                if self.states[part][-2].current_attributes.clef != []:
                    for clef in self.states[part][-1].initial_attributes.clef:
                        error = clef.compare(self.states[part][-2].current_attributes.clef) 
                        if error is not None and not clef.print_object:
                            self.save_error_to_dict(score, line_id, part+1, error)

            # KEY
            if self.states[part][-1].initial_attributes.key == []:
                self.save_error_to_dict(score, line_id, part+1, Errors.NoKey)
            else:
                if self.states[part][-2].current_attributes.key is not None:
                    for key in self.states[part][-1].initial_attributes.key:
                        error = key.compare(self.states[part][-2].current_attributes.key)
                        if error is not None and not key.print_object:
                            self.save_error_to_dict(score, line_id, part+1, error)

            # TIMESIG
            if self.states[part][-1].initial_attributes.timesig == []:
                self.save_error_to_dict(score, line_id, part+1, Errors.NoTimesig)
            else:
                if self.states[part][-2].current_attributes.timesig is not None:
                    for time in self.states[part][-1].initial_attributes.timesig:
                        error =  time.compare(self.states[part][-2].current_attributes.timesig)
                        if error is not None and not time.print_object:
                            self.save_error_to_dict(score, line_id, part+1, error)


    def parse_for_attributes(self, mxml_tree: ET.ElementTree) -> None:
        '''
        Funció que actualitzi el score states de la linea amb els atributs inicials i els finals, perque es puguin comparar i veure
          si es canvia de clef amb print_object = Fals (Cas erroni) a la seguent linia
        '''
        part_id = 0
        root = mxml_tree.getroot()
        for child in root:
            if child.tag == "part":
                # Add state to that part state list
                if part_id in self.states and isinstance(self.states[part_id], list):
                    self.states[part_id].append(MST.ScoreState(self.print_notes))
                else:
                    self.states[part_id] = [MST.ScoreState(self.print_notes)]

                self._visit_part(child, part_id)
                part_id += 1


    def save_error_to_dict(self, score: str, line_id: str, part: int, error: Errors) -> None:
        
        if score not in self.error_dict:
                self.error_dict[score] = {}
        if line_id not in self.error_dict[score]:
            self.error_dict[score][line_id] = {}
        if part not in self.error_dict[score][line_id]:
            self.error_dict[score][line_id][part] = [error.value]
        else:
            self.error_dict[score][line_id][part].append(error.value)


    def _visit_part(
        self,
        part_element: ET.Element,
        part_id: int,
    ) -> None:
        for measure in part_element:
            self._visit_measure(measure, part_id)


    def _visit_measure(self, measure: ET.Element, part_id: int) -> None:
        for child in measure:
            if child.tag == "note":
                self._preparse_note(child, part_id)
            elif child.tag == "backup":
                self._backup_or_forward(False, child, part_id)
            elif child.tag == "forward":
                self._backup_or_forward(True, child, part_id)
            elif child.tag == "attributes":
                self._visit_attributes(child, part_id)
        self._new_measure(part_id)
        #self.states.change_time(Fraction(0))

    def _new_measure(self, part_id) -> None:
        # print("NEW MEASURE", end="\n\n")
        self.states[part_id][-1].new_measure()

        # Soooo... apparently musicXML allows beams going from measure to measure...
        # self.group_stack.reset()
        #self.current_chord = {grace: None for grace in [False, True]}
    

    def _preparse_note(self, note: ET.Element, part_id: int) -> None:
        
        is_chord = note.find("chord")
        duration_element = note.find("duration")
        if is_chord is not None or duration_element is None:
            return None

        duration = int(duration_element.text)
        #print(self.states[-1])
        self.states[part_id][-1].set_buffer(duration)
        #print(self.states[-1])
        self.states[part_id][-1].move_buffer()
        #print(self.states[-1])

        if self.print_notes:
            print("PART DE LA NOTA: ", part_id+1)
            print("NOTE!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(self.states[part_id][-1].current_time)
            print("ATTRIBUTES DESPRES DE NOTA!!!!!!!!!!!!!!!!!!!!!!!!!") 
            print(self.states[part_id][-1].current_attributes)


    def _backup_or_forward(
        self,
        forward: bool,
        element: ET.Element,
        part_id: int
    ) -> None:
        value_element = element[0]
        assert (
            value_element is not None and value_element.text is not None
        ), "Empty or invalid backup element"

        increment = int(value_element.text)
        if not forward:
            increment *= -1
        self.states[part_id][-1].increment_time(increment)


    def _visit_attributes(
            self,
            attributes: ET.Element,
            part_id: int,
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
            self.states[part_id][-1].move_buffer()

            key_elements: List[ET.Element] = []
            timesig_elements: List[ET.Element] = []
            clef_elements: List[ET.Element] = []

            for child in attributes:
                if child.tag == "divisions":
                    if child.text is not None:
                        self.states[part_id][-1]._divisions = int(child.text)
                elif child.tag == "staves":
                    nstaves = child.text
                    nstaves = cast(str, nstaves)
                    self.states[part_id][-1].change_staves(int(nstaves))
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
                output_attributes.clef.append(clef)

            for timesig_elm in timesig_elements:
                timesig = self._visit_time(timesig_elm)
                output_attributes.timesig.append(timesig)
                
            # Merge once to account for the new clef and time, since these are needed for
            # the correct position of key accidentals (could merge a dict and pass it as
            # a parameter to the key processing function but I am lazy).

            self.states[part_id][-1].attributes = output_attributes

            for key_elm in key_elements:
                key_processed = self._visit_key(key_elm, part_id)
                output_attributes.key.append(key_processed)

            self.states[part_id][-1].attributes = output_attributes
            
            if self.states[part_id][-1].initial_attributes.xml_object == None:
                self.states[part_id][-1].initial_attributes = output_attributes


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

        staff_element = clef.get("number", "1")
        staff = int(staff_element)

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
            print_object,
            staff
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
        part_id: int,
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
        return self._key_alters(key, part_id)
    

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

        staff_val: Optional[str] = key.get("number", None)
        if staff_val is None:
            staff = self._ALL_STAVES
        else:
            staff = int(staff_val)

        key_fifths = Key(key, is_fifths=True, print_object=print_object, fifths=fifths, cancel=cancel, staff=staff)

        key_fifths.convert_fifths_to_key_alter()
        key_fifths.order_by_alter_steps()

        return key_fifths
        
    

    def _key_alters(
        self,
        key: ET.Element,
        part_id: int,
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

        staff_val: Optional[str] = key.get("number", None)
        if staff_val is None:
            staff = self._ALL_STAVES
        else:
            staff = int(staff_val)

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

        actual_key = Key(key, is_fifths=False, print_object=print_object, alter_steps=alter_steps, 
                   alter_value=alter_values, staff=staff #, alter_accidentals=alter_symbols
                   )
        
        #Si no es la primera key, actualitzar la key anterior amb els canvis afegits a aquesta
        if(len(self.states[part_id]) > 1):
            actual_key.get_absolute_keys(self.states[part_id][-2].current_attributes.key)

        actual_key.order_by_alter_steps()

        return actual_key
