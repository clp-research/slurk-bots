# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import json
from pathlib import Path


ROOT = Path(__file__).parent.resolve()


# instruction and bot messages
TASK_GREETING = Path(f"{ROOT}/data/task_greeting.txt").read_text().strip().split("\n\n")
INSTRUCTIONS = dict(
    player=Path(f"{ROOT}/data/piece_legend.html").read_text().strip(),
    wizard=Path(f"{ROOT}/data/piece_legend.html").read_text().strip(),
)

# base html messages with common colors
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"
SUCCESS_COLOR = "Green"

# various game variables
TIME_LEFT = 5  # how many minutes a user can stay in a room before closing it
BOARDS_PER_ROOM = 20
BOARDS_PER_LEVEL = 2
INSTRUCTION_BASE_LINK = "https://expdata.ling.uni-potsdam.de/cocobot"

# data
CONFIG = {
    "width": 8.0,
    "height": 8.0,
    "move_step": 1,
    "prevent_overlap": False,
}  # golmi config for working boards
EMPTYSTATE = json.loads(
    Path(f"{ROOT}/data/empty_state.json").read_text()
)  # golmi empty state
SELECTIONSTATE = json.loads(
    Path(f"{ROOT}/data/selection_state.json").read_text()
)  # golmi selection state for the wizard
STATES = Path(
    f"{ROOT}/data/sequences"
)  # jsonl file containing all the boards for the bot
RULES = json.loads(
    Path(f"{ROOT}/data/allowed_moves.json").read_text()
)  # file containing placement rules
