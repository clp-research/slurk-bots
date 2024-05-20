import re
import json
import logging

from PIL import Image
import io
import base64

from .coco import (
    init_board,
    put,
    plot_board,
    remove_shape,
    SameShapeStackingError,
    SameShapeAtAlternateLevels,
    SameColorAtAlternateLevels,
    SameColorStackingError,
    NotOnTopOfScrewError,
    DepthMismatchError,
    BridgePlacementError,
    DimensionsMismatchError,
)

from pathlib import Path


ROOT = Path(__file__).parent.resolve()
RELATED_FILE_PATH = Path(
    f"{ROOT}"
)


class CodeSimulator:
    def __init__(self, gridwidth, gridheight):
        self.gridwidth = gridwidth
        self.gridheight = gridheight
        self.code_dict = {}
        self.num_turns = 0
        self.cur_world = None

    def reset(self):
        self.code_list = []
        self.cur_world = None

    def convert_np_array_to_image(self, array):
        img = Image.fromarray(array)
        img_byte_array = io.BytesIO()
        img.save(img_byte_array, format="PNG")
        img_byte_array = img_byte_array.getvalue()
        return img_byte_array

    def encode_pil_image_to_base64(self, img_byte_array):
        encoded_string = base64.b64encode(img_byte_array)
        return encoded_string.decode("utf-8")

    def cleanup_response(self, value):
        if "```python" in value:
            value = value.replace("```python", "").strip()
        if "```" in value:
            value = value.replace("```", "").strip()
        if value[0] == ":":
            value = value[1:].strip()
        if value[-1] in ["\n", ";", ".", ","]:
            value = value[:-1].strip()
        if "Output:" in value:
            value = value.split("Output:")[1].strip()
        elif "Output" in value:
            value = value.split("Output")[1].strip()

        return value


    def resetboardstate(self, rows, cols):
        board = init_board(rows, cols)
        save_filename = f"{RELATED_FILE_PATH}/empty_world_state.png"
        plot_board(board, save_filename)
        return save_filename        


    def _get_x_y(self, code):
        match = re.search(r'x=(\d+),\s*y=(\d+)', code)
        if not match:
            # If not found, try to match the position format
            match = re.search(r"put\(board,\s*'\w+?',\s*'\w+?',\s*(\d+),\s*(\d+)\)", code)
        if match:
            x, y = match.groups()
            return x, y
        else:
            return None, None

    def undo(self):
        if self.num_turns == 0:
            return "No actions to undo"

        for c_ in self.code_dict[self.num_turns - 1]:
            x, y = self._get_x_y(c_)
            logging.debug(f"Undoing: {c_}, x: {x}, y: {y}")
            if x is not None and y is not None:
                self.cur_world = remove_shape(self.cur_world, int(x), int(y))
            else:
                logging.debug("Undo failed for code: ", c_)

        self.code_dict[self.num_turns] = ["UNDO"]
        self.num_turns += 1
        save_filename = f"{RELATED_FILE_PATH}/gen_response_{len(self.cur_world)}.png"
        plot_board(self.cur_world, save_filename)        
        return save_filename
            

    def run(self, code):
        print("Running code: ", code)

        if self.cur_world is None:
            self.cur_world = init_board(self.gridwidth, self.gridheight)
        
        board = self.cur_world
        for c_ in code:
            try:
                exec(c_)
            except Exception as error:
                logging.error(f"Error in executing code: {c_}, {error}")
                return None


        self.code_dict[self.num_turns] = code
        self.num_turns += 1
        self.cur_world = board
        save_filename = f"{RELATED_FILE_PATH}/gen_response_{len(self.cur_world)}.png"
        plot_board(board, save_filename)
        return save_filename        
        #plot_board(board, "b1.png")

    def save(self, filename):
        logging.debug(f"Current code dict: {self.code_dict}, Saving to {filename}")
        with open(f"{RELATED_FILE_PATH}/{filename}", "w") as file:
            file.write("board=init_board(8,8)\n\n")
            for step in self.code_dict:
                for code in self.code_dict[step]:
                    file.write(f"{code}\n")
                file.write("\n")
        return f"Saved the skill to {RELATED_FILE_PATH}/{filename}"
            

