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

    def __init__(self, categories_to_check: List[str], list_affected_jsons: bool) -> None:

        self.categories_to_check = categories_to_check       
        self.list_affected_jsons = list_affected_jsons

        self.json_input_folder = "/compartitPau/DoloresDB_Shared/Alignments20250709"
        self.json_output_folder = "/home/gasbert/Desktop/dolores_fixing/dolores-tools/merge_and_validate/solve_stem_ids/fixed_jsons"
        self.svg_input_folder = "/compartitPau/DoloresDB_Shared/WrongSVG"
        self.svg_output_folder = "/home/gasbert/Desktop/dolores_fixing/dolores-tools/merge_and_validate/solve_stem_ids/fixed_svgs"

        if not os.path.exists(self.json_output_folder):
            os.makedirs(self.json_output_folder)
        if not os.path.exists(self.svg_output_folder):
            os.makedirs(self.svg_output_folder)

        self.files = {}
        self.matching_json_path = "merge_and_validate/solve_stem_ids/matching_id_files.json"

        if self.list_affected_jsons:            
            svg_files = sorted(os.listdir(self.svg_input_folder))
            for json_file in sorted(os.listdir(self.json_input_folder)):
                self.files[json_file] = {}
                standard_name = json_file.split('_final')[0]
                for svg in svg_files:
                    if standard_name in svg:
                        self.files[json_file][svg] = False
        else:
            try:
                with open(self.matching_json_path, "r") as f:
                    self.files = json.load(f)
            except:
                svg_files = sorted(os.listdir(self.svg_input_folder))
                for json_file in sorted(os.listdir(self.json_input_folder)):
                    self.files[json_file] = {}
                    standard_name = json_file.split('_final')[0]
                    for svg in svg_files:
                        if standard_name in svg:
                            self.files[json_file][svg] = False

                self.identify_affected_jsons()

        
        

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
    
    def solve_categories(self) -> None:
        if 'stem' in self.categories_to_check:
            self.solve_stem_and_flag_ids_json()
            self.solve_stem_and_flag_ids_svg()

    def solve_stem_and_flag_ids_json(self) -> None:
        id = 0
        for json_file in self.files.keys():
            id += 1
            if id > 10:
                break
            #Convert self.categories_to_check to their respective category_id
            #Parse elements with these category ids to check if atleast there's one that doesnt contain the category name
            print("ARREGLANT: ", json_file)
            json_path = os.path.join(self.json_input_folder, json_file)
            faulty_stem_objects = {}
            all_noteheads = {}
            stem_ids = []

            with open(json_path, "r") as f:
                # Get stem and notehead categoryIds
                data = json.load(f)
                for cat in data.get("categories", []):
                    if cat.get("name") == "stem":
                        stem_ids.append(cat["id"])
                    if cat.get("name") == "notehead":
                        notehead_id = cat["id"]

                # Get all notehead and stem objects separated by line
                for element in data.get("annotations", []):
                    if element["categoryId"] in stem_ids:
                        if "stem" not in element["id"]:
                            line_id = element["id"].split(':')[0]
                            if line_id not in faulty_stem_objects.keys():
                                faulty_stem_objects[line_id] = {}
                            faulty_stem_objects[line_id][element["id"]] = element["bbox"]
 
                    if element["categoryId"] == notehead_id:
                        line_id = element["id"].split(':')[0]
                        if line_id not in all_noteheads.keys():
                            all_noteheads[line_id] = {}
                        all_noteheads[line_id][element["id"]] = element["bbox"]

                fixed_stem_ids = {}
                fixed_flag_ids = {}

                # For each stem, find which notehead is closer by bbox and create fixed id
                for line in faulty_stem_objects.keys():
                    for stem_object_id, stem_object_bbox in faulty_stem_objects[line].items():
                        # Get corners of stem bbox
                        stem_left, stem_top, width, height = stem_object_bbox
                        stem_corners = [
                            (stem_left, stem_top),
                            (stem_left + width, stem_top),
                            (stem_left, stem_top + height),
                            (stem_left + width, stem_top + height)
                        ]

                        min_dist = float('inf')
                        closest_notehead_id = None

                        for notehead_object_id, notehead_object_bbox in all_noteheads[line].items():
                            note_left, note_top, width, height = notehead_object_bbox
                            note_corners = [
                                (note_left, note_top),
                                (note_left + width, note_top),
                                (note_left, note_top + height),
                                (note_left + width, note_top + height)
                            ]

                            # Compute minimal distance between any pair of corners
                            for sc in stem_corners:
                                for nc in note_corners:
                                    dist = ((sc[0] - nc[0]) ** 2 + (sc[1] - nc[1]) ** 2) ** 0.5
                                    if dist < min_dist:
                                        min_dist = dist
                                        closest_notehead_id = notehead_object_id

                        # Check if the notehead is part of a chord
                        # Agafem svg file corresponent a la linia que ens interessa
                        line_number = line.removeprefix("line").zfill(2)
                        for file in self.files[json_file].keys():
                            if line_number in file.split('.')[-2]:
                                svg_file = file
                                break
                        svg_notehead_id = notehead_object_id.split(':')[-1]
                        tree = ET.parse(os.path.join(self.svg_input_folder, svg_file))
                        root = tree.getroot()
                        is_chord = self.is_chord(root, svg_notehead_id)

                        if is_chord:
                            print("CHORDDD WTFFFFFFFFFFFFFFFFFFF")
                        else:
                            # Construir stem id correcte
                            correct_stem_id = closest_notehead_id.removesuffix("notehead") + "stem"
                            fixed_stem_ids[stem_object_id] = correct_stem_id
                            fixed_flag_ids[stem_object_id + ".flag"] = correct_stem_id + ".flag"
                # Replace stem ids in annotations
                for annotation in data.get("annotations", []):
                    if annotation["id"] in fixed_stem_ids:
                        annotation["id"] = fixed_stem_ids[annotation["id"]]
                    if annotation["id"] in fixed_flag_ids:
                        annotation["id"] = fixed_flag_ids[annotation["id"]]
                # Write the modified data to a new file

                with open(os.path.join(self.json_output_folder, json_file), "w") as out_f:
                    json.dump(data, out_f, indent=4)


    def is_chord(self, svg_root: ET.Element, notehead_id: str) -> bool:
        # Traverse the SVG tree to find the element with the given id
        for elem in svg_root.iter():
            if elem.attrib.get("id") == notehead_id:
                parent_map = {c: p for p in svg_root.iter() for c in p}
                parent = parent_map.get(elem)
                if parent is not None and parent.attrib.get("class") == "chord":
                    return True
                else:
                    return False
        return False


    def solve_stem_and_flag_ids_svg(self) -> None:
        id = 0
        for json_file in self.files.keys():
            id += 1
            if id > 10:
                break
            for svg_file in self.files[json_file].keys():
                tree = ET.parse(os.path.join(self.svg_input_folder, svg_file))
                root = tree.getroot()
                # Build a parent map for quick parent lookup
                parent_map = {c: p for p in root.iter() for c in p}

                for elem in root.iter():
                    if elem.attrib.get("class") == "stem" and "stem" not in elem.attrib["id"]:
                        parent = parent_map.get(elem)
                        # Si no es chord
                        if parent is not None and parent.attrib.get("class") == "note":
                            note_id = parent.attrib.get("id")
                            if note_id:
                                elem.attrib["id"] = f"{note_id}.stem"
                                for child in elem:
                                    if child.attrib.get("class") == "flag" and "stem" not in child.attrib.get("id"):
                                        child.attrib["id"] = f"{note_id}.stem.flag"

                # Write the modified SVG to the output folder
                output_svg_path = os.path.join(self.svg_output_folder, svg_file)
                tree.write(output_svg_path, encoding="utf-8", xml_declaration=True)