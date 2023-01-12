# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

from pathlib import Path

ROOT = Path().resolve() #os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


TASK_GREETING = Path(f"{ROOT}/golmi/data/task_greeting.txt").read_text().strip().split("\n\n")
WIZARD_INSTR = Path(f"{ROOT}/golmi/data/instruction_wizard.txt").read_text().strip()
PLAYER_INSTR = Path(f"{ROOT}/golmi/data/instruction_player.txt").read_text().strip()

BOARDS = Path(f"{ROOT}/golmi/data/boards.jsonl")
BOARDS_PER_ROOM = 10


TIMEOUT_TIMER = 60  # minutes of inactivity before the room is closed automatically


COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"


TYPES = "https://raw.githubusercontent.com/clp-research/golmi/exp-descrimage/app/descrimage/static/types.png"

# points to give to the users
POSITIVE_REWARD = 10  # right piece selected
NEGATIVE_REWARD = 0  # wrong piece selected
