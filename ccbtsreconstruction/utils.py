import copy
import json
import itertools
from pathlib import Path
from threading import Timer

from .config import *
from .golmi_client import *




class ActionNode:
    """Base class for the linked list representing
    the action history, every action performed by the wizard
    if saved as a node in this linked list to allow for
    the redo and undo button
    """

    def __init__(self, action, obj):
        self.action = action
        self.obj = obj
        self.parent = None
        self.child = None

    def __str__(self):
        return f"Node({self.action}, {self.obj['type']})"

    def __repr__(self):
        return self.__str__()

    def next_state(self):
        if self.child is not None:
            return self.child
        return None

    def previous_state(self):
        if self.parent is not None:
            return self.parent
        return None

    def add_action(self, action, object):
        new_node = ActionNode(action, object)
        new_node.parent = self
        self.child = new_node
        return new_node

    @classmethod
    def new_tree(cls):
        return cls("root", None)


class MoveEvaluator:
    """Given a json file containing the placing rules
    this class decides if a move is allowed or not
    """

    def __init__(self, rules):
        self.rules = rules

    def can_place_on_top(self, this_obj, top_obj):
        if top_obj["type"] in self.rules:
            allowed_objs_on_top = self.rules[top_obj["type"]]["rule"]
            if this_obj["type"] not in allowed_objs_on_top:
                return False, self.rules[top_obj["type"]]["reason"]
        return True, ""

    def on_board(self, x, y):
        if x < 0 or x >= CONFIG["width"]:
            return False, "object outside of board"

        if y < 0 or y >= CONFIG["height"]:
            return False, "object outside of board"

        return True, ""

    def is_allowed(self, this_obj, client, x, y, block_size):
        # coordinates must be on the board
        board_x = x // block_size
        board_y = y // block_size

        allowed, reason = self.on_board(board_x, board_y)
        if allowed is False:
            return False, reason

        # last item on cell cannot be a screw
        cell_objs = client.get_entire_cell(
            x=x, y=y, block_size=block_size, board="wizard_working"
        )

        if cell_objs:
            # make sure this object can be placed on the last one on this cell
            top_obj = cell_objs[-1]
            valid_placement, reason = self.can_place_on_top(this_obj, top_obj)
            if valid_placement is False:
                return False, reason

        if "bridge" in this_obj["type"]:
            # make sure bridges are levled on board
            this_cell_height = len(cell_objs)

            if this_obj["type"] == "hbridge":
                other_cell = (x + block_size, y)
            elif this_obj["type"] == "vbridge":
                other_cell = (x, y + block_size)

            x, y = other_cell

            # make sure other cell is on board
            allowed, reason = self.on_board(x // block_size, y // block_size)
            if allowed is False:
                return False, reason

            other_cell_objs = client.get_entire_cell(
                x=x, y=y, block_size=block_size, board="wizard_working"
            )
            other_cell_height = len(other_cell_objs)

            if this_cell_height != other_cell_height:
                return False, "a bridge must be positioned on cells of the same height"

            if other_cell_objs:
                # make sure bridge is not resting on a screw
                valid_placement, reason = self.can_place_on_top(
                    this_obj, other_cell_objs[-1]
                )
                if valid_placement is False:
                    return False, reason
        return True, ""


def new_obj_name(state):
    """
    given a state this function finds a unique numerical
    name for a new object
    """
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


