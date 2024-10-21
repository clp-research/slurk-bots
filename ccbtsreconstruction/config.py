# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import json
from pathlib import Path


ROOT = Path(__file__).parent.resolve()


# instruction and bot messages
INSTRUCTIONS = dict(
    wizard=Path(f"{ROOT}/data/piece_legend.html").read_text().strip(),
)

# base html messages with common colors
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"
SUCCESS_COLOR = "Green"

# various game variables
TIME_LEFT = 60  # how many minutes a user can stay in a room before closing it
BOARDS_PER_ROOM = 20
BOARDS_PER_LEVEL = 2
SEQUENCES_PER_ROOM = 1
MAX_EPISODES_PER_SESSION = 3  # This is used to display in the titlebar to know the number of episodes played in a session

# points system
STARTING_POINTS = 0
POSITIVE_REWARD = 10  # right piece selected
NEGATIVE_REWARD = -5  # wrong piece selected

# timers
TIMEOUT_TIMER = 60
LEAVE_TIMER = 3
WAITING_ROOM_TIMER = 60

# data
# The board width and height to be updated inside the class: QuadrupleClient -> load_config() in golmi_client.py
# Also to be updated in the file selection_state.json
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
#SURVEY = Path(f"{ROOT}/data/survey.html").read_text()
