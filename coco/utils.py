import copy
import json
import itertools
from pathlib import Path
from threading import Timer

from .config import *
from .golmi_client import *
from .dataloader import Dataloader


class RoomTimer:
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()
        self.typing_timer = None
        self.left_room = dict()

    def start_timer(self):
        self.timer = Timer(
            TIMEOUT_TIMER * 60, self.function, args=[self.room_id, "timeout"]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.info("reset timer")

    def cancel(self):
        self.timer.cancel()

    def cancel_all_timers(self):
        self.timer.cancel()
        self.typing_timer.cancel()
        for timer in self.left_room.values():
            timer.cancel()

    def user_joined(self, user):
        timer = self.left_room.get(user)
        if timer is not None:
            self.left_room[user].cancel()

    def user_left(self, user):
        self.left_room[user] = Timer(
            LEAVE_TIMER * 60, self.function, args=[self.room_id, "user_left"]
        )
        self.left_room[user].start()


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


class Session:
    def __init__(self):
        self.players = list()
        self.timer = None
        self.golmi_client = None
        self.current_action = ActionNode.new_tree()
        self.states = Dataloader(STATES)
        self.checkpoint = EMPTYSTATE
        self.game_over = False
        self.can_load_next_episode = False
        self.points = 0

    def close(self):
        try:
            self.golmi_client.disconnect()
            self.timer.cancel_all_timers()
        except:
            pass


class SessionManager(dict):
    waiting_room_timers = dict()

    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)


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


# PATTERN DETECTION IS CURRENTLY NOT USED!!
# leaving this code here for future reference
class Pattern(dict):
    """
    this class is a representation of a given
    pattern on a golmi board and is able to detect
    the pattern on any other golmi board with the
    detect method
    """

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
                            other_board_coor = (
                                f"{board_x + movement[0]}:{board_y + movement[1]}"
                            )

                            if other_board_coor in board["objs_grid"]:
                                # get the name of the bjects on the other cell
                                other_board_cells[other_board_coor] = board[
                                    "objs_grid"
                                ][other_board_coor]

                        board_pattern_named = {coor: objs}
                        board_pattern_ids = {coor: cell}

                        # convert other cells from the board from obj_ids to object name
                        for key, value in other_board_cells.items():
                            board_pattern_named[key] = [
                                board["objs"][i]["type"] for i in value
                            ]
                            board_pattern_ids[key] = value

                        if len(board_pattern_named.values()) == len(self.values()):
                            board_pieces = list(board_pattern_named.values())
                            pattern_pieces = list(self.values())
                            board_pieces.sort()
                            pattern_pieces.sort()

                            if pattern_pieces == board_pieces:
                                # we have the same object names, make sure the pattern on the board
                                # is composed by the same number of objects of this pattern
                                flatten = itertools.chain.from_iterable(
                                    board_pattern_ids.values()
                                )
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
