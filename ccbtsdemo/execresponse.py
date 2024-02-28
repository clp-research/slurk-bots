import logging

from PIL import Image
import io
import base64

from .coco import (
    init_board,
    put,
    plot_board,
    SameShapeStackingError,
    SameShapeAtAlternateLevels,
    NotOnTopOfScrewError,
    DepthMismatchError,
)

from pathlib import Path


ROOT = Path(__file__).parent.resolve()
RELATED_FILE_PATH = Path(
    f"{ROOT}"
)


def convert_np_array_to_image(array):
    img = Image.fromarray(array)
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format="PNG")
    img_byte_array = img_byte_array.getvalue()
    return img_byte_array

def encode_pil_image_to_base64(img_byte_array):
    encoded_string = base64.b64encode(img_byte_array)
    return encoded_string.decode("utf-8")


def resetboardstate(rows, cols):
    board = init_board(rows, cols)
    save_filename = f"{RELATED_FILE_PATH}/empty_world_state.png"
    plot_board(board, save_filename)
    return save_filename


def list_occupied_cells_with_details(board):
    occupied_cells = {}

    for row in range(board.shape[2]):
        for col in range(board.shape[3]):
            cell_elements = []
            # check each layer for the current cell
            for layer in range(board.shape[0]):
                # get shape and color
                shape = board[layer, 0, row, col]
                color = board[layer, 1, row, col]
                # If the shape is not '0', then the cell is occupied
                if shape != "0":
                    cell_elements.append((shape, color))

            if cell_elements:
                occupied_cells[(row, col)] = cell_elements

    return occupied_cells

def cleanup_response(value):
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



def execute_response(rows, cols, response):
    board = init_board(rows, cols)

    if not response:
        return None, "No response available for execution"

    logging.debug(f"response = {response}")

    for turn, code in response.items():
        if "EXEC_ERROR" in code:
            continue

        logging.debug(f"Turn {turn} -> {code}")
        code = cleanup_response(code)
        logging.debug(f"Cleaned up response = {code}")

        try:
            exec(code)
            logging.debug(f"Current World State {list_occupied_cells_with_details(board)}")
            #plot_board(board, f"gen_response_{dialogue_pair}_{turn}.png")
        except Exception as e:
            error = True
            logging.debug(f"Current World State {list_occupied_cells_with_details(board)}")
            logging.debug(f"{type(e).__name__}, {e}")
            return None, type(e).__name__, turn

    # This is for matplotlib generation
    save_filename = f"{RELATED_FILE_PATH}/gen_response_{len(response)}.png"
    plot_board(board, save_filename)
    logging.debug("Saved the board")
    logging.debug("Returning from execute_response")
    return save_filename, False, turn
