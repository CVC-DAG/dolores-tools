from typing import Optional, List
from xml.etree import ElementTree as ET

from copy import deepcopy
from enum import Enum

from . import types as TT
from . import musicxml as MXML

SHARP_ORDER = ['F', 'C', 'G', 'D', 'A', 'E', 'B']
FLAT_ORDER = ['B', 'E', 'A', 'D', 'G', 'C', 'F']

FIFTHS_TO_ALTERATIONS = {
    -7: [('B', -1), ('E', -1), ('A', -1), ('D', -1), ('G', -1), ('C', -1), ('F', -1)],
    -6: [('B', -1), ('E', -1), ('A', -1), ('D', -1), ('G', -1), ('C', -1)],
    -5: [('B', -1), ('E', -1), ('A', -1), ('D', -1), ('G', -1)],
    -4: [('B', -1), ('E', -1), ('A', -1), ('D', -1)],
    -3: [('B', -1), ('E', -1), ('A', -1)],
    -2: [('B', -1), ('E', -1)],
    -1: [('B', -1)],
     0: [],
     1: [('F', 1)],
     2: [('F', 1), ('C', 1)],
     3: [('F', 1), ('C', 1), ('G', 1)],
     4: [('F', 1), ('C', 1), ('G', 1), ('D', 1)],
     5: [('F', 1), ('C', 1), ('G', 1), ('D', 1), ('A', 1)],
     6: [('F', 1), ('C', 1), ('G', 1), ('D', 1), ('A', 1), ('E', 1)],
     7: [('F', 1), ('C', 1), ('G', 1), ('D', 1), ('A', 1), ('E', 1), ('B', 1)],
}

CANCEL_TO_NATURALS = {
    -7: [('B', 0), ('E', 0), ('A', 0), ('D', 0), ('G', 0), ('C', 0), ('F', 0)],
    -6: [('B', 0), ('E', 0), ('A', 0), ('D', 0), ('G', 0), ('C', 0)],
    -5: [('B', 0), ('E', 0), ('A', 0), ('D', 0), ('G', 0)],
    -4: [('B', 0), ('E', 0), ('A', 0), ('D', 0)],
    -3: [('B', 0), ('E', 0), ('A', 0)],
    -2: [('B', 0), ('E', 0)],
    -1: [('B', 0)],
     0: [],
     1: [('F', 0)],
     2: [('F', 0), ('C', 0)],
     3: [('F', 0), ('C', 0), ('G', 0)],
     4: [('F', 0), ('C', 0), ('G', 0), ('D', 0)],
     5: [('F', 0), ('C', 0), ('G', 0), ('D', 0), ('A', 0)],
     6: [('F', 0), ('C', 0), ('G', 0), ('D', 0), ('A', 0), ('E', 0)],
     7: [('F', 0), ('C', 0), ('G', 0), ('D', 0), ('A', 0), ('E', 0), ('B', 0)],
}

VALUE_TO_ACCIDENTAL = {
    1: TT.AccidentalValue.SHARP,
    0: TT.AccidentalValue.NATURAL,
    -1: TT.AccidentalValue.FLAT
}

class Errors(Enum):
    """
    Possibles error del Dolores
    """

    ClefChangeNoPrintError = "ClefChangeNoPrintError"
    TimesigChangeNoPrintError = "TimesigChangeNoPrintError"
    KeyChangeNoPrintError = "KeyChangeNoPrintError"
    '''Fifhts2FifthsError = "Fifhts2FifthsError"
    Alter2AlterError = "Alter2AlterError"
    Fifths2AlterEquivalent = "Fifths2AlterEquivalent"
    Alter2FifthsEquivalent = "Alter2FifthsEquivalent"
    Fifths2AlterError = "Fifths2AlterError"
    Alter2FifthsError = "Alter2FifthsError"'''
    NoClef = "NoClef"
    NoTimesig = "NoTimesig"
    NoKey = "NoKey"


class Clef:
    def __init__(
        self,
        xml_object: ET.Element = None,
        sign: TT.ClefSign = None,
        octave_change: int = None,
        line: int = None,
        print_object: bool = None
    ) -> None:
        self.xml_object = xml_object
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
            deepcopy(self.xml_object),
            self.clef.copy(),
            self.timesig.copy(),
            self.key.copy(),
        )
    
    def compare(self, other: object) -> Errors:
        if not isinstance(other, Clef):
            return NotImplemented
        if self.sign != other.sign or self.octave_change != other.octave_change:
            return Errors.ClefChangeNoPrintError
        return None

class TimeSig:
    def __init__(
        self,
        xml_object: ET.Element = None,
        time_value: tuple[int, int] = None,
        staff: int = None,
        time_type: TT.TimeSymbol = None,
        print_object: bool = None
    ) -> None:
        self.xml_object = xml_object
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
    
    def compare(self, other: object) -> Errors:
        if not isinstance(other, TimeSig):
            return NotImplemented
        if self.time_value != other.time_value or self.staff != other.staff or \
            self.time_type != other.time_type:
            return Errors.TimesigChangeNoPrintError
        return None
    

class Key:
    def __init__(
        self,
        xml_object: ET.Element = None,
        is_fifths: bool = None,
        print_object: bool = None,
        fifths: Optional[int] = None,
        cancel: Optional[int] = None,
        alter_steps: Optional[List[MXML.Step]] = None,
        alter_value: Optional[List[int]] = None,
        #alter_accidentals: Optional[List[TT.AccidentalValue]] = None
    ) -> None:
        self.xml_object = xml_object
        self.is_fifths = is_fifths
        self.print_object = print_object
        self.fifths = fifths
        self.cancel = cancel
        self.alter_steps = alter_steps
        self.alter_value = alter_value
        #self.alter_accidentals = alter_accidentals
    
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
            f"========= KEY =========\nAlter Steps: {self.alter_steps}"
            f"\nAlter Value: {self.alter_value}"
            #f"\nAlter Accidentals: {self.alter_accidentals}"
            f"\nPrint_Object: {self.print_object}"
            ) + "\n - - -\n"
    
    '''def compare(self, other: object) -> Errors:
        if not isinstance(other, Key):
            return NotImplemented
        if self.is_fifths != other.is_fifths:
            if self.is_fifths:
                conversion_error = other.convert_key_alter_to_fifths(self.fifths)
                if self.fifths != other.fifths or conversion_error:
                    return Errors.Fifths2AlterError
                else:
                    return Errors.Fifths2AlterEquivalent
            else:
                conversion_error = self.convert_key_alter_to_fifths()
                if self.fifths != other.fifths or conversion_error:
                    return Errors.Alter2FifthsError
                else:
                    return Errors.Alter2FifthsEquivalent
        if self.is_fifths:
            if self.fifths != other.fifths:
                return Errors.Fifhts2FifthsError
        else:
            if self.alter_steps != other.alter_steps or self.alter_value != other.alter_value \
                or self.alter_accidentals != other.alter_accidentals:
                return Errors.Alter2AlterError
        return None'''
    
    def compare(self, other: object) -> Errors:
        if not isinstance(other, Key):
            return NotImplemented
        if self.alter_steps != other.alter_steps or self.alter_value != other.alter_value:
            return Errors.KeyChangeNoPrintError
        return None
        

    def convert_key_alter_to_fifths(self, previous_fifths: int = None) -> bool:
        """
        Converts a <key> element in <key-step>/<key-alter> format into a single <fifths> element.
        Also adds a <cancel> element based on the previous key signature, if known.
        
        Parameters:
            key_element (etree._Element): A <key> element from MusicXML.
        """
        key_steps = self.xml_object.findall("key-step")
        key_alters = self.xml_object.findall("key-alter")
        '''print(self.alter_steps)
        print(self.alter_value)
        print(key_steps)
        print(key_alters)'''
        assert len(key_steps) == len(key_alters), (
            "Mismatch between number of <key-step> and <key-alter> elements"
        )

        # Build ordered list of (step, alter)
        alterations = [(step.text, int(alter.text)) for step, alter in zip(key_steps, key_alters)]
        cancel_text = None
        fifths = None

        if len(alterations) == 1:
            step, alt = alterations[0]
            try:
                fifths = TONIC_TO_FIFTHS[(step, alt)]
            except KeyError:
                raise ValueError(f"Tonic {step}{'#' if alt==1 else 'b'} "
                                f"is not a standard key signature")
        else:
            # Validate all alterations are either sharps or flats
            alteration_values = [alter for _, alter in alterations]
            alteration_set = set(alteration_values)
            assert alteration_set <= {1, 0, -1}, (
                f"Unsupported alteration values {alteration_set}. Only pure sharps or flats supported."
            )

            # Validate altered steps are in correct order
            print(alteration_values)
            if 1 in alteration_values:
                sharp_steps = [step for step, alter in alterations if alter == 1]
                if sharp_steps == SHARP_ORDER[:len(sharp_steps)]:
                    fifths = len(sharp_steps)
                else:
                    # Non-conventional key signature (No es pot traduir a fifths)
                    return True

                #Cancel al reduir sharps
                if 0 in alteration_values and len(alteration_values) <= len(SHARP_ORDER):
                    natural_steps = [step for step, alter in alterations if alter == 0]
                    if natural_steps == SHARP_ORDER[len(sharp_steps):len(alteration_values)]:
                        cancel_text = len(alteration_values)
                    

            elif -1 in alteration_values:
                flat_steps = [step for step, alter in alterations if alter == -1]
                if flat_steps == FLAT_ORDER[:len(flat_steps)]:
                    fifths = -len(flat_steps)
                else:
                    # Non-conventional key signature (No es pot traduir a fifths)
                    return True
                
                #Cancel al reduir flats
                if 0 in alteration_values and len(alteration_values) <= len(FLAT_ORDER):
                    natural_steps = [step for step, alter in alterations if alter == 0]
                    if natural_steps == FLAT_ORDER[len(flat_steps):len(alteration_values)]:
                        cancel_text = len(alteration_values)

            #Cancel quan canvia de sharps a flats i viceversa
            if 0 in alteration_values and cancel_text is None:
                natural_steps = [step for step, alter in alterations if alter == 0]
                if natural_steps == FLAT_ORDER[:len(natural_steps)]:
                    cancel_text = -len(natural_steps)
                elif natural_steps == SHARP_ORDER[:len(natural_steps)]:
                    cancel_text = len(natural_steps)
                else:
                    # Non-conventional key signature (No es pot traduir a fifths)
                    return True
                
                if cancel_text is not None and fifths is None:
                    fifths = 0

        '''# Remove existing <key-step> and <key-alter> elements
        for elem in key_steps + key_alters:
            self.xml_object.remove(elem)'''

        # add <cancel> if caller supplied previous value and we intend to print key
        if cancel_text is not None:
            '''cancel = ET.SubElement(self.xml_object, "cancel")
            cancel.text = str(cancel_text)
            cancel.set("mode", "sharp" if cancel_text > 0 else "flat")'''
            self.cancel = cancel_text

        '''fifths_elem = ET.SubElement(self.xml_object, "fifths")
        fifths_elem.text = str(fifths)'''

        # update state
        self.fifths = fifths

        return False
            

    def convert_fifths_to_key_alter(self, previous_key: object = None) -> None:
        """
        Converts a <fifths> value in a <key> element into corresponding
        <key-step> and <key-alter> subelements.

        We don't use get_absolute_keys, as fifths are already absolute.
        """    
        # Get the <fifths> element
        if self.fifths is None:
            raise ValueError("No <fifths> element found")

        if self.fifths not in FIFTHS_TO_ALTERATIONS:
            raise ValueError(f"Invalid fifths value: {self.fifths}")

        # Get the alteration list
        alterations = FIFTHS_TO_ALTERATIONS[self.fifths]  

        self.alter_steps = []
        self.alter_value = []
        #self.alter_accidentals = []
        for step, alter in alterations:
            self.alter_steps.append(MXML.Step[step])
            self.alter_value.append(alter)
            #self.alter_accidentals.append(VALUE_TO_ACCIDENTAL[alter])

        # Get the <cancel> element
        if self.cancel is not None:
            if self.cancel not in CANCEL_TO_NATURALS:
                raise ValueError(f"Invalid cancel value: {self.cancel}")
            alterations = CANCEL_TO_NATURALS[self.cancel]
            self.alter_steps.append(MXML.Step[step])
            self.alter_value.append(0)
            #self.alter_accidentals.append(TT.AccidentalValue.NATURAL)
        
        self.is_fifths = False



    def get_absolute_keys(self, previous_key: object = None) -> None:
        """
        Agafar key anterior, aplicar canvis a la nova key, i actualitzar la key nova amb aquests canvis.
        D'alguna forma ens quedem amb la key absoluta
        """

        actual_steps = previous_key.alter_steps.copy()
        actual_value = previous_key.alter_value.copy()
        #actual_accidentals = previous_key.alter_accidentals.copy()

        #Treu sharps o flats si hi ha naturals a la nova key
        natural_steps = [step for step, val in zip(self.alter_steps, self.alter_value) if val == 0]
        filtered = [
            (step, val)
            for step, val in zip(actual_steps, actual_value)
            if step not in natural_steps
        ]
        if filtered:
            actual_steps, actual_value = zip(*filtered)
            actual_steps = list(actual_steps)
            actual_value = list(actual_value)
            #actual_accidentals = list(actual_accidentals)
        else:
            actual_steps, actual_value = [], []

        #Posar sharps
        sharp_steps = [step for step, val in zip(self.alter_steps, self.alter_value) if val == 1]
        for step in sharp_steps:
            if step in actual_steps:
                idx = actual_steps.index(step)
                #Si hi ha un flat salta error, si ja hi ha un sharp no fem res
                if actual_value[idx] == -1:
                    raise ValueError(f"Can't put a sharp key after a flat key without cancelling first")
            else:
                #En canvi, si no hi ha ningun valor a aquell step, afegim el sharp
                actual_steps.append(step)
                actual_value.append(1)
                #self.alter_accidentals.append(TT.AccidentalValue.SHARP)

        #Posar flats
        flat_steps = [step for step, val in zip(self.alter_steps, self.alter_value) if val == -1]
        for step in flat_steps:
            if step in actual_steps:
                idx = actual_steps.index(step)
                #Si hi ha un sharp salta error, si ja hi ha un flat no fem res
                if actual_value[idx] == 1:
                    raise ValueError(f"Can't put a flat key after a sharp key without cancelling first")
            else:
                #En canvi, si no hi ha ningun valor a aquell step, afegim el flat
                actual_steps.append(step)
                actual_value.append(-1)
                #self.alter_accidentals.append(TT.AccidentalValue.FLAT)

        self.alter_steps = actual_steps
        self.alter_value = actual_value
        #self.alter_accidentals = actual_accidentals

    
    def order_by_alter_steps(self) -> None:
        if len(self.alter_steps) > 1:
            zipped = list(zip(self.alter_steps, self.alter_value))
            zipped_sorted = sorted(zipped, key=lambda x: x[0])
            steps_sorted, value_sorted = zip(*zipped_sorted)

            self.alter_steps = list(steps_sorted)
            self.alter_value = list(value_sorted)
        




    










    
    



