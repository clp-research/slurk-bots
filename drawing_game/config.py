# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import os
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

TASK_GREETING = Path(f"{ROOT}/data/task_greeting.txt")

TASK_TITLE = "Describe the grid to your partner and see how what they draw matches."

COMPACT_GRID_INSTANCES = Path(f"{ROOT}/data/compact_grids/")
RANDOM_GRID_INSTANCES = Path(f"{ROOT}/data/random_grids/")

STARTING_POINTS = 0

TIMEOUT_TIMER = 5  # minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 3  # minutes if a user is alone in a room
WAITING_PARTNER_TIMER = 10  # minutes a user waits for a partner

N = 1

GAME_MODE = "one_blind"

SEED = None
# Whether to randomly sample images or present them in linear order.
SHUFFLE = True

with open(Path(f"{ROOT}/data/instr_player_A.html")) as html_f:
    INSTRUCTIONS_A = html_f.read()

with open(Path(f"{ROOT}/data/instr_player_B.html")) as html_f:
    INSTRUCTIONS_B = html_f.read()

with open(Path(f"{ROOT}/data/keyboard_instructions.html")) as html_f:
    KEYBOARD_INSTRUCTIONS = html_f.read()


