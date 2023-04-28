# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

from pathlib import Path
import json

ROOT = Path(__file__).parent.resolve()


def task_greeting():
    greeting = Path(f"{ROOT}/data/task_greeting.txt")
    return greeting.read_text().strip().split("\n\n")


def wizard_instr():
    instr = Path(f"{ROOT}/data/instruction_wizard.txt")
    return instr.read_text().strip()


def player_instr():
    instr = Path(f"{ROOT}/data/instruction_player.txt")
    return instr.read_text().strip()


BOARDS = Path(f"{ROOT}/data/boards.jsonl")
BOARDS_PER_ROOM = -1  # -1 to load entire dataset


TIMEOUT_TIMER = 5  # minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 3  # minutes if a user is alone in a room


COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"


TYPES = "https://raw.githubusercontent.com/clp-research/golmi/exp-descrimage/app/descrimage/static/types.png"

# points to give to the users
STARTING_POINTS = 0
POSITIVE_REWARD = 10  # right piece selected
NEGATIVE_REWARD = -5  # wrong piece selected


DEMO_BOARD = json.loads(Path(f"{ROOT}/data/demoboard.json").read_text())
