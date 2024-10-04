import logging
import random

from .base64encode import encode_image_to_base64

from pathlib import Path


ROOT = Path(__file__).parent.resolve()
RELATED_FOLDER_PATH = Path(
    f"{ROOT}/data/sequences/"
)


class Dataloader:
    def __init__(self):
        self.images = self.load_images()
        print(self.images.keys())
        self.sorted_keys = sorted(self.images.keys(), key=lambda x: int(x.split('_')[1]))
        self.current_index = self.load_image_viewing_index()

    def load_images(self):
        logging.debug(f"Loading images from {RELATED_FOLDER_PATH}")
        images = {}
        for image in RELATED_FOLDER_PATH.iterdir():
            if image.is_file() and image.suffix in [".png", ".jpg"]:
                images[image.stem] = encode_image_to_base64(image)

        logging.debug(f"Loaded images: {len(images)}")
        return images
    
    def load_image_viewing_index(self):
        try:
            with open(f"{ROOT}/data/sequences/image_viewing_index.txt", "r") as file:
                current_index = int(file.read().strip())
                logging.debug(f"Current image viewing index: {current_index}")
                return current_index
        except FileNotFoundError:
            logging.debug("image_viewing_index.txt is not available, returning empty dict")
            return -1   
        
    def save_image_viewing_index(self):
        with open(f"{ROOT}/data/sequences/image_viewing_index.txt", "w") as file:
            file.write(str(self.current_index))
            logging.debug(f"Saved current image viewing index: {self.current_index}")
    

    def get_target_image(self):

        next_index = (self.current_index + 1) % len(self.sorted_keys)
        next_file = self.sorted_keys[next_index]
        self.current_index = next_index
        self.save_image_viewing_index()
        logging.debug(f"Target Board file: {next_file}")
        return self.images[next_file]
  


    def get_target_image_random(self):

        #Reset used images if all images have been used
        if len(self.used_images) == len(self.images):
            logging.debug("All images have been used, resetting used images list.")
            self.used_images = []

        logging.debug(f"Getting target image, self.used_images = {self.used_images}")
        random_image = None
        #To ensure we dont get the same image again
        while random_image not in self.used_images:
            random_image = random.choice(list(self.images.keys()))
            logging.debug(f"Random image file: {random_image}")
            self.used_images.append(random_image)
            return self.images[random_image]

    def get_empty_world_state(self):
        logging.debug(f"Loading empty world state from {ROOT}/data/base_images/empty_world_state.png")
        return encode_image_to_base64(Path(f"{ROOT}/data/base_images/empty_world_state.png"))

    def get_legend_image(self):
        logging.debug(f"Loading legend image from {ROOT}/data/base_images/legend_description.png")
        return encode_image_to_base64(Path(f"{ROOT}/data/base_images/legend_description.png"))


if __name__ == "__main__":
    dl = Dataloader()
    print(dl.get_target_image())
    print(dl.get_target_image())
    print(dl.get_target_image())
    print(dl.get_target_image())
    print(dl.get_target_image())


