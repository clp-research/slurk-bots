import logging
import random
import re
import base64
import json
#from .base64encode import encode_image_to_base64

from pathlib import Path


ROOT = Path(__file__).parent.resolve()
RELATED_IMAGE_PATH = Path(
    f"{ROOT}/data/sequences/"
)
RELATED_LEGEND_PATH = Path(
    f"{ROOT}/data/sequences/legends"
)


class Dataloader:
    def __init__(self):
        self.images = self.load_images()
        self.legend_images = self.load_legend_images()
        self.image_view_status = {}#self.load_image_viewing_status()
        self.legend_info = self.get_legend_map()
        self.object_names = self.get_object_names()

    def extract_number(self, file_path):
        # Extract the numerical part of the filename
        match = re.search(r'\d+', file_path.stem)
        return int(match.group()) if match else 0
       

    def load_image_viewing_status(self):
        try:
            with open(f"{ROOT}/data/sequences/image_viewing_status.json", "r") as file:
                image_view = json.load(file)
                logging.debug(f"Current image viewing status: {image_view}")
                return image_view
        except FileNotFoundError:
            logging.debug("image_viewing_status.json is not available, returning empty dict")
            return {}
        
    def get_legend_map(self):
        try:
            with open(f"{ROOT}/data/sequences/legends/board_legend_info.json", "r") as file:
                legend_info = json.load(file)
                logging.debug(f"Current legend mapping: {legend_info}")
                return legend_info
        except FileNotFoundError:
            logging.debug("board_legend_info.json is not available, returning empty dict")
            return {}

    def get_object_names(self):
        try:
            with open(f"{ROOT}/data/sequences/legends/object_names.json", "r") as file:
                legend_info = json.load(file)
                logging.debug(f"Loaded object names: {len(legend_info)}")
                return legend_info
        except FileNotFoundError:
            logging.debug("object_names.json is not available, returning empty dict")
            return {}


    def save_image_viewing_status(self):
        logging.debug(f"Saving image viewing status to {ROOT}/data/sequences/image_viewing_status.json")
        with open(f"{ROOT}/data/sequences/image_viewing_status.json", "w") as file:
            json.dump(self.image_view_status, file)

    def encode_image_to_base64(self, image):
        try:
            with open(image, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read())
                return encoded_string.decode('utf-8')  # Convert bytes to a UTF-8 string
        except FileNotFoundError:
            return None

    def load_images(self):
        logging.debug(f"Loading images from {RELATED_IMAGE_PATH}")
        images = {}
        #sorted_files = sorted(RELATED_IMAGE_PATH.iterdir(), key=self.extract_number) 
        #logging.debug(f"sorted files are {sorted_files}")
        for image in RELATED_IMAGE_PATH.iterdir():
            if image.is_file() and image.exists() and image.suffix in [".png", ".jpg", ".jpeg"]:
                images[image.stem] = self.encode_image_to_base64(image)

        logging.debug(f"Loaded images: {len(images)}")
        return images
    
    def load_legend_images(self):
        logging.debug(f"Loading legend images from {RELATED_LEGEND_PATH}")
        images = {}
        for image in RELATED_LEGEND_PATH.iterdir():
            if image.is_file() and image.exists() and image.suffix in [".png", ".jpg", ".jpeg"]:
                images[image.stem] = self.encode_image_to_base64(image)

        logging.debug(f"Loaded legend images: {len(images)}")
        return images    

    def get_target_image(self):
        #Reset used images if all images have been used
        self.image_view_status = self.load_image_viewing_status()
        if len(self.image_view_status) == len(self.images):
            logging.debug("All images have been used, resetting used images list.")
            #self.used_images = []
            return "empty_world_state.png", None, None, None

        random_image = None
        #To ensure we dont get the same image again
        #Also check the file has not been used before
        while random_image is None or random_image in self.image_view_status:
            #random_image = random.choice(list(self.images.keys()))
            random_image = random.choice(list(self.images.keys()))
            logging.debug(f"Random image file: {random_image}")
            if random_image not in self.image_view_status:
                self.image_view_status[random_image] = True
                legend_name = self.legend_info.get(random_image, None)
                legend_image = None
                object_name = None
                if legend_name is not None:
                    legend_image = self.legend_images[legend_name]
                    object_name = self.object_names.get(legend_name, None)
                    #if object_name is not None:
                    #    object_name = f"Object name: {object_name}"
                logging.debug(f"Image {random_image}, Object_name: {object_name} has not been used before, returning.")
                return random_image, self.images[random_image], legend_image, object_name
            else:
                logging.debug(f"Image {random_image} has already been used, trying again.")


    def get_empty_world_state(self):
        logging.debug(f"Loading empty world state from {ROOT}/data/base_images/empty_world_state.png")
        return self.encode_image_to_base64(Path(f"{ROOT}/data/base_images/empty_world_state.png"))

    def get_legend_image(self):
        logging.debug(f"Loading legend image from {ROOT}/data/base_images/legend_description.png")
        return self.encode_image_to_base64(Path(f"{ROOT}/data/base_images/legend_description.png"))


if __name__ == "__main__":
    dl = Dataloader()
    print(dl.get_target_image())


