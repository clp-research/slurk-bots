import logging
import random

from .base64encode import encode_image_to_base64

from pathlib import Path


ROOT = Path(__file__).parent.resolve()
RELATED_FOLDER_PATH = Path(
    f"{ROOT}/data/sequences/"
)


def load_images():
    logging.debug(f"Loading images from {RELATED_FOLDER_PATH}")
    images = {}
    for image in RELATED_FOLDER_PATH.iterdir():
        if image.is_file():
            images[image.stem] = encode_image_to_base64(image)

    logging.debug(f"Loaded images: {len(images)}")
    return images

def get_target_image():
    images = load_images()
    random_image = random.choice(list(images.keys()))
    logging.debug(f"Random image file: {random_image}")
    return images[random_image]

def get_empty_world_state():
    logging.debug(f"Loading empty world state from {ROOT}/data/base_images/empty_world_state.png")
    return encode_image_to_base64(Path(f"{ROOT}/data/base_images/empty_world_state.png"))

def get_legend_image():
    logging.debug(f"Loading legend image from {ROOT}/data/base_images/legend_description.png")
    return encode_image_to_base64(Path(f"{ROOT}/data/base_images/legend_description.png"))


if __name__ == "__main__":
    print(get_target_image())


