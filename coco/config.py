# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import copy
import json
import itertools
from pathlib import Path
import random


ROOT = Path(__file__).parent.resolve()


TASK_GREETING = Path(f"{ROOT}/data/task_greeting.txt").read_text().strip().split("\n\n")


INSTRUCTIONS = dict(
    player=Path(f"{ROOT}/data/piece_legend.html").read_text().strip(),
    wizard=Path(f"{ROOT}/data/piece_legend.html").read_text().strip()
)


COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"
SUCCESS_COLOR = "Green"


TIME_LEFT = 5  # how many minutes a user can stay in a room before closing it


CONFIG = {"width": 7.0, "height": 7.0, "move_step": 1, "prevent_overlap": False}
EMPTYSTATE = json.loads(Path(f"{ROOT}/data/empty_state.json").read_text())
SELECTIONSTATE = json.loads(Path(f"{ROOT}/data/selection_state.json").read_text())
STATES = Path(f"{ROOT}/data/states.jsonl")
RULES = json.loads(Path(f"{ROOT}/data/allowed_moves.json").read_text())


def load_states():
    pool = list()
    with STATES.open(encoding="utf-8") as infile:
        for line in infile:
            pool.append(
                json.loads(line)
            )

    random.shuffle(pool)
    return pool


def new_obj_name(state):
    # obtain used ids
    objs = [int(i) for i in state["objs"].keys()]
    objs.sort()

    if not objs:
        return "0"

    # calculate next possible id
    highest = objs[-1]
    possible = set(range(highest + 2))
    new_ids = list(possible - set(objs))
    new_ids.sort()

    return str(new_ids[0])


class Pattern(dict):
    n_elements = 0
    name = ""

    @property
    def cells(self):
        return len(self.keys())

    def detect(self, this_cell, board):
        coor, cell = this_cell
        objs = [board["objs"][i]["type"] for i in cell]
        if objs in self.values():
            for coordinate, part in self.items():
                if objs == part:
                    # there is a match, try to match the other cells from the pattern
                    rest_pattern = copy.deepcopy(self)
                    rest_pattern.pop(coordinate)

                    if not rest_pattern:
                        # pattern only has one cell
                        return True
                    else:
                        # collect the other cells from the board
                        # that could complete this pattern
                        other_board_cells = dict()
                        for other_c in rest_pattern.keys():
                            # obtain the other coordinates from this pattern
                            other_x, other_y = map(int, other_c.split(":"))
                            
                            # coordinate of this cell
                            this_x, this_y = map(int, coordinate.split(":"))

                            # calculate relative position of other cell to current cell
                            movement = (this_x - other_x, this_y - other_y)
                            
                            # index other cells on the board
                            board_x, board_y = map(int, coor.split(":"))
                            other_board_coor = f"{board_x + movement[0]}:{board_y + movement[1]}"

                            if other_board_coor in board["objs_grid"]:
                                # get the name of the bjects on the other cell
                                other_board_cells[other_board_coor] = board["objs_grid"][other_board_coor]

                        board_pattern_named = {coor: objs}
                        board_pattern_ids = {coor: cell}

                        # convert other cells from the board from obj_ids to object name
                        for key, value in other_board_cells.items():
                            board_pattern_named[key] = [board["objs"][i]["type"] for i in value]
                            board_pattern_ids[key] = value

                        if len(board_pattern_named.values()) == len(self.values()):
                            board_pieces = list(board_pattern_named.values())
                            pattern_pieces = list(self.values())
                            board_pieces.sort()
                            pattern_pieces.sort()

                            if pattern_pieces == board_pieces:
                                # we have the same object names, make sure the pattern on the board
                                # is composed by the same number of objects of this pattern
                                flatten = itertools.chain.from_iterable(board_pattern_ids.values())
                                n = len(set([i for i in flatten]))
                                if n == self.n_elements:
                                    return True
        return False


def get_patterns():
    patterns = list()
    for filename in Path(f"{ROOT}/data/patterns").iterdir():
        if filename.suffix == ".json":
            pattern_dict = json.loads(filename.read_text())

            this_pattern = Pattern()
            for position, objs in pattern_dict["objs_grid"].items():
                this_pattern[position] = [pattern_dict["objs"][i]["type"] for i in objs]

            flatten = itertools.chain.from_iterable(pattern_dict["objs_grid"].values())
            n = len(set([i for i in flatten]))
            this_pattern.n_elements = n
            this_pattern.name = filename.stem

            patterns.append(this_pattern)

    return patterns
