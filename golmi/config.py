# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

from pathlib import Path

ROOT = Path().resolve() #os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def task_greeting():
    greeting = Path(f"{ROOT}/golmi/data/task_greeting.txt")
    return greeting.read_text().strip().split("\n\n")


def wizard_instr():
    instr = Path(f"{ROOT}/golmi/data/instruction_wizard.txt")
    return instr.read_text().strip()


def player_instr():
    instr = Path(f"{ROOT}/golmi/data/instruction_player.txt")
    return instr.read_text().strip()


BOARDS = Path(f"{ROOT}/golmi/data/boards.jsonl")
BOARDS_PER_ROOM = 10


TIMEOUT_TIMER = 10  # minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 5  # minutes if a user is alone in a room


COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"


TYPES = "https://raw.githubusercontent.com/clp-research/golmi/exp-descrimage/app/descrimage/static/types.png"

# points to give to the users
STARTING_POINTS = 0
POSITIVE_REWARD = 50  # right piece selected
NEGATIVE_REWARD = -25  # wrong piece selected
