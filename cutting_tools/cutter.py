import os
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
from PIL import Image
import io
import logging

from config import username, password, backend_url

GLOBAL_ACCESS_TOKEN = None

class Cutter:
    def __init__(self, cut_particcellas: bool = False, cut_monophonic: bool = False):
        # Backend info
        self.backend_base_url = backend_url
        self.username = username
        self.password = password
        
        #Backend pre-ops
        self._authenticate()
        self.projects_dict = self._fetch_projects()
        
        #Local info
        self.output_base = Path("output_data")
        self.monophonic_mxmls_dir = self.output_base / "monophonic/musicxmls"
        self.monophonic_img_dir = self.output_base / "monophonic/imgs"
        self.particcellas_mxmls_dir = self.output_base / "particcellas/musicxmls"
        self.particcellas_img_dir = self.output_base / "particcellas/imgs"
        self.polyphonic_mxmls_dir = self.output_base / "polyphonic/musicxmls"
        self.monophonic_mxmls_dir.mkdir(parents=True, exist_ok=True)
        self.monophonic_img_dir.mkdir(parents=True, exist_ok=True)
        self.particcellas_mxmls_dir.mkdir(parents=True, exist_ok=True)
        self.particcellas_img_dir.mkdir(parents=True, exist_ok=True)
        self.polyphonic_mxmls_dir.mkdir(parents=True, exist_ok=True)
        
        #Program info
        self.cut_particcellas = cut_particcellas
        self.cut_monophonic = cut_monophonic
        self.img_padding = 0  # Padding for image cropping

        # Logging setup
        self.log_file = self.output_base / "particcellas_log.txt"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(message)s",
            handlers=[
                logging.FileHandler(self.log_file, mode='a'),
                logging.StreamHandler()
            ]
        )

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

    def _fetch_alignment(self, project_id, line_id):
        global GLOBAL_ACCESS_TOKEN
        url = f"{self.backend_base_url}/alignment/{project_id}/{line_id}"
        headers = {}
        if GLOBAL_ACCESS_TOKEN:
            headers['Authorization'] = f"Bearer {GLOBAL_ACCESS_TOKEN}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching alignment for project {project_id}, line {line_id}: {e}")
            return None

    def _fetch_image(self, project_id):
        global GLOBAL_ACCESS_TOKEN
        url = f"{self.backend_base_url}/image/{project_id}"
        headers = {}
        if GLOBAL_ACCESS_TOKEN:
            headers['Authorization'] = f"Bearer {GLOBAL_ACCESS_TOKEN}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"Error fetching image for project {project_id}: {e}")
            return None
        
    def is_monophonic(self, part):
        # Return False if the part has a staff-layout item
        if part.find(".//staff-layout") is not None:
            return False

        staff_voices = {}  # maps staff number to set of voices used

        for measure in part.findall("measure"):
            for note in measure.findall("note"):
                voice_el = note.find("voice")
                staff_el = note.find("staff")

                voice = voice_el.text.strip() if voice_el is not None else "1"
                staff = staff_el.text.strip() if staff_el is not None else "1"

                if staff not in staff_voices:
                    staff_voices[staff] = set()
                staff_voices[staff].add(voice)

        # Check if any staff has more than one voice
        for voices in staff_voices.values():
            if len(voices) > 1:
                return False  # Polyphonic: multiple voices in one staff

        return True 

    def cut(self):
        for project_id, project_name in self.projects_dict.items():
            lines_info = self._fetch_lines(project_id)
            if not lines_info or "line_ids" not in lines_info:
                continue

            # Fetch project image 
            image_bytes = self._fetch_image(project_id)
            try:
                image_obj = Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                print(f"Error opening image for project {project_id}: {e}")
                image_obj = None

            for line_id in lines_info["line_ids"]:
                line_coords = lines_info["line_coords"][line_id-1]
                musicxml_bytes = self._fetch_musicxml(project_id, line_id)
                if not musicxml_bytes:
                    continue
                try:
                    tree = ET.ElementTree(ET.fromstring(musicxml_bytes))
                except Exception as e:
                    print(f"Error parsing MusicXML for project {project_id}, line {line_id}: {e}")
                    continue
                root = tree.getroot()
                parts = root.findall('.//part')
                file_stem = f"{project_name}.{str(line_id).zfill(2)}"
                
                if len(parts) <= 1:
                    if self.cut_monophonic:
                        if self.is_monophonic(parts[0]):
                            print(f"Processing monophonic: {project_name} (ID: {project_id}) line {line_id}")
                            
                            # Save musicxml as it is
                            out_file = self.monophonic_mxmls_dir / f"{file_stem}.musicxml"
                            with open(out_file, "wb") as f:
                                f.write(musicxml_bytes)
                            
                            # Calculate min second index and max fourth index from bbox values
                            alignment = self._fetch_alignment(project_id, line_id)
                            min_second = None
                            max_fourth = None
                            if alignment and "annotations" in alignment:
                                for ann in alignment["annotations"]:
                                    ann_id = ann.get("mxml_id")
                                    bbox = ann.get("bbox")
                                    if bbox and isinstance(bbox, list) and len(bbox) == 4:
                                        second = bbox[1]
                                        fourth = bbox[3]
                                        if min_second is None or second < min_second:
                                            min_second = second
                                        if max_fourth is None or fourth > max_fourth:
                                            max_fourth = fourth
                            #print(f"Part {part_id} min second index: {min_second}, max fourth index: {max_fourth}")

                            # Cut and save image for this line
                            if image_obj and min_second is not None and max_fourth is not None:
                                # Offset to line coords
                                min_second = min_second + line_coords[1]
                                max_fourth = max_fourth + line_coords[1]
                                # Ensure bounds are within image
                                width, height = image_obj.size
                                top = max(0, min_second - self.img_padding)
                                bottom = min(height, max_fourth + self.img_padding)
                                if top <= bottom:
                                    cropped = image_obj.crop((0, top, width, bottom))
                                    img_out_file = self.monophonic_img_dir / f"{file_stem}.png"
                                    cropped.save(img_out_file)
                                else:
                                    print("ValueError: Coordinate 'lower' is less than 'upper'")
                                    continue
                            else:
                                print(f"Could not cut image for line {line_id} (missing image or bbox info)")
                                continue
                        else:
                            #Per les polifoniques simplement guardem musicxml as it is
                            print(f"Processing polyphonic: {project_name} (ID: {project_id}) line {line_id}")
                            out_file = self.polyphonic_mxmls_dir / f"{file_stem}.musicxml"
                            with open(out_file, "wb") as f:
                                f.write(musicxml_bytes)
                else:
                    if self.cut_particcellas:
                        log_msg = f"Splitting particcella: {project_name} (ID: {project_id}) line {line_id}"
                        print(log_msg)
                        logging.info(log_msg)
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
                            # Fetch alignment data for this line
                            alignment = self._fetch_alignment(project_id, line_id)
                            mxml_bbox_dict = {}
                            if alignment and "annotations" in alignment:
                                mxml_ids = {elem.attrib.get('id') for elem in part.iter() if elem.attrib.get('id')}
                                for ann in alignment["annotations"]:
                                    ann_id = ann.get("mxml_id")
                                    if ann_id and (ann_id in mxml_ids or any(ann_id.startswith(f"{mid}.") for mid in mxml_ids)):
                                        mxml_bbox_dict[ann_id] = ann.get("bbox")
                            log_msg = f"Part {part_id} mxml_id->bbox: {mxml_bbox_dict}"
                            #print(log_msg)
                            logging.info(log_msg)

                            # Calculate min second index and max fourth index from bbox values
                            min_second = None
                            max_fourth = None
                            for ann_id, bbox in mxml_bbox_dict.items():
                                #'pP' not in ann_id --> Temporal fix degut a id erroni de les measures a alineacions (Tots els atributs d'una measure els posa a la part 1 independentment de a quina part pertanyin realment)
                                if bbox and isinstance(bbox, list) and len(bbox) == 4 \
                                        and 'pP' not in ann_id \
                                        and 'barline' not in ann_id:
                                    second = bbox[1]
                                    fourth = bbox[3]
                                    if min_second is None or second < min_second:
                                        min_second = second
                                    if max_fourth is None or fourth > max_fourth:
                                        max_fourth = fourth

                            log_msg = f"Part {part_id} min second index: {min_second}, max fourth index: {max_fourth}"
                            #print(log_msg)
                            logging.info(log_msg)

                            # Cut and save image for this part
                            if image_obj and min_second is not None and max_fourth is not None:
                                # Offset to line coords
                                min_second = min_second + line_coords[1]
                                max_fourth = max_fourth + line_coords[1]
                                # Ensure bounds are within image
                                width, height = image_obj.size
                                top = max(0, min_second - self.img_padding)
                                print("Height: ", height)
                                print("max_fourth: ", max_fourth)
                                bottom = min(height, max_fourth + self.img_padding)
                                if top <= bottom:
                                    cropped = image_obj.crop((0, top, width, bottom))     
                                    img_out_file = self.particcellas_img_dir / f"{file_stem}_P{str(idx+1).zfill(2)}.png"
                                    cropped.save(img_out_file)
                                else:
                                    print("ValueError: Coordinate 'lower' is less than 'upper'")
                                    continue
                            else:
                                print(f"Could not cut image for part {part_id} (missing image or bbox info)")
                                continue

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
                            out_file = self.particcellas_mxmls_dir / f"{file_stem}_P{str(idx+1).zfill(2)}.musicxml"
                            new_tree.write(out_file, encoding='utf-8', xml_declaration=True)

    def _filter_part_list(self, part_list_elem, part_id):
        new_part_list = ET.Element(part_list_elem.tag, part_list_elem.attrib)
        for child in part_list_elem:
            if child.tag.endswith('score-part') and child.attrib.get('id') == part_id:
                new_part_list.append(self._deepcopy_element(child))
        return new_part_list

    def _deepcopy_element(self, elem):
        new_elem = ET.Element(elem.tag, elem.attrib)
        new_elem.text = elem.text
        new_elem.tail = elem.tail
        for child in elem:
            new_elem.append(self._deepcopy_element(child))
        return new_elem

def cut_scores(cut_particcellas: bool = False, cut_monophonic: bool = False):
    cutter = Cutter(cut_particcellas=cut_particcellas, cut_monophonic=cut_monophonic)
    cutter.cut()
    print("Score processing finished. Output in " + str(cutter.output_base))