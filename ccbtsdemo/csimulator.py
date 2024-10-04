import logging
import re
import json
import copy

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
    f"{ROOT}/skills/"
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
            return "No Code to Undo", None

        cur_turns = self.num_turns
        while(cur_turns > 0 and self.code_dict[cur_turns - 1]["status"] == "UNDO"):
            cur_turns -= 1

        if cur_turns <= 0:
            return "No Code to Undo", None
        
        use_turn = cur_turns - 1

        '''
        undo_code = self.code_dict[use_turn]["code"]
        for c_ in self.code_dict[use_turn]["code"]:
            x, y = self._get_x_y(c_)
            logging.debug(f"Undoing: {c_}, x: {x}, y: {y}")
            if x is not None and y is not None:
                self.cur_world = remove_shape(self.cur_world, int(x), int(y))
            else:
                logging.debug("Undo failed for code: ", c_)
        '''
        undo_code = self.code_dict[use_turn]["code"]
        undo_cells = self.code_dict[use_turn]["modified_cells"]
        logging.debug(f"Cells to run the undo operation: {undo_cells}")
        '''
        for cell in undo_cells:
            x, y = cell.split(":")
            self.cur_world = remove_shape(self.cur_world, int(x), int(y))

        self.code_dict[use_turn]["status"] = "UNDO"
        save_filename = f"{RELATED_FILE_PATH}/gen_response_{len(self.cur_world)}_undo.png"
        plot_board(self.cur_world, save_filename)
        plot_board(self.cur_world, "b1.png")
        return save_filename, undo_code
        '''
        for cell, shapes in undo_cells.items():
            logging.debug(f"cell: {cell}, shapes: {shapes}")
            #In coco file, remove_shape() uses co-ordinates and removes the topmost shape, so no need to pass the shapes in reverse order
            for shape in shapes:
                x, y = cell.split(":")
                self.cur_world = remove_shape(self.cur_world, int(x), int(y))
                if shape[0] in ["L"]:
                    self.cur_world = remove_shape(self.cur_world, int(x), int(y)+1)
                elif shape[0] in ["T"]:
                    self.cur_world = remove_shape(self.cur_world, int(x)+1, int(y))
                cur_board_state = self._list_occupied_cells_with_details(self.cur_world)
                logging.debug(f"Board State after undo: {cur_board_state}")

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

    def _get_diff(self, prev_board, cur_board):

        diff = {}
        for cell in cur_board:
            if cell not in prev_board:
                if cell not in diff:
                    diff[cell] = []
                diff[cell].extend(cur_board[cell])
            else:
                if cur_board[cell] != prev_board[cell]:
                    if cell not in diff:
                        diff[cell] = []
                    diff[cell].extend(list(set(cur_board[cell]) - set(prev_board[cell])))

        return diff


    def run(self, code):
        #print("Running code: ", code)

        if self.cur_world is None:
            self.cur_world = init_board(self.gridwidth, self.gridheight)
        
        temp_world = copy.deepcopy(self.cur_world)
        board = temp_world#self.cur_world
        prev_board_state = self._list_occupied_cells_with_details(board)
        logging.debug(f"Board State: {prev_board_state}")

        if "for" in code[0]:
            code = code[0]
            logging.error(f"Executing the code: {code}")
            exec(code)
        else:
            logging.error(f"Iterating throught the code: {code}")
            for c_ in code:
                logging.debug(f"c_ = {c_}")
                try:
                    exec(c_)
                except Exception as error:
                    logging.error(f"Error in executing code:\n{c_}\n{error}")
                    logging.error(f"Board State: {self._list_occupied_cells_with_details(board)}")
                    raise error

        logging.error(f"Completed the execution of the code")
        cur_board_state = self._list_occupied_cells_with_details(board)
        #self.code_dict[self.num_turns] = code
        diff_cells = self._get_diff(prev_board_state, cur_board_state)
        logging.debug(f"modified_cells: {diff_cells}")
        self.code_dict[self.num_turns] = {"code": code, "status": "run", "modified_cells": diff_cells}
        self.num_turns += 1
        self.cur_world = board
        save_filename = f"{RELATED_FILE_PATH}/gen_response_{len(self.cur_world)}.png"
        plot_board(board, save_filename)
        plot_board(board, "b1.png")
        return save_filename 

    def repeat_run(self, skill_code, repeat_code):
        logging.debug(f"Running repeat code: {repeat_code}")
        if self.cur_world is None:
            self.cur_world = init_board(self.gridwidth, self.gridheight)
        
        temp_world = copy.deepcopy(self.cur_world)
        board = temp_world
        prev_board_state = self._list_occupied_cells_with_details(board)
        logging.debug(f"Current Board State: {prev_board_state}")
        if repeat_code.startswith("def") and repeat_code.endswith(":"):
            total_code = repeat_code
        else:
            total_code = skill_code + "\n" + repeat_code
        logging.debug(f"Total Code:\n{total_code}")

        #for c_ in total_code:
        try:
            exec(total_code)
        except Exception as error:
            logging.error(f"Error in executing code: {total_code}, {error}")
            logging.error(f"Board State: {self._list_occupied_cells_with_details(board)}")
            raise error

        cur_board_state = self._list_occupied_cells_with_details(board)
        diff_cells = self._get_diff(prev_board_state, cur_board_state)
        self.code_dict[self.num_turns] = {"code": [total_code], "status": "run", "modified_cells": diff_cells}
        self.num_turns += 1
        self.cur_world = board
        save_filename = f"{RELATED_FILE_PATH}/gen_response_{len(self.cur_world)}.png"
        plot_board(board, save_filename)
        plot_board(board, "b1.png")
        return save_filename

    def save(self, filename):
        if not self.code_dict:
            logging.debug(f"No code to save, returning")
            return False
        
        #Check if the world is only of UNDOs, then return
        if all([self.code_dict[step]["status"] == "UNDO" for step in self.code_dict]):
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
            

