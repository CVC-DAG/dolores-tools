import os
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET

class Particcellas:
    def __init__(self, input_folder, output_folder):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)

    def process(self):
        for root, _, files in os.walk(self.input_folder):
            rel_dir = Path(root).relative_to(self.input_folder)
            out_dir = self.output_folder / rel_dir
            out_dir.mkdir(parents=True, exist_ok=True)
            for file in files:
                if file.lower().endswith('.musicxml'):
                    self._process_musicxml(Path(root) / file, out_dir)
                else:
                    shutil.copy2(Path(root) / file, out_dir / file)

    def _process_musicxml(self, file_path, out_dir):
        tree = ET.parse(file_path)
        root = tree.getroot()
        parts = root.findall('.//part')
        if len(parts) <= 1:
            shutil.copy2(file_path, out_dir / file_path.name)
            return

        # Find the part-list element and its index
        part_list = None
        part_list_idx = None
        for idx, child in enumerate(root):
            if child.tag.endswith('part-list'):
                part_list = child
                part_list_idx = idx
                break

        for idx, part in enumerate(parts):
            part_id = part.attrib.get('id', f'part{idx+1}')
            # Copy all elements before part-list
            new_root = ET.Element(root.tag, root.attrib)
            for child in list(root)[:part_list_idx]:
                new_root.append(self._deepcopy_element(child))
            # Add filtered part-list
            if part_list is not None:
                filtered_part_list = self._filter_part_list(part_list, part_id)
                new_root.append(filtered_part_list)
            # Add this part
            new_root.append(self._deepcopy_element(part))
            # Write new file
            new_tree = ET.ElementTree(new_root)
            out_name = f"{file_path.stem}_{part_id}.musicxml"
            out_file = out_dir / out_name
            new_tree.write(out_file, encoding='utf-8', xml_declaration=True)

    def _filter_part_list(self, part_list_elem, part_id):
        # Deep copy and keep only the score-part with the matching id
        new_part_list = ET.Element(part_list_elem.tag, part_list_elem.attrib)
        for child in part_list_elem:
            if child.tag.endswith('score-part') and child.attrib.get('id') == part_id:
                new_part_list.append(self._deepcopy_element(child))
        return new_part_list

    def _deepcopy_element(self, elem):
        # Recursively deep copy an ElementTree element
        new_elem = ET.Element(elem.tag, elem.attrib)
        new_elem.text = elem.text
        new_elem.tail = elem.tail
        for child in elem:
            new_elem.append(self._deepcopy_element(child))
        return new_elem

def cut_particcellas(input_folder):
    input_folder = Path(input_folder)
    output_folder = input_folder.parent / (input_folder.name + "_particcellas")
    particcellas = Particcellas(input_folder, output_folder)
    particcellas.process()
    print(f"Particcellas cut in: {output_folder}")