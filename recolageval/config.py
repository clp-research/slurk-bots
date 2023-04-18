# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

from pathlib import Path

ROOT = Path(__file__).parent.resolve()


def task_greeting():
    greeting = Path(f"{ROOT}/data/task_greeting.txt")
    return greeting.read_text().strip().split("\n\n")


def task_instr():
    instr = Path(f"{ROOT}/data/instruction.txt")
    return instr.read_text().strip()


BOARDS = Path(f"{ROOT}/data/boards.jsonl")
BOARDS_PER_ROOM = 15


TIMEOUT_TIMER = 10  # minutes of inactivity before the room is closed automatically


COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"


TYPES = "https://raw.githubusercontent.com/clp-research/golmi/exp-descrimage/app/descrimage/static/types.png"
