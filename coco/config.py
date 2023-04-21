# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import json
from pathlib import Path
import random

ROOT = Path().resolve() #os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


TASK_GREETING = Path(f"{ROOT}/ccbts/data/task_greeting.txt").read_text().strip().split("\n\n")

INSTRUCTIONS = dict(
    player=Path(f"{ROOT}/ccbts/data/instruction_player.html").read_text().strip(),
    wizard=Path(f"{ROOT}/ccbts/data/instruction_wizard.html").read_text().strip()
)



COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"


TIME_LEFT = 5  # how many minutes a user can stay in a room before closing it


CONFIG = {"width": 7.0, "height": 7.0, "move_step": 1, "prevent_overlap": False}
OBJS = {
    "bridge": {
        "id_n": 0,
        "type": "bridge",
        "x": 0,
        "y": 0,
        "rotation": 0,
        "color": ["red", "#ff0000", [255, 0, 0]],
        "block_matrix": [[1, 1]]
    },
    "nut": {
        "id_n": 0,
        "type": "nut",
        "x": 0,
        "y": 0,
        "rotation": 0,
        "color": ["red", "#ff0000", [255, 0, 0]],
        "block_matrix": [[1]]
    },
    "washer": {
        "id_n": 0,
        "type": "washer",
        "x": 0,
        "y": 0,
        "rotation": 0,
        "color": ["red", "#ff0000", [255, 0, 0]],
        "block_matrix": [[1]]
    },
    "screw": {
        "id_n": 0,
        "type": "screw",
        "x": 0,
        "y": 0,
        "rotation": 0,
        "color": ["red", "#ff0000", [255, 0, 0]],
        "block_matrix": [[1]]
    }
}

COLORS = {
    "green": ["green", "#008000", [0, 128, 0]],
    "red":  ["red", "#ff0000", [255, 0, 0]],
    "yellow" : ["yellow", "#ffa500", [255, 165, 0]],
    "blue": ["blue", "#1b4ccd", [27, 76, 205]]
}


EMPTYSTATE = json.loads(Path(f"{ROOT}/ccbts/data/empty_state.json").read_text())
SELECTIONSTATE = json.loads(Path(f"{ROOT}/ccbts/data/selection_state.json").read_text())
STATES = Path(f"{ROOT}/ccbts/data/states.json")


def get_random_state():
    pool = list()
    with STATES.open(encoding="utf-8") as infile:
        for line in infile:
            pool.append(
                json.loads(line)
            )
        
    return random.choice(pool)


def name_generator():
    """
    make sure objects are placed with increasing id
    """
    n = 0
    while True:
        yield n
        n += 1

NAME_GEN = name_generator()
