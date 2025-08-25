import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast
from xml.etree import ElementTree as ET
import json
import copy
from collections import defaultdict

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
            #self.solve_stem_flag_chord_ids_svg()
            self.solve_stem_and_flag_ids_json()
            

    def solve_stem_and_flag_ids_json(self) -> None:
        id = 0
        for json_file in self.files.keys():
            id += 1
            '''if id < 21:
                continue'''
            '''if "XAC_ACAN_SMIAu63_082_" not in json_file:
                continue'''
            #Convert self.categories_to_check to their respective category_id
            #Parse elements with these category ids to check if atleast there's one that doesnt contain the category name
            print("ARREGLANT: ", json_file)
            json_path = os.path.join(self.json_input_folder, json_file)
            faulty_stem_objects = {}
            all_noteheads = {}
            stem_ids = []
            already_correct_stems = {}
            stem_ids.append(28)

            with open(json_path, "r") as f:
                # Get stem and notehead categoryIds
                data = json.load(f)
                for cat in data.get("categories", []):
                    # El id de la categoria line1:note2.stem.line1 tambe es stem, aixi que li poso el 28 i ja esta
                    #if cat.get("name") == "stem":
                    #    stem_ids.append(cat["id"])
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
                        else:
                            line_id = element["id"].split(':')[0]
                            if line_id not in already_correct_stems.keys():
                                already_correct_stems[line_id] = []
                            already_correct_stems[line_id].append(element["id"].split(':')[1].removesuffix(".stem"))

 
                    if element["categoryId"] == notehead_id:
                        line_id = element["id"].split(':')[0]
                        if line_id not in all_noteheads.keys():
                            all_noteheads[line_id] = {}
                        all_noteheads[line_id][element["id"].split(':')[-1]] = element["bbox"]

                fixed_stem_ids = {}
                fixed_flag_ids = {}

                # For each stem, find which notehead is closer by bbox and create fixed id
                for line in faulty_stem_objects.keys():
                    #print(line)

                    # Agafem svg file corresponent a la linia que ens interessa
                    line_number = line.removeprefix("line").zfill(2)
                    if line_number == "00":
                        n_lines_svg = sum(1 for f in os.listdir(self.svg_output_folder) if json_file.removesuffix("_final.json") in f)
                        if n_lines_svg > 1:
                            print("linies amb valor 00000000000000000000000000000 wtfffffffff")
                            continue
                        else:
                            line_number = "01"

                    for file in self.files[json_file].keys():
                        if line_number in file.split('.')[-2]:
                            svg_file = file
                            break
                    
                    tree = ET.parse(os.path.join(self.svg_output_folder, svg_file))
                    svg_output_root = tree.getroot()

                    stem_parent_dict = self.get_available_stem_parents_dict(svg_output_root, line)
                    
                    # Trec parents que ja tinguin el stem correcte
                    if line in already_correct_stems.keys():
                        for correct_parent in already_correct_stems[line]:
                            if correct_parent in stem_parent_dict.keys():
                                del stem_parent_dict[correct_parent]
                    
                    stem_parent_to_noteheads_dict, stem_parent_dict = self.get_stem_parent_to_noteheads_dict(svg_output_root, stem_parent_dict)
                    
                    available_noteheads = [nh for noteheads in stem_parent_to_noteheads_dict.values() for nh in noteheads]
                    notehead_bboxes = {k: v for k, v in all_noteheads[line].items() if k in available_noteheads}
                    
                    # Cas en el que una notehead esta al svg pero no al json
                    missing_noteheads = [nh for nh in available_noteheads if nh not in notehead_bboxes]
                    if missing_noteheads:   
                        #Treure noteheads d'available noteheads
                        available_noteheads = [x for x in available_noteheads if x not in missing_noteheads]
                        #Treure noteheads de stem_parent_to_notehead
                        for parent in stem_parent_to_noteheads_dict:
                            stem_parent_to_noteheads_dict[parent] = [nh for nh in stem_parent_to_noteheads_dict[parent] if nh not in missing_noteheads]
                        #Treure parents buits a stem_parent_to_notehead de stem_parent_to_notehead i stem_parent dict
                        for parent in list(stem_parent_to_noteheads_dict.keys()):
                            if not stem_parent_to_noteheads_dict[parent]:  # empty list
                                del stem_parent_to_noteheads_dict[parent]
                                del stem_parent_dict[parent]

                    all_distances_dict = {}
                    for parent in stem_parent_dict.keys():
                        all_distances_dict[parent] = {}
                    
                    # Creem una matriu (feta de diccionaris) de distancies entre stems i objectes pare
                    for stem_object_id, stem_object_bbox in faulty_stem_objects[line].items():
                        # Get corners of stem bbox
                        stem_left, stem_top, width, height = stem_object_bbox
                        stem_corners = [
                            (stem_left, stem_top),
                            (stem_left + width, stem_top),
                            (stem_left, stem_top + height),
                            (stem_left + width, stem_top + height)
                        ]

                        for notehead_object_id, notehead_object_bbox in notehead_bboxes.items():
                            min_dist = float('inf')

                            note_left, note_top, width, height = notehead_object_bbox
                            note_corners = [
                                (note_left, note_top),
                                (note_left + width, note_top),
                                (note_left, note_top + height),
                                (note_left + width, note_top + height)
                            ]

                            # Compute minimal distance between any pair of corners
                            overlapping = self.check_bbox_overlap(stem_object_bbox, notehead_object_bbox)
                            for sc in stem_corners:
                                for nc in note_corners:
                                    dist = ((sc[0] - nc[0]) ** 2 + (sc[1] - nc[1]) ** 2) ** 0.5
                                    # If both bounding boxes overlap they get bonus points
                                    if overlapping:
                                        dist = dist - 10
                                    if dist < min_dist:
                                        min_dist = dist
                            
                            stem_parent = next(k for k, v in stem_parent_to_noteheads_dict.items() if notehead_object_id in v)
                            if stem_object_id in all_distances_dict[stem_parent].keys():
                                if min_dist < all_distances_dict[stem_parent][stem_object_id]:
                                    all_distances_dict[stem_parent][stem_object_id] = min_dist
                            else:
                                all_distances_dict[stem_parent][stem_object_id] = min_dist
                    x = 1
                    # Assignem stem amb minima distancia a cada objecte pare, resolent duplicats
                    result = self.final_stem_assigning(all_distances_dict)

                    for parent, stems_dict in result.items():
                        # stems_dict has only one key-value pair
                        stem, value = next(iter(stems_dict.items()))
                        
                        whole_stem_id = line + ':' + parent + '.stem'
                        fixed_stem_ids[stem] = whole_stem_id
                                                
         
                    '''for stem_object_id, (whole_stem_id, closest_notehead_id, min_dist) in fixed_stem_ids.items():
                        fixed_flag_ids[stem_object_id + ".flag"] = whole_stem_id + ".flag"'''

                # Replace stem ids in annotations
                new_annotations = []
                for annotation in data.get("annotations", []):
                    if annotation["id"] in fixed_stem_ids:
                        annotation["id"] = fixed_stem_ids[annotation["id"]]
                        new_annotations.append(annotation)
                    '''elif annotation["id"] in fixed_flag_ids:
                        #Comprovar que la flag existeixi al svg
                        annotation["id"] = fixed_flag_ids[annotation["id"]]
                        new_annotations.append(annotation)'''

                data["annotations"] = new_annotations

                with open(os.path.join(self.json_output_folder, json_file), "w") as out_f:
                    json.dump(data, out_f, indent=4)


    def is_chord(self, svg_root: ET.Element, note_id: str) -> bool:
        # Traverse the SVG tree to find the element with the given id
        for elem in svg_root.iter():
            if elem.attrib.get("id") == note_id:
                parent_map = {c: p for p in svg_root.iter() for c in p}
                parent = parent_map.get(elem)
                if parent is not None and parent.attrib.get("class") == "chord":
                    return True
                else:
                    return False
        return False
    
    def get_brother_stem_id(self, svg_root: ET.Element, note_id: str) -> str:
        for elem in svg_root.iter():
            if elem.attrib.get("id") == note_id:
                parent_map = {c: p for p in svg_root.iter() for c in p}
                parent = parent_map.get(elem)
                if parent is not None:
                    for sibling in parent:
                        if sibling.attrib.get("class") == "stem":
                            return sibling.attrib.get("id")
                return None



    def solve_stem_flag_chord_ids_svg(self) -> None:
        id = 0
        for json_file in self.files.keys():
            id += 1
            '''if id > 10:
                break'''
            for svg_file in self.files[json_file].keys():
                print("ARREGLANT: ", svg_file)
                tree = ET.parse(os.path.join(self.svg_input_folder, svg_file))
                root = tree.getroot()
                # Build a parent map for quick parent lookup
                parent_map = {c: p for p in root.iter() for c in p}

                # Fix chords
                for elem in root.iter():
                    if elem.attrib.get("class") == "chord" and "chord" not in elem.attrib["id"]:
                        new_id = "chord."
                        for child in elem:
                            if child.attrib.get("class") == "note":
                                if new_id == "chord.":
                                    new_id += child.attrib["id"]
                                else:
                                    new_id = new_id + "_" + child.attrib["id"]
                        if new_id != "chord.":
                            elem.attrib["id"] = new_id


                for elem in root.iter():
                    if elem.attrib.get("class") == "stem":
                        # M'he trobat alguna stem que no te id
                        if "id" not in elem.attrib:
                            continue
                        if "stem" not in elem.attrib["id"]:
                            parent = parent_map.get(elem)
                            # Si no es chord
                            if parent is not None and (parent.attrib.get("class") == "note" or parent.attrib.get("class") == "chord"):
                                parent_id = parent.attrib.get("id")
                                if parent_id:
                                    elem.attrib["id"] = f"{parent_id}.stem"
                                    for child in elem:
                                        if child.attrib.get("class") == "flag" and "stem" not in child.attrib.get("id"):
                                            child.attrib["id"] = f"{parent_id}.stem.flag"

                # Write the modified SVG to the output folder
                output_svg_path = os.path.join(self.svg_output_folder, svg_file)
                tree.write(output_svg_path, encoding="utf-8", xml_declaration=True)

    def check_bbox_overlap(self, box1, box2):
        """
        Checks if two bounding boxes overlap.

        Each box is a tuple (left, top, width, height).
        Returns True if the boxes overlap, False otherwise.
        """
        left1, top1, width1, height1 = box1
        left2, top2, width2, height2 = box2

        right1 = left1 + width1
        bottom1 = top1 + height1
        right2 = left2 + width2
        bottom2 = top2 + height2

        # Check for no overlap condition
        if right1 <= left2 or right2 <= left1:
            return False
        if bottom1 <= top2 or bottom2 <= top1:
            return False

        return True
    

    def buscar_repetits(self, fixed_stem_ids, chord_to_noteheads):
                        
        repeated = {}
        # Group stem_object_ids by closest_notehead_id
        for stem_object_id, (whole_stem_id, closest_notehead_id, min_dist) in fixed_stem_ids.items():
            
            # Check if a notehead is part of a chord and always get first notehead
            for chord_id, note_ids in chord_to_noteheads.items():
                if closest_notehead_id in note_ids:
                    closest_notehead_id = note_ids[0]
                    break

            if closest_notehead_id not in repeated:
                repeated[closest_notehead_id] = ([], [])
            repeated[closest_notehead_id][0].append(stem_object_id)
            repeated[closest_notehead_id][1].append(min_dist)

        # Filter out entries that are not truly repeated (only 1 stem)
        repeated = {
            notehead_id: (stem_ids, dists)
            for notehead_id, (stem_ids, dists) in repeated.items()
            if len(stem_ids) > 1
        }

        return repeated
    

    def llista_stems_a_canviar(self, repeated, noteheads_prohibides, chord_to_noteheads):
        # QUE RETORNI STEMS A CANVIAR, NOTEHEADS PROHIBIDES

        stems_a_canviar = []
        for closest_notehead_id, (stem_ids, min_dists) in repeated.items():
            paired = zip(stem_ids, min_dists)
            best_stem_id, best_min_dist = min(paired, key=lambda x: x[1])
            for stem_id in stem_ids:
                if stem_id != best_stem_id:
                    stems_a_canviar.append(stem_id)
                    
                    # Si es una chord posem totes les noteheads de la chord com a prohibides
                    noteheads = None
                    for chord_id, note_ids in chord_to_noteheads.items():
                        if closest_notehead_id in note_ids:
                            noteheads = note_ids
                            break
                    if noteheads is None:
                        noteheads = [closest_notehead_id]
                    
                    if stem_id not in noteheads_prohibides.keys():
                        noteheads_prohibides[stem_id] = []
                    for notehead_id in noteheads:
                        noteheads_prohibides[stem_id].append(notehead_id)

        return stems_a_canviar, noteheads_prohibides
    

    def actualitzar_noteheads(self, fixed_stem_ids, all_noteheads, stems_a_canviar, noteheads_prohibides, faulty_stem_objects, line, json_file):
        
        for stem_object_id, stem_object_bbox in faulty_stem_objects[line].items():
            if stem_object_id in stems_a_canviar:
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
                    if notehead_object_id in noteheads_prohibides[stem_object_id]:
                        continue
                    note_left, note_top, width, height = notehead_object_bbox
                    note_corners = [
                        (note_left, note_top),
                        (note_left + width, note_top),
                        (note_left, note_top + height),
                        (note_left + width, note_top + height)
                    ]

                    # Compute minimal distance between any pair of corners
                    overlapping = self.check_bbox_overlap(stem_object_bbox, notehead_object_bbox)
                    for sc in stem_corners:
                        for nc in note_corners:
                            dist = ((sc[0] - nc[0]) ** 2 + (sc[1] - nc[1]) ** 2) ** 0.5
                            # If both bounding boxes overlap they get bonus points
                            if overlapping:
                                dist = dist - 10
                            if dist < min_dist:
                                min_dist = dist
                                closest_notehead_id = notehead_object_id

                # Si li assigna una notehead, funciona de forma normal
                if closest_notehead_id:
                    # Check if the notehead is part of a chord
                    # Agafem svg file corresponent a la linia que ens interessa
                    line_number = line.removeprefix("line").zfill(2)
                    if line_number == "00":
                        line_number = "01"

                    for file in self.files[json_file].keys():
                        if line_number in file.split('.')[-2]:
                            svg_file = file
                            break

                    svg_notehead_id = closest_notehead_id.split(':')[-1]
                    svg_note_id = svg_notehead_id.split('.')[0]
                    
                    tree = ET.parse(os.path.join(self.svg_input_folder, svg_file))
                    root = tree.getroot()
                    is_chord = self.is_chord(root, svg_note_id)

                    if is_chord:
                        #Buscar la mateixa note al fixed svg, agafar el id del stem germa i ficarlo com a id al json 
                        tree = ET.parse(os.path.join(self.svg_output_folder, svg_file))
                        root = tree.getroot()
                        correct_stem_id = self.get_brother_stem_id(root, svg_note_id)
                        if correct_stem_id is not None:
                            whole_stem_id = line + ":" + correct_stem_id
                            fixed_stem_ids[stem_object_id] = (whole_stem_id, closest_notehead_id, min_dist)
                    else:
                        # Construir stem id correcte
                        correct_stem_id = closest_notehead_id.removesuffix("notehead") + "stem"
                        fixed_stem_ids[stem_object_id] = (correct_stem_id, closest_notehead_id, min_dist)
                # Si no li assigna notehead perque no queden, no arregla aquell id especific
                else:
                    print("NO ARREGLA SSTEEEEEEM WTRFFFFFFFFFFF")
                    del fixed_stem_ids[stem_object_id]
        return fixed_stem_ids


    def get_chord_notehead_dict(self, svg_root: ET.Element, line: str) -> dict:
        chord_notehead_dict = {}

        # Traverse all elements in the SVG
        for elem in svg_root.iter():
            if elem.attrib.get("class") == "chord":
                chord_id = elem.attrib.get("id")
                notehead_ids = []

                # Look for notehead elements inside the chord
                for subelem in elem.iter():
                    if subelem.attrib.get("class") == "notehead":
                        notehead_id = subelem.attrib.get("id")
                        if notehead_id:
                            notehead_ids.append(line + ":" + notehead_id)

                if chord_id:
                    chord_notehead_dict[chord_id] = notehead_ids

        return chord_notehead_dict


    def treure_repetits(self, fixed_stem_ids, all_noteheads, faulty_stem_objects, line, json_file, svg_root):
                            
        chord_to_noteheads = self.get_chord_notehead_dict(svg_root, line)
        repeated = self.buscar_repetits(fixed_stem_ids, chord_to_noteheads)
        noteheads_prohibides = {}
        while repeated != {}:
            stems_a_canviar, noteheads_prohibides = self.llista_stems_a_canviar(repeated, noteheads_prohibides, chord_to_noteheads)
            
            if stems_a_canviar == []:
                break

            fixed_stem_ids = self.actualitzar_noteheads(fixed_stem_ids, all_noteheads, stems_a_canviar, noteheads_prohibides, faulty_stem_objects, line, json_file)
            
            repeated = self.buscar_repetits(fixed_stem_ids, chord_to_noteheads)

        return fixed_stem_ids


    def get_available_stem_parents_dict(self, svg_root: ET.Element, line: str) -> dict:
        stem_parents_dict = {}

        # Traverse all elements in the SVG
        for elem in svg_root.iter():
            if elem.attrib.get("class") == "stem":
                elem_id = elem.attrib.get("id")

                # Pel cas on al SVG hi ha un objecte de classe stem sense id
                if not elem_id:
                    continue

                parent_id = elem_id.removesuffix(".stem")

                if parent_id not in stem_parents_dict.keys():
                    stem_parents_dict[parent_id] = 1
                else:
                    stem_parents_dict[parent_id] += 1

        return stem_parents_dict


    def get_stem_parent_to_noteheads_dict(self, svg_root: ET.Element, stem_parents_dict: dict) -> dict:
        stem_parents_to_noteheads = {}

        for elem in svg_root.iter():
            if elem.attrib.get("id") in stem_parents_dict.keys():
                stem_parents_to_noteheads[elem.attrib.get("id")] = []
                for subelem in elem.iter():
                    if subelem.attrib.get("class") == "notehead":
                        stem_parents_to_noteheads[elem.attrib.get("id")].append(subelem.attrib.get("id"))
                
                # Pel bug concret on una note no te notehead ni al svg ni al json
                if stem_parents_to_noteheads[elem.attrib.get("id")] == []:
                    del stem_parents_to_noteheads[elem.attrib.get("id")]
                    del stem_parents_dict[elem.attrib.get("id")]

        return stem_parents_to_noteheads, stem_parents_dict


    def final_stem_assigning(self, all_distances_dict: dict) -> dict:
        
        #Agafem el stem amb minima distancia per cada parent object
        result = {
            parent: {min(stems, key=stems.get): min(stems.values())}
            for parent, stems in all_distances_dict.items()
        }   

        # Comprovem si hi ha stems repetits als minims dels parents objects (no podem assignar dos stems a un mateix objecte -> ids duplicats)
        duplicates = defaultdict(list)
        for parent, stems in result.items():
            for stem in stems:
                duplicates[stem].append(parent)
        duplicates = {stem: parents for stem, parents in duplicates.items() if len(parents) > 1}

        # Mentre hi hagi repetits
        while duplicates:
            
            # Mirem quins stems es repeteixen i eliminem de la matriu de distances els no optims
            for stem, parents in duplicates.items():
                
                min_dist = float('inf')
                for parent in parents:
                    if all_distances_dict[parent][stem] < min_dist:
                        min_parent = parent
                        min_dist = all_distances_dict[parent][stem]

                # Elimino de la matriu de distancies els stems repetits de aquests pares repetits menys el pare amb distancia minima
                for parent in parents:
                    if parent != min_parent:
                        del all_distances_dict[parent][stem]
            
            # Pel cas quan al json no hi ha alguns stems del svg
            for parent in list(all_distances_dict.keys()):
                if not all_distances_dict[parent]:  # empty dict
                    del all_distances_dict[parent]

            # Tornem a agafar el stem amb minima distancia amb la matriu de distancies actualitzada
            result = {
                parent: {min(stems, key=stems.get): min(stems.values())}
                for parent, stems in all_distances_dict.items()
            }

            # Tornem a comprovar si hi ha stems repetits
            duplicates = defaultdict(list)
            for parent, stems in result.items():
                for stem in stems:
                    duplicates[stem].append(parent)
            duplicates = {stem: parents for stem, parents in duplicates.items() if len(parents) > 1}

        return result




