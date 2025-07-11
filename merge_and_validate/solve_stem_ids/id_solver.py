import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast
from xml.etree import ElementTree as ET
import json

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

MeasureID = Tuple[str, str]



class UnsupportedElement(ValueError):
    """Exception to throw with (currently) unsupported elements."""


class IdSolver():
    """Navigates a MXML file"""

    def __init__(self, categories_to_check: List[str], list_affected_jsons: bool) -> None:

        self.categories_to_check = categories_to_check       
        self.list_affected_jsons = list_affected_jsons

        self.json_input_folder = "/compartitPau/DoloresDB_Shared/Alignments20250709"
        self.svg_input_folder = "/compartitPau/DoloresDB_Shared/WrongSVG"

        if self.list_affected_jsons:
            self.matching_json_path = "merge_and_validate/solve_stem_ids/matching_id_files.json"

        self.files = {}
        svg_files = sorted(os.listdir(self.svg_input_folder))
        for json_file in sorted(os.listdir(self.json_input_folder)):
            self.files[json_file] = {}
            standard_name = json_file.split('_final')[0]
            for svg in svg_files:
                if standard_name in svg:
                    self.files[json_file][svg] = False

        ns = {"svg": "http://www.w3.org/2000/svg"}
        ET.register_namespace('', ns["svg"])


    def identify_affected_jsons(self) -> None:

        for json_file in os.listdir(self.json_input_folder):
            #Convert self.categories_to_check to their respective category_id
            #Parse elements with these category ids to check if atleast there's one that doesnt contain the category name
            json_path = os.path.join(self.json_input_folder, json_file)
            json_ids = []

            with open(json_path, "r") as f:
                data = json.load(f)
                category_id2name = {
                    cat["id"]: cat.get("name")
                    for cat in data.get("categories", [])
                    if cat.get("name") in self.categories_to_check
                }

                faulty_file = False

                for element in data.get("annotations", []):
                    if element["categoryId"] in category_id2name.keys():

                        json_ids.append(element["id"].split(':')[-1])

                        if category_id2name[element["categoryId"]] not in element["id"]:
                            faulty_file = True
                            break
                
            if not faulty_file:
                del self.files[json_file]
            else:
                for svg_file in self.files[json_file].keys():
                    tree = ET.parse(os.path.join(self.svg_input_folder, svg_file))
                    root = tree.getroot()
                    matching_ids = self.check_id_matching_svg(root, self.categories_to_check, json_ids)
                    self.files[json_file][svg_file] = matching_ids
            print("Checked: ", json_file)

            with open(self.matching_json_path, "w") as matching_file:
                json.dump(self.files, matching_file, indent=4, sort_keys=True)


    def check_id_matching_svg(self, element: ET.Element, target_classes: List[str], json_ids: List[str], class_found: bool = False) -> Optional[bool]:
        # Recursive function that returns False if found any non matching IDs,
        # , False if it found at least one non-matching ID, and None if there
        # were no instances of the classes we are checking
        class_attr = element.attrib.get("class")
        elem_id = element.attrib.get("id")

        if class_attr:
            if class_attr in target_classes and elem_id:
                class_found = True
                if elem_id not in json_ids:
                    return False  # Found a non-matching id, break recursion

        for child in element:
            result = self.check_id_matching_svg(child, target_classes, json_ids, class_found)
            if result is False:
                return False
            elif result is True:
                class_found = True

        return True if class_found else None
           