import json
from pathlib import Path
import copy
import itertools

type_1_connector = json.loads(Path("type-1_connector.json").read_text())
type_2_bridge = json.loads(Path("type-2_bridge.json").read_text())
type_3_screw = json.loads(Path("type-3_screw.json").read_text())

patterns = dict()
pattern_len = dict()
for name, element in [
    ("1conn", type_1_connector),
    ("2brid", type_2_bridge),
    ("3screw", type_3_screw),
]:
    pattern = dict()
    for position, objs in element["objs_grid"].items():
        pattern[position] = [element["objs"][i]["type"] for i in objs]

    flatten = itertools.chain.from_iterable(element["objs_grid"].values())
    n = len(set([i for i in flatten]))

    patterns[name] = pattern
    pattern_len[name] = n

board = json.loads(Path("board.json").read_text())
for coor, cell in board["objs_grid"].items():
    objs = [board["objs"][i]["type"] for i in cell]
    
    for name, pattern in patterns.items():
        if objs in pattern.values():
            for coordinate, part in pattern.items():
                if objs == part:
                    rest_pattern = copy.deepcopy(pattern)
                    rest_pattern.pop(coordinate)

                    if rest_pattern:
                        other_board_cells = dict()
                        for other_c in rest_pattern.keys():
                            other_x, other_y = other_c.split(":")
                            other_x = int(other_x)
                            other_y = int(other_y)
                            
                            this_x, this_y = coordinate.split(":")
                            this_x = int(this_x)
                            this_y = int(this_y)

                            movement = (this_x - other_x, this_y - other_y)
                            board_x, board_y = coor.split(":")
                            board_x = int(board_x)
                            board_y = int(board_y)
                            other_board_coor = f"{board_x + movement[0]}:{board_y + movement[1]}"

                            if other_board_coor in board["objs_grid"]:
                                other_board_cells[other_board_coor] = board["objs_grid"][other_board_coor]

                        board_pattern_named = {coor: objs}
                        board_pattern_ids = {coor: cell}

                        for key, value in other_board_cells.items():
                            board_pattern_named[key] = [board["objs"][i]["type"] for i in value]
                            board_pattern_ids[key] = value

                        if len(board_pattern_named.values()) == len(pattern.values()):
                            board_pieces = list(board_pattern_named.values())
                            pattern_pieces = list(pattern.values())
                            board_pieces.sort()
                            pattern_pieces.sort()

                            if pattern_pieces == board_pieces:
                                flatten = itertools.chain.from_iterable(board_pattern_ids.values())
                                n = len(set([i for i in flatten]))
                                if n == pattern_len[name]:
                                    print(name)

                    else:
                        print(name)
