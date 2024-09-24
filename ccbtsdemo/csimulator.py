import logging
import re
import json

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
        self.reset()


    def reset(self):
        self.cur_world = None
        self.num_turns = 0
        self.code_dict = {}

        board = init_board(self.gridwidth, self.gridheight)
        plot_board(board, "b1.png")        


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
        
    def get_current_world_code(self):
        code_list = []
        for step in self.code_dict:
            if self.code_dict[step]["status"] == "UNDO":
                continue
            for code in self.code_dict[step]["code"]:
                code_list.append(code)
        return code_list


    def undo(self):
        if self.num_turns == 0 or self.cur_world is None:
            return None, None

        cur_turns = self.num_turns
        while(cur_turns > 0 and self.code_dict[cur_turns - 1]["status"] == "UNDO"):
            cur_turns -= 1

        if cur_turns <= 0:
            return None, None
        
        use_turn = cur_turns - 1

        undo_code = self.code_dict[use_turn]["code"]
        for c_ in self.code_dict[use_turn]["code"]:
            x, y = self._get_x_y(c_)
            logging.debug(f"Undoing: {c_}, x: {x}, y: {y}")
            if x is not None and y is not None:
                self.cur_world = remove_shape(self.cur_world, int(x), int(y))
            else:
                logging.debug("Undo failed for code: ", c_)


        self.code_dict[use_turn]["status"] = "UNDO"
        save_filename = f"{RELATED_FILE_PATH}/gen_response_{len(self.cur_world)}_undo.png"
        plot_board(self.cur_world, save_filename)
        plot_board(self.cur_world, "b1.png")
        return save_filename, undo_code


    def getskill(self, filename):
        try:
            with open(f"{RELATED_FILE_PATH}/{filename}", "r") as file:
                return file.read()
        except Exception as error:
            logging.error(f"Error in reading skill file: {filename}, {error}")
            return None
        
    def _list_occupied_cells_with_details(self, board):
        occupied_cells = {}

        if board is None:
            return occupied_cells

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
                    occupied_cells[f"{row}:{col}"] = cell_elements

        return occupied_cells           


    def run(self, code):
        #print("Running code: ", code)

        if self.cur_world is None:
            self.cur_world = init_board(self.gridwidth, self.gridheight)
        
        board = self.cur_world
        for c_ in code:
            try:
                exec(c_)
            except Exception as error:
                logging.error(f"Error in executing code: {c_}, {error}")
                logging.error(f"Board State: {self._list_occupied_cells_with_details(self.cur_world)}")
                raise error


        #self.code_dict[self.num_turns] = code
        self.code_dict[self.num_turns] = {"code": code, "status": "run"}
        self.num_turns += 1
        self.cur_world = board
        save_filename = f"{RELATED_FILE_PATH}/gen_response_{len(self.cur_world)}.png"
        plot_board(board, save_filename)
        plot_board(board, "b1.png")
        return save_filename 

    def repeat_run(self, skill_code, repeat_code):
        print(f"Running repeat code: {repeat_code}")
        if self.cur_world is None:
            self.cur_world = init_board(self.gridwidth, self.gridheight)
        
        board = self.cur_world
        total_code = skill_code + "\n" + repeat_code
        #for c_ in total_code:
        exec(total_code)

        self.code_dict[self.num_turns] = {"code": total_code, "status": "run"}
        self.num_turns += 1
        self.cur_world = board
        plot_board(board, "b1.png")

    def save(self, filename):
        if not self.code_dict:
            logging.debug(f"No code to save, returning")
            return False

        logging.debug(f"Current code dict: {self.code_dict}, Saving to {filename}")
        with open(f"{RELATED_FILE_PATH}/{filename}", "w") as file:
            file.write("board=init_board(8,8)\n\n")
            for step in self.code_dict:
                if self.code_dict[step]["status"] == "UNDO":
                    continue
                for code in self.code_dict[step]["code"]:
                    file.write(f"{code}\n")
                file.write("\n")
        logging.debug(f"Saved the skill at {RELATED_FILE_PATH}/{filename}")
        return True


    def save_abstract_function(self, filename, skill_function):
        logging.debug(f"Saving abstract function to {filename}, skill_function: {skill_function}")
        with open(f"{RELATED_FILE_PATH}/{filename}", "w") as file:
            file.write(skill_function)
            logging.debug(f"Saved abstract function to {filename}")
            

