import logging
import os
import json
import base64

from pathlib import Path


ROOT = Path(__file__).parent.resolve()
RELATED_INSTRUCTION_PATH = Path(
    f"{ROOT}/data/sequences/"
)
RELATED_LEGEND_PATH = Path(
    f"{ROOT}/data/sequences/legend"
)

class Dataloader:
    def __init__(self):
        self.boards, self.sorted_boards = self.load_instructions()
        self.legend_images = self.load_legend_images()
        self.legend_map = self.readjsonfile(f"{RELATED_LEGEND_PATH}/board_legend_info.json")
        self.board_view_status = {}#self.load_image_viewing_status()
        self.legend_info = self.get_legend_map()
        self.object_names = self.get_object_names()

    def readjsonfile(self, file_path):
        with open(file_path, "r") as file:
            return json.load(file)
        
    # Function to save the current index to the progress file
    def save_progress(self, current_index, progress_file):
        with open(progress_file, 'w') as f:
            f.write(str(current_index))

    # Function to load the last saved index from the progress file
    def load_progress(self, progress_file):
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                return int(f.read())
        return 0  # Start from the first key if no progress is saved        


    def load_instructions(self):
        logging.debug(f"Loading instructions from {RELATED_INSTRUCTION_PATH}")
        boards = {}
        sorted_boards = {}
        #sorted_files = sorted(RELATED_IMAGE_PATH.iterdir(), key=self.extract_number) 
        #logging.debug(f"sorted files are {sorted_files}")
        for annotfile in RELATED_INSTRUCTION_PATH.iterdir():
            if annotfile.is_file() and annotfile.exists() and annotfile.suffix in [".json"]:
                boards[annotfile.stem] = self.readjsonfile(annotfile)
                sorted_keys = sorted(boards[annotfile.stem].keys())
                sorted_boards[annotfile.stem] = sorted_keys
                progress_file = f"{RELATED_INSTRUCTION_PATH}/{annotfile.stem}_progress.txt"
                self.save_progress(0, progress_file)

        logging.debug(f"Loaded instructions: {len(boards)}, {boards.keys()}")
        return boards, sorted_boards
    
    def encode_image_to_base64(self, image):
        try:
            with open(image, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read())
                return encoded_string.decode('utf-8')  # Convert bytes to a UTF-8 string
        except FileNotFoundError:
            return None    

    def load_legend_images(self):
        logging.debug(f"Loading legend images from {RELATED_LEGEND_PATH}")
        images = {}
        for image in RELATED_LEGEND_PATH.iterdir():
            if image.is_file() and image.exists() and image.suffix in [".png", ".jpg", ".jpeg"]:
                images[image.stem] = self.encode_image_to_base64(image)

        logging.debug(f"Loaded legend images: {len(images)}")
        return images  

    def load_board_viewing_status(self):
        try:
            with open(f"{RELATED_INSTRUCTION_PATH}/board_viewing_status.json", "r") as file:
                image_view = json.load(file)
                logging.debug(f"Current board viewing status: {image_view}")
                return image_view
        except FileNotFoundError:
            logging.debug("board_viewing_status.json is not available, returning empty dict")
            return {}
        
    def get_target_board(self):
        board_info = {}
        legend_image_path = None
        self.board_view_status = self.load_board_viewing_status()
        if len(self.board_view_status) == len(self.boards):
            logging.debug("All boards have been used.")
            #self.used_images = []
            return None, None
        
        for board_file in self.boards:
            if "rb" in board_file:
                continue

            progress_file = f"{RELATED_INSTRUCTION_PATH}/{board_file}_progress.txt"
            current_index = self.load_progress(progress_file)

            if current_index < len(self.sorted_boards[board_file]):
                # Get the current key and its instructions
                current_key = self.sorted_boards[board_file][current_index]
                object_name = str(current_key).split("_")[1].strip()
                current_instructions = self.boards[board_file][current_key]["cleaned_instructions"]
                if "sb" in board_file:
                    current_instructions = f"These are the instructions to build {object_name}. " + current_instructions
                logging.debug(f"Current_index: {current_index}, Current_key: {current_key}, Current instructions are: {current_instructions}")
                board_info['instruction'] = current_instructions
                board_info["filename"] = board_file
                board_info["boardname"] = str(current_key)
                board_info["objectname"] = object_name
                board_info["legendname"] = None
                board_info["legend_image_base64"] = None

                current_index += 1
                self.save_progress(current_index, progress_file)

                if "rb" in board_file:
                    # TODO: Add the legend image to the return
                    legend_file_name = self.legend_map[str(current_key)]
                    legend_image_base64 = self.encode_image_to_base64(f"{RELATED_LEGEND_PATH}/{legend_file_name}.png")
                    board_info["legendname"] = {"filename": legend_file_name, "objectname": legend_file_name.split("_")[1].strip()}
                    board_info["legend_image_base64"] = f"data:image/png;base64,{legend_image_base64}"

            else:
                logging.debug(f"All instructions have been processed for the file {board_file}")
                continue

            break

        return board_info



    def get_legend_map(self):
        try:
            with open(f"{RELATED_LEGEND_PATH}/board_legend_info.json", "r") as file:
                legend_info = json.load(file)
                logging.debug(f"Current legend mapping: {legend_info}")
                return legend_info
        except FileNotFoundError:
            logging.debug("board_legend_info.json is not available, returning empty dict")
            return {}

    def get_object_names(self):
        try:
            with open(f"{RELATED_LEGEND_PATH}/object_names.json", "r") as file:
                legend_info = json.load(file)
                logging.debug(f"Loaded object names: {len(legend_info)}")
                return legend_info
        except FileNotFoundError:
            logging.debug("object_names.json is not available, returning empty dict")
            return {}
        
    def save_board_viewing_status(self):
        logging.debug(f"Saving board viewing status to {RELATED_INSTRUCTION_PATH}/board_viewing_status.json")
        with open(f"{RELATED_INSTRUCTION_PATH}/board_viewing_status.json", "w") as file:
            json.dump(self.board_view_status, file)        
