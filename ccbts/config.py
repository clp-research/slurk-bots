# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import json
from pathlib import Path

ROOT = Path().resolve() #os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


TASK_GREETING = Path(f"{ROOT}/ccbts/data/task_greeting.txt").read_text().strip().split("\n\n")

INSTRUCTIONS = dict(
    player=Path(f"{ROOT}/ccbts/data/instruction_player.html").read_text().strip(),
    wizard=Path(f"{ROOT}/ccbts/data/instruction_wizard.html").read_text().strip()
)

# IMGS = [image for image in Path(f"{ROOT}/ccbts/data/images").iterdir()]
IMGS = [
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/parallel-bridges.png",
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/square-bridges.png",
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/stack-bridges-nuts.png",
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/stack-nuts-screws.png",
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/stack-nuts-washers-screws.png"
]


COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"


TIME_LEFT = 5  # how many minutes a user can stay in a room before closing it


CONFIG = {"width": 4.0, "height": 4.0, "move_step": 1, "prevent_overlap": False}
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



TESTSTATE = json.loads(Path(f"{ROOT}/ccbts/data/state.json").read_text())